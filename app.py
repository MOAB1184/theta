from flask import Flask, render_template, redirect, url_for, request, jsonify, send_file, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import time
import openai
import base64
import json
from tempfile import NamedTemporaryFile
import google.generativeai as genai
import datetime
import re
from dotenv import load_dotenv
import stripe
import random
import string
from stripe.error import SignatureVerificationError
import boto3
from botocore.exceptions import ClientError
from flask_pymongo import PyMongo
from bson.objectid import ObjectId

# Try to load environment variables from .env file
try:
    load_dotenv()
    print("Successfully loaded .env file")
except Exception as e:
    print(f"Error loading .env file: {e}. Using environment variables if available.")

# Define base data directory for all storage
BASE_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'local_data'))
os.makedirs(BASE_DATA_DIR, exist_ok=True)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'thetasummary-secret-key'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=7)  # Sessions last 7 days
app.config['SESSION_PERMANENT'] = True

# Use absolute path for SQLite database in /tmp for Vercel compatibility
# DB_DIR = os.path.join(BASE_DATA_DIR, 'database')
# os.makedirs(DB_DIR, exist_ok=True)
db_path = '/tmp/users.db'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

# Configure user files directory
USER_FILES_DIR = os.path.join(BASE_DATA_DIR, 'user_files')

# Update UPLOAD_FOLDER to use Wasabi
app.config['UPLOAD_FOLDER'] = os.getenv('WASABI_BUCKET_NAME')

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Global prompt management using MongoDB

def get_global_prompt():
    doc = mongo.db.settings.find_one({'_id': 'global_prompt'})
    if doc and 'prompt_text' in doc:
        return doc['prompt_text']
    return BASE_PROMPT

def save_global_prompt(prompt_text):
    mongo.db.settings.update_one(
        {'_id': 'global_prompt'},
        {'$set': {'prompt_text': prompt_text}},
        upsert=True
    )

# Configure Deepseek
DEEPSEEK_MODEL = "deepseek-reasoner"
DEEPSEEK_URL = "https://api.deepseek.com/v1"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Configure Deepseek client
deepseek_client = openai.OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_URL,
)

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Base Prompt that handles subject detection and formatting
BASE_PROMPT = """
Please analyze this transcript and determine the subject. Then, summarize it according to the appropriate template below:

FOR MATHEMATICS:
Please summarize this class transcript in the following manner:
Section 1: Key Formulas and Their Use Cases
Formulas (at least 200 words):
List all the formulas explicitly mentioned in the class.
For each formula, provide a brief explanation of its components.
Then, describe the use case of each formula with a practical example or scenario where it would be applied.

Section 2: Example Problems and Solutions
Provide 4 example problems and solve each one step-by-step.
For each problem, include the following:
State the problem/question clearly.
Show the solution process step by step, using mathematical notation.
Provide a clear English explanation of each step, describing the logic behind the operation.
Include the final answer explicitly at the end of each problem.
You don't have to use examples from the lecture and can use your own.

FOR SOCIAL STUDIES:
Please summarize this social studies class transcript in the following manner:
Section 1: Key Concepts and Terms
Definitions and Key Terms (at least 200 words):
List and define all the key terms, figures, events, and concepts discussed in the class.
Explain their significance in the context of the subject matter, such as history, geography, government, or economics.

Section 2: Historical Events and Timelines
Historical Overview:
Identify and summarize the major historical events or movements covered in the class.
Provide a timeline (if applicable) of significant events and their impact on the world or a specific region.
Explain the cause and effect relationships between events.

Section 3: Case Studies and Examples
Provide 4 case studies or examples and explain their importance:
For each case study or example:
Describe the event or concept.
Explain why it is important in the context of social studies (e.g., historical significance, social change, political impact).
Relate it to the broader themes of the class (e.g., governance, cultural shifts, or economic development).

Section 4: Application to Modern Society
Modern-Day Relevance (at least 200 words):
Discuss how the concepts and events discussed in class are relevant to today's world.
Provide real-world examples of how these concepts are still influencing modern society, such as politics, economics, or culture.

FOR SCIENCE:
Please summarize this science class transcript in the following manner:
Section 1: Key Concepts and Definitions
Definitions (at least 200 words):
List and define all the key scientific concepts, terms, and theories discussed in the class.
Provide clear, concise definitions for each term or concept.
Include explanations of why these concepts are important in the scientific field being discussed.

Section 2: Key Formulas and Their Use Cases
Formulas (if applicable):
List any formulas that were mentioned in the class.
Explain each formula, breaking down its components.
Provide real-world use cases or examples where these formulas are applied.

Section 3: Example Problems and Solutions
Provide 4 example problems and solve each one step-by-step.
For each problem:
State the problem/question clearly.
Show the solution process step-by-step, including all relevant calculations or reasoning.
Explain each step in simple English to ensure the concept is understood.
Present the final answer at the end of each problem.

Section 4: Real-World Applications
Real-World Connections (at least 200 words):
Explain how the scientific concepts or theories discussed in the class are applied in the real world.
Provide examples of industries, technologies, or situations where these concepts are directly relevant.

FOR OTHER SUBJECTS (Default):
Please summarize this class transcript in the following manner:
Section 1: Key Concepts and Definitions
Definitions (at least 200 words):
List and define all the important concepts, theories, or key terms discussed in the class.
Provide a clear, concise explanation for each concept or term.
Explain why each concept is important in the context of the subject, and provide any related examples or applications.

Section 2: Key Ideas and Theories
Theories and Frameworks:
Summarize the key ideas or frameworks introduced during the class.
For each theory or concept, explain its significance and how it contributes to the subject's field.

Section 3: Example Problems and Applications
Provide 4 example problems, exercises, or applications and solve each one step-by-step (if applicable):
For each example:
State the problem or scenario clearly.
Show how to solve the problem or approach the situation step-by-step.
Explain each step in simple English, ensuring the reasoning is clear.
Provide the final result or outcome explicitly.

Section 4: Practical Applications or Case Studies
Real-World Applications (at least 200 words):
Discuss how the concepts, theories, or key ideas from the class apply to real-world scenarios.
Provide examples or case studies where the subject matter is used in practical situations, whether in industry, technology, or day-to-day life.

Section 5: Key Takeaways and Summary
Key Takeaways:
Summarize the most important lessons or insights gained from the class.
Highlight how these takeaways can be applied in future studies or professional settings.

Transcript:
"""

