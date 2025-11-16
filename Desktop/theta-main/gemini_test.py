import os
import math
from pydub import AudioSegment
import google.generativeai as genai
import tempfile

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
AUDIO_FILE = 'test_audio.m4a'
MIME_TYPE = 'audio/m4a'
CHUNK_LENGTH_MS = 2 * 60 * 1000  # 2 minutes

if not GEMINI_API_KEY:
    print('GEMINI_API_KEY not set!')
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)

def transcribe_chunk(chunk_bytes):
    transcription_prompt = 'Please transcribe this audio exactly as it is. Do not add any additional text or formatting.'
    gemini_model = genai.GenerativeModel('gemini-2.0-flash-lite')
    audio_part = {'mime_type': MIME_TYPE, 'data': chunk_bytes}
    try:
        response = gemini_model.generate_content([audio_part, transcription_prompt])
        return response.text
    except Exception as e:
        print('Gemini API error:', e)
        return ''

def main():
    audio = AudioSegment.from_file(AUDIO_FILE)
    num_chunks = math.ceil(len(audio) / CHUNK_LENGTH_MS)
    print(f'Loaded audio file: {AUDIO_FILE}, size: {len(audio)} ms, {num_chunks} chunks')
    full_transcript = ''
    for i in range(num_chunks):
        start = i * CHUNK_LENGTH_MS
        end = min((i + 1) * CHUNK_LENGTH_MS, len(audio))
        chunk = audio[start:end]
        with tempfile.NamedTemporaryFile(suffix='.m4a', delete=False) as tmp:
            chunk.export(tmp.name, format='m4a')
            tmp.seek(0)
            chunk_bytes = tmp.read()
        print(f'Transcribing chunk {i+1}/{num_chunks}...')
        transcript = transcribe_chunk(chunk_bytes)
        print(f'Chunk {i+1} transcript length: {len(transcript)}')
        full_transcript += transcript + '\n'
        os.remove(tmp.name)
    print('Full transcript:')
    print(full_transcript)

if __name__ == '__main__':
    main() 