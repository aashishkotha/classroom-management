import sqlite3
import os

def check_system():
    print("="*60)
    print("SYSTEM DIAGNOSTICS")
    print("="*60)
    
    conn = sqlite3.connect('classroom.db')
    cursor = conn.cursor()
    
    # Check students
    print("\n[STUDENTS]")
    cursor.execute('SELECT id, name, roll_number, is_active FROM students')
    students = cursor.fetchall()
    
    if not students:
        print("No students found in database.")
    
    for s in students:
        status = "ACTIVE" if s[3] else "DELETED (Soft)"
        print(f"ID: {s[0]} | Name: {s[1]} | Roll: {s[2]} | Status: {status}")
        
        # Check folder
        folder_name = s[1].lower().replace(' ', '_')
        folder_path = os.path.join('static', 'student_images', folder_name)
        if os.path.exists(folder_path):
            files = os.listdir(folder_path)
            print(f"   -> Image Folder: EXISTS ({len(files)} files)")
        else:
            print(f"   -> Image Folder: MISSING")
            
    conn.close()
    print("\nDone.")

if __name__ == "__main__":
    check_system()
