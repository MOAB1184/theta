import os
import base64
import google.generativeai as genai

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
AUDIO_FILE = 'test_audio.m4a'  # Place your test file in the same directory
MIME_TYPE = 'audio/m4a'

if not GEMINI_API_KEY:
    print('GEMINI_API_KEY not set!')
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)

def main():
    with open(AUDIO_FILE, 'rb') as f:
        audio_bytes = f.read()
    print(f'Loaded audio file: {AUDIO_FILE}, size: {len(audio_bytes)} bytes')
    transcription_prompt = 'Please transcribe this audio exactly as it is. Do not add any additional text or formatting.'
    gemini_model = genai.GenerativeModel('gemini-2.0-flash-lite')
    audio_part = {'mime_type': MIME_TYPE, 'data': audio_bytes}
    try:
        print('Sending to Gemini API...')
        response = gemini_model.generate_content([audio_part, transcription_prompt])
        print('Gemini API call completed.')
        print('Transcript:')
        print(response.text)
    except Exception as e:
        print('Gemini API error:', e)

if __name__ == '__main__':
    main() 