# LATEX Prompt for when LaTeX format is explicitly requested
LATEX_PROMPT = """
Please analyze this transcript and create a comprehensive LaTeX summary. Structure the output as a proper LaTeX document with:

\\documentclass{article}
\\usepackage[utf8]{inputenc}
\\usepackage{amsmath}
\\begin{document}

Focus on:
1. Key historical events and their significance
2. Important concepts and terminology
3. Cause-effect relationships
4. Modern implications and relevance

Format using proper LaTeX sections (\\section{}, \\subsection{}), bullet points (\\begin{itemize}), and emphasis (\\textbf{}, \\emph{}) where appropriate.

If this is a mathematics transcript, please include a section with 4 example questions, showing all steps and explanations for each solution.

End with \\end{document}

Ensure all special characters are properly escaped.

Transcript:
"""

# Use BASE_PROMPT as default
DEFAULT_GLOBAL_PROMPT = BASE_PROMPT

# Initialize Wasabi S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('WASABI_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('WASABI_SECRET_ACCESS_KEY'),
    endpoint_url=os.getenv('WASABI_ENDPOINT'),
    region_name=os.getenv('WASABI_REGION')
)

# MongoDB config
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
app.config["MONGO_DBNAME"] = os.getenv("MONGO_DBNAME")
mongo = PyMongo(app)

print("MONGO_URI:", app.config["MONGO_URI"])
print("mongo:", mongo)
print("mongo.db:", mongo.db)

# Helper functions for user, class, and school management

def get_user_by_username(username):
    return mongo.db.users.find_one({"username": username})

def create_user(username, password_hash, role, is_admin=False, school_id=None):
    user = {
        "username": username,
        "password_hash": password_hash,
        "role": role,
        "is_admin": is_admin,
        "school_id": ObjectId(school_id) if school_id else None,
        "subscribed": False
    }
    return mongo.db.users.insert_one(user)

def get_school_by_id(school_id):
    return mongo.db.schools.find_one({"_id": ObjectId(school_id)})

def get_all_schools():
    return list(mongo.db.schools.find())

def create_school(name, district, state):
    return mongo.db.schools.insert_one({"name": name, "district": district, "state": state})

# Authentication routes using MongoDB
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    schools = get_all_schools()

    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            role = request.form.get('role')
            school_id = request.form.get('school_id') if role == 'teacher' else None

            if not role or role not in ['student', 'teacher']:
                            return render_template('register.html', error='Invalid role selected', username=username, schools=schools)

            if role == 'teacher' and not school_id:
                            return render_template('register.html', error='Please select a school.', username=username, role=role, schools=schools)

            existing_user = get_user_by_username(username)
            if existing_user:
                            return render_template('register.html', error='Username already exists', role=role, username=username, schools=schools)

            password_hash = generate_password_hash(password)
            if role == 'teacher':
                            # Add to pending_teachers for admin approval
                            teacher = {
                                "username": username,
                                "password_hash": password_hash,
                                "role": role,
                                "is_admin": False,
                                "school_id": ObjectId(school_id) if school_id else None,
                                "subscribed": False
                            }
                            mongo.db.pending_teachers.insert_one(teacher)
                            return render_template('register.html', error='Teacher account request sent! Waiting for admin approval.', schools=schools)
            else:
                            create_user(username, password_hash, role, is_admin=False, school_id=school_id)
                            user = get_user_by_username(username)
                            session['user_id'] = str(user['_id'])
                            session['username'] = user['username']
                            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        except Exception as e:
            import traceback
            error_message = f"REGISTER ERROR: {e}<br><pre>{traceback.format_exc()}</pre>"
            return render_template('register.html', error=error_message, username=request.form.get('username'), role=request.form.get('role'), schools=schools)
    return render_template('register.html', role='student', schools=schools)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = get_user_by_username(username)
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid username or password', username=username)
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Main routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    if not user:
        return redirect(url_for('logout'))
    users = list(mongo.db.users.find())
    class_data = []
    if user['role'] == 'teacher':
        classes = list(mongo.db.classes.find({"teacher_id": user['_id']}))
        for class_obj in classes:
            class_code = class_obj.get('class_code')
            class_dir = f"{user['username']}/classes/{class_code}"
            summary_count = 0
            recording_count = 0
            transcript_count = 0
            try:
                response = s3_client.list_objects_v2(Bucket=os.getenv('WASABI_BUCKET_NAME'), Prefix=class_dir)
                if 'Contents' in response:
                    for obj in response['Contents']:
                        key = obj['Key']
                        if key.startswith(f"{class_dir}/summary_"):
                            summary_count += 1
                        elif key.startswith(f"{class_dir}/recording_"):
                            recording_count += 1
                        elif key.startswith(f"{class_dir}/transcript_"):
                            transcript_count += 1
            except Exception as e:
                print(f"Error counting files for class {class_code}: {e}")
            class_obj['summary_count'] = summary_count
            class_obj['recording_count'] = recording_count
            class_obj['transcript_count'] = transcript_count
            class_data.append(class_obj)
        return render_template('dashboard.html', 
                             classes=class_data, 
                             user_role=user['role'], 
                             is_admin=user.get('is_admin', False),
                             username=user['username'],
                             users=users)
    else:
        # Students see only their enrolled classes
        enrolled_class_ids = user.get('enrolled_classes', [])
        classes = list(mongo.db.classes.find({"_id": {"$in": enrolled_class_ids}})) if enrolled_class_ids else []
        for class_obj in classes:
            class_code = class_obj.get('class_code')
            class_dir = f"{user['username']}/classes/{class_code}"
            summary_count = 0
            recording_count = 0
            transcript_count = 0
            try:
                response = s3_client.list_objects_v2(Bucket=os.getenv('WASABI_BUCKET_NAME'), Prefix=class_dir)
                if 'Contents' in response:
                    for obj in response['Contents']:
                        key = obj['Key']
                        if key.startswith(f"{class_dir}/summary_"):
                            summary_count += 1
                        elif key.startswith(f"{class_dir}/recording_"):
                            recording_count += 1
                        elif key.startswith(f"{class_dir}/transcript_"):
                            transcript_count += 1
            except Exception as e:
                print(f"Error counting files for class {class_code}: {e}")
            class_obj['summary_count'] = summary_count
            class_obj['recording_count'] = recording_count
            class_obj['transcript_count'] = transcript_count
            class_data.append(class_obj)
        return render_template('dashboard.html', 
                             classes=class_data, 
                             user_role=user['role'], 
                             is_admin=user.get('is_admin', False),
                             username=user['username'],
                             users=users)

