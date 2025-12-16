import sqlite3

conn = sqlite3.connect('classroom.db')
cursor = conn.cursor()

print("\n--- CLASSES ---")
for row in cursor.execute('SELECT id, name, user_id FROM classes'):
    print(f"ID: {row[0]}, Name: {row[1]}, User: {row[2]}")

print("\n--- STUDENTS ---")
for row in cursor.execute('SELECT id, name, class_id FROM students'):
    print(f"ID: {row[0]}, Name: {row[1]}, Class: {row[2]}")

conn.close()
