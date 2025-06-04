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
import requests
from openai import OpenAI
from vercel_blob import put
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to load environment variables from .env file
try:
    load_dotenv()
    logger.info("Successfully loaded .env file")
except Exception as e:
    logger.error(f"Error loading .env file: {e}. Using environment variables if available.")

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'thetasummary-secret-key'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=7)  # Sessions last 7 days
app.config['SESSION_PERMANENT'] = True
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 100  # 100MB in bytes

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

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_URL = os.getenv('DEEPSEEK_URL', 'https://api.deepseek.com/v1')
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-reasoner')

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
            demo_code = request.form.get('demo_code')
            register_method = request.form.get('register_method', 'demo')

            if not role or role not in ['student', 'teacher']:
                return render_template('register.html', error='Invalid role selected', username=username, schools=schools)

            if register_method == 'plan':
                # User claims to have purchased a plan, check for active subscription
                if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                    return render_template('register.html', error='Invalid email address', username=username, schools=schools)
                paid_user = mongo.db.users.find_one({
                    "email": email,
                    "subscription_status": "active",
                    "subscribed": True
                })
                if not paid_user:
                    return render_template('register.html', error='No active subscription found for this email. Please purchase a plan first.', username=username, schools=schools)
                # Optionally, you could log them in or allow them to set a password here
                flash('Account already exists for this email. Please log in.', 'error')
                return redirect(url_for('login'))
            else:
                # Demo code path
                if not demo_code:
                    return redirect(url_for('buy'))
                # Validate demo code if provided
                demo_code_obj = mongo.db.demo_codes.find_one({
                    "code": demo_code,
                    "used": False,
                    "expires_at": {"$gt": datetime.datetime.utcnow()}
                })
                if not demo_code_obj:
                    return render_template('register.html', error='Invalid or expired demo code', username=username, role=role, schools=schools)
                # Mark demo code as used
                mongo.db.demo_codes.update_one(
                    {"_id": demo_code_obj["_id"]},
                    {"$set": {"used": True}}
                )

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
                
                # Send verification email
                verification_url = url_for('verify_email', token=user.verification_token, _external=True)
                email_template = render_template('email/verify_email.html',
                                              username=username,
                                              verification_url=verification_url)
                send_email(email, 'Verify your ThetaSummary account', email_template)
                
                flash('Registration successful! Please check your email to verify your account.', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            import traceback
            error_message = f"REGISTER ERROR: {e}<br><pre>{traceback.format_exc()}</pre>"
            return render_template('register.html', error=error_message, username=request.form.get('username'), role=request.form.get('role'), schools=schools)
    return render_template('register.html', role='student', schools=schools)

def send_email(to_email, subject, html_content):
    try:
        message = SendGridMail(
            from_email=os.getenv('MAIL_DEFAULT_SENDER', 'noreply@thetasummary.com'),
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        sendgrid_client.send(message)
        logger.info(f"Email sent successfully to {to_email}")
    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {e}")
        raise e

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

        # Get user and check subscription limits
        user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        # Check if user has an active subscription
        if not user.get('subscribed') or user.get('subscription_status') != 'active':
            return jsonify({'status': 'error', 'message': 'Active subscription required to generate summaries'}), 403

        # Get plan limits
        plan_limits = user.get('plan_limits', {})
        subscription_type = user.get('subscription_type', 'plus')

        # Count summaries for today and this month
        today = datetime.datetime.utcnow().date()
        month_start = datetime.datetime(today.year, today.month, 1)
        
        # Get all summaries for the user's classes
        summaries_today = 0
        summaries_month = 0
        
        if user['role'] == 'teacher':
            classes = list(mongo.db.classes.find({"teacher_id": user['_id']}))
        else:
            enrolled_class_ids = user.get('enrolled_classes', [])
            classes = list(mongo.db.classes.find({"_id": {"$in": enrolled_class_ids}})) if enrolled_class_ids else []

        for class_obj in classes:
            teacher = mongo.db.users.find_one({"_id": class_obj['teacher_id']})
            if not teacher:
                continue
                
            class_dir = f"{teacher['username']}/classes/{class_obj['class_code']}"
            try:
                response = s3_client.list_objects_v2(Bucket=os.getenv('WASABI_BUCKET_NAME'), Prefix=class_dir)
                if 'Contents' in response:
                    for obj in response['Contents']:
                        key = obj['Key']
                        if key.startswith(f"{class_dir}/summary_"):
                            filename = key.split('/')[-1]
                            try:
                                summary_timestamp = int(filename.split('_')[1].split('.')[0])
                                summary_date = datetime.datetime.fromtimestamp(summary_timestamp).date()
                                summary_datetime = datetime.datetime.fromtimestamp(summary_timestamp)
                                
                                if summary_date == today:
                                    summaries_today += 1
                                if summary_datetime >= month_start:
                                    summaries_month += 1
                            except (ValueError, IndexError):
                                continue
            except Exception as e:
                logger.error(f"Error counting summaries: {e}")
                continue

        # Check limits based on subscription type
        if subscription_type == 'plus':
            if summaries_today >= plan_limits.get('summaries_per_day', 2):
                return jsonify({
                    'status': 'error',
                    'message': f'Daily limit reached ({plan_limits.get("summaries_per_day", 2)} summaries per day). Please upgrade to Pro for more summaries.'
                }), 403
        elif subscription_type == 'pro':
            if summaries_month >= plan_limits.get('summaries_per_month', 150):
                return jsonify({
                    'status': 'error',
                    'message': f'Monthly limit reached ({plan_limits.get("summaries_per_month", 150)} summaries per month). Please upgrade to Enterprise for unlimited summaries.'
                }), 403

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
def admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    if not user or not user.get('is_admin'):
        return redirect(url_for('dashboard'))
    
    # Get user statistics
    pro_users_count = mongo.db.users.count_documents({"subscription_type": "pro", "subscription_status": "active"})
    enterprise_users_count = mongo.db.users.count_documents({"subscription_type": "enterprise", "subscription_status": "active"})
    plus_users_count = mongo.db.users.count_documents({"subscription_type": "plus", "subscription_status": "active"})
    
    # Get all users
    users = list(mongo.db.users.find())
    
    # Get pending teachers
    pending_teachers = list(mongo.db.pending_teachers.find())
    
    # Get global prompt
    global_prompt = get_global_prompt()
    
    # Get active demo code if it exists
    active_demo_code = mongo.db.demo_codes.find_one({
        "created_by": user['_id'],
        "expires_at": {"$gt": datetime.datetime.utcnow()},
        "used": False
    })
    
    demo_code = active_demo_code['code'] if active_demo_code else None
    demo_code_expiry = active_demo_code['expires_at'].strftime('%Y-%m-%d %H:%M:%S UTC') if active_demo_code else None
    
    return render_template('admin.html', 
                         username=user['username'],
                         pro_users_count=pro_users_count,
                         enterprise_users_count=enterprise_users_count,
                         plus_users_count=plus_users_count,
                         users=users, 
                         pending_teachers=pending_teachers, 
                         global_prompt=global_prompt,
                         demo_code=demo_code,
                         demo_code_expiry=demo_code_expiry)

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
        return redirect(url_for('admin'))
    
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
    return redirect(url_for('admin'))

@app.route('/admin/delete_class/<class_id>', methods=['POST'])
def admin_delete_class(class_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    if not user or not user.get('is_admin'):
        return redirect(url_for('dashboard'))
    mongo.db.classes.delete_one({"_id": ObjectId(class_id)})
    return redirect(url_for('admin'))

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
        return redirect(url_for('dashboard'))
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
    mongo.db.users.delete_one({"_id": ObjectId(teacher_id)})
    return redirect(url_for('admin'))

@app.route('/admin/credit_tokens', methods=['POST'])
def credit_tokens():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Check if user is admin
    admin = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    if not admin or not admin.get('is_admin'):
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        user_id = request.form.get('user_id')
        token_amount = int(request.form.get('token_amount', 0))
        
        if not user_id or token_amount <= 0:
            flash('Invalid token amount or user', 'error')
            return redirect(url_for('admin'))
        
        # Update user's token balance
        result = mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$inc": {"token_balance": token_amount}}
        )
        
        if result.modified_count > 0:
            flash(f'Successfully credited {token_amount} tokens to user', 'success')
        else:
            flash('Failed to credit tokens', 'error')
            
    except Exception as e:
        flash(f'Error crediting tokens: {str(e)}', 'error')
    
    return redirect(url_for('admin'))

@app.route('/buy', methods=['GET', 'POST'])
def buy():
    if request.method == 'POST':
        user = None
        if 'user_id' in session:
            user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
            if not user:
                return redirect(url_for('logout'))
        error = None
        try:
            subscription_type = request.form.get('subscription_type')
            if not subscription_type or subscription_type not in ['plus', 'pro', 'enterprise']:
                raise ValueError('Invalid subscription type')
            prices = {
                'plus': os.getenv('STRIPE_PLUS_PRICE_ID'),
                'pro': os.getenv('STRIPE_PRO_PRICE_ID'),
                'enterprise': os.getenv('STRIPE_ENTERPRISE_PRICE_ID')
            }
            # Use email from form if not logged in
            email = request.form.get('email') if not user else user.get('email')
            if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                error = 'A valid email is required to purchase a plan.'
                return render_template('buy.html', 
                                     error=error,
                                     username=session.get('username', ''),
                                     current_subscription=None,
                                     stripe_public_key=os.getenv('STRIPE_PUBLIC_KEY'))
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': prices[subscription_type],
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=url_for('payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=url_for('payment_cancelled', _external=True),
                client_reference_id=str(user['_id']) if user else None,
                customer_email=email,
                metadata={
                    'user_id': str(user['_id']) if user else '',
                    'subscription_type': subscription_type,
                    'email': email
                }
            )
            return redirect(checkout_session.url, code=303)
        except Exception as e:
            error = str(e)
            logger.error(f"Error creating checkout session: {e}")
        return render_template('buy.html', 
                             error=error,
                             username=session.get('username', ''),
                             current_subscription=None,
                             stripe_public_key=os.getenv('STRIPE_PUBLIC_KEY'))
    # GET request: allow anyone to view
    username = session.get('username', '') if 'user_id' in session else ''
    current_subscription = None
    if 'user_id' in session:
        user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
        if user:
            current_subscription = user.get('subscription_type', 'plus')
    return render_template('buy.html', 
                         error=None,
                         username=username,
                         current_subscription=current_subscription,
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
        
        # Set plan limits based on subscription type
        plan_limits = {
            'plus': {
                'summaries_per_day': 2,
                'summaries_per_month': 60  # 2 per day * 30 days
            },
            'pro': {
                'summaries_per_day': 5,  # 150/30 = 5 per day
                'summaries_per_month': 150
            },
            'enterprise': {
                'summaries_per_day': float('inf'),
                'summaries_per_month': float('inf')
            }
        }
        
        mongo.db.users.update_one(
            {"_id": ObjectId(session['user_id'])},
            {
                "$set": {
                    "subscription_type": subscription_type,
                    "subscription_status": "active",
                    "subscription_start": datetime.datetime.utcnow(),
                    "subscription_id": subscription_id,
                    "subscribed": True,
                    "plan_limits": plan_limits[subscription_type]
                }
            }
        )
        
        # Send confirmation email
        user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
        if user and user.get('email'):
            email_template = render_template('email/subscription_confirmation.html',
                                          username=user['username'],
                                          subscription_type=subscription_type,
                                          plan_limits=plan_limits[subscription_type])
            send_email(user['email'], 'Your ThetaSummary subscription is active!', email_template)
        
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
    # Update the summary's approved status
    mongo.db.classes.update_one(
        {"_id": ObjectId(class_id)},
        {"$set": {"summaries.$[elem].approved": True}},
        array_filters=[{"elem.filename": filename}]
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
        data = request.get_json()
        blob_url = data.get('blob_url')
        mime_type = data.get('mime_type')
        class_id = data.get('class_id')
        
        if not all([blob_url, mime_type, class_id]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Download the audio from the blob URL
        response = requests.get(blob_url)
        if not response.ok:
            return jsonify({'error': 'Failed to download audio from blob'}), 500
            
        audio_data = response.content
        
        # Continue with your existing transcription logic using audio_data
        # ... rest of your transcription code ...
        
    except Exception as e:
        print(f"Error in transcription: {str(e)}")
        return jsonify({'error': 'Failed to process audio'}), 500

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

@app.errorhandler(413)
def handle_413(e):
    if request.path.startswith('/api/'):
        return jsonify({
            'status': 'error',
            'message': 'File too large. Maximum file size is 100MB. Please upload a smaller file or recording.'
        }), 413
    return render_template('error.html', 
                         error_message='File too large. Maximum file size is 100MB. Please upload a smaller file or recording.',
                         username=session.get('username', '')), 413

def generate_summary(transcript, timestamp, class_id):
    """Generate a summary using DeepSeek API. This function is called by the queue workers."""
    logger.info(f"[SUMMARY] Starting summarization for class_id={class_id}, timestamp={timestamp}")
    if not DEEPSEEK_API_KEY:
        raise Exception("DeepSeek API key not configured")
        
    summarization_prompt_template = get_global_prompt()
    if not summarization_prompt_template.strip().endswith("Transcript:"):
        full_summarization_prompt = summarization_prompt_template + "\n\nTranscript:\n" + transcript
    else:
        full_summarization_prompt = summarization_prompt_template + transcript
        
    logger.info("Using DeepSeek for summarization...")
    try:
        deepseek_client = openai.OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_URL)
        summary_resp = deepseek_client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": full_summarization_prompt}],
            stream=False
        )
        summary = summary_resp.choices[0].message.content
        logger.info(f"[SUMMARY] Finished summarization for class_id={class_id}, timestamp={timestamp}")
    except Exception as e:
        logger.error(f"[SUMMARY] Summarization failed for class_id={class_id}, timestamp={timestamp}: {e}")
        logger.error(f"DeepSeek API error: {e}")
        if "authenticate" in str(e).lower() or "authorization" in str(e).lower():
            raise Exception("DeepSeek API key is invalid")
        raise Exception(f"Error with DeepSeek API: {str(e)}")
        
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

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_MODEL = "google/gemini-2.5-flash-preview-05-20"
OPENROUTER_SITE_URL = os.getenv('OPENROUTER_SITE_URL', 'https://thetasummary.com')
OPENROUTER_SITE_TITLE = os.getenv('OPENROUTER_SITE_TITLE', 'ThetaSummary')

@app.route('/api/summaries', methods=['GET'])
def get_summaries():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    user = mongo.db.users.find_one({'_id': ObjectId(session['user_id'])})
    class_id = request.args.get('class_id')
    if not class_id:
        return jsonify({'status': 'error', 'message': 'Missing class_id'}), 400
    class_obj = mongo.db.classes.find_one({'_id': ObjectId(class_id)})
    if not class_obj:
        return jsonify({'status': 'error', 'message': 'Class not found'}), 404
    # Check if user is in class
    if user['role'] == 'teacher' and class_obj['teacher_id'] != user['_id']:
        return jsonify({'status': 'error', 'message': 'Access denied'}), 403
    if user['role'] == 'student' and user['_id'] not in class_obj.get('students', []):
        return jsonify({'status': 'error', 'message': 'Access denied'}), 403

    # Get list of approved summaries from the class object
    approved_summaries = [s['filename'] for s in class_obj.get('summaries', []) if s.get('approved', False)]
    
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
                    # Only include approved summaries
                    if filename not in approved_summaries:
                        continue
                    # Parse date from filename
                    try:
                        timestamp_str = filename.split('_')[1].split('.')[0]
                        timestamp = int(timestamp_str)
                        date_obj = datetime.datetime.fromtimestamp(timestamp)
                        date_str = date_obj.strftime('%Y-%m-%d %I:%M %p')
                    except Exception:
                        date_str = 'Unknown date'
                        timestamp = 0
                    # Get preview (first 200 chars)
                    try:
                        file_obj = s3_client.get_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=key)
                        preview = file_obj['Body'].read(200).decode('utf-8')
                    except Exception:
                        preview = '[Error loading summary]'
                    summaries.append({'filename': filename, 'title': filename, 'date': date_str, 'timestamp': timestamp, 'preview': preview})
        # Sort summaries by timestamp, latest first
        summaries.sort(key=lambda x: x['timestamp'], reverse=True)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    return jsonify({'status': 'success', 'summaries': summaries})

@app.route('/api/chat', methods=['POST'])
def chat_api():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    try:
        data = request.get_json()
        message = data.get('message')
        attached_summaries = data.get('attachedSummaries', [])
        class_id = data.get('class_id') or request.args.get('class_id')
        if not message:
            return jsonify({'status': 'error', 'message': 'No message provided'}), 400

        # Get user and check token balance
        user = mongo.db.users.find_one({'_id': ObjectId(session['user_id'])})
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        # Check if user has any tokens at all
        if user.get('token_balance', 0) <= 0:
            return jsonify({
                'status': 'error',
                'message': 'You have no tokens remaining. Please purchase more tokens to continue.',
                'redirect': url_for('buy')
            }), 402

        # Fetch summary content from Wasabi S3
        summaries_content = []
        if attached_summaries and class_id:
            class_obj = mongo.db.classes.find_one({'_id': ObjectId(class_id)})
            if class_obj:
                # Get list of approved summaries
                approved_summaries = [s['filename'] for s in class_obj.get('summaries', []) if s.get('approved', False)]
                # Filter attached_summaries to only include approved ones
                approved_attached = [f for f in attached_summaries if f in approved_summaries]
                
                teacher = mongo.db.users.find_one({'_id': class_obj['teacher_id']})
                class_code = class_obj.get('class_code')
                for filename in approved_attached:
                    key = f"{teacher['username']}/classes/{class_code}/{filename}"
                    try:
                        file_obj = s3_client.get_object(Bucket=os.getenv('WASABI_BUCKET_NAME'), Key=key)
                        content = file_obj['Body'].read().decode('utf-8')
                        summaries_content.append(content)
                    except Exception as e:
                        summaries_content.append('[Error loading summary]')
        
        # Create context from summaries
        context = "\n\n".join(summaries_content) if summaries_content else ""
        
        # Add context to the message if there are summaries
        full_message = f"""You are Theta, an AI assistant designed to help users with their educational needs. Absolutely every math expression, variable, or formula—no matter how short—must be wrapped in single dollar signs $...$ for inline math or double dollar signs $$...$$ for display math. Never use LaTeX for non-math text, and never leave a math expression unwrapped. Do not use LaTeX for explanations, italics, or regular text. Do not include any LaTeX document headers, environments, or preambles—just the math expression itself. Your goal is to provide clear, accurate, and helpful responses while maintaining a professional and friendly tone. Use consistent LaTeX formatting for all mathematical expressions.

Context from attached summaries:
{context}

User message: {message}"""
        
        # Initialize OpenRouter client
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )
        
        # Call OpenRouter API
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": OPENROUTER_SITE_URL,
                "X-Title": OPENROUTER_SITE_TITLE,
            },
            model=OPENROUTER_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": full_message
                }
            ]
        )
        
        ai_response = completion.choices[0].message.content
        
        # Calculate actual token usage
        input_tokens = completion.usage.prompt_tokens
        output_tokens = completion.usage.completion_tokens
        
        # Update user's token balance and usage
        mongo.db.users.update_one(
            {'_id': ObjectId(session['user_id'])},
            {
                '$inc': {
                    'token_balance': -(input_tokens + output_tokens),
                    'chat_input_tokens': int(input_tokens),
                    'chat_output_tokens': int(output_tokens)
                }
            }
        )
        
        return jsonify({'status': 'success', 'response': ai_response})
    except Exception as e:
        logger.error(f"Error in chat API: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Token pricing constants
INPUT_TOKEN_PRICE = 0.15  # $0.15 per 1M tokens
OUTPUT_TOKEN_PRICE = 0.60  # $0.60 per 1M tokens
PLUS_PRO_TOKEN_PRICE = 1.00  # $1.00 per 1M tokens for Plus/Pro users

@app.route('/purchase_tokens', methods=['POST'])
def purchase_tokens():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        token_amount = int(request.form.get('token_amount', 0))
        if token_amount <= 0:
            flash('Invalid token amount', 'error')
            return redirect(url_for('buy'))
        
        user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
        if not user:
            return redirect(url_for('logout'))
        
        # Calculate price based on user's subscription type
        if user.get('subscription_type') in ['plus', 'pro']:
            price = token_amount * PLUS_PRO_TOKEN_PRICE
        else:
            price = token_amount * (INPUT_TOKEN_PRICE + OUTPUT_TOKEN_PRICE)
        
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'{token_amount}M Tokens',
                        'description': 'Token purchase for ThetaSummary'
                    },
                    'unit_amount': int(price * 100)  # Convert to cents
                },
                'quantity': 1
            }],
            mode='payment',
            success_url=url_for('token_purchase_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('token_purchase_cancelled', _external=True),
            client_reference_id=str(user['_id']),
            metadata={
                'user_id': str(user['_id']),
                'token_amount': token_amount
            }
        )
        
        return redirect(checkout_session.url, code=303)
        
    except Exception as e:
        logger.error(f"Error creating token purchase session: {e}")
        flash('Error processing token purchase', 'error')
        return redirect(url_for('buy'))

