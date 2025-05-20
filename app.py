from flask import Flask, render_template, redirect, url_for, request, jsonify, send_file, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
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
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=7)  # Sessions last 7 days
app.config['SESSION_PERMANENT'] = True

# Use absolute path for SQLite database
DB_DIR = os.path.join(BASE_DATA_DIR, 'database')
os.makedirs(DB_DIR, exist_ok=True)
db_path = os.path.join(DB_DIR, 'users.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

# Configure user files directory
USER_FILES_DIR = os.path.join(BASE_DATA_DIR, 'user_files')
app.config['UPLOAD_FOLDER'] = USER_FILES_DIR

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Initialize Flask-Session
Session(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

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

# User model with admin flag
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  # Kept for now, but role='admin' is preferred
    role = db.Column(db.String(50), nullable=False, default='student') # student, teacher, admin
    
    # Add relationships for classes
    teaching_classes = db.relationship('Class', backref='teacher', lazy=True, foreign_keys='Class.teacher_id')
    enrolled_classes = db.relationship('Class', secondary='class_enrollment', backref='students', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Class model
class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Add relationship for summaries
    summaries = db.relationship('Summary', backref='class', lazy=True)

# Class enrollment association table
class_enrollment = db.Table('class_enrollment',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('class_id', db.Integer, db.ForeignKey('class.id'), primary_key=True)
)

# Summary model to track summaries per class
class Summary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# Simplified Prompt model
class Prompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prompt_type = db.Column(db.String(50), nullable=False, unique=True, default='global')
    prompt_text = db.Column(db.Text, nullable=False)
    use_latex = db.Column(db.Boolean, default=False)  # Toggle for LaTeX format
    
    @staticmethod
    def get_prompt(prompt_type='global'): 
        prompt = Prompt.query.filter_by(prompt_type=prompt_type).first()
        if prompt:
            # Return the appropriate prompt based on the LaTeX setting
            if prompt.use_latex:
                return LATEX_PROMPT
            return prompt.prompt_text
        # Return default if not found
        return DEFAULT_GLOBAL_PROMPT
    
    @staticmethod
    def is_latex(prompt_type='global'):
        """Check if LaTeX format is enabled"""
        prompt = Prompt.query.filter_by(prompt_type=prompt_type).first()
        if prompt:
            return prompt.use_latex
        return False

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_admin_user():
    """Create admin user if it doesn't exist"""
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(username="admin", is_admin=True, role="admin")
        admin.set_password("duggy")
        db.session.add(admin)
        db.session.commit()
        print("Admin user created")
    else:
        # Ensure existing admin has the role
        if admin.role != "admin":
            admin.role = "admin"
            admin.is_admin = True # Ensure is_admin is also true
            db.session.commit()
            print("Updated existing admin user to have 'admin' role.")
        else:
            print("Admin user already exists with correct role")

def initialize_prompts():
    """Initialize the global prompt if it doesn't exist"""
    existing_prompt = Prompt.query.filter_by(prompt_type='global').first()
    if not existing_prompt:
        # Create with default prompt text and LaTeX setting
        new_prompt = Prompt(
            prompt_type='global', 
            prompt_text=DEFAULT_GLOBAL_PROMPT,
            use_latex=False
        )
        db.session.add(new_prompt)
        db.session.commit()
        print("Global prompt initialized")
    else:
        # Update fields if needed for existing prompts
        if not hasattr(existing_prompt, 'use_latex') or existing_prompt.use_latex is None:
            existing_prompt.use_latex = False
            db.session.commit()
            print("Updated existing prompt with LaTeX setting")
        print("Global prompt already exists")

def count_user_summaries(username, role):
    user_summaries_dir = os.path.join(app.config['UPLOAD_FOLDER'], username, role, 'summaries')
    summary_count = 0
    
    if os.path.exists(user_summaries_dir):
        for filename in os.listdir(user_summaries_dir):
            if filename.startswith('summary_'):
                summary_count += 1
    
    # Count class summaries
    classes = []
    if role == 'teacher':
        classes = Class.query.filter_by(teacher_id=User.query.filter_by(username=username).first().id).all()
    elif role == 'student':
        user = User.query.filter_by(username=username).first()
        classes = user.enrolled_classes
    
    for class_obj in classes:
        class_summaries_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'class_summaries', str(class_obj.id))
        if os.path.exists(class_summaries_dir):
            for filename in os.listdir(class_summaries_dir):
                if filename.startswith('summary_'):
                    summary_count += 1
    
    return summary_count

# Authentication routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        if not role or role not in ['student', 'teacher']:
            return render_template('register.html', error='Invalid role selected', username=username)

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template('register.html', error='Username already exists', role=role, username=username)
        
        new_user = User(username=username, role=role)
        new_user.is_admin = False

        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        # Create user directory and role-specific subdirectories including new subfolders
        user_base_dir = os.path.join(app.config['UPLOAD_FOLDER'], username)
        os.makedirs(user_base_dir, exist_ok=True)
        
        # Create role-specific base folder (student or teacher)
        user_role_specific_base_dir = os.path.join(user_base_dir, role)
        os.makedirs(user_role_specific_base_dir, exist_ok=True)

        # Create subfolders for recordings, transcripts, and summaries within the role-specific directory
        os.makedirs(os.path.join(user_role_specific_base_dir, 'recordings'), exist_ok=True)
        os.makedirs(os.path.join(user_role_specific_base_dir, 'transcripts'), exist_ok=True)
        os.makedirs(os.path.join(user_role_specific_base_dir, 'summaries'), exist_ok=True)

        # Ensure the other role's base folder is also created (e.g. if registered as student, create empty teacher folder structure)
        other_role = 'teacher' if role == 'student' else 'student'
        other_role_specific_base_dir = os.path.join(user_base_dir, other_role)
        os.makedirs(other_role_specific_base_dir, exist_ok=True)
        os.makedirs(os.path.join(other_role_specific_base_dir, 'recordings'), exist_ok=True)
        os.makedirs(os.path.join(other_role_specific_base_dir, 'transcripts'), exist_ok=True)
        os.makedirs(os.path.join(other_role_specific_base_dir, 'summaries'), exist_ok=True)
        
        login_user(new_user)
        return redirect(url_for('dashboard'))
    
    return render_template('register.html', role='student')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # Role selection on login is not implemented here as it's part of user data
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)  # Set remember=True to make the session permanent
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid username or password', username=username)
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Main routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Get summary count for the current user
    summary_count = count_user_summaries(current_user.username, current_user.role)
    
    if current_user.role == 'teacher':
        # Teachers see only their own classes
        classes = Class.query.filter_by(teacher_id=current_user.id).order_by(Class.created_at.desc()).all()
        return render_template('dashboard.html', classes=classes, user_role=current_user.role, summaries=summary_count)
    else:
        # Students see only their enrolled classes
        enrolled_classes = current_user.enrolled_classes
        return render_template('dashboard.html', classes=enrolled_classes, user_role=current_user.role, summaries=summary_count)

@app.route('/recordings')
@login_required
def recordings():
    return render_template('recordings.html')

@app.route('/summaries')
@login_required
def summaries():
    summary_files_data = []
    
    # Get user-specific summaries
    user_summaries_dir = os.path.join(app.config['UPLOAD_FOLDER'], current_user.username, current_user.role, 'summaries')
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
    if current_user.role == 'teacher':
        classes = Class.query.filter_by(teacher_id=current_user.id).all()
    elif current_user.role == 'student':
        classes = current_user.enrolled_classes
    
    for class_obj in classes:
        class_summaries_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'class_summaries', str(class_obj.id))
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
                        'class_name': class_obj.name
                    })
    
    summary_files_data.sort(key=lambda x: x['date'], reverse=True)
    return render_template('summaries.html', summaries=summary_files_data)

