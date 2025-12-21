from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response, session
import os
from datetime import datetime, timedelta
import cv2
import numpy as np
from werkzeug.utils import secure_filename
import shutil
import sqlite3
import json

from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# ... existing code ...

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User Model
class User(UserMixin):
    def __init__(self, id, username, full_name):
        self.id = id
        self.username = username
        self.full_name = full_name

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user['id'], user['username'], user['full_name'])
    return None

# Auth Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            # Update last_login
            try:
                conn = get_db_connection()
                conn.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user['id'],))
                conn.commit()
                conn.close()
            except: pass
            
            user_obj = User(user['id'], user['username'], user['full_name'])
            login_user(user_obj)
            flash(f'Welcome back, {user["full_name"]}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
            
    return render_template('login.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
        if user:
            import secrets
            from datetime import timedelta, datetime
            token = secrets.token_urlsafe(16)
            expiry = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
            
            conn.execute('UPDATE users SET reset_token = ?, reset_token_expiry = ? WHERE id = ?',
                         (token, expiry, user['id']))
            conn.commit()
            
            # Simulation
            reset_link = url_for('reset_password', token=token, _external=True)
            print(f"\n{'='*50}\nPASSWORD RESET SIMULATION for: {email}\nLink: {reset_link}\n{'='*50}\n")
            flash('Reset link sent to console (Development Mode)', 'info')
        else:
            flash('Email not found', 'error')
        conn.close()
        return redirect(url_for('login'))
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE reset_token = ? AND reset_token_expiry > CURRENT_TIMESTAMP', (token,)).fetchone()
    
    if not user:
        conn.close()
        flash('Invalid or expired reset token', 'error')
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        
        if password != confirm:
            flash('Passwords do not match', 'error')
            return render_template('reset_password.html')
            
        hashed = generate_password_hash(password)
        conn.execute('UPDATE users SET password_hash = ?, reset_token = NULL, reset_token_expiry = NULL WHERE id = ?',
                     (hashed, user['id']))
        conn.commit()
        conn.close()
        
        flash('Password reset successful! Please login.', 'success')
        return redirect(url_for('login'))
        
    conn.close()
    return render_template('reset_password.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        
        hashed_password = generate_password_hash(password)
        
        try:
            conn = get_db_connection()
            conn.execute('INSERT INTO users (username, password_hash, full_name) VALUES (?, ?, ?)',
                         (username, hashed_password, full_name))
            conn.commit()
            conn.close()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists!', 'error')
            
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))
@app.after_request
def add_header(response):
    """Disable caching"""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# Configuration
UPLOAD_FOLDER = 'static/uploads'
STUDENT_IMAGES = 'static/student_images'
DATABASE_FILE = 'classroom.db'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STUDENT_IMAGES, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024  # 64MB max file size

# Initialize database
from database import init_database
init_database()

# Initialize face recognition - Using AI (InsightFace)
face_recognizer = None

# Initialize AI Face Recognition
try:
    from ai_face_recognition import AIFaceRecognition
    face_recognizer = AIFaceRecognition()
    print("[OK] AI Face Recognition (InsightFace) initialized")
except Exception as e:
    print(f"[ERROR] AI Integration Error: {e}")
    face_recognizer = None

# Global camera variable
camera = None

@app.route('/get_latest_attendance')
def get_latest_attendance():
    """Get latest attendance for AJAX update"""
    class_id = request.args.get('class_id')
    
    # Get today's attendance
    try:
        from database import get_attendance_report
        # Just getting today's records for now
        # Ideally we would have a dedicated function for "today's live attendance"
        # but reusing get_attendance_report for today is fine
        today = datetime.now().strftime('%Y-%m-%d')
        # We need a new DB function or query for this specific view effectively
        
        # Quick inline query to stop the 404s
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        query = """
            SELECT s.name, s.roll_number, a.time_in 
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            WHERE a.date = ?
        """
        params = [today]
        
        if class_id:
            query += " AND a.class_id = ?"
            params.append(class_id)
            
        query += " ORDER BY a.timestamp DESC"
        
        cursor.execute(query, params)
        records = cursor.fetchall()
        conn.close()
        
        result = []
        for r in records:
            result.append({
                'student_name': r[0],
                'roll_number': r[1],
                'time_in': r[2]
            })
            
        return jsonify(result)
    except Exception as e:
        print(f"Error fetching attendance: {e}")
        return jsonify([])

# Allowed image extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# ============================================================================
# DASHBOARD & MAIN ROUTES
# ============================================================================

# Old index route removed in favor of the login-protected one below
# ============================================================================
# CLASS MANAGEMENT ROUTES
# ============================================================================

@app.route('/classes')
def classes():
    """View all classes"""
    conn = get_db_connection()
    classes = conn.execute('SELECT * FROM classes WHERE is_active = 1 ORDER BY name').fetchall()
    
    # Get student count for each class
    class_data = []
    for cls in classes:
        student_count = conn.execute(
            'SELECT COUNT(*) as count FROM students WHERE class_id = ? AND is_active = 1',
            (cls['id'],)
        ).fetchone()['count']
        
    """Manage classes"""
    conn = get_db_connection()
    # Filter by user
    classes = conn.execute('SELECT *, (SELECT COUNT(*) FROM students WHERE class_id = classes.id AND is_active = 1) as student_count FROM classes WHERE is_active = 1 AND user_id = ?', (current_user.id,)).fetchall()
    conn.close()
    return render_template('classes.html', classes=classes)

@app.route('/add_class', methods=['GET', 'POST'])
@login_required
def add_class():
    """Add new class"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        subject = request.form.get('subject', '').strip()
        room_number = request.form.get('room_number', '').strip() # Changed 'room' to 'room_number' for consistency
        schedule = request.form.get('schedule', '').strip()
        
        if not name:
            flash('Class name is required!', 'error')
        else:
            try:
                # We need to update add_class in database.py to accept user_id
                # Or execute raw SQL here:
                conn = get_db_connection()
                conn.execute('INSERT INTO classes (name, subject, room_number, schedule, user_id) VALUES (?, ?, ?, ?, ?)',
                            (name, subject, room_number, schedule, current_user.id))
                conn.commit()
                conn.close()
                    
                flash('Class added successfully!', 'success')
                return redirect(url_for('classes'))
            except sqlite3.IntegrityError:
                flash('Class name must be unique!', 'error')
            except Exception as e:
                flash(f'Error adding class: {e}', 'error')
                
    return render_template('add_class.html')



# ============================================================================
# STUDENT MANAGEMENT ROUTES
# ============================================================================

@app.route('/students')
@app.route('/students/<int:class_id>')
@login_required
def students(class_id=None):
    """View all students or students in a specific class"""
    conn = get_db_connection()
    
    if class_id:
        # Verify class belongs to user
        cls = conn.execute('SELECT * FROM classes WHERE id = ? AND user_id = ?', (class_id, current_user.id)).fetchone()
        if not cls:
            flash('Access Denied', 'error')
            conn.close()
            return redirect(url_for('classes'))

        students = conn.execute('''
            SELECT s.*, c.name as class_name 
            FROM students s
            JOIN classes c ON s.class_id = c.id
            WHERE s.is_active = 1 AND s.class_id = ?
            ORDER BY s.name
        ''', (class_id,)).fetchall()
        current_class = cls
    else:
        # Show all students for THIS user's classes
        students = conn.execute('''
            SELECT s.*, c.name as class_name 
            FROM students s
            JOIN classes c ON s.class_id = c.id
            WHERE s.is_active = 1 AND c.user_id = ?
            ORDER BY s.name
        ''', (current_user.id,)).fetchall()
        current_class = None
    
    classes = conn.execute('SELECT * FROM classes WHERE is_active = 1 AND user_id = ?', (current_user.id,)).fetchall()
    conn.close()
    
    return render_template('students.html', 
                         students=students, 
                         classes=classes,
                         current_class=current_class)

@app.route('/add_student', methods=['GET', 'POST'])
@login_required
def add_student():
    """Add new student page"""
    conn = get_db_connection()
    # Only show THIS user's classes
    classes = conn.execute('SELECT * FROM classes WHERE is_active = 1 AND user_id = ?', (current_user.id,)).fetchall()
    conn.close()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        roll_number = request.form.get('roll_number', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        class_id = request.form.get('class_id', 1, type=int)
        
        if not name:
            flash('Student name is required!', 'error')
            return render_template('add_student.html', classes=classes)
        
        # Handle image upload
        if 'images' not in request.files:
            flash('Please select at least one image!', 'error')
            return render_template('add_student.html', classes=classes)
        
        # Hybrid File Collection (Works with BOTH single and multi-input forms)
        files = request.files.getlist('images')
        
        # If 'images' list is empty, check for individual image1, image2... fields
        if not files:
            print("DEBUG: No 'images' list found, checking individual fields...")
            for i in range(1, 6):
                f = request.files.get(f'image{i}')
                if f:
                    files.append(f)

        print(f"DEBUG: Processing {len(files)} potential files")
        
        valid_files = []
        for f in files:
            if f and f.filename and allowed_file(f.filename):
                valid_files.append(f)
            elif f and f.filename:
                print(f"DEBUG: Rejected file extension: {f.filename}")
        
        print(f"DEBUG: Valid files count: {len(valid_files)}")
        
        if len(valid_files) < 1:
            print("DEBUG: No valid files found!")
            flash('Please upload at least one valid image (JPG/PNG)!', 'error')
            return render_template('add_student.html', classes=classes)
        
        # Add student to database
        from database import add_student
        student_id = add_student(name, roll_number, email, phone, class_id)
        print(f"DEBUG: Added student to DB with ID: {student_id}")
        
        if student_id:
            # Create student folder with ID prefix to ensure uniqueness
            folder_name = f"{student_id}_{secure_filename(name.lower().replace(' ', '_'))}"
            student_folder = os.path.join(STUDENT_IMAGES, folder_name)
            os.makedirs(student_folder, exist_ok=True)
            
            # Save uploaded images
            image_count = 0
            for file in valid_files:
                filename = f"{image_count + 1}.jpg"
                file_path = os.path.join(student_folder, filename)
                file.save(file_path)
                image_count += 1
            
            flash(f'Student {name} added successfully with {image_count} images! Please train the system.', 'success')
            return redirect(url_for('students'))
        else:
            flash('Error adding student. Roll number might already exist.', 'error')
    
    return render_template('add_student.html', classes=classes)

@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    """Edit student information"""
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    classes = conn.execute('SELECT * FROM classes WHERE is_active = 1').fetchall()
    
    if not student:
        flash('Student not found!', 'error')
        return redirect(url_for('students'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        roll_number = request.form.get('roll_number', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        class_id = request.form.get('class_id', type=int)
        
        from database import update_student
        update_student(student_id, name, roll_number, email, phone, class_id)
        
        flash('Student updated successfully!', 'success')
        conn.close()
        return redirect(url_for('students'))
    
    conn.close()
    return render_template('edit_student.html', student=student, classes=classes)

@app.route('/delete_student/<int:student_id>')
def delete_student(student_id):
    """Delete a student"""
    conn = get_db_connection()
    student = conn.execute('SELECT name FROM students WHERE id = ?', (student_id,)).fetchone()
    
    if student:
        # Try to delete student images folder (Try new format first, then legacy)
        secure_name = secure_filename(student['name'].lower().replace(' ', '_'))
        
        # New format: {id}_{name}
        new_folder_name = f"{student_id}_{secure_name}"
        new_student_folder = os.path.join(STUDENT_IMAGES, new_folder_name)
        
        # Legacy format: {name}
        legacy_folder_name = secure_name
        legacy_student_folder = os.path.join(STUDENT_IMAGES, legacy_folder_name)
        
        if os.path.exists(new_student_folder):
             try:
                shutil.rmtree(new_student_folder)
             except Exception as e:
                print(f"Error deleting new folder: {e}")
        elif os.path.exists(legacy_student_folder):
             try:
                shutil.rmtree(legacy_student_folder)
             except Exception as e:
                print(f"Error deleting legacy folder: {e}")
    
    conn.close()
    
    try:
        from database import delete_student
        delete_student(student_id)
    except Exception as e:
        print(f"Error deleting from DB: {e}")
        flash(f'Error deleting student: {e}', 'error')
        return redirect(url_for('students'))
    
    # Retrain system to update model immediately
    # try:
    #     if face_recognizer:
    #         face_recognizer.train_from_images()
    # except:
    #     pass
        
    flash('Student deleted successfully! Please retrain the system.', 'success')
    return redirect(url_for('students'))

# ============================================================================
# ATTENDANCE ROUTES
# ============================================================================

@app.route('/')
@login_required
def index():
    conn = get_db_connection()
    # Only count students belonging to THIS faculty's classes
    students_query = '''
        SELECT COUNT(*) 
        FROM students s
        JOIN classes c ON s.class_id = c.id
        WHERE c.user_id = ? AND s.is_active = 1
    '''
    students_count = conn.execute(students_query, (current_user.id,)).fetchone()[0]
    
    # Only count classes belonging to THIS faculty
    classes_count = conn.execute('SELECT COUNT(*) FROM classes WHERE user_id = ? AND is_active = 1', (current_user.id,)).fetchone()[0]
    
    # Attendance for today (filtered by user's classes)
    today = datetime.now().strftime('%Y-%m-%d')
    attendance_query = """
        SELECT COUNT(*) 
        FROM attendance a
        JOIN classes c ON a.class_id = c.id
        WHERE a.date = ? AND c.user_id = ?
    """
    attendance_count = conn.execute(attendance_query, (today, current_user.id)).fetchone()[0]
    
    # Recent attendance records
    recent_query = """
        SELECT s.name, c.name as class_name, a.time_in 
        FROM attendance a 
        JOIN students s ON a.student_id = s.id 
        JOIN classes c ON a.class_id = c.id
        WHERE c.user_id = ?
        ORDER BY a.created_at DESC LIMIT 5
    """
    recent_attendance = conn.execute(recent_query, (current_user.id,)).fetchall()
    
    # Get active classes for dashboard list
    classes = conn.execute('SELECT * FROM classes WHERE user_id = ? AND is_active = 1', (current_user.id,)).fetchall()
    
    conn.close()
    
    # Calculate rate
    attendance_rate = (attendance_count / students_count * 100) if students_count > 0 else 0
    
    return render_template('index.html', 
                         students_count=students_count,
                         classes_count=classes_count,
                         attendance_count=attendance_count,
                         attendance_rate=attendance_rate,
                         recent_attendance=recent_attendance,
                         classes=classes)

@app.route('/attendance')
@app.route('/attendance/<int:class_id>')
@login_required
def attendance(class_id=None):
    """Attendance page with camera"""
    conn = get_db_connection()
    
    # Get all classes for THIS user
    classes = conn.execute('SELECT * FROM classes WHERE is_active = 1 AND user_id = ?', (current_user.id,)).fetchall()
    
    # Get today's attendance
    today = datetime.now().strftime('%Y-%m-%d')
    
    if class_id:
        attendance_records = conn.execute('''
            SELECT s.id, s.name, s.roll_number, a.time_in, a.time_out
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            WHERE a.date = ? AND a.class_id = ? AND s.is_active = 1
            ORDER BY a.time_in DESC
        ''', (today, class_id)).fetchall()
        
        students = conn.execute('''
            SELECT * FROM students 
            WHERE class_id = ? AND is_active = 1 
            ORDER BY name
        ''', (class_id,)).fetchall()
        
        current_class = conn.execute('SELECT * FROM classes WHERE id = ?', (class_id,)).fetchone()
    else:

        # Show stats for ALL classes owned by this user
        attendance_records = conn.execute('''
            SELECT s.id, s.name, s.roll_number, a.time_in, a.time_out, c.name as class_name
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            JOIN classes c ON a.class_id = c.id
            WHERE a.date = ? AND s.is_active = 1 AND c.user_id = ?
            ORDER BY a.time_in DESC
        ''', (today, current_user.id)).fetchall()
        
        # Only show students belonging to THIS user
        students = conn.execute('''
            SELECT s.* FROM students s
            JOIN classes c ON s.class_id = c.id
            WHERE s.is_active = 1 AND c.user_id = ?
            ORDER BY s.name
        ''', (current_user.id,)).fetchall()
        current_class = None
    
    conn.close()
    
    return render_template('attendance.html',
                         classes=classes,
                         current_class=current_class,
                         attendance=attendance_records,
                         students=students,
                         selected_class_id=class_id)

@app.route('/verify_face', methods=['POST'])
@login_required
def verify_face():
    """Verify face from uploaded snapshot"""
    try:
        data = request.json
        if not data or 'image' not in data:
            return jsonify({'status': 'error', 'message': 'No image data'})
        
        # Decode base64 image
        import base64
        image_data = data['image'].split(',')[1]
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if face_recognizer:
            # We use a strict threshold for single-snap verification
            faces = face_recognizer.recognize_faces(frame, current_user.id, confidence_threshold=100)
            
            if faces:
                # Get best match
                best_match = min(faces, key=lambda x: x['raw_confidence'])
                
                if best_match['name'] != "Unknown":
                    # Mark attendance
                    student_id = best_match['student_id']
                    
                    # Log attendance in DB
                    from database import mark_attendance
                    
                    try:
                        # Determine class to mark attendance in
                        target_class_id = data.get('class_id')
                        
                        # Validate target_class_id (might be 'None' string or empty)
                        if not target_class_id or str(target_class_id).lower() == 'none' or str(target_class_id) == '':
                             # Fallback: Mark in student's enrolled class
                             conn = get_db_connection()
                             row = conn.execute('SELECT class_id FROM students WHERE id = ?', (student_id,)).fetchone()
                             conn.close()
                             if row:
                                 target_class_id = row[0]
                             else:
                                 target_class_id = 1 # Last resort
                        else:
                            # Use provided class ID
                            try:
                                target_class_id = int(target_class_id)
                            except:
                                target_class_id = 1

                        result = mark_attendance(student_id, target_class_id)
                        
                        if result:
                            msg = f"Welcome, {best_match['name']}! Attendance Marked."
                        else:
                            msg = f"Welcome back, {best_match['name']}! (Already marked)"
                        
                        # Fix: Convert numpy integers to python int for JSON
                        safe_match = {
                            'name': best_match['name'],
                            'student_id': int(best_match['student_id']) if best_match['student_id'] is not None else None,
                            'confidence': float(best_match['confidence']),
                            'raw_confidence': float(best_match['raw_confidence']),
                            'roll_number': best_match.get('roll_number', '') # If available
                        }
                        
                        now_str = datetime.now().strftime('%I:%M %p')
                            
                        return jsonify({
                            'status': 'success',
                            'student': safe_match,
                            'message': msg,
                            'attendance_marked': True,
                            'time_in': now_str
                        })
                    except Exception as db_err:
                        print(f"DB Error: {db_err}")
                        return jsonify({'status': 'error', 'message': f"Database Error: {str(db_err)}"})
                else:
                     return jsonify({'status': 'unknown', 'message': 'Face not recognized. Try getting closer.'})
            else:
                 return jsonify({'status': 'no_face', 'message': 'No face detected in photo.'})
        else:
            return jsonify({'status': 'error', 'message': 'System not trained yet.'})

    except Exception as e:
        print(f"Verification Check Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f"Server Error: {str(e)}"})

@app.route('/stop_camera')
def stop_camera():
    """Stop the camera feed"""
    global camera
    if camera:
        camera.release()
        camera = None
    return jsonify({'status': 'camera_stopped'})

@app.route('/camera_feed')
@app.route('/camera_feed/<int:class_id>')
@login_required
def camera_feed(class_id=None):
    """Video streaming route with face recognition"""
    
    # Capture user ID for the thread
    user_id = current_user.id
    
    # Store class_id in session for use in frame generation
    if class_id:
        session['current_class_id'] = class_id
    
    def generate_frames():
        camera = None
        recognized_students = set()  # Track recognized students in this session
        last_recognition_time = {}  # Track last recognition time for each student
        
        try:
            # Try to open camera
            for camera_index in [0, 1, 2]:
                camera = cv2.VideoCapture(camera_index)
                if camera.isOpened():
                    print(f"✓ Camera {camera_index} opened")
                    break
                camera.release()
                camera = None
            
            if camera is None:
                # Generate error frame
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(frame, "Camera Not Available", (150, 240),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                ret, buffer = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                return
            
            frame_count = 0
            
            while True:
                success, frame = camera.read()
                if not success:
                    break
                
                frame_count += 1
                
                # Process every 3rd frame for performance
                if frame_count % 3 == 0 and face_recognizer:
                    try:
                        # Recognize faces using user-specific model
                        recognized_faces = face_recognizer.recognize_faces(frame, user_id)
                        
                        # Draw faces and mark attendance
                        current_time = datetime.now()
                        
                        for face in recognized_faces:
                            if face['student_id'] and face['name'] != "Unknown":
                                student_id = face['student_id']
                                
                                # Check if we should mark attendance (not marked in last 5 seconds)
                                if student_id not in last_recognition_time or \
                                   (current_time - last_recognition_time[student_id]).seconds > 5:
                                    
                                    # Mark attendance
                                    from database import mark_attendance
                                    cls_id = session.get('current_class_id', 1)
                                    
                                    if mark_attendance(student_id, cls_id):
                                        recognized_students.add(face['name'])
                                        print(f"✓ Attendance marked for {face['name']}")
                                    
                                    last_recognition_time[student_id] = current_time
                        
                        # Draw faces on frame
                        frame = face_recognizer.draw_faces(frame, recognized_faces)
                        
                        # Add info text
                        cv2.putText(frame, f"Recognized: {len(recognized_students)}", 
                                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    except Exception as e:
                        print(f"Recognition error: {e}")
                
                # Encode frame
                ret, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
                
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        except Exception as e:
            print(f"Camera error: {e}")
        
        finally:
            if camera:
                camera.release()
                print("Camera released")
    
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/mark_attendance_manual', methods=['POST'])
def mark_attendance_manual():
    """Manually mark attendance for a student"""
    student_id = request.form.get('student_id', type=int)
    class_id = request.form.get('class_id', 1, type=int)
    
    if not student_id:
        flash('Student ID required!', 'error')
        return redirect(url_for('attendance'))
    
    from database import mark_attendance
    success = mark_attendance(student_id, class_id)
    
    if success:
        flash('Attendance marked successfully!', 'success')
    else:
        flash('Attendance already marked for today!', 'warning')
    
    return redirect(url_for('attendance', class_id=class_id))



@app.route('/delete_class/<int:class_id>')
@login_required
def delete_class(class_id):
    """Delete a class"""
    conn = get_db_connection()
    # Check ownership
    class_obj = conn.execute('SELECT * FROM classes WHERE id = ? AND user_id = ?', (class_id, current_user.id)).fetchone()
    conn.close()
    
    if not class_obj:
        flash('Class not found or access denied!', 'error')
        return redirect(url_for('classes'))

    try:
        # Delete student images from filesystem first
        conn = get_db_connection()
        students = conn.execute('SELECT id FROM students WHERE class_id = ?', (class_id,)).fetchall()
        conn.close()
        
        for student in students:
            s_id = student['id']
            # Find and delete student folder
            if os.path.exists(STUDENT_IMAGES):
                for folder in os.listdir(STUDENT_IMAGES):
                    # Check for ID_Name format or legacy Name format (though legacy is hard to target by ID alone without precise name match)
                    # We focus on ID prefix
                    if folder.startswith(f"{s_id}_"):
                        folder_path = os.path.join(STUDENT_IMAGES, folder)
                        try:
                            shutil.rmtree(folder_path)
                            print(f"Deleted folder: {folder}")
                        except Exception as e:
                            print(f"Error deleting path {folder_path}: {e}")

        from database import delete_class
        delete_class(class_id)
        
        # Trigger model retrain (optional, but good practice)
        # We can just leave it to user to retrain
        
        flash('Class and all associated students permanently deleted!', 'success')
    except Exception as e:
        flash(f'Error deleting class: {e}', 'error')
        
    return redirect(url_for('classes'))

@app.route('/reset_attendance')
def reset_attendance():
    """Reset all attendance records"""
    from database import reset_all_attendance
    if reset_all_attendance():
        flash('All attendance records reset!', 'success')
    else:
        flash('Error resetting attendance!', 'error')
    return redirect(url_for('attendance'))

# ============================================================================
# TRAINING & SYSTEM ROUTES
# ============================================================================

@app.route('/train_faces')
@login_required
def train_faces():
    """Train face recognition system"""
    if not face_recognizer:
        flash('Face recognition system not available!', 'error')
        return redirect(url_for('students'))
    
    try:
        # Train model for THIS user
        success, message = face_recognizer.train_user_model(current_user.id, STUDENT_IMAGES)
        
        if success:
            flash(message, 'success')
        else:
            flash(f'Training failed: {message}', 'error')
    except Exception as e:
        flash(f'Training error: {str(e)}', 'error')
    
    return redirect(url_for('students'))

# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/api/stats')
@login_required
def api_stats():
    """Get system statistics for current user"""
    conn = get_db_connection()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Students owned by user
    s_query = "SELECT COUNT(*) as c FROM students s JOIN classes c ON s.class_id = c.id WHERE s.is_active = 1 AND c.user_id = ?"
    
    # Classes owned by user
    c_query = "SELECT COUNT(*) as c FROM classes WHERE is_active = 1 AND user_id = ?"
    
    # Attendance for user's classes
    a_query = """
        SELECT COUNT(DISTINCT a.student_id) as c 
        FROM attendance a 
        JOIN classes c ON a.class_id = c.id
        WHERE a.date = ? AND c.user_id = ?
    """
    
    stats = {
        'total_students': conn.execute(s_query, (current_user.id,)).fetchone()['c'],
        'total_classes': conn.execute(c_query, (current_user.id,)).fetchone()['c'],
        'today_attendance': conn.execute(a_query, (today, current_user.id)).fetchone()['c'],
    }
    
    conn.close()
    return jsonify(stats)

@app.route('/api/attendance/<date>')
def api_attendance_by_date(date):
    """Get attendance for a specific date"""
    from database import get_attendance_by_date
    records = get_attendance_by_date(date)
    return jsonify([dict(r) for r in records])

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Cleanup inactive users on startup
    try:
        from database import cleanup_inactive_users
        cleanup_inactive_users(days_limit=3)
    except Exception as e:
        print(f"Startup Cleanup Error: {e}")
        
    app.run(debug=True, host='0.0.0.0', port=5000)