@app.route('/recordings')
def recordings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    if not user:
        return redirect(url_for('logout'))
    
    # Get user's classes
    if user['role'] == 'teacher':
        classes = list(mongo.db.classes.find({"teacher_id": user['_id']}))
    else:
        enrolled_class_ids = user.get('enrolled_classes', [])
        classes = list(mongo.db.classes.find({"_id": {"$in": enrolled_class_ids}})) if enrolled_class_ids else []
    
    return render_template('recordings.html', 
                         classes=classes,
                         username=user['username'])

@app.route('/summaries')
def summaries():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    if not user:
        return redirect(url_for('logout'))
        
    summary_files_data = []
    
    # Get user-specific summaries
    user_summaries_dir = os.path.join(app.config['UPLOAD_FOLDER'], session['username'], session['role'], 'summaries')
    if os.path.exists(user_summaries_dir):
        for filename in os.listdir(user_summaries_dir):
            if filename.startswith('summary_'):
                timestamp_str = filename.split('_')[1].split('.')[0]
                filepath = os.path.join(user_summaries_dir, filename)
                preview = 'Preview unavailable'
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        preview_content = f.read(200)
                        preview = ' '.join(preview_content.split())
                        if len(preview_content) >= 200:
                            preview += '...'
                except Exception as e:
                    print(f"Error reading preview for {filename}: {e}")
                
                date_str = 'Unknown date'
                try:
                    date_obj = datetime.datetime.fromtimestamp(int(timestamp_str))
                    date_str = date_obj.strftime('%Y-%m-%d %H:%M')
                except ValueError:
                    print(f"Could not parse timestamp: {timestamp_str} for file {filename}")
                
                summary_files_data.append({
                    'filename': filename,
                    'date': date_str,
                    'preview': preview,
                    'class_name': None
                })
    
    # Get class-specific summaries
    classes = []
    if session['role'] == 'teacher':
        classes = mongo.db.classes.find({"teacher_id": session['user_id']})
    elif session['role'] == 'student':
        classes = mongo.db.classes.find({"students": session['user_id']})
    
    for class_obj in classes:
        class_summaries_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'class_summaries', str(class_obj['_id']))
        if os.path.exists(class_summaries_dir):
            for filename in os.listdir(class_summaries_dir):
                if filename.startswith('summary_'):
                    timestamp_str = filename.split('_')[1].split('.')[0]
                    filepath = os.path.join(class_summaries_dir, filename)
                    preview = 'Preview unavailable'
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            preview_content = f.read(200)
                            preview = ' '.join(preview_content.split())
                            if len(preview_content) >= 200:
                                preview += '...'
                    except Exception as e:
                        print(f"Error reading preview for {filename}: {e}")
                    
                    date_str = 'Unknown date'
                    try:
                        date_obj = datetime.datetime.fromtimestamp(int(timestamp_str))
                        date_str = date_obj.strftime('%Y-%m-%d %H:%M')
                    except ValueError:
                        print(f"Could not parse timestamp: {timestamp_str} for file {filename}")
                    
                    summary_files_data.append({
                        'filename': filename,
                        'date': date_str,
                        'preview': preview,
                        'class_name': class_obj['name']
                    })
    
    summary_files_data.sort(key=lambda x: x['date'], reverse=True)
    return render_template('summaries.html', 
                         summaries=summary_files_data,
                         username=user['username'])

