import sqlite3
import os
from datetime import datetime, timedelta
import shutil



def delete_user_data(user_id):
    """Hard delete ALL data for a user"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # 1. Get all classes for user
    classes = cursor.execute('SELECT id FROM classes WHERE user_id = ?', (user_id,)).fetchall()
    
    for cls in classes:
        cls_id = cls[0]
        # Get students
        students = cursor.execute('SELECT id FROM students WHERE class_id = ?', (cls_id,)).fetchall()
        
        for stu in students:
            s_id = stu[0]
            # Delete files
            img_dir = 'static/student_images'
            if os.path.exists(img_dir):
                 for f in os.listdir(img_dir):
                     if f.startswith(f"{s_id}_"):
                         try:
                             path = os.path.join(img_dir, f)
                             if os.path.isdir(path):
                                 shutil.rmtree(path)
                         except: pass

        # Delete attendance
        cursor.execute('DELETE FROM attendance WHERE class_id = ?', (cls_id,))
        # Delete students
        cursor.execute('DELETE FROM students WHERE class_id = ?', (cls_id,))
        
    # Delete classes
    cursor.execute('DELETE FROM classes WHERE user_id = ?', (user_id,))
    
    # Delete user models
    try:
        if os.path.exists(f'models/user_{user_id}.yml'):
            os.remove(f'models/user_{user_id}.yml')
        if os.path.exists(f'models/labels_{user_id}.pkl'):
            os.remove(f'models/labels_{user_id}.pkl')
    except: pass

    conn.commit()
    conn.close()

def cleanup_inactive_users(days_limit=3):
    """Remove users inactive for N days"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        limit_date = (datetime.now() - timedelta(days=days_limit)).strftime('%Y-%m-%d %H:%M:%S')
        
        users = cursor.execute('''
            SELECT id FROM users 
            WHERE (last_login IS NOT NULL AND last_login < ?)
            OR (last_login IS NULL AND created_at < ?)
        ''', (limit_date, limit_date)).fetchall()
        
        conn.close()
        
        count = 0
        for u in users:
            print(f"Cleaning up inactive User ID: {u[0]}")
            delete_user_data(u[0])
            
            # Finally delete user record
            conn = sqlite3.connect(DATABASE_FILE)
            conn.execute('DELETE FROM users WHERE id = ?', (u[0],))
            conn.commit()
            conn.close()
            count += 1
            
        if count > 0:
            print(f"Cleanup: Removed {count} inactive users.")
            
    except Exception as e:
        print(f"Cleanup Error: {e}")

DATABASE_FILE = 'classroom.db'

