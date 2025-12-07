from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
import os
from datetime import datetime
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
from werkzeug.utils import secure_filename
import sqlite3
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
            
            # Don't delete existing folder - just ensure it exists
            try:
                os.makedirs(student_folder, exist_ok=True)
            except PermissionError:
                flash(f'Permission denied to access student folder for {name}. Please check folder permissions.', 'error')
                return redirect(url_for('add_student'))
            
            # Save uploaded images (overwrite existing ones)
            image_count = 0
            for file in valid_files:
                filename = secure_filename(file.filename)
                if filename:
                    # Use sequential numbering (1.jpg, 2.jpg, etc.)
                    file_path = os.path.join(student_folder, f"{image_count + 1}.jpg")
                    file.save(file_path)
                    image_count += 1
            
            if image_count > 0:
                flash(f'Student {name} added successfully with {image_count} images!', 'success')
            else:
                flash(f'Student {name} reactivated but no images were uploaded!', 'warning')
            return redirect(url_for('classroom'))
        else:
            flash('Error adding student. Please try again.', 'error')
    
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
    """Video streaming route with face recognition"""
    if not CV2_AVAILABLE or not NUMPY_AVAILABLE:
        # Return a placeholder image if OpenCV or numpy is not available
        def generate_placeholder():
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + b'Camera not available on cloud hosting' + b'\r\n'
        
        return Response(generate_placeholder(), mimetype='multipart/x-mixed-replace; boundary=frame')
    
    def generate_frames():
        try:
            from simple_face_recognition import SimpleFaceRecognition
            recognizer = SimpleFaceRecognition()
            
            # Try different camera indices
            camera = None
            for camera_index in [0, 1, 2]:
                camera = cv2.VideoCapture(camera_index)
                if camera.isOpened():
                    print(f"Camera {camera_index} opened successfully")
                    break
                else:
                    camera.release()
                    camera = None
            
            if camera is None:
                print("No camera found")
                # Generate a placeholder frame
                while True:
                    # Create a black frame with text
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(frame, "Camera Not Found", (200, 240), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                    ret, buffer = cv2.imencode('.jpg', frame)
                    frame = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                    break
            
            recognized_students = set()
            
            while True:
                success, frame = camera.read()
                if not success:
                    print("Failed to read from camera")
                    break
                else:
                    # Perform face recognition
                    try:
                        names, processed_frame = recognizer.recognize_face(frame)
                        
                        if names:
                            print(f"Recognized faces: {names}")
                        
                        # Mark attendance for newly recognized students
                        for name in names:
                            if name not in recognized_students:
                                print(f"New recognition: {name}")
                                mark_attendance_for_student(name)
                                recognized_students.add(name)
                            else:
                                print(f"Already recognized: {name}")
                    except Exception as e:
                        print(f"Face recognition error: {e}")
                        processed_frame = frame
                    
                    ret, buffer = cv2.imencode('.jpg', processed_frame)
                    frame = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            
            camera.release()
            
        except Exception as e:
            print(f"Camera feed error: {e}")
            # Generate error frame
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, f"Camera Error: {str(e)}", (100, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def mark_attendance_for_student(student_name):
    """Mark attendance for a recognized student"""
    try:
        print(f"Attempting to mark attendance for: {student_name}")
        conn = get_db_connection()
        student = conn.execute('SELECT id FROM students WHERE name = ? AND is_active = 1', (student_name,)).fetchone()
        
        if student:
            print(f"Found student ID: {student['id']}")
            from database import mark_attendance
            success = mark_attendance(student['id'])
            print(f"Attendance marked for {student_name}: {success}")
            
            if success:
                flash(f'Attendance marked for {student_name}!', 'success')
        else:
            print(f"Student not found: {student_name}")
        
        conn.close()
    except Exception as e:
        print(f"Error marking attendance: {e}")
        import traceback
        traceback.print_exc()

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

@app.route('/train_faces')
def train_faces():
    """Trigger face training"""
    try:
        from simple_face_recognition import SimpleFaceRecognition
        recognizer = SimpleFaceRecognition()
        success = recognizer.train_faces()
        
        if success:
            flash('Face training completed successfully using OpenCV!', 'success')
        else:
            flash('Face training failed. No student images found.', 'error')
    except Exception as e:
        flash(f'Error during training: {str(e)}', 'error')
    
    return redirect(url_for('classroom'))

@app.route('/reset_attendance')
def reset_attendance():
    """Reset all attendance records"""
    try:
        from database import reset_all_attendance
        success = reset_all_attendance()
        
        if success:
            flash('All attendance records have been reset successfully!', 'success')
        else:
            flash('Failed to reset attendance records.', 'error')
    except Exception as e:
        flash(f'Error resetting attendance: {str(e)}', 'error')
    
    return redirect(url_for('attendance'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