@app.route('/api/transcribe', methods=['POST'])
def transcribe():
    try:
        audio_base64 = request.json.get('audio_base64')
        mime_type = request.json.get('mime_type')
        class_id = request.json.get('class_id')

        if not audio_base64 or not mime_type:
            return jsonify({'status': 'error', 'message': "Missing audio data or mime_type."}), 400
        
        if not GEMINI_API_KEY:
            return jsonify({'status': 'error', 'message': "Gemini API key not configured. Please set the GEMINI_API_KEY environment variable."}), 500
            
        print("Decoding audio and using Gemini for transcription...")
        
        try:
            audio_bytes = base64.b64decode(audio_base64)
        except Exception as e:
            print(f"Error decoding base64 audio: {e}")
            return jsonify({'status': 'error', 'message': f"Invalid audio data: {str(e)}"}), 400

        transcription_prompt = "Please transcribe this audio."
        
        try:
            gemini_model = genai.GenerativeModel('gemini-1.5-flash')  # Changed to gemini-1.5-flash
            audio_part = {
                'mime_type': mime_type,
                'data': audio_bytes
            }
            gemini_response = gemini_model.generate_content([audio_part, transcription_prompt])
            transcript = gemini_response.text
        except Exception as e:
            print(f"Gemini API error: {e}")
            if "API key not valid" in str(e) or "API_KEY_INVALID" in str(e):
                return jsonify({'status': 'error', 'message': "Gemini API key is invalid. Please check configuration."}), 500
            if "model not found" in str(e).lower() or "model unavailable" in str(e).lower():
                return jsonify({'status': 'error', 'message': "Gemini 1.5 Flash model unavailable. Please check model availability or try gemini-1.5-flash-8b."}), 500
            if hasattr(e, 'response') and hasattr(e.response, 'prompt_feedback'):
                if e.response.prompt_feedback.block_reason:
                    reason = e.response.prompt_feedback.block_reason
                    return jsonify({'status': 'error', 'message': f"Transcription failed due to content policy: {reason}."}), 400
            return jsonify({'status': 'error', 'message': f"Error with Gemini API: {str(e)}"}), 500

        # Create directories and save transcript
        timestamp = str(int(time.time()))
        recording_filename = f"recording_{timestamp}.txt"
        transcript_filename = f"transcript_{timestamp}.txt"
            
        if class_id:
            # Save to class directory under user's directory
            class_obj = mongo.db.classes.find_one({"_id": ObjectId(class_id)})
            if not class_obj:
                return jsonify({'status': 'error', 'message': 'Class not found'}), 404
            # Verify user access
            if session['role'] == 'teacher' and class_obj['teacher_id'] != ObjectId(session['user_id']):
                return jsonify({'status': 'error', 'message': 'Unauthorized access to class'}), 403
            elif session['role'] == 'student' and ObjectId(session['user_id']) not in class_obj.get('students', []):
                return jsonify({'status': 'error', 'message': 'Unauthorized access to class'}), 403
            
            class_dir = f"{session['username']}/classes/{class_obj['class_code']}"
            recording_path = f"{class_dir}/{recording_filename}"
            transcript_path = f"{class_dir}/{transcript_filename}"
        else:
            # Save to user's personal directory
            user_dir = f"{session['username']}"
            recording_path = f"{user_dir}/{recording_filename}"
            transcript_path = f"{user_dir}/{transcript_filename}"

        # Save received base64 audio and real transcript to Wasabi
        s3_client.put_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=recording_path, Body=audio_base64)
        s3_client.put_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=transcript_path, Body=transcript)
            
        return jsonify({
            'status': 'success',
            'transcript': transcript,
            'transcript_filename': transcript_filename,
            'timestamp': timestamp
        })
                
    except Exception as e:
        print(f"Error in transcribe endpoint: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Error processing: {str(e)}"
        }), 500

@app.route('/api/summarize', methods=['POST'])
def summarize():
    try:
        transcript = request.json.get('transcript')
        timestamp = request.json.get('timestamp')
        class_id = request.json.get('class_id')
        if not transcript or not timestamp:
            return jsonify({'status': 'error', 'message': "Missing transcript or timestamp"}), 400
        if not DEEPSEEK_API_KEY:
            return jsonify({'status': 'error', 'message': "Deepseek API key not configured. Please set the DEEPSEEK_API_KEY environment variable."}), 500
        
        # Get the global prompt from MongoDB
        summarization_prompt_template = get_global_prompt()
        if not summarization_prompt_template.strip().endswith("Transcript:"):
            full_summarization_prompt = summarization_prompt_template + "\n\nTranscript:\n" + transcript
        else:
            full_summarization_prompt = summarization_prompt_template + transcript

        print("Using Deepseek for summarization...")
        try:
            summary_resp = deepseek_client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[{"role": "user", "content": full_summarization_prompt}],
                stream=False
            )
            summary = summary_resp.choices[0].message.content
            subject = detect_subject(summary)
        except Exception as e:
            print(f"Deepseek API error: {e}")
            if "authenticate" in str(e).lower() or "authorization" in str(e).lower():
                return jsonify({'status': 'error', 'message': "Deepseek API key is invalid. Please check configuration."}), 500
            return jsonify({'status': 'error', 'message': f"Error with Deepseek API: {str(e)}"}), 500
        
        # Save the summary
        summary_filename = f"summary_{timestamp}.txt"
        summary_path = None
        if class_id:
            # Save to class directory under teacher's directory
            class_obj = mongo.db.classes.find_one({"_id": ObjectId(class_id)})
            if not class_obj:
                return jsonify({'status': 'error', 'message': 'Class not found'}), 404
            teacher = mongo.db.users.find_one({"_id": class_obj['teacher_id']})
            class_dir = f"{teacher['username']}/classes/{class_obj['class_code']}"
            summary_path = f"{class_dir}/{summary_filename}"
            s3_client.put_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=summary_path, Body=summary)
            # Add to DB if not already present
            mongo.db.classes.update_one(
                {"_id": ObjectId(class_id)},
                {"$addToSet": {"summaries": {
                    "filename": summary_filename,
                    "created_at": datetime.datetime.utcnow(),
                    "approved": False
                }}}
            )
        else:
            # Save to user's personal directory
            user_dir = f"{session['username']}"
            summary_path = f"{user_dir}/{summary_filename}"
            s3_client.put_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=summary_path, Body=summary)
        return jsonify({
            'status': 'success',
            'summary': summary,
            'summary_filename': summary_filename,
            'subject': subject
        })
    except Exception as e:
        print(f"Error in summarize endpoint: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Error processing: {str(e)}"
        }), 500