def init_database():
    """Initialize the SQLite database with enhanced schema"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # Create users table (Faculty)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Migration: Add last_login to users
    try:
        cursor.execute("SELECT last_login FROM users LIMIT 1")
    except sqlite3.OperationalError:
        print("Migrating DB: Adding last_login to users...")
        cursor.execute("ALTER TABLE users ADD COLUMN last_login TIMESTAMP")
    
    # Ensure active column exists for everyone if missing (safety)
    try:
         cursor.execute("SELECT is_active FROM students LIMIT 1")
    except:
         cursor.execute("ALTER TABLE students ADD COLUMN is_active BOOLEAN DEFAULT 1")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            subject TEXT,
            teacher_name TEXT,
            room_number TEXT,
            schedule TEXT,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Check if user_id exists in classes, if not add it (Migration)
    try:
        cursor.execute("SELECT user_id FROM classes LIMIT 1")
    except sqlite3.OperationalError:
        print("Migrating DB: Adding user_id to classes...")
        cursor.execute("ALTER TABLE classes ADD COLUMN user_id INTEGER DEFAULT 1")

    # Create students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_number TEXT UNIQUE,
            email TEXT,
            phone TEXT,
            class_id INTEGER DEFAULT 1,
            image_count INTEGER DEFAULT 0,
            face_encoding TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (class_id) REFERENCES classes (id)
        )
    ''')
    
    # Create attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            class_id INTEGER,
            date TEXT NOT NULL,
            time_in TEXT,
            time_out TEXT,
            status TEXT DEFAULT 'present',
            session_type TEXT DEFAULT 'regular',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students (id),
            FOREIGN KEY (class_id) REFERENCES classes (id)
        )
    ''')
    
    # Create face_encodings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS face_encodings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            encoding_data TEXT NOT NULL,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
    ''')
    
    # Create sessions table for class sessions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER,
            session_name TEXT,
            session_date TEXT,
            start_time TEXT,
            end_time TEXT,
            status TEXT DEFAULT 'scheduled',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (class_id) REFERENCES classes (id)
        )
    ''')
    
    # Insert default class if none exists
    cursor.execute('SELECT COUNT(*) FROM classes')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO classes (name, subject, teacher_name, room_number) 
            VALUES (?, ?, ?, ?)
        ''', ('Default Class', 'General', 'Admin', 'Room 101'))
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

def add_class(name, subject=None, teacher_name=None, room_number=None, schedule=None):
    """Add a new class"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            'INSERT INTO classes (name, subject, teacher_name, room_number, schedule) VALUES (?, ?, ?, ?, ?)',
            (name, subject, teacher_name, room_number, schedule)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_all_classes():
    """Get all active classes"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM classes WHERE is_active = 1 ORDER BY name')
    classes = cursor.fetchall()
    conn.close()
    return classes

def add_student(name, roll_number=None, email=None, phone=None, class_id=1):
    """Add a new student to the database"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    try:
        # Check if student already exists by roll number
        if roll_number:
            cursor.execute('SELECT id, is_active FROM students WHERE roll_number = ?', (roll_number,))
            existing = cursor.fetchone()
            
            if existing:
                # If exists but is inactive, reactivate it
                if not existing[1]:
                    cursor.execute('''
                        UPDATE students 
                        SET is_active = 1, name = ?, email = ?, phone = ?, class_id = ? 
                        WHERE roll_number = ?
                    ''', (name, email, phone, class_id, roll_number))
                    student_id = existing[0]
                else:
                    # Already active, return existing ID
                    return existing[0]
            else:
                # Add new student
                cursor.execute(
                    'INSERT INTO students (name, roll_number, email, phone, class_id) VALUES (?, ?, ?, ?, ?)',
                    (name, roll_number, email, phone, class_id)
                )
                student_id = cursor.lastrowid
        else:
            # No roll number, just add
            cursor.execute(
                'INSERT INTO students (name, roll_number, email, phone, class_id) VALUES (?, ?, ?, ?, ?)',
                (name, roll_number, email, phone, class_id)
            )
            student_id = cursor.lastrowid
        
        conn.commit()
        return student_id
    except sqlite3.IntegrityError as e:
        print(f"Database integrity error: {e}")
        return None
    finally:
        conn.close()

def get_all_students(class_id=None):
    """Get all students from database"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    if class_id:
        cursor.execute('SELECT * FROM students WHERE is_active = 1 AND class_id = ? ORDER BY name', (class_id,))
    else:
        cursor.execute('SELECT * FROM students WHERE is_active = 1 ORDER BY name')
    
    students = cursor.fetchall()
    conn.close()
    return students

def update_student(student_id, name=None, roll_number=None, email=None, phone=None, class_id=None):
    """Update student information"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if name:
        updates.append('name = ?')
        params.append(name)
    if roll_number:
        updates.append('roll_number = ?')
        params.append(roll_number)
    if email:
        updates.append('email = ?')
        params.append(email)
    if phone:
        updates.append('phone = ?')
        params.append(phone)
    if class_id:
        updates.append('class_id = ?')
        params.append(class_id)
    
    if updates:
        params.append(student_id)
        query = f"UPDATE students SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
    
    conn.close()

