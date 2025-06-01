from flask import Flask, render_template, redirect, url_for, request, jsonify, send_file, flash, session, Response
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
from io import BytesIO
from queue_manager import summarization_queue
import uuid
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor
from flask_mail import Mail, Message
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail as SendGridMail

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to load environment variables from .env file
try:
    load_dotenv()
    logger.info("Successfully loaded .env file")
except Exception as e:
    logger.error(f"Error loading .env file: {e}. Using environment variables if available.")

# Define base data directory for all storage
BASE_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'local_data'))
os.makedirs(BASE_DATA_DIR, exist_ok=True)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'thetasummary-secret-key'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=7)  # Sessions last 7 days
app.config['SESSION_PERMANENT'] = True

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.sendgrid.net'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'apikey'
app.config['MAIL_PASSWORD'] = os.getenv('SENDGRID_API_KEY')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@thetasummary.com')

# Initialize Flask-Mail
mail = Mail(app)

# Initialize SendGrid
sendgrid_client = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))

# Use absolute path for SQLite database in /tmp for Vercel compatibility
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

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("Gemini API configured successfully")
else:
    logger.warning("GEMINI_API_KEY not set")

# Base Prompt that handles subject detection and formatting
BASE_PROMPT = """
Please summarize this class transcript according to the appropriate template below:

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

logger.info("MONGO_URI: %s", app.config["MONGO_URI"])
logger.info("MongoDB initialized: %s", mongo)
logger.info("MongoDB database: %s", mongo.db)

# Helper functions for user, class, and school management
def get_user_by_username(username):
    return mongo.db.users.find_one({"username": username})

def create_user(username, password_hash, role, email, is_admin=False, school_id=None):
    user = {
        "username": username,
        "password_hash": password_hash,
        "role": role,
        "email": email,
        "email_verified": False,
        "verification_token": ''.join(random.choices(string.ascii_letters + string.digits, k=32)),
        "is_admin": is_admin,
        "school_id": ObjectId(school_id) if school_id else None,
        "subscribed": False,
        "subscription_type": "plus",
        "subscription_start": None,
        "subscription_end": None,
        "subscription_status": "inactive",
        "talk_to_theta_enabled": False
    }
    return mongo.db.users.insert_one(user)

def get_school_by_id(school_id):
    return mongo.db.schools.find_one({"_id": ObjectId(school_id)})

def get_all_schools():
    return list(mongo.db.schools.find())

def create_school(name, district, state):
    return mongo.db.schools.insert_one({"name": name, "district": district, "state": state})

# Configure Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

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
            email = request.form.get('email')
            role = request.form.get('role')
            school_id = request.form.get('school_id') if role == 'teacher' else None

            if not role or role not in ['student', 'teacher']:
                    return render_template('register.html', error='Invalid role selected', username=username, schools=schools)

            if role == 'teacher':
                    if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                        return render_template('register.html', error='Invalid email address', username=username, schools=schools)
                    if not school_id:
                        return render_template('register.html', error='Please select a school.', username=username, role=role, schools=schools)
                    existing_email = mongo.db.users.find_one({"email": email})
                    if existing_email:
                        return render_template('register.html', error='Email already registered', role=role, username=username, schools=schools)
                
            existing_user = get_user_by_username(username)
            if existing_user:
                    return render_template('register.html', error='Username already exists', role=role, username=username, schools=schools)

            password_hash = generate_password_hash(password)
            if role == 'teacher':
                    teacher = {
                        "username": username,
                        "password_hash": password_hash,
                        "role": role,
                        "email": email,
                        "email_verified": False,
                        "verification_token": ''.join(random.choices(string.ascii_letters + string.digits, k=32)),
                        "is_admin": False,
                        "school_id": ObjectId(school_id) if school_id else None,
                        "subscribed": False
                    }
                    mongo.db.pending_teachers.insert_one(teacher)
                    return render_template('register.html', error='Teacher account request sent! Waiting for admin approval.', schools=schools)
            else:
                    user = create_user(username, password_hash, role, email, is_admin=False, school_id=school_id)
                    session['user_id'] = str(user.inserted_id)
                    session['username'] = username
                    session['role'] = role
                    flash('Registration successful! You can now join classes.', 'success')
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
                        if key.endswith('.txt'):
                            if 'summary_' in key:
                                summary_count += 1
                            elif 'recording_' in key:
                                recording_count += 1
                            elif 'transcript_' in key:
                                transcript_count += 1
            except Exception as e:
                logger.error(f"Error counting files for class {class_code}: {e}")
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
            teacher = mongo.db.users.find_one({"_id": class_obj['teacher_id']})
            if not teacher:
                continue
            class_dir = f"{teacher['username']}/classes/{class_code}"
            summary_count = 0
            recording_count = 0
            transcript_count = 0
            try:
                response = s3_client.list_objects_v2(Bucket=os.getenv('WASABI_BUCKET_NAME'), Prefix=class_dir)
                if 'Contents' in response:
                    for obj in response['Contents']:
                        key = obj['Key']
                        if key.endswith('.txt'):
                            if 'summary_' in key:
                                summary_count += 1
                            elif 'recording_' in key:
                                recording_count += 1
                            elif 'transcript_' in key:
                                transcript_count += 1
            except Exception as e:
                logger.error(f"Error counting files for class {class_code}: {e}")
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
    
    # Get class_id from query parameter
    class_id = request.args.get('class_id')
    
    return render_template('recordings.html', 
                         classes=classes,
                         username=user['username'],
                         user_role=user['role'],
                         class_id=class_id)

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
                    logger.error(f"Error reading preview for {filename}: {e}")
                
                date_str = 'Unknown date'
                try:
                    timestamp = int(timestamp_str)
                    date_obj = datetime.datetime.fromtimestamp(timestamp)
                    date_str = date_obj.strftime('%Y-%m-%d %I:%M %p')
                except ValueError:
                    logger.error(f"Could not parse timestamp: {timestamp_str} for file {filename}")
                
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
                        logger.error(f"Error reading preview for {filename}: {e}")
                    
                    date_str = 'Unknown date'
                    try:
                        timestamp = int(timestamp_str)
                        date_obj = datetime.datetime.fromtimestamp(timestamp)
                        date_str = date_obj.strftime('%Y-%m-%d %I:%M %p')
                    except ValueError:
                        logger.error(f"Could not parse timestamp: {timestamp_str} for file {filename}")
                    
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

# Create a thread pool with 10 workers for parallel processing
thread_pool = ThreadPoolExecutor(max_workers=10)

@app.route('/api/summarize', methods=['POST'])
def summarize():
    try:
        data = request.get_json()
        if not data or 'transcript' not in data:
            return jsonify({'status': 'error', 'message': 'No transcript provided'}), 400

        transcript = data['transcript']
        timestamp = data.get('timestamp', datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
        class_id = data.get('class_id')

        if not class_id:
            return jsonify({'status': 'error', 'message': 'No class ID provided'}), 400

        # Generate a unique task ID
        task_id = f"{int(time.time())}-{uuid.uuid4()}"

        # Submit the summarization task
        future = summarization_queue.executor.submit(
            generate_summary,
            transcript,
            timestamp,
            class_id
        )

        # Add the task to the queue
        summarization_queue.add_task(task_id, future)

        return jsonify({
            'status': 'success',
            'task_id': task_id,
            'message': 'Summarization task started'
        })
                
    except Exception as e:
        logger.error(f"Error in summarize endpoint: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/summarize/status/<task_id>', methods=['GET'])
def get_summarization_status(task_id):
    try:
        result = summarization_queue.get_result(task_id)
        if result is None:
                    return jsonify({'status': 'error', 'message': 'Task not found'}), 404
                
        if result['status'] == 'completed':
            return jsonify({
            'status': 'success',
            'result': result['result']
        })
        elif result['status'] == 'failed':
            return jsonify({
                        'status': 'failed',
                        'message': result.get('error', 'Unknown error occurred')
                    })
        else:
                    return jsonify({'status': 'processing'})
    except Exception as e:
        logger.error(f"Error checking summarization status: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/check_file', methods=['POST'])
def check_file():
    try:
        filename = request.json.get('filename')
        if not filename or not filename.startswith('summary_'):
            return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
        
        logger.info(f"Checking file: {filename}")
        
        # First try user's own summaries
        user_summaries_dir = f"{session['username']}/{session['role']}/summaries"
        user_file_path = f"{user_summaries_dir}/{filename}"
        logger.info(f"Trying user path: {user_file_path}")
        try:
            s3_client.head_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=user_file_path)
            logger.info(f"Found file at user path: {user_file_path}")
            return jsonify({'status': 'success', 'exists': True, 'path': 'user'})
        except ClientError as e:
            logger.info(f"Not found at user path: {e}")

        # Then check all classes the user is a teacher or student in
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
            logger.info(f"Trying class path: {class_file_path}")
            
            try:
                s3_client.head_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=class_file_path)
                logger.info(f"Found file at class path: {class_file_path}")
                return jsonify({'status': 'success', 'exists': True, 'path': 'class', 'class_id': str(class_obj['_id'])})
            except ClientError as e:
                logger.info(f"Not found at class path: {e}")
                continue

        logger.info(f"File not found in any location: {filename}")
        return jsonify({'status': 'success', 'exists': False}), 200
        
    except Exception as e:
        logger.error(f"Error in check_file endpoint: {str(e)}")
        return jsonify({'status': 'error', 'message': f"Error checking file: {str(e)}"}), 500

@app.route('/view_summary/<filename>')
def view_summary(filename):
    if not filename.startswith('summary_'):
        return "Invalid file type for this view.", 400

    logger.info(f"Attempting to view summary: {filename}")
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    if not user:
        return redirect(url_for('logout'))

    # First try user's own summaries
    user_summaries_dir = f"{session['username']}/{session['role']}/summaries"
    user_file_path = f"{user_summaries_dir}/{filename}"
    logger.info(f"Trying user path: {user_file_path}")
    try:
        response = s3_client.get_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=user_file_path)
        content = response['Body'].read().decode('utf-8')
        logger.info(f"Found file at user path: {user_file_path}")
        return render_template('view_summary.html', 
                             content=content, 
                             filename=filename,
                             is_admin=user.get('is_admin', False),
                             username=user['username'],
                             user_role=user['role'],
                             classes=list(mongo.db.classes.find({'teacher_id': user['_id']})) if user['role'] == 'teacher' else [],
                             class_id=None)
    except ClientError as e:
        logger.info(f"Not found at user path: {e}")

    # Then check all classes the user is a teacher or student in
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
        logger.info(f"Trying class path: {class_file_path}")
        
        try:
            response = s3_client.get_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=class_file_path)
            content = response['Body'].read().decode('utf-8')
            logger.info(f"Found file at class path: {class_file_path}")
            return render_template('view_summary.html', 
                                 content=content, 
                                 filename=filename,
                                 is_admin=user.get('is_admin', False),
                                 username=user['username'],
                                 user_role=user['role'],
                                 classes=list(mongo.db.classes.find({'teacher_id': user['_id']})) if user['role'] == 'teacher' else [],
                                 class_id=str(class_obj['_id']))
        except ClientError as e:
            logger.info(f"Not found at class path: {e}")
            continue
            
    logger.info(f"File not found in any location: {filename}")
    return "File not found or access denied.", 404

@app.route('/download/<filename>')
def download_file(filename):
    # Sanitize filename
    filename = os.path.basename(filename)
    logger.info(f"Attempting to download file: {filename}")
    
    # First try user's own files
    user_role_dir = f"{session['username']}/{session['role']}"
    file_path = None
    if filename.startswith('summary_'):
        file_path = f"{user_role_dir}/summaries/{filename}"
    elif filename.startswith('transcript_'):
        file_path = f"{user_role_dir}/transcripts/{filename}"
    elif filename.startswith('recording_'):
        file_path = f"{user_role_dir}/recordings/{filename}"
        
    logger.info(f"Trying user path: {file_path}")
    try:
        response = s3_client.get_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=file_path)
        file_data = response['Body'].read()
        logger.info(f"Found file at user path: {file_path}")
        return send_file(BytesIO(file_data), as_attachment=True, download_name=filename)
    except ClientError as e:
        logger.info(f"Not found at user path: {e}")
    
    # Then check all classes the user is a teacher or student in
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
        logger.info(f"Trying class path: {class_file_path}")
        
        try:
            response = s3_client.get_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=class_file_path)
            file_data = response['Body'].read()
            logger.info(f"Found file at class path: {class_file_path}")
            return send_file(BytesIO(file_data), as_attachment=True, download_name=filename)
        except ClientError as e:
            logger.info(f"Not found at class path: {e}")
            continue
            
    logger.info(f"File not found in any location: {filename}")
    return "File not found or access denied.", 404

# Admin routes
@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    if not user or not user.get('is_admin'):
        return redirect(url_for('dashboard'))
    
    # Get subscription statistics
    pro_users_count = mongo.db.users.count_documents({
        "subscription_type": "pro",
        "subscription_status": "active"
    })
    enterprise_users_count = mongo.db.users.count_documents({
        "subscription_type": "enterprise",
        "subscription_status": "active"
    })
    plus_users_count = mongo.db.users.count_documents({
        "subscription_type": "plus"
    })
    
    users = list(mongo.db.users.find())
    schools = list(mongo.db.schools.find())
    school_map = {str(s['_id']): s['name'] for s in schools}
    pending_teachers = list(mongo.db.pending_teachers.find())
    # Attach school name to each pending teacher
    for teacher in pending_teachers:
        school_id = str(teacher.get('school_id')) if teacher.get('school_id') else None
        teacher['school_name'] = school_map.get(school_id, 'N/A')
    global_prompt = get_global_prompt()
    
    return render_template('admin.html', 
                         users=users, 
                         schools=schools, 
                         pending_teachers=pending_teachers, 
                         global_prompt=global_prompt,
                         pro_users_count=pro_users_count,
                         enterprise_users_count=enterprise_users_count,
                         plus_users_count=plus_users_count)

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
                        date_str = date_obj.strftime('%Y-%m-%d %I:%M %p')
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
        logger.error(f"Error fetching summaries for class {class_code}: {e}")
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
    logger.info('DEBUG: class_obj["pending_requests"] = %s', pending_requests)
    pending_objs = []
    for student_id in pending_requests:
        student = mongo.db.users.find_one({'_id': student_id})
        if student:
            pending_objs.append({'id': str(student['_id']), 'username': student['username']})
    logger.info('DEBUG: pending_objs = %s', pending_objs)
    # Pass correct counts
    summary_count = len(summaries)
    student_count = len(student_objs)
    # Pass all classes for sidebar if teacher
    sidebar_classes = []
    if user['role'] == 'teacher':
        sidebar_classes = list(mongo.db.classes.find({'teacher_id': user['_id']}))
    # For talk_to_theta_enabled:
    if user['role'] == 'teacher':
        talk_to_theta_enabled = user.get('talk_to_theta_enabled', False)
    else:
        talk_to_theta_enabled = teacher.get('talk_to_theta_enabled', False)
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
                         student_count=student_count,
                         classes=sidebar_classes if user['role'] == 'teacher' else [],
                         talk_to_theta_enabled=talk_to_theta_enabled)

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
            logger.error(f"Error scanning class files: {e}")
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
            logger.error(f"Error scanning user files: {e}")
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
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    if not user:
        return redirect(url_for('logout'))
    
    error = None
    if request.method == 'POST':
        try:
            subscription_type = request.form.get('subscription_type')
            if not subscription_type or subscription_type not in ['plus', 'pro', 'enterprise']:
                raise ValueError('Invalid subscription type')
            
            # Create Stripe checkout session
            prices = {
                'plus': os.getenv('STRIPE_PLUS_PRICE_ID'),
                'pro': os.getenv('STRIPE_PRO_PRICE_ID'),
                'enterprise': os.getenv('STRIPE_ENTERPRISE_PRICE_ID')
            }
            
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': prices[subscription_type],
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=url_for('payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=url_for('payment_cancelled', _external=True),
                client_reference_id=str(user['_id']),
                customer_email=user.get('email'),
                metadata={
                    'user_id': str(user['_id']),
                    'subscription_type': subscription_type
                }
            )
            
            return redirect(checkout_session.url, code=303)
            
        except Exception as e:
            error = str(e)
            logger.error(f"Error creating checkout session: {e}")
    
    return render_template('buy.html', 
                         error=error,
                         username=user['username'],
                         current_subscription=user.get('subscription_type', 'plus'),
                         stripe_public_key=os.getenv('STRIPE_PUBLIC_KEY'))

@app.route('/payment/success')
def payment_success():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    session_id = request.args.get('session_id')
    if not session_id:
        return redirect(url_for('dashboard'))
    
    try:
        # Retrieve the checkout session
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        
        # Verify the session belongs to this user
        if checkout_session.client_reference_id != str(session['user_id']):
            return redirect(url_for('dashboard'))
        
        # Update user's subscription
        subscription_type = checkout_session.metadata.get('subscription_type')
        subscription_id = checkout_session.subscription
        
        mongo.db.users.update_one(
            {"_id": ObjectId(session['user_id'])},
            {
                "$set": {
                    "subscription_type": subscription_type,
                    "subscription_status": "active",
                    "subscription_start": datetime.datetime.utcnow(),
                    "subscription_id": subscription_id,
                    "subscribed": True
                }
            }
        )
        
        flash('Payment successful! Your subscription has been activated.', 'success')
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        logger.error(f"Error processing successful payment: {e}")
        flash('There was an error processing your payment. Please contact support.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/payment/cancelled')
def payment_cancelled():
    flash('Payment was cancelled.', 'info')
    return redirect(url_for('buy'))

@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        return 'Invalid signature', 400
    
    # Handle the event
    if event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        user = mongo.db.users.find_one({"subscription_id": subscription.id})
        if user:
            mongo.db.users.update_one(
                {"_id": user['_id']},
                {
                    "$set": {
                        "subscription_status": "cancelled",
                        "subscribed": False
                    }
                }
            )
    
    return '', 200

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
            logger.error(f"Error deleting summary file from Wasabi: {e}")
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

@app.route('/api/transcribe', methods=['POST'])
def transcribe():
    logger.info("Starting transcription process")
    try:
        audio_base64 = request.json.get('audio_base64')
        mime_type = request.json.get('mime_type')
        class_id = request.json.get('class_id')
        logger.info("Received request with mime_type: %s, class_id: %s", mime_type, class_id)

        if not audio_base64 or not mime_type:
            logger.error("Missing audio data or mime_type")
            return jsonify({'status': 'error', 'message': "Missing audio data or mime_type."}), 400
        if not GEMINI_API_KEY:
            logger.error("Gemini API key not configured")
            return jsonify({'status': 'error', 'message': "Gemini API key not configured. Please set the GEMINI_API_KEY environment variable."}), 500

        logger.info("Decoding base64 audio data")
        try:
            audio_bytes = base64.b64decode(audio_base64)
            logger.info("Audio decoded successfully, size: %d bytes", len(audio_bytes))
        except Exception as e:
            logger.error("Error decoding base64 audio: %s", str(e))
            return jsonify({'status': 'error', 'message': f"Invalid audio data: {str(e)}"}), 400

        transcription_prompt = "Please transcribe this audio exactly as it is. Do not add any additional text or formatting."
        gemini_model_name = 'gemini-2.0-flash-lite'
        logger.info("Initializing Gemini model: %s", gemini_model_name)
        try:
            gemini_model = genai.GenerativeModel(gemini_model_name)
            logger.info("Gemini model initialized successfully")
            audio_part = {
                'mime_type': mime_type,
                'data': audio_bytes
            }
            logger.info("Sending transcription request to Gemini API")
            gemini_response = gemini_model.generate_content([audio_part, transcription_prompt])
            transcript = gemini_response.text
            logger.info("Transcription successful, transcript length: %d characters", len(transcript))
        except Exception as e:
            logger.error("Gemini API error: %s\n%s", str(e), traceback.format_exc())
            if "API key not valid" in str(e) or "API_KEY_INVALID" in str(e):
                logger.error("Invalid Gemini API key")
                return jsonify({'status': 'error', 'message': "Gemini API key is invalid. Please check configuration."}), 500
            if "model not found" in str(e).lower() or "model unavailable" in str(e).lower():
                logger.error("Gemini 2.0 Flash Lite model unavailable")
                return jsonify({'status': 'error', 'message': "Gemini 2.0 Flash Lite model unavailable. Please check model availability in Google Cloud Console."}), 500
            if hasattr(e, 'response') and hasattr(e.response, 'prompt_feedback'):
                if e.response.prompt_feedback.block_reason:
                    reason = e.response.prompt_feedback.block_reason
                    logger.error("Transcription blocked due to content policy: %s", reason)
                    return jsonify({'status': 'error', 'message': f"Transcription failed due to content policy: {reason}."}), 400
            logger.error("Unexpected Gemini API error")
            return jsonify({'status': 'error', 'message': f"Error with Gemini API: {str(e)}"}), 500

        # Create directories and save transcript
        timestamp = str(int(time.time()))
        recording_filename = f"recording_{timestamp}.txt"
        transcript_filename = f"transcript_{timestamp}.txt"
        logger.info("Generated filenames: recording=%s, transcript=%s", recording_filename, transcript_filename)

        if class_id:
            logger.info("Validating class_id: %s", class_id)
            class_obj = mongo.db.classes.find_one({"_id": ObjectId(class_id)})
            if not class_obj:
                logger.error("Class not found for class_id: %s", class_id)
                return jsonify({'status': 'error', 'message': 'Class not found'}), 404
            if session['role'] == 'teacher' and class_obj['teacher_id'] != ObjectId(session['user_id']):
                logger.error("Unauthorized teacher access to class_id: %s", class_id)
                return jsonify({'status': 'error', 'message': 'Unauthorized access to class'}), 403
            elif session['role'] == 'student' and ObjectId(session['user_id']) not in class_obj.get('students', []):
                logger.error("Unauthorized student access to class_id: %s", class_id)
                return jsonify({'status': 'error', 'message': 'Unauthorized access to class'}), 403
            class_dir = f"{session['username']}/classes/{class_obj['class_code']}"
            recording_path = f"{class_dir}/{recording_filename}"
            transcript_path = f"{class_dir}/{transcript_filename}"
        else:
            user_dir = f"{session['username']}"
            recording_path = f"{user_dir}/{recording_filename}"
            transcript_path = f"{user_dir}/{transcript_filename}"
        logger.info("Saving files to Wasabi S3: recording_path=%s, transcript_path=%s", recording_path, transcript_path)
        try:
            s3_client.put_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=recording_path, Body=audio_base64)
            s3_client.put_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=transcript_path, Body=transcript)
            logger.info("Files saved to Wasabi S3 successfully")
        except Exception as e:
            logger.error("Error saving files to Wasabi S3: %s", str(e))
            return jsonify({'status': 'error', 'message': f"Error saving files to storage: {str(e)}"}), 500

        logger.info("Transcription completed successfully")
        return jsonify({
            'status': 'success',
            'transcript': transcript,
            'transcript_filename': transcript_filename,
            'timestamp': timestamp
        })
    except Exception as e:
        logger.error("Unexpected error in transcribe endpoint: %s\n%s", str(e), traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f"Error processing: {str(e)}"
        }), 500

@app.errorhandler(Exception)
def handle_exception(e):
    # Only return JSON for API routes
    if request.path.startswith('/api/'):
        import traceback
        return jsonify({
            "status": "error",
            "message": str(e),
            "trace": traceback.format_exc()
        }), 500
    # Otherwise, use default error handling
    return str(e), 500

def generate_summary(transcript, timestamp, class_id):
    """Generate a summary using Deepseek API. This function is called by the queue workers."""
    if not DEEPSEEK_API_KEY:
        raise Exception("Deepseek API key not configured")
        
    summarization_prompt_template = get_global_prompt()
    if not summarization_prompt_template.strip().endswith("Transcript:"):
        full_summarization_prompt = summarization_prompt_template + "\n\nTranscript:\n" + transcript
    else:
        full_summarization_prompt = summarization_prompt_template + transcript
        
    logger.info("Using Deepseek for summarization...")
    try:
        summary_resp = deepseek_client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": full_summarization_prompt}],
            stream=False
        )
        summary = summary_resp.choices[0].message.content
    except Exception as e:
        logger.error(f"Deepseek API error: {e}")
        if "authenticate" in str(e).lower() or "authorization" in str(e).lower():
            raise Exception("Deepseek API key is invalid")
        raise Exception(f"Error with Deepseek API: {str(e)}")
        
    summary_filename = f"summary_{timestamp}.txt"
    summary_path = None
    
    class_obj = mongo.db.classes.find_one({"_id": ObjectId(class_id)})
    if not class_obj:
        raise Exception('Class not found')
        
    teacher = mongo.db.users.find_one({"_id": class_obj['teacher_id']})
    class_dir = f"{teacher['username']}/classes/{class_obj['class_code']}"
    summary_path = f"{class_dir}/{summary_filename}"
    
    logger.info(f"Trying to save summary to S3 at: {summary_path}")
    s3_client.put_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=summary_path, Body=summary)
    
    mongo.db.classes.update_one(
        {"_id": ObjectId(class_id)},
        {"$addToSet": {"summaries": {
            "filename": summary_filename,
            "created_at": datetime.datetime.utcnow(),
            "approved": False
        }}}
    )
    
    # Send email notification
    if teacher.get('email') and teacher.get('email_verified'):
        email_template = render_template('email/summary_complete.html',
                                      username=teacher['username'],
                                      class_name=class_obj['name'],
                                      summary_url=url_for('view_summary', filename=summary_filename, _external=True))
        send_email(teacher['email'], 'Your summary is ready!', email_template)
    
    return {
        'summary': summary,
        'summary_filename': summary_filename
    }

@app.route('/verify-email/<token>')
def verify_email(token):
    user = mongo.db.users.find_one({"verification_token": token})
    if user:
        mongo.db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"email_verified": True}, "$unset": {"verification_token": ""}}
        )
        flash('Email verified successfully!', 'success')
    else:
        flash('Invalid verification token.', 'error')
    return redirect(url_for('login'))

@app.route('/api/class_summaries/<class_id>')
def api_class_summaries(class_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    user = mongo.db.users.find_one({'_id': ObjectId(session['user_id'])})
    class_obj = mongo.db.classes.find_one({'_id': ObjectId(class_id)})
    if not class_obj:
        return jsonify({'status': 'error', 'message': 'Class not found'}), 404
    # Check if user is in class
    if user['role'] == 'teacher' and class_obj['teacher_id'] != user['_id']:
        return jsonify({'status': 'error', 'message': 'Access denied'}), 403
    if user['role'] == 'student' and user['_id'] not in class_obj.get('students', []):
        return jsonify({'status': 'error', 'message': 'Access denied'}), 403
    teacher = mongo.db.users.find_one({'_id': class_obj['teacher_id']})
    class_code = class_obj.get('class_code')
    class_dir = f"{teacher['username']}/classes/{class_code}"
    summaries = []
    try:
        response = s3_client.list_objects_v2(Bucket=os.getenv('WASABI_BUCKET_NAME'), Prefix=class_dir)
        if 'Contents' in response:
            for obj in response['Contents']:
                key = obj['Key']
                if key.startswith(f"{class_dir}/summary_"):
                    filename = key.split('/')[-1]
                    # Parse date from filename
                    try:
                        timestamp_str = filename.split('_')[1].split('.')[0]
                        timestamp = int(timestamp_str)
                        date_obj = datetime.datetime.fromtimestamp(timestamp)
                        date_str = date_obj.strftime('%Y-%m-%d %I:%M %p')
                    except Exception:
                        date_str = 'Unknown date'
                        timestamp = 0
                    # Get content (first 2000 chars for performance)
                    try:
                        file_obj = s3_client.get_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=key)
                        content = file_obj['Body'].read(2000).decode('utf-8')
                    except Exception:
                        content = '[Error loading summary]'
                    summaries.append({'filename': filename, 'content': content, 'date': date_str, 'timestamp': timestamp})
        # Sort summaries by timestamp, latest first
        summaries.sort(key=lambda x: x['timestamp'], reverse=True)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    return jsonify({'status': 'success', 'summaries': summaries})

@app.route('/admin/toggle_theta/<user_id>', methods=['POST'])
def toggle_theta(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    if not user or not user.get('is_admin'):
        return redirect(url_for('dashboard'))
    target = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if not target or target.get('role') != 'teacher':
        return redirect(url_for('admin_dashboard'))
    enabled = not target.get('talk_to_theta_enabled', False)
    mongo.db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"talk_to_theta_enabled": enabled}})
    return redirect(url_for('admin_dashboard'))

@app.route('/chat')
def chat():
    return render_template('chat.html')

if __name__ == '__main__':
    ensure_admin_and_school()
    app.run(debug=True) 