def detect_subject(summary_text):
    """Detect the likely subject based on summary content"""
    # Simple keyword-based subject detection
    subject_keywords = {
        "Mathematics": ["equation", "formula", "theorem", "math", "calculus", "algebra", "geometry", "solve for", "equals", "variable", "function", "graph", "polynomial"],
        "Science": ["experiment", "lab", "hypothesis", "theory", "biology", "physics", "chemistry", "reaction", "molecule", "atom", "cell", "enzyme", "ecosystem"],
        "Social Studies": ["history", "geography", "economics", "government", "civilization", "politics", "society", "culture", "war", "revolution", "president", "country", "nation"],
        "Literature": ["novel", "poetry", "author", "character", "theme", "literary", "shakespeare", "poem", "fiction", "narrative", "symbolism", "metaphor"]
    }
    
    # Count keyword occurrences for each subject
    subject_scores = {subject: 0 for subject in subject_keywords}
    for subject, keywords in subject_keywords.items():
        for keyword in keywords:
            # Case insensitive search
            pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
            matches = pattern.findall(summary_text)
            subject_scores[subject] += len(matches)
    
    # Return the subject with the highest score, or "General" if no keywords match
    max_subject = max(subject_scores.items(), key=lambda x: x[1])
    if max_subject[1] > 0:
        return max_subject[0]
    else:
        return "General"

@app.route('/api/check_file', methods=['POST'])
def check_file():
    try:
        filename = request.json.get('filename')
        if not filename or not filename.startswith('summary_'):
            return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
        
        # Check user-specific summaries
        user_summaries_dir = f"{session['username']}/{session['role']}/summaries"
        user_file_path = f"{user_summaries_dir}/{filename}"
        try:
            s3_client.head_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=user_file_path)
            return jsonify({'status': 'success', 'exists': True, 'path': 'user'})
        except ClientError:
            pass
        
        # Check class-specific summaries
        classes = mongo.db.classes.find({"teacher_id": session['user_id']})
        for class_obj in classes:
            class_summaries_dir = f"class_summaries/{class_obj['_id']}"
            class_file_path = f"{class_summaries_dir}/{filename}"
            try:
                s3_client.head_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=class_file_path)
                return jsonify({'status': 'success', 'exists': True, 'path': 'class', 'class_id': class_obj['_id']})
            except ClientError:
                pass
        
        return jsonify({'status': 'success', 'exists': False}), 200
    except Exception as e:
        print(f"Error in check_file endpoint: {str(e)}")
        return jsonify({'status': 'error', 'message': f"Error checking file: {str(e)}"}), 500

@app.route('/view_summary/<filename>')
def view_summary(filename):
    if not filename.startswith('summary_'):
        return "Invalid file type for this view.", 400

    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    if not user:
        return redirect(url_for('logout'))

    # Check user-specific summaries (legacy, if any)
    user_summaries_dir = f"{session['username']}/{session['role']}/summaries"
    user_file_path = f"{user_summaries_dir}/{filename}"
    try:
        response = s3_client.get_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=user_file_path)
        content = response['Body'].read().decode('utf-8')
        return render_template('view_summary.html', 
                             content=content, 
                             filename=filename,
                             is_admin=user.get('is_admin', False),
                             username=user['username'])
    except ClientError:
        pass

    # Check all classes the user is a teacher or student in
    class_query = {"$or": [
        {"teacher_id": user['_id']},
        {"students": user['_id']}
    ]}
    classes = mongo.db.classes.find(class_query)
    for class_obj in classes:
        teacher = mongo.db.users.find_one({"_id": class_obj['teacher_id']})
        if not teacher:
            continue
        class_dir = f"{teacher['username']}/classes/{class_obj['class_code']}"
        class_file_path = f"{class_dir}/{filename}"
        try:
            response = s3_client.get_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=class_file_path)
            content = response['Body'].read().decode('utf-8')
            return render_template('view_summary.html', 
                                 content=content, 
                                 filename=filename,
                                 is_admin=user.get('is_admin', False),
                                 username=user['username'])
        except ClientError:
            pass
    return "File not found or access denied.", 404