def delete_student(student_id):
    """Delete a student (soft delete)"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE students SET is_active = 0 WHERE id = ?', (student_id,))
    conn.commit()
    conn.close()

def mark_attendance(student_id, class_id=1, date=None, time_in=None):
    """Mark attendance for a student"""
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    if time_in is None:
        time_in = datetime.now().strftime('%H:%M:%S')
    
    try:
        # Increase timeout to 30s to handle locks
        with sqlite3.connect(DATABASE_FILE, timeout=30) as conn:
            cursor = conn.cursor()

            # Check if student belongs to a class owned by the same user?
            # Relaxed Rule: Allow marking if the target class belongs to the same user OR strict enroll is disabled.
            # Ideally, valid attendance implies the student IS in the class or it's a cross-class session.
            
            # Get Student's User (via Class)
            student_owner_query = '''
                SELECT c.user_id 
                FROM classes c 
                JOIN students s ON s.class_id = c.id 
                WHERE s.id = ?
            '''
            student_owner = cursor.execute(student_owner_query, (student_id,)).fetchone()
            
            # Get Target Class's User
            class_owner_query = 'SELECT user_id FROM classes WHERE id = ?'
            class_owner = cursor.execute(class_owner_query, (class_id,)).fetchone()
            
            if not student_owner or not class_owner:
                # Fallback: Student or Class invalid
                return False
                
            if student_owner[0] != class_owner[0]:
                print(f"Refused: Student {student_id} (User {student_owner[0]}) tried to attend Class {class_id} (User {class_owner[0]})")
                return False
            
            # If owners match, we allow cross-class attendance logic (e.g. combined class)
            # OR we can just allow it because it's the same teacher.
                
            # Check if already marked today
            cursor.execute(
                'SELECT id FROM attendance WHERE student_id = ? AND date = ? AND class_id = ?',
                (student_id, date, class_id)
            )
            
            existing = cursor.fetchone()
            
            if existing is None:
                cursor.execute(
                    'INSERT INTO attendance (student_id, class_id, date, time_in) VALUES (?, ?, ?, ?)',
                    (student_id, class_id, date, time_in)
                )
                conn.commit()
                return True
            
            return False # Already marked
            
    except Exception as e:
        print(f"Database Error in mark_attendance: {e}")
        raise e  # Re-raise to be caught by app.py
    return False

def get_attendance_by_date(date=None, class_id=None):
    """Get attendance records for a specific date"""
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    if class_id:
        cursor.execute('''
            SELECT s.id, s.name, s.roll_number, a.time_in, a.time_out, a.status
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            WHERE a.date = ? AND a.class_id = ? AND s.is_active = 1
            ORDER BY a.time_in
        ''', (date, class_id))
    else:
        cursor.execute('''
            SELECT s.id, s.name, s.roll_number, a.time_in, a.time_out, a.status
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            WHERE a.date = ? AND s.is_active = 1
            ORDER BY a.time_in
        ''', (date,))
    
    records = cursor.fetchall()
    conn.close()
    return records

def get_attendance_stats(class_id=None, start_date=None, end_date=None):
    """Get attendance statistics"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    if not start_date:
        start_date = datetime.now().strftime('%Y-%m-%d')
    if not end_date:
        end_date = start_date
    
    if class_id:
        cursor.execute('''
            SELECT 
                COUNT(DISTINCT student_id) as present_count,
                COUNT(*) as total_records
            FROM attendance
            WHERE date BETWEEN ? AND ? AND class_id = ?
        ''', (start_date, end_date, class_id))
    else:
        cursor.execute('''
            SELECT 
                COUNT(DISTINCT student_id) as present_count,
                COUNT(*) as total_records
            FROM attendance
            WHERE date BETWEEN ? AND ?
        ''', (start_date, end_date))
    
    stats = cursor.fetchone()
    conn.close()
    return stats

def save_face_encoding(student_id, encoding_data, image_path):
    """Save face encoding to database"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT INTO face_encodings (student_id, encoding_data, image_path) VALUES (?, ?, ?)',
        (student_id, encoding_data, image_path)
    )
    
    conn.commit()
    conn.close()

def delete_class(class_id):
    """Hard delete a class and its students completely"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    # 1. Delete Attendance for this class
    cursor.execute('DELETE FROM attendance WHERE class_id = ?', (class_id,))
    
    # 2. Delete Students in this class
    # (Attendance also references students, so deleting students might be redundant if we del attendance by class_id above, 
    # but some attendance might be cross-referenced? No, attendance has class_id)
    cursor.execute('DELETE FROM students WHERE class_id = ?', (class_id,))
    
    # 3. Delete Class
    cursor.execute('DELETE FROM classes WHERE id = ?', (class_id,))
    
    conn.commit()
    conn.close()

def reset_all_attendance():
    """Reset all attendance records"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM attendance')
        conn.commit()
        print("All attendance records have been reset!")
        return True
    except Exception as e:
        print(f"Error resetting attendance: {e}")
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    init_database()