@app.route('/api/transcribe', methods=['POST'])
@login_required
def transcribe():
    try:
        audio_base64 = request.json.get('audio_base64')
        mime_type = request.json.get('mime_type')

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
            gemini_model = genai.GenerativeModel('gemini-1.5-flash')
            # Prepare audio part for Gemini API
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
            # Check for specific content-related errors from Gemini
            if hasattr(e, 'response') and hasattr(e.response, 'prompt_feedback'):
                if e.response.prompt_feedback.block_reason:
                    reason = e.response.prompt_feedback.block_reason
                    return jsonify({'status': 'error', 'message': f"Transcription failed due to content policy: {reason}."}), 400
            return jsonify({'status': 'error', 'message': f"Error with Gemini API: {str(e)}"}), 500

        # Create directories and save transcript first
        user_role_dir = os.path.join(app.config['UPLOAD_FOLDER'], current_user.username, current_user.role)
        recordings_dir = os.path.join(user_role_dir, 'recordings')
        transcripts_dir = os.path.join(user_role_dir, 'transcripts')
        
        # Ensure directories exist
        os.makedirs(recordings_dir, exist_ok=True)
        os.makedirs(transcripts_dir, exist_ok=True)
            
        timestamp = str(int(time.time()))
        recording_filename = f"recording_{timestamp}.txt"
        transcript_filename = f"transcript_{timestamp}.txt"
            
        recording_path = os.path.join(recordings_dir, recording_filename)
        transcript_path = os.path.join(transcripts_dir, transcript_filename)

        # Save received base64 audio and real transcript
        with open(recording_path, 'w', encoding='utf-8') as f:
            f.write(audio_base64) # Save the actual base64 audio string
            
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(transcript)
            
        # Return the transcript and associated data - without summarizing yet
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