@app.route('/download/<filename>')
def download_file(filename):
    # Sanitize filename
    filename = os.path.basename(filename)
    user_role_dir = f"{session['username']}/{session['role']}"
    file_path = None
    if filename.startswith('summary_'):
        file_path = f"{user_role_dir}/summaries/{filename}"
    elif filename.startswith('transcript_'):
        file_path = f"{user_role_dir}/transcripts/{filename}"
    elif filename.startswith('recording_'):
        file_path = f"{user_role_dir}/recordings/{filename}"
    try:
        response = s3_client.get_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=file_path)
        return send_file(response['Body'], as_attachment=True, download_name=filename)
    except ClientError:
        pass
    # Check all classes the user is a teacher or student in
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    class_query = {"$or": [
        {"teacher_id": user['_id']},
        {"students": user['_id']}
    ]}
    classes = mongo.db.classes.find(class_query)
    for class_obj in classes:
        teacher = mongo.db.users.find_one({"_id": class_obj['teacher_id']})
        if not teacher:
            continue
        class_dir = f"{teacher['username']}/classes/{class_obj['class_code']}"
        class_file_path = f"{class_dir}/{filename}"
        try:
            response = s3_client.get_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=class_file_path)
            return send_file(response['Body'], as_attachment=True, download_name=filename)
        except ClientError:
            pass
    return "File not found or access denied.", 404

# Admin routes
@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    if not user or not user.get('is_admin'):
        return redirect(url_for('dashboard'))
    users = list(mongo.db.users.find())
    schools = list(mongo.db.schools.find())
    school_map = {str(s['_id']): s['name'] for s in schools}
    pending_teachers = list(mongo.db.pending_teachers.find())
    # Attach school name to each pending teacher
    for teacher in pending_teachers:
        school_id = str(teacher.get('school_id')) if teacher.get('school_id') else None
        teacher['school_name'] = school_map.get(school_id, 'N/A')
    global_prompt = get_global_prompt()
    return render_template('admin.html', users=users, schools=schools, pending_teachers=pending_teachers, global_prompt=global_prompt)

@app.route('/admin/prompts/edit', methods=['GET', 'POST'])
def edit_global_prompt():
    if not session.get('is_admin') and session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
    
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    if not user:
        return redirect(url_for('logout'))
    
    current_prompt = get_global_prompt()
    
    if request.method == 'POST':
        # Get form data
        prompt_text = request.form.get('prompt_text', '')
        
        # Check if reset to default was requested
        reset_to_default = request.form.get('reset_to_default') == 'true'
        
        if reset_to_default:
            prompt_text = BASE_PROMPT
        
        # Save the prompt
        save_global_prompt(prompt_text)
        
        flash("Global prompt updated successfully!", "success")
        return redirect(url_for('admin_dashboard'))
    
    return render_template('edit_prompt.html', 
                         prompt={'prompt_text': current_prompt}, 
                         prompt_title="Global Summarization Prompt",
                         username=user['username'])

@app.route('/create_class', methods=['GET', 'POST'])
def create_class():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    if not user or user['role'] != 'teacher':
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        class_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            
        new_class = {
            "name": name,
            "description": description,
            "class_code": class_code,
            "teacher_id": user['_id'],
            "students": [],
            "summaries": []
        }
        
        mongo.db.classes.insert_one(new_class)
        return redirect(url_for('dashboard'))
        
    return render_template('create_class.html', 
                         error=None,
                         is_admin=user.get('is_admin', False),
                         username=user['username'])

