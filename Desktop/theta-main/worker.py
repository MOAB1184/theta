import os
import time
from celery import Celery
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
import google.generativeai as genai
import openai
import base64
import requests

load_dotenv()

celery_app = Celery('worker', broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'))

mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
client = MongoClient(mongo_uri)
db = client['theta_summary']
jobs_col = db['jobs']

JOBS_DIR = os.getenv('JOBS_DIR', os.path.abspath('jobs'))

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_URL = os.getenv('DEEPSEEK_URL', 'https://api.deepseek.com/v1')
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-reasoner')

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

if not DEEPSEEK_API_KEY:
    print("Warning: DEEPSEEK_API_KEY not set")

def log_job(job_id, message):
    job = jobs_col.find_one({'job_id': job_id})
    if not job:
        return
    log_path = job.get('log_path')
    if log_path:
        with open(log_path, 'a') as f:
            f.write(f"[{datetime.utcnow()}] {message}\n")

@celery_app.task
def process_job(job_id):
    job = jobs_col.find_one({'job_id': job_id})
    if not job:
        return
    job_dir = os.path.dirname(job['input_path'])
    input_path = job['input_path']
    transcript_path = os.path.join(job_dir, f'transcript_{job_id}.txt')
    summary_path = os.path.join(job_dir, f'summary_{job_id}.txt')
    try:
        jobs_col.update_one({'job_id': job_id}, {'$set': {'status': 'processing', 'updated_at': datetime.utcnow()}})
        log_job(job_id, 'Started processing')
        # 1. Transcribe with Gemini
        with open(input_path, 'rb') as f:
            audio_bytes = f.read()
        gemini_model = genai.GenerativeModel('gemini-2.0-flash-lite')
        audio_part = {
            'mime_type': 'audio/wav',  # You may want to detect or store the real mime type
            'data': audio_bytes
        }
        gemini_response = gemini_model.generate_content([audio_part, "Please transcribe this audio."])
        transcript = gemini_response.text
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(transcript)
        log_job(job_id, 'Transcription complete')
        # 2. Summarize with DeepSeek
        prompt = "Please summarize this transcript for a student. Transcript: " + transcript
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": DEEPSEEK_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        
        print(f"Making request to {DEEPSEEK_URL}/chat/completions")
        response = requests.post(
            f"{DEEPSEEK_URL}/chat/completions",
            headers=headers,
            json=data,
            timeout=300
        )
        
        if response.status_code != 200:
            error_msg = f"API request failed with status {response.status_code}: {response.text}"
            print(error_msg)
            raise Exception(error_msg)
            
        result = response.json()
        summary = result['choices'][0]['message']['content']
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary)
        log_job(job_id, 'Summarization complete')
        jobs_col.update_one({'job_id': job_id}, {'$set': {
            'status': 'done',
            'output_path': summary_path,
            'transcript_path': transcript_path,
            'updated_at': datetime.utcnow()
        }})
    except Exception as e:
        log_job(job_id, f'Error: {e}')
        jobs_col.update_one({'job_id': job_id}, {'$set': {'status': 'error', 'error': str(e), 'updated_at': datetime.utcnow()}}) 