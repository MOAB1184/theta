import os
import base64
import time
import traceback
from bson import ObjectId
from flask import current_app
from pymongo import MongoClient
import google.generativeai as genai
import logging
import signal
import math
from pydub import AudioSegment
import tempfile

MONGO_URI = os.getenv('MONGO_URI')
MONGO_DBNAME = os.getenv('MONGO_DBNAME')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
WASABI_BUCKET_NAME = os.getenv('WASABI_BUCKET_NAME')

client = MongoClient(MONGO_URI)
db = client[MONGO_DBNAME]
jobs_col = db.jobs

logger = logging.getLogger(__name__)

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException('Gemini API call timed out')

def transcribe_chunk(chunk_bytes, mime_type):
    transcription_prompt = 'Please transcribe this audio exactly as it is. Do not add any additional text or formatting.'
    gemini_model = genai.GenerativeModel('gemini-2.0-flash-lite')
    audio_part = {'mime_type': mime_type, 'data': chunk_bytes}
    try:
        response = gemini_model.generate_content([audio_part, transcription_prompt])
        return response.text
    except Exception as e:
        logger.error(f'Gemini API error: {e}\n{traceback.format_exc()}')
        return ''

CHUNK_LENGTH_MS = 2 * 60 * 1000  # 2 minutes

def process_transcription_job(audio_base64, mime_type, class_id, user_id, username):
    try:
        if not audio_base64 or not mime_type:
            return {'status': 'error', 'message': 'Missing audio data or mime_type.'}
        if not GEMINI_API_KEY:
            return {'status': 'error', 'message': 'Gemini API key not configured.'}
        audio_bytes = base64.b64decode(audio_base64)
        # Write to temp file for chunking
        with tempfile.NamedTemporaryFile(suffix='.audio', delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            tmp_path = tmp.name
        audio = AudioSegment.from_file(tmp_path)
        os.remove(tmp_path)
        num_chunks = math.ceil(len(audio) / CHUNK_LENGTH_MS)
        logger.info(f'Audio length: {len(audio)} ms, {num_chunks} chunks')
        full_transcript = ''
        for i in range(num_chunks):
            start = i * CHUNK_LENGTH_MS
            end = min((i + 1) * CHUNK_LENGTH_MS, len(audio))
            chunk = audio[start:end]
            with tempfile.NamedTemporaryFile(suffix='.audio', delete=False) as chunk_tmp:
                chunk.export(chunk_tmp.name, format=mime_type.split('/')[-1])
                chunk_tmp.seek(0)
                chunk_bytes = chunk_tmp.read()
            logger.info(f'Transcribing chunk {i+1}/{num_chunks}...')
            transcript = transcribe_chunk(chunk_bytes, mime_type)
            logger.info(f'Chunk {i+1} transcript length: {len(transcript)}')
            full_transcript += transcript + '\n'
            os.remove(chunk_tmp.name)
        timestamp = str(int(time.time()))
        recording_filename = f"recording_{timestamp}.txt"
        transcript_filename = f"transcript_{timestamp}.txt"
        # Save job result in MongoDB
        job_doc = {
            'user_id': user_id,
            'username': username,
            'class_id': class_id,
            'timestamp': timestamp,
            'transcript': full_transcript,
            'transcript_filename': transcript_filename,
            'status': 'done',
            'created_at': time.time()
        }
        jobs_col.insert_one(job_doc)
        return {
            'status': 'success',
            'transcript': full_transcript,
            'transcript_filename': transcript_filename,
            'timestamp': timestamp
        }
    except Exception as e:
        logger.error(f'Error in process_transcription_job: {e}\n{traceback.format_exc()}')
        return {'status': 'error', 'message': f'Error processing: {str(e)}', 'trace': traceback.format_exc()} 