@app.route('/classes/<class_id>')
def view_class(class_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    class_obj = mongo.db.classes.find_one({"_id": ObjectId(class_id)})
    if not class_obj:
        return redirect(url_for('dashboard'))
    # Check if user has access
    if user['role'] == 'teacher' and class_obj['teacher_id'] != user['_id']:
        return redirect(url_for('dashboard'))
    elif user['role'] == 'student' and user['_id'] not in class_obj.get('students', []):
        return redirect(url_for('dashboard'))
        
    # Always use teacher's username for summary S3 path
    teacher = mongo.db.users.find_one({"_id": class_obj['teacher_id']})
    class_code = class_obj.get('class_code')
    class_dir = f"{teacher['username']}/classes/{class_code}"
    all_summaries = []
    try:
        response = s3_client.list_objects_v2(Bucket=os.getenv('WASABI_BUCKET_NAME'), Prefix=class_dir)
        if 'Contents' in response:
            for obj in response['Contents']:
                key = obj['Key']
                if key.startswith(f"{class_dir}/summary_"):
                    filename = key.split('/')[-1]
                    timestamp_str = filename.split('_')[1].split('.')[0]
                    try:
                        timestamp = int(timestamp_str)
                        date_obj = datetime.datetime.fromtimestamp(timestamp)
                        date_str = date_obj.strftime('%Y-%m-%d %H:%M')
                    except Exception:
                        date_str = 'Unknown date'
                        timestamp = 0
                    all_summaries.append({
                        'filename': filename,
                        'created_at': date_str,
                        'timestamp': timestamp
                    })
        all_summaries.sort(key=lambda x: x['timestamp'], reverse=True)
    except Exception as e:
        print(f"Error fetching summaries for class {class_code}: {e}")

    # Get approval status from DB
    summary_db_list = class_obj.get('summaries', [])
    summary_approval = {s['filename']: s for s in summary_db_list}
    # Filter for students
    if user['role'] == 'student':
        summaries = [s for s in all_summaries if summary_approval.get(s['filename'], {}).get('approved')]
    else:
        # For teachers, show all and add approval status
        for s in all_summaries:
            s['approved'] = summary_approval.get(s['filename'], {}).get('approved', False)
        summaries = all_summaries

    # Fetch students with usernames
    student_objs = []
    for student_id in class_obj.get('students', []):
        student = mongo.db.users.find_one({'_id': student_id})
        if student:
            student_objs.append({'id': str(student['_id']), 'username': student['username']})

    # Fetch pending student requests (if you want to implement approval system)
    pending_requests = class_obj.get('pending_requests', [])
    print('DEBUG: class_obj["pending_requests"] =', pending_requests)
    pending_objs = []
    for student_id in pending_requests:
        student = mongo.db.users.find_one({'_id': student_id})
        if student:
            pending_objs.append({'id': str(student['_id']), 'username': student['username']})
    print('DEBUG: pending_objs =', pending_objs)

    # Pass correct counts
    summary_count = len(summaries)
    student_count = len(student_objs)

    return render_template('view_class.html', 
                         class_obj=class_obj,
                         user_role=user['role'],
                         is_admin=user.get('is_admin', False),
                         username=user['username'],
                         user_id=str(user['_id']),
                         users=list(mongo.db.users.find()),
                         summaries=summaries,
                         students=student_objs,
                         pending_requests=pending_objs,
                         summary_count=summary_count,
                         student_count=student_count)

@app.route('/classes/<class_id>/enroll', methods=['POST'])
def enroll_in_class(class_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    if user['role'] != 'student':
        return redirect(url_for('dashboard'))
    class_obj = mongo.db.classes.find_one({"_id": ObjectId(class_id)})
    if not class_obj:
        return redirect(url_for('dashboard'))
    if user['_id'] in class_obj.get('students', []):
        return redirect(url_for('dashboard'))
    mongo.db.classes.update_one({"_id": class_obj['_id']}, {"$push": {"students": user['_id']}})
    mongo.db.users.update_one({"_id": user['_id']}, {"$push": {"enrolled_classes": class_obj['_id']}})
    return redirect(url_for('dashboard'))
    
@app.route('/join_class', methods=['GET', 'POST'])
def join_class():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    if user['role'] != 'student':
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        class_code = request.form.get('class_code', '').strip().upper()
        class_obj = mongo.db.classes.find_one({"class_code": class_code})
        if not class_obj:
            return render_template('join_class.html', error='Invalid class code')
        if user['_id'] in class_obj.get('students', []):
            return render_template('join_class.html', error='You are already enrolled in this class')
        if user['_id'] in class_obj.get('pending_requests', []):
            return render_template('join_class.html', error='You have already requested to join this class')
        # Add to pending_requests
        mongo.db.classes.update_one({"_id": class_obj['_id']}, {"$addToSet": {"pending_requests": user['_id']}})
        return render_template('join_class.html', error='Join request sent! Waiting for teacher approval.')
    return render_template('join_class.html')

@app.route('/classes/<class_id>/remove_student/<student_id>', methods=['POST'])
def remove_student_from_class(class_id, student_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    class_obj = mongo.db.classes.find_one({"_id": ObjectId(class_id)})
    if user['role'] != 'teacher' or class_obj['teacher_id'] != user['_id']:
        return redirect(url_for('dashboard'))
    mongo.db.classes.update_one({"_id": class_obj['_id']}, {"$pull": {"students": ObjectId(student_id)}})
    mongo.db.users.update_one({"_id": ObjectId(student_id)}, {"$pull": {"enrolled_classes": class_obj['_id']}})
    return redirect(url_for('view_class', class_id=class_id))

@app.route('/classes/<class_id>/delete', methods=['POST'])
def teacher_delete_class(class_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    class_obj = mongo.db.classes.find_one({"_id": ObjectId(class_id)})
    if user['role'] != 'teacher' or class_obj['teacher_id'] != user['_id']:
        return redirect(url_for('dashboard'))
    mongo.db.classes.delete_one({"_id": class_obj['_id']})
    return redirect(url_for('dashboard'))
        
@app.route('/admin/delete_user/<user_id>', methods=['POST'])
def admin_delete_user(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    if not user or not user.get('is_admin'):
        return redirect(url_for('dashboard'))
    mongo.db.users.delete_one({"_id": ObjectId(user_id)})
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_class/<class_id>', methods=['POST'])
def admin_delete_class(class_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    if not user or not user.get('is_admin'):
        return redirect(url_for('dashboard'))
    mongo.db.classes.delete_one({"_id": ObjectId(class_id)})
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/create_school', methods=['GET', 'POST'])
def create_school_route():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    if not user or not user.get('is_admin'):
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name = request.form.get('school_name', '').strip()
        district = request.form.get('school_district', '').strip()
        state = request.form.get('school_state', '').strip()
        if not name or not district or not state:
            return render_template('create_school.html', error='All fields are required.', schools=get_all_schools())
        if mongo.db.schools.find_one({"name": name}):
            return render_template('create_school.html', error='School already exists.', schools=get_all_schools())
        mongo.db.schools.insert_one({"name": name, "district": district, "state": state})
        return redirect(url_for('admin_dashboard'))
    return render_template('create_school.html', schools=get_all_schools())

def scan_wasabi_files(username, class_code=None):
    """Scan Wasabi S3 for summaries, recordings, and transcripts in the respective folders."""
    files = []
    if class_code:
        # Scan class-specific files
        class_dir = f"{username}/classes/{class_code}"
        try:
            response = s3_client.list_objects_v2(Bucket=os.getenv('WASABI_BUCKET_NAME'), Prefix=class_dir)
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    if key.endswith('.txt'):
                        files.append(key)
        except ClientError as e:
            print(f"Error scanning class files: {e}")
    else:
        # Scan user-specific files
        user_dir = f"{username}"
        try:
            response = s3_client.list_objects_v2(Bucket=os.getenv('WASABI_BUCKET_NAME'), Prefix=user_dir)
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    if key.endswith('.txt'):
                        files.append(key)
        except ClientError as e:
            print(f"Error scanning user files: {e}")
    return files

def ensure_admin_and_school():
    with app.app_context():
        if mongo.db.schools.count_documents({}) == 0:
            mongo.db.schools.insert_one({"name": "Default High School", "district": "Default District", "state": "CA"})
        admin = mongo.db.users.find_one({"username": "admin"})
        if not admin:
            password_hash = generate_password_hash("duggy")
            mongo.db.users.insert_one({
                "username": "admin",
                "password_hash": password_hash,
                "role": "admin",
                "is_admin": True,
                "subscribed": False
            })
        else:
            if admin.get("role") != "admin" or not admin.get("is_admin"):
                mongo.db.users.update_one({"_id": admin["_id"]}, {"$set": {"role": "admin", "is_admin": True}})

@app.route('/classes/<class_id>/approve_student/<student_id>', methods=['POST'])
def approve_student(class_id, student_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    class_obj = mongo.db.classes.find_one({"_id": ObjectId(class_id)})
    if not class_obj or user['role'] != 'teacher' or class_obj['teacher_id'] != user['_id']:
        return redirect(url_for('dashboard'))
    # Remove from pending_requests and add to students
    mongo.db.classes.update_one(
        {"_id": ObjectId(class_id)},
        {"$pull": {"pending_requests": ObjectId(student_id)}, "$addToSet": {"students": ObjectId(student_id)}}
    )
    mongo.db.users.update_one({"_id": ObjectId(student_id)}, {"$addToSet": {"enrolled_classes": ObjectId(class_id)}})
    return redirect(url_for('view_class', class_id=class_id))

@app.route('/admin/approve_teacher/<teacher_id>', methods=['POST'])
def approve_teacher(teacher_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    if not user or not user.get('is_admin'):
        return redirect(url_for('dashboard'))
    teacher = mongo.db.pending_teachers.find_one({"_id": ObjectId(teacher_id)})
    if not teacher:
        return redirect(url_for('admin_dashboard'))
    # Move teacher to users collection
    mongo.db.users.insert_one(teacher)
    mongo.db.pending_teachers.delete_one({"_id": ObjectId(teacher_id)})
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/deny_teacher/<teacher_id>', methods=['POST'])
def deny_teacher(teacher_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    if not user or not user.get('is_admin'):
        return redirect(url_for('dashboard'))
    mongo.db.pending_teachers.delete_one({"_id": ObjectId(teacher_id)})
    return redirect(url_for('admin_dashboard'))

@app.route('/buy', methods=['GET', 'POST'])
def buy():
    error = None
    if request.method == 'POST':
        # Placeholder for future logic
        pass
    return render_template('buy.html', error=error)

@app.route('/classes/<class_id>/approve_summary/<filename>', methods=['POST'])
def approve_summary(class_id, filename):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    class_obj = mongo.db.classes.find_one({"_id": ObjectId(class_id)})
    if not class_obj or user['role'] != 'teacher' or class_obj['teacher_id'] != user['_id']:
        return redirect(url_for('dashboard'))
    mongo.db.classes.update_one(
        {"_id": ObjectId(class_id), "summaries.filename": filename},
        {"$set": {"summaries.$.approved": True}}
    )
    return redirect(url_for('view_class', class_id=class_id))

@app.route('/classes/<class_id>/deny_summary/<filename>', methods=['POST'])
def deny_summary(class_id, filename):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    class_obj = mongo.db.classes.find_one({"_id": ObjectId(class_id)})
    if not class_obj or user['role'] != 'teacher' or class_obj['teacher_id'] != user['_id']:
        return redirect(url_for('dashboard'))
    # Remove summary entry from DB
    mongo.db.classes.update_one(
        {"_id": ObjectId(class_id)},
        {"$pull": {"summaries": {"filename": filename}}}
    )
    # Optionally, delete the file from Wasabi
    class_code = class_obj.get('class_code')
    teacher = mongo.db.users.find_one({"_id": class_obj['teacher_id']})
    if teacher:
        class_dir = f"{teacher['username']}/classes/{class_code}"
        summary_path = f"{class_dir}/{filename}"
        try:
            s3_client.delete_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=summary_path)
        except Exception as e:
            print(f"Error deleting summary file from Wasabi: {e}")
    return redirect(url_for('view_class', class_id=class_id))

@app.route('/view_summary_raw/<filename>')
def view_summary_raw(filename):
    if 'user_id' not in session:
        return '', 401
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    # Try to find the summary in all possible class dirs
    classes = mongo.db.classes.find({"teacher_id": user['_id']})
    for class_obj in classes:
        class_code = class_obj.get('class_code')
        class_dir = f"{user['username']}/classes/{class_code}"
        summary_path = f"{class_dir}/{filename}"
        try:
            response = s3_client.get_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=summary_path)
            return response['Body'].read().decode('utf-8')
        except Exception:
            continue
    return '', 404

@app.route('/edit_summary/<filename>', methods=['POST'])
def edit_summary(filename):
    if 'user_id' not in session:
        return '', 401
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    content = request.json.get('content')
    # Try to find the summary in all possible class dirs
    classes = mongo.db.classes.find({"teacher_id": user['_id']})
    for class_obj in classes:
        class_code = class_obj.get('class_code')
        class_dir = f"{user['username']}/classes/{class_code}"
        summary_path = f"{class_dir}/{filename}"
        try:
            s3_client.put_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=summary_path, Body=content)
            return '', 200
        except Exception:
            continue
    return '', 404

if __name__ == '__main__':
    ensure_admin_and_school()
    app.run(debug=True) 