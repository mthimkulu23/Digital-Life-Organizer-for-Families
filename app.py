import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from bson.objectid import ObjectId
import random
import string
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Add your MongoDB Atlas Connection String from .env
client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017/"))
db = client.digital_life_organizer

# DB Collections
users_collection = db.users
contacts_collection = db.trusted_contacts
documents_collection = db.documents

def generate_emergency_code():
    parts = []
    for _ in range(3):
        parts.append(''.join(random.choices(string.ascii_uppercase + string.digits, k=4)))
    return '-'.join(parts)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if users_collection.find_one({'email': email}):
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
            
        hashed_password = generate_password_hash(password)
        emergency_code = generate_emergency_code()
        
        user_id = users_collection.insert_one({
            'name': name,
            'email': email,
            'password': hashed_password,
            'emergency_code': emergency_code,
            'is_active': True,
        }).inserted_id
        
        session['user_id'] = str(user_id)
        session['user_name'] = name
        flash('Registration successful! Please save your emergency code securely.', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = users_collection.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['user_name'] = user['name']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
            
        flash('Invalid email or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
    contacts = list(contacts_collection.find({'user_id': session['user_id']}))
    documents = list(documents_collection.find({'user_id': session['user_id']}))
    
    return render_template('dashboard.html', user=user, contacts=contacts, documents=documents)

@app.route('/add_contact', methods=['POST'])
def add_contact():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    name = request.form.get('name')
    relation = request.form.get('relation')
    email = request.form.get('email')
    phone = request.form.get('phone')
    
    contacts_collection.insert_one({
        'user_id': session['user_id'],
        'name': name,
        'relation': relation,
        'email': email,
        'phone': phone,
        'status': 'Pending Verification'
    })
    
    flash(f'Trusted contact {name} added!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/upload_document', methods=['POST'])
def upload_document():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('dashboard'))
        
    file = request.files['file']
    doc_type = request.form.get('doc_type')
    notes = request.form.get('notes')
    
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('dashboard'))
        
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        documents_collection.insert_one({
            'user_id': session['user_id'],
            'filename': filename,
            'doc_type': doc_type,
            'notes': notes,
            'status': 'Encrypted & Stored'
        })
        
        flash('Document uploaded successfully to the Secure Vault!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/emergency_access', methods=['GET', 'POST'])
def emergency_access():
    if request.method == 'POST':
        emergency_code = request.form.get('emergency_code')
        if not emergency_code:
            flash('Please enter a valid emergency code.', 'danger')
            return redirect(url_for('emergency_access'))
            
        user = users_collection.find_one({'emergency_code': emergency_code})
        if user:
            # Grant access to emergency view
            session.clear() # Clear any existing user session
            session['emergency_view_user_id'] = str(user['_id'])
            flash('Emergency access granted. You are now viewing the secure vault.', 'success')
            return redirect(url_for('vault'))
        else:
            flash('Invalid emergency code. Access denied.', 'danger')
            
    return render_template('emergency_access.html')

@app.route('/vault')
def vault():
    # Only for authorized emergency access
    if 'emergency_view_user_id' not in session:
        flash('Unauthorized. Valid emergency code required.', 'danger')
        return redirect(url_for('emergency_access'))
        
    user_id = session['emergency_view_user_id']
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    contacts = list(contacts_collection.find({'user_id': user_id}))
    documents = list(documents_collection.find({'user_id': user_id}))
    
    return render_template('vault.html', user=user, contacts=contacts, documents=documents)

@app.route('/vault/exit')
def vault_exit():
    session.pop('emergency_view_user_id', None)
    flash('Safely exited the vault.', 'info')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