# Endpoint for summarization after transcript is downloaded
@app.route('/api/summarize', methods=['POST'])
@login_required
def summarize():
    try:
        transcript = request.json.get('transcript')
        timestamp = request.json.get('timestamp')
        class_id = request.json.get('class_id')
        
        if not transcript or not timestamp:
            return jsonify({'status': 'error', 'message': "Missing transcript or timestamp"}), 400
        
        # Check if Deepseek API key is configured
        if not DEEPSEEK_API_KEY:
            return jsonify({'status': 'error', 'message': "Deepseek API key not configured. Please set the DEEPSEEK_API_KEY environment variable."}), 500
        
        # Get the appropriate prompt
        if Prompt.is_latex('global'):
            summarization_prompt_template = LATEX_PROMPT
        else:
            summarization_prompt_template = Prompt.get_prompt('global')
        
        # Combine prompt with transcript
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
            # Save to class summary folder and DB
            class_obj = Class.query.get(class_id)
            if not class_obj:
                return jsonify({'status': 'error', 'message': 'Class not found'}), 404
            # Verify user access
            if current_user.role == 'teacher' and class_obj.teacher_id != current_user.id:
                return jsonify({'status': 'error', 'message': 'Unauthorized access to class'}), 403
            elif current_user.role == 'student' and class_obj not in current_user.enrolled_classes:
                return jsonify({'status': 'error', 'message': 'Unauthorized access to class'}), 403
            class_summaries_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'class_summaries', str(class_id))
            os.makedirs(class_summaries_dir, exist_ok=True)
            summary_path = os.path.join(class_summaries_dir, summary_filename)
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(summary)
            # Add to DB if not already present
            if not Summary.query.filter_by(filename=summary_filename, class_id=class_id).first():
                db.session.add(Summary(filename=summary_filename, class_id=class_id))
                db.session.commit()
        else:
            # Save to user summaries folder
            user_role_dir = os.path.join(app.config['UPLOAD_FOLDER'], current_user.username, current_user.role)
            summaries_dir = os.path.join(user_role_dir, 'summaries')
            os.makedirs(summaries_dir, exist_ok=True)
            summary_path = os.path.join(summaries_dir, summary_filename)
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(summary)
        
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
@login_required
def check_file():
    try:
        filename = request.json.get('filename')
        if not filename or not filename.startswith('summary_'):
            return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
        
        # Check user-specific summaries
        user_summaries_dir = os.path.join(app.config['UPLOAD_FOLDER'], current_user.username, current_user.role, 'summaries')
        user_file_path = os.path.join(user_summaries_dir, filename)
        if os.path.exists(user_file_path) and os.path.isfile(user_file_path):
            return jsonify({'status': 'success', 'exists': True, 'path': 'user'})
        
        # Check class-specific summaries
        classes = []
        if current_user.role == 'teacher':
            classes = Class.query.filter_by(teacher_id=current_user.id).all()
        elif current_user.role == 'student':
            classes = current_user.enrolled_classes
        
        for class_obj in classes:
            class_summaries_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'class_summaries', str(class_obj.id))
            class_file_path = os.path.join(class_summaries_dir, filename)
            if os.path.exists(class_file_path) and os.path.isfile(class_file_path):
                return jsonify({'status': 'success', 'exists': True, 'path': 'class', 'class_id': class_obj.id})
        
        return jsonify({'status': 'success', 'exists': False}), 200
    except Exception as e:
        print(f"Error in check_file endpoint: {str(e)}")
        return jsonify({'status': 'error', 'message': f"Error checking file: {str(e)}"}), 500

