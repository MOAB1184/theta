import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
from worker import process_job

load_dotenv()

app = FastAPI()

# MongoDB setup
mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
client = MongoClient(mongo_uri)
db = client['theta_summary']
jobs_col = db['jobs']

JOBS_DIR = os.path.abspath('jobs')
os.makedirs(JOBS_DIR, exist_ok=True)

@app.post('/submit_job')
def submit_job(user_id: str, file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(JOBS_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    input_path = os.path.join(job_dir, f'input_{job_id}.audio')
    with open(input_path, 'wb') as f:
        f.write(file.file.read())
    job_doc = {
        'job_id': job_id,
        'user_id': user_id,
        'status': 'queued',
        'input_path': input_path,
        'output_path': None,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
        'log_path': os.path.join(job_dir, f'log_{job_id}.txt')
    }
    jobs_col.insert_one(job_doc)
    process_job.delay(job_id)
    return {'job_id': job_id, 'status': 'queued'}

@app.get('/job_status/{job_id}')
def job_status(job_id: str):
    job = jobs_col.find_one({'job_id': job_id})
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    return {
        'job_id': job['job_id'],
        'status': job['status'],
        'created_at': job['created_at'],
        'updated_at': job['updated_at']
    }

@app.get('/job_result/{job_id}')
def job_result(job_id: str):
    job = jobs_col.find_one({'job_id': job_id})
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    if job['status'] != 'done' or not job.get('output_path'):
        return JSONResponse({'status': job['status'], 'message': 'Not ready'})
    return FileResponse(job['output_path'], filename=os.path.basename(job['output_path'])) 