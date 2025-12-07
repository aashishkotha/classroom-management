import sqlite3
import os
from datetime import datetime

DATABASE_FILE = 'classroom.db'

def init_database():
    """Initialize the SQLite database"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # Create students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            roll_number TEXT,
            email TEXT,
            image_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Create attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            date TEXT NOT NULL,
            time_in TEXT,
            time_out TEXT,
            status TEXT DEFAULT 'present',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students (id)
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
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

def add_student(name, roll_number=None, email=None):
    """Add a new student to the database"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    try:
        # Check if student already exists (including inactive ones)
        cursor.execute('SELECT id FROM students WHERE name = ?', (name,))
        existing = cursor.fetchone()
        
        if existing:
            # If exists but is inactive, reactivate it
            cursor.execute('UPDATE students SET is_active = 1, roll_number = ?, email = ? WHERE name = ?', 
                          (roll_number, email, name))
            student_id = existing[0]
        else:
            # Add new student
            cursor.execute(
                'INSERT INTO students (name, roll_number, email) VALUES (?, ?, ?)',
                (name, roll_number, email)
            )
            student_id = cursor.lastrowid
        
        conn.commit()
        return student_id
    except sqlite3.IntegrityError as e:
        print(f"Database integrity error: {e}")
        return None
    finally:
        conn.close()

def get_all_students():
    """Get all students from database"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM students WHERE is_active = 1 ORDER BY name')
    students = cursor.fetchall()
    
    conn.close()
    return students

def delete_student(student_id):
    """Delete a student (soft delete)"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute('UPDATE students SET is_active = 0 WHERE id = ?', (student_id,))
    conn.commit()
    conn.close()

def mark_attendance(student_id, date=None, time_in=None):
    """Mark attendance for a student"""
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    if time_in is None:
        time_in = datetime.now().strftime('%H:%M:%S')
    
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # Check if already marked today
    cursor.execute(
        'SELECT id FROM attendance WHERE student_id = ? AND date = ?',
        (student_id, date)
    )
    
    if cursor.fetchone() is None:
        cursor.execute(
            'INSERT INTO attendance (student_id, date, time_in) VALUES (?, ?, ?)',
            (student_id, date, time_in)
        )
        conn.commit()
        return True
    return False

def get_attendance_by_date(date=None):
    """Get attendance records for a specific date"""
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT s.name, a.time_in, a.time_out, a.status
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE a.date = ? AND s.is_active = 1
        ORDER BY a.time_in
    ''', (date,))
    
    records = cursor.fetchall()
    conn.close()
    return records

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
