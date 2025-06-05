import os
import base64
import time
import traceback
from bson import ObjectId
from flask import current_app
from pymongo import MongoClient
import google.generativeai as genai

MONGO_URI = os.getenv('MONGO_URI')
MONGO_DBNAME = os.getenv('MONGO_DBNAME')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
WASABI_BUCKET_NAME = os.getenv('WASABI_BUCKET_NAME')

client = MongoClient(MONGO_URI)
db = client[MONGO_DBNAME]
jobs_col = db.jobs

def process_transcription_job(audio_base64, mime_type, class_id, user_id, username):
    try:
        if not audio_base64 or not mime_type:
            return {'status': 'error', 'message': 'Missing audio data or mime_type.'}
        if not GEMINI_API_KEY:
            return {'status': 'error', 'message': 'Gemini API key not configured.'}
        audio_bytes = base64.b64decode(audio_base64)
        transcription_prompt = 'Please transcribe this audio exactly as it is. Do not add any additional text or formatting.'
        gemini_model = genai.GenerativeModel('gemini-2.0-flash-lite')
        audio_part = {'mime_type': mime_type, 'data': audio_bytes}
        gemini_response = gemini_model.generate_content([audio_part, transcription_prompt])
        transcript = gemini_response.text
        timestamp = str(int(time.time()))
        recording_filename = f"recording_{timestamp}.txt"
        transcript_filename = f"transcript_{timestamp}.txt"
        # Save job result in MongoDB
        job_doc = {
            'user_id': user_id,
            'username': username,
            'class_id': class_id,
            'timestamp': timestamp,
            'transcript': transcript,
            'transcript_filename': transcript_filename,
            'status': 'done',
            'created_at': time.time()
        }
        jobs_col.insert_one(job_doc)
        return {
            'status': 'success',
            'transcript': transcript,
            'transcript_filename': transcript_filename,
            'timestamp': timestamp
        }
    except Exception as e:
        return {'status': 'error', 'message': f'Error processing: {str(e)}', 'trace': traceback.format_exc()} 