@app.route('/token_purchase_success')
def token_purchase_success():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        session_id = request.args.get('session_id')
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        
        if checkout_session.payment_status == 'paid':
            user_id = checkout_session.metadata.get('user_id')
            token_amount = int(checkout_session.metadata.get('token_amount', 0))
            
            # Update user's token balance
            mongo.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$inc": {"token_balance": token_amount * 1_000_000}}  # Convert millions to actual tokens
            )
            
            flash('Token purchase successful!', 'success')
        else:
            flash('Payment not completed', 'error')
            
    except Exception as e:
        logger.error(f"Error processing token purchase success: {e}")
        flash('Error processing payment', 'error')
    
    return redirect(url_for('admin'))

@app.route('/token_purchase_cancelled')
def token_purchase_cancelled():
    flash('Token purchase cancelled', 'info')
    return redirect(url_for('admin'))

@app.route('/generate_demo_code', methods=['POST'])
def generate_demo_code():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    if not user or not user.get('is_admin'):
        return redirect(url_for('dashboard'))
    
    try:
        # Check for existing active demo code
        existing_code = mongo.db.demo_codes.find_one({
            "created_by": user['_id'],
            "expires_at": {"$gt": datetime.datetime.utcnow()},
            "used": False
        })
        
        if existing_code:
            flash('An active demo code already exists. Please wait for it to expire or be used.', 'error')
            return redirect(url_for('admin', 
                                  demo_code=existing_code['code'], 
                                  demo_code_expiry=existing_code['expires_at'].strftime('%Y-%m-%d %H:%M:%S UTC')))
        
        # Generate a random 8-character code
        demo_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        expiry_date = datetime.datetime.utcnow() + datetime.timedelta(days=2)
        
        # Store the demo code
        mongo.db.demo_codes.insert_one({
            "code": demo_code,
            "created_by": user['_id'],
            "created_at": datetime.datetime.utcnow(),
            "expires_at": expiry_date,
            "used": False
        })
        
        return redirect(url_for('admin', 
                              demo_code=demo_code, 
                              demo_code_expiry=expiry_date.strftime('%Y-%m-%d %H:%M:%S UTC')))
        
    except Exception as e:
        logger.error(f"Error generating demo code: {e}")
        flash('Error generating demo code', 'error')
        return redirect(url_for('admin'))