@app.route('/view_summary/<filename>')
@login_required
def view_summary(filename):
    if not filename.startswith('summary_'):
        return "Invalid file type for this view.", 400

    # Check user-specific summaries
    user_summaries_dir = os.path.join(app.config['UPLOAD_FOLDER'], current_user.username, current_user.role, 'summaries')
    user_file_path = os.path.join(user_summaries_dir, filename)
    if os.path.exists(user_file_path) and os.path.isfile(user_file_path):
        try:
            with open(user_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return render_template('view_summary.html', content=content, filename=filename)
        except Exception as e:
            return f"Error reading file: {str(e)}", 500

    # Check class-specific summaries
    classes = []
    if current_user.role == 'teacher':
        classes = Class.query.filter_by(teacher_id=current_user.id).all()
    elif current_user.role == 'student':
        classes = current_user.enrolled_classes
    
    for class_obj in classes:
        class_summaries_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'class_summaries', str(class_obj.id))
        class_file_path = os.path.join(class_summaries_dir, filename)
        if os.path.exists(class_file_path) and os.path.isfile(class_file_path):
            try:
                with open(class_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return render_template('view_summary.html', content=content, filename=filename)
            except Exception as e:
                return f"Error reading file: {str(e)}", 500
    
    return "File not found or access denied.", 404

@app.route('/download/<filename>')
@login_required
def download_file(filename):
    # Sanitize filename
    filename = os.path.basename(filename)
    
    # Check user-specific files
    user_role_dir = os.path.join(app.config['UPLOAD_FOLDER'], current_user.username, current_user.role)
    file_path = None
    if filename.startswith('summary_'):
        file_path = os.path.join(user_role_dir, 'summaries', filename)
    elif filename.startswith('transcript_'):
        file_path = os.path.join(user_role_dir, 'transcripts', filename)
    elif filename.startswith('recording_'):
        file_path = os.path.join(user_role_dir, 'recordings', filename)
    
    if file_path and os.path.exists(file_path) and os.path.isfile(file_path):
        return send_file(file_path, as_attachment=True)
    
    # Check class-specific summaries
    classes = []
    if current_user.role == 'teacher':
        classes = Class.query.filter_by(teacher_id=current_user.id).all()
    elif current_user.role == 'student':
        classes = current_user.enrolled_classes
    
    for class_obj in classes:
        class_summaries_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'class_summaries', str(class_obj.id))
        class_file_path = os.path.join(class_summaries_dir, filename)
        if os.path.exists(class_file_path) and os.path.isfile(class_file_path):
            return send_file(class_file_path, as_attachment=True)
    
    return "File not found or access denied.", 404

