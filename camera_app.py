from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
import sqlite3
import cv2
import os
import pickle
import base64
from datetime import datetime
from werkzeug.utils import secure_filename
import threading
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Configuration
UPLOAD_FOLDER = 'static/uploads'
STUDENT_IMAGES = 'static/student_images'
DATABASE_FILE = 'classroom.db'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STUDENT_IMAGES, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Camera state
camera_active = False
camera_thread = None
current_frame = None

# Initialize database
from database import init_database
init_database()

# Allowed image extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    """Main dashboard"""
    conn = get_db_connection()
    students = conn.execute('SELECT * FROM students WHERE is_active = 1 ORDER BY name').fetchall()
    
    # Get today's attendance
    today = datetime.now().strftime('%Y-%m-%d')
    attendance = conn.execute('''
        SELECT s.name, a.time_in 
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE a.date = ? AND s.is_active = 1
        ORDER BY a.time_in
    ''', (today,)).fetchall()
    
    conn.close()
    
    return render_template('index.html', students=students, attendance=attendance)

@app.route('/classroom')
def classroom():
    """Classroom management page"""
    conn = get_db_connection()
    students = conn.execute('SELECT * FROM students WHERE is_active = 1 ORDER BY name').fetchall()
    conn.close()
    return render_template('classroom.html', students=students)

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    """Add new student page"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        roll_number = request.form.get('roll_number', '').strip()
        email = request.form.get('email', '').strip()
        
        if not name:
            flash('Student name is required!', 'error')
            return render_template('add_student.html')
        
        # Handle image upload
        if 'images' not in request.files:
            flash('Please select at least one image!', 'error')
            return render_template('add_student.html')
        
        files = request.files.getlist('images')
        valid_files = [f for f in files if f and f.filename and allowed_file(f.filename)]
        
        if not valid_files:
            flash('Please upload valid image files!', 'error')
            return render_template('add_student.html')
        
        # Add student to database
        from database import add_student
        student_id = add_student(name, roll_number, email)
        
        if student_id:
            # Create student folder
            student_folder = os.path.join(STUDENT_IMAGES, secure_filename(name.lower()))
            os.makedirs(student_folder, exist_ok=True)
            
            # Save uploaded images
            image_count = 0
            for file in valid_files:
                filename = secure_filename(file.filename)
                if filename:
                    file_path = os.path.join(student_folder, f"{image_count + 1}.jpg")
                    file.save(file_path)
                    image_count += 1
            
            flash(f'Student {name} added successfully with {image_count} images!', 'success')
            return redirect(url_for('classroom'))
        else:
            flash('Student with this name already exists!', 'error')
    
    return render_template('add_student.html')

@app.route('/delete_student/<int:student_id>')
def delete_student(student_id):
    """Delete a student"""
    from database import delete_student
    delete_student(student_id)
    flash('Student deleted successfully!', 'success')
    return redirect(url_for('classroom'))

@app.route('/attendance')
def attendance():
    """Attendance page with camera"""
    conn = get_db_connection()
    students = conn.execute('SELECT * FROM students WHERE is_active = 1 ORDER BY name').fetchall()
    
    # Get today's attendance
    today = datetime.now().strftime('%Y-%m-%d')
    attendance_records = conn.execute('''
        SELECT s.name, a.time_in, a.time_out
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE a.date = ? AND s.is_active = 1
        ORDER BY a.time_in
    ''', (today,)).fetchall()
    
    conn.close()
    return render_template('attendance.html', students=students, attendance=attendance_records)

@app.route('/camera_feed')
def camera_feed():
    """Video streaming route"""
    def generate_frames():
        camera = cv2.VideoCapture(0)
        while True:
            success, frame = camera.read()
            if not success:
                break
            else:
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        camera.release()
    
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    """Mark attendance via API"""
    student_name = request.json.get('student_name')
    
    if not student_name:
        return jsonify({'success': False, 'message': 'Student name required'})
    
    conn = get_db_connection()
    student = conn.execute('SELECT id FROM students WHERE name = ? AND is_active = 1', (student_name,)).fetchone()
    
    if student:
        from database import mark_attendance
        success = mark_attendance(student['id'])
        
        if success:
            conn.close()
            return jsonify({'success': True, 'message': f'Attendance marked for {student_name}'})
        else:
            conn.close()
            return jsonify({'success': False, 'message': 'Attendance already marked today'})
    else:
        conn.close()
        return jsonify({'success': False, 'message': 'Student not found'})

@app.route('/train_faces')
def train_faces():
    """Train face recognition"""
    try:
        # This would integrate with your existing face recognition training
        flash('Face training feature requires additional setup. See documentation.', 'info')
        return redirect(url_for('classroom'))
    except Exception as e:
        flash(f'Error during training: {str(e)}', 'error')
        return redirect(url_for('classroom'))

@app.route('/api/students')
def api_students():
    """API endpoint for students data"""
    conn = get_db_connection()
    students = conn.execute('SELECT id, name FROM students WHERE is_active = 1').fetchall()
    conn.close()
    return jsonify([dict(row) for row in students])

@app.route('/api/attendance')
def api_attendance():
    """API endpoint for attendance data"""
    today = datetime.now().strftime('%Y-%m-%d')
    conn = get_db_connection()
    attendance = conn.execute('''
        SELECT s.name, a.time_in, a.time_out
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE a.date = ? AND s.is_active = 1
        ORDER BY a.time_in
    ''', (today,)).fetchall()
    conn.close()
    return jsonify([dict(row) for row in attendance])

if __name__ == '__main__':
    app.run(debug=True, port=5000)