@app.template_filter('commaformat')
def commaformat(value):
    try:
        return f"{int(value):,}"
    except Exception:
        return value

@app.route('/admin/promote_teacher/<user_id>', methods=['POST'])
def promote_teacher(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Check if user is admin
    admin = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    if not admin or not admin.get('is_admin'):
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        subscription_type = request.form.get('subscription_type')
        if not subscription_type or subscription_type not in ['plus', 'pro', 'enterprise']:
            flash('Invalid subscription type', 'error')
            return redirect(url_for('admin'))
        
        # Set plan limits based on subscription type
        plan_limits = {
            'plus': {
                'summaries_per_day': 2,
                'summaries_per_month': 60  # 2 per day * 30 days
            },
            'pro': {
                'summaries_per_day': 5,  # 150/30 = 5 per day
                'summaries_per_month': 150
            },
            'enterprise': {
                'summaries_per_day': float('inf'),
                'summaries_per_month': float('inf')
            }
        }
        
        # Update teacher's subscription
        result = mongo.db.users.update_one(
            {"_id": ObjectId(user_id), "role": "teacher"},
            {
                "$set": {
                    "subscription_type": subscription_type,
                    "subscription_status": "active",
                    "subscription_start": datetime.datetime.utcnow(),
                    "subscribed": True,
                    "plan_limits": plan_limits[subscription_type]
                }
            }
        )
        
        if result.modified_count > 0:
            flash(f'Successfully promoted teacher to {subscription_type.capitalize()} plan', 'success')
        else:
            flash('Failed to promote teacher', 'error')
            
    except Exception as e:
        flash(f'Error promoting teacher: {str(e)}', 'error')
    
    return redirect(url_for('admin'))

@app.route('/purchase_recording_time', methods=['POST'])
def purchase_recording_time():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        recording_hours = int(request.form.get('recording_hours', 0))
        if recording_hours <= 0:
            flash('Invalid recording hours amount', 'error')
            return redirect(url_for('buy'))
        
        user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
        if not user:
            return redirect(url_for('logout'))
        
        # Calculate price (20 cents per hour)
        price = recording_hours * 0.20
        
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'{recording_hours} Hours of Recording Time',
                        'description': 'Additional recording time for ThetaSummary'
                    },
                    'unit_amount': int(price * 100)  # Convert to cents
                },
                'quantity': 1
            }],
            mode='payment',
            success_url=url_for('recording_time_purchase_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('recording_time_purchase_cancelled', _external=True),
            client_reference_id=str(user['_id']),
            metadata={
                'user_id': str(user['_id']),
                'recording_hours': recording_hours
            }
        )
        
        return redirect(checkout_session.url, code=303)
        
    except Exception as e:
        logger.error(f"Error creating recording time purchase session: {e}")
        flash('Error processing recording time purchase', 'error')
        return redirect(url_for('buy'))