# Admin routes
@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin and current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
    # Fetch the single global prompt
    global_prompt = Prompt.query.filter_by(prompt_type='global').first()
    if not global_prompt:
        global_prompt = Prompt(prompt_type='global', prompt_text=DEFAULT_GLOBAL_PROMPT, use_latex=False)
    
    users = User.query.all()
    return render_template('admin.html', global_prompt=global_prompt, users=users)

@app.route('/admin/prompts/edit', methods=['GET', 'POST'])
@login_required
def edit_global_prompt():
    if not current_user.is_admin and current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
    prompt = Prompt.query.filter_by(prompt_type='global').first()
    
    if not prompt:
        flash("Global prompt not found. Please restart the application.", "error")
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        # Get form data
        use_latex = request.form.get('use_latex') == 'on'
        prompt_text = request.form.get('prompt_text', '')
        
        # Check if reset to default was requested
        reset_to_default = request.form.get('reset_to_default') == 'true'
        
        if reset_to_default:
            prompt_text = LATEX_PROMPT if use_latex else BASE_PROMPT
        
        # Update the prompt
        prompt.use_latex = use_latex
        prompt.prompt_text = prompt_text
        db.session.commit()
        
        flash("Global prompt updated successfully!", "success")
        return redirect(url_for('admin_dashboard'))
    
    return render_template('edit_prompt.html', prompt=prompt, prompt_title="Global Summarization Prompt")

@app.route('/classes/create', methods=['GET', 'POST'])
@login_required
def create_class():
    if current_user.role != 'teacher':
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            return render_template('create_class.html', error='Class name is required')
            
        new_class = Class(
            name=name,
            description=description,
            teacher_id=current_user.id
        )
        
        db.session.add(new_class)
        db.session.commit()
        
        return redirect(url_for('dashboard'))
        
    return render_template('create_class.html')

@app.route('/classes/<int:class_id>')
@login_required
def view_class(class_id):
    class_obj = Class.query.get_or_404(class_id)
    
    # Check if user has access to this class
    if current_user.role == 'teacher' and class_obj.teacher_id != current_user.id:
        return redirect(url_for('dashboard'))
    elif current_user.role == 'student' and class_obj not in current_user.enrolled_classes:
        return redirect(url_for('dashboard'))
    
    # Get summaries for this class
    summaries = Summary.query.filter_by(class_id=class_id).order_by(Summary.created_at.desc()).all()
    
    return render_template('view_class.html', class_obj=class_obj, summaries=summaries)

@app.route('/classes/<int:class_id>/enroll', methods=['POST'])
@login_required
def enroll_in_class(class_id):
    if current_user.role != 'student':
        return redirect(url_for('dashboard'))
        
    class_obj = Class.query.get_or_404(class_id)
    
    if class_obj in current_user.enrolled_classes:
        flash('You are already enrolled in this class', 'info')
    else:
        current_user.enrolled_classes.append(class_obj)
        db.session.commit()
        flash('Successfully enrolled in class', 'success')
        
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        # Create tables
        try:
            db.create_all()
            print("Database tables created!")
            
            # Create admin user and initialize prompts
            create_admin_user()
            initialize_prompts()
            
            # Create test classes if they don't exist (for development)
            if Class.query.count() == 0:
                test_teacher = User.query.filter_by(username='admin').first()
                if test_teacher:
                    test_class = Class(
                        name='Test Class',
                        description='A test class for development purposes',
                        teacher_id=test_teacher.id
                    )
                    db.session.add(test_class)
                    db.session.commit()
                    print("Test class created!")
        except Exception as e:
            print(f"Error initializing database: {e}")
    app.run(debug=True) 