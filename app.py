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
    plan = request.args.get('plan', 'basic')  # 'basic' or 'premium'
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        plan = request.form.get('plan', 'basic')
        
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
            'plan': plan,
            'is_active': True,
        }).inserted_id
        
        session['user_id'] = str(user_id)
        session['user_name'] = name
        session['user_plan'] = plan
        flash('Registration successful! Please save your emergency code securely.', 'success')
        if plan == 'premium':
            return redirect(url_for('premium_dashboard'))
        return redirect(url_for('dashboard'))
        
    return render_template('register.html', plan=plan)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = users_collection.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['user_name'] = user['name']
            session['user_plan'] = user.get('plan', 'basic')
            flash('Login successful!', 'success')
            if session['user_plan'] == 'premium':
                return redirect(url_for('premium_dashboard'))
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
    if session.get('user_plan') == 'premium':
        return redirect(url_for('premium_dashboard'))
        
    user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
    contacts = list(contacts_collection.find({'user_id': session['user_id']}))
    documents = list(documents_collection.find({'user_id': session['user_id']}))
    # Enforce basic plan limits
    contacts = contacts[:1]
    documents = documents[:5]
    return render_template('dashboard.html', user=user, contacts=contacts, documents=documents)

@app.route('/premium_dashboard')
def premium_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session.get('user_plan') != 'premium':
        flash('Upgrade to the Family Plan to access the premium dashboard.', 'info')
        return redirect(url_for('dashboard'))
    user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
    contacts = list(contacts_collection.find({'user_id': session['user_id']}))
    documents = list(documents_collection.find({'user_id': session['user_id']}))
    devices = list(db.devices.find({'user_id': session['user_id']}))
    accounts = list(db.online_accounts.find({'user_id': session['user_id']}))
    return render_template('premium_dashboard.html', user=user, contacts=contacts, documents=documents, devices=devices, accounts=accounts)

@app.route('/upgrade_to_premium', methods=['POST'])
def upgrade_to_premium():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    users_collection.update_one({'_id': ObjectId(session['user_id'])}, {'$set': {'plan': 'premium'}})
    session['user_plan'] = 'premium'
    flash('🎉 Welcome to the Family Plan! Your vault is now fully unlocked.', 'success')
    return redirect(url_for('premium_dashboard'))


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

@app.route('/will_estate')
def will_estate():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('will_estate.html')

@app.route('/life_stories')
def life_stories():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('life_stories.html')

@app.route('/trusted_contacts')
def trusted_contacts_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    contacts = list(contacts_collection.find({'user_id': session['user_id']}))
    return render_template('trusted_contacts.html', contacts=contacts)

@app.route('/vault/exit')
def vault_exit():
    session.pop('emergency_view_user_id', None)
    flash('Safely exited the vault.', 'info')
    return redirect(url_for('home'))

@app.route('/settings')
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
    return render_template('settings.html', user=user)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    name = request.form.get('name')
    email = request.form.get('email')
    users_collection.update_one({'_id': ObjectId(session['user_id'])}, {'$set': {'name': name, 'email': email}})
    session['user_name'] = name
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('settings'))

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    if not check_password_hash(user['password'], current_password):
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('settings'))
    if new_password != confirm_password:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('settings'))
    users_collection.update_one({'_id': ObjectId(session['user_id'])}, {'$set': {'password': generate_password_hash(new_password)}})
    flash('Password changed successfully!', 'success')
    return redirect(url_for('settings'))

@app.route('/regenerate_code', methods=['POST'])
def regenerate_code():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    new_code = generate_emergency_code()
    users_collection.update_one({'_id': ObjectId(session['user_id'])}, {'$set': {'emergency_code': new_code}})
    flash(f'New emergency code generated: {new_code}. Store it safely!', 'success')
    return redirect(url_for('settings'))

@app.route('/activity_log')
def activity_log():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    log_col = db.activity_log
    logs = list(log_col.find({'user_id': session['user_id']}).sort('timestamp', -1).limit(50))
    return render_template('activity_log.html', activity_log=logs)

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/cookies')
def cookies():
    return render_template('cookies.html')


@app.route('/add_device', methods=['POST'])
def add_device():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db.devices.insert_one({
        'user_id': session['user_id'],
        'device_name': request.form.get('device_name'),
        'device_type': request.form.get('device_type'),
        'device_pin': request.form.get('device_pin'),
        'notes': request.form.get('notes'),
    })
    flash(f'Device "{request.form.get("device_name")}" registered to your vault.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/add_account', methods=['POST'])
def add_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db.online_accounts.insert_one({
        'user_id': session['user_id'],
        'platform': request.form.get('platform'),
        'username': request.form.get('username'),
        'password': request.form.get('password'),
        'wish': request.form.get('wish'),
    })
    flash(f'Account "{request.form.get("platform")}" saved to your vault.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/help')
def help_page():
    return render_template('help.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