@app.route('/recording_time_purchase_success')
def recording_time_purchase_success():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        session_id = request.args.get('session_id')
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        
        if checkout_session.payment_status == 'paid':
            user_id = checkout_session.metadata.get('user_id')
            recording_hours = int(checkout_session.metadata.get('recording_hours', 0))
            
            # Update user's recording time balance
            mongo.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$inc": {"recording_time_balance": recording_hours}}
            )
            
            flash('Recording time purchase successful!', 'success')
        else:
            flash('Payment not completed', 'error')
            
    except Exception as e:
        logger.error(f"Error processing recording time purchase success: {e}")
        flash('Error processing payment', 'error')
    
    return redirect(url_for('buy'))

@app.route('/recording_time_purchase_cancelled')
def recording_time_purchase_cancelled():
    flash('Recording time purchase cancelled', 'info')
    return redirect(url_for('buy'))

@app.route('/api/get-upload-url', methods=['POST'])
@login_required
def get_upload_url():
    try:
        data = request.get_json()
        filename = data.get('filename')
        content_type = data.get('contentType')
        class_id = data.get('class_id')
        
        if not all([filename, content_type, class_id]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Generate a unique path for the blob
        path = f"recordings/{class_id}/{filename}"
        
        # Upload an empty file to get the blob URL (since put uploads directly)
        result = put(path=path, data=b'', options={
            "access": "public",
            "token": os.getenv('BLOB_READ_WRITE_TOKEN')
        })
        
        return jsonify({
            'uploadUrl': result.get('url'),
            'blobUrl': result.get('url')
        })
        
    except Exception as e:
        print(f"Error generating upload URL: {str(e)}")
        return jsonify({'error': 'Failed to generate upload URL'}), 500

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

if __name__ == '__main__':
    ensure_admin_and_school()
    app.run(debug=True) 