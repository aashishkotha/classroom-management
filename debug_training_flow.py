import sqlite3
import os
import cv2
import pickle
import numpy as np
from pathlib import Path
from werkzeug.utils import secure_filename

def debug_train(user_id=1):
    print(f"--- Debug Training for User {user_id} ---")
    student_images_dir = 'static/student_images'
    
    conn = sqlite3.connect('classroom.db')
    cursor = conn.cursor()
    query = '''
        SELECT s.id, s.name, s.roll_number 
        FROM students s
        JOIN classes c ON s.class_id = c.id
        WHERE s.is_active = 1 AND c.user_id = ?
    '''
    cursor.execute(query, (user_id,))
    students = cursor.fetchall()
    conn.close()
    
    print(f"Found {len(students)} active students for user {user_id}")
    
    faces = []
    
    for student_id, student_name, roll_number in students:
        print(f"\nChecking Student: {student_name} (ID: {student_id})")
        
        secure_name = secure_filename(student_name.lower().replace(' ', '_'))
        
        path_new = os.path.join(student_images_dir, f"{student_id}_{secure_name}")
        path_legacy = os.path.join(student_images_dir, secure_name)
        
        print(f"  Path New: {path_new} ({'EXISTS' if os.path.exists(path_new) else 'MISSING'})")
        print(f"  Path Legacy: {path_legacy} ({'EXISTS' if os.path.exists(path_legacy) else 'MISSING'})")
        
        student_folder = None
        if os.path.exists(path_new):
            student_folder = path_new
        elif os.path.exists(path_legacy):
            student_folder = path_legacy
            
        if not student_folder:
            print("  SKIP: No folder found")
            continue
            
        print(f"  Using Folder: {student_folder}")
        
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png']:
            found = list(Path(student_folder).glob(ext))
            image_files.extend(found)
            
        print(f"  Found {len(image_files)} images")
        
        count = 0
        for img_path in image_files:
            try:
                img = cv2.imread(str(img_path))
                if img is None: 
                    print(f"    Fail read: {img_path.name}")
                    continue
                
                # Check face detection
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                detected = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
                
                if len(detected) > 0:
                    count += 1
                else:
                    print(f"    No face in {img_path.name}")
                    
            except Exception as e:
                print(f"    Error: {e}")
                
        print(f"  Valid Faces: {count}")
        if count > 0:
            faces.append(1) # just counting
            
    if not faces:
        print("\nFAILURE: No valid faces collected from any student.")
    else:
        print("\nSUCCESS: Would train successfully.")

if __name__ == "__main__":
    debug_train(1)
