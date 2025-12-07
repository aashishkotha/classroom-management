import cv2
import numpy as np
import os
import pickle
from PIL import Image
import sqlite3
from datetime import datetime

class SimpleFaceRecognition:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.known_faces = {}
        self.face_labels = {}
        self.load_known_faces()
    
    def load_known_faces(self):
        """Load known faces from student images"""
        try:
            conn = sqlite3.connect('classroom.db')
            cursor = conn.cursor()
            
            # Get all students
            cursor.execute('SELECT id, name FROM students WHERE is_active = 1')
            students = cursor.fetchall()
            
            for student_id, name in students:
                student_folder = f'static/student_images/{name.lower()}'
                if os.path.exists(student_folder):
                    images = [f for f in os.listdir(student_folder) if f.endswith(('.jpg', '.png', '.jpeg'))]
                    face_encodings = []
                    
                    for img_file in images:
                        img_path = os.path.join(student_folder, img_file)
                        face_encoding = self.extract_face_encoding(img_path)
                        if face_encoding is not None:
                            face_encodings.append(face_encoding)
                    
                    if face_encodings:
                        # Average the encodings for this person
                        avg_encoding = np.mean(face_encodings, axis=0)
                        self.known_faces[student_id] = avg_encoding
                        self.face_labels[student_id] = name
            
            conn.close()
            print(f"Loaded {len(self.known_faces)} known faces")
            
        except Exception as e:
            print(f"Error loading faces: {e}")
    
    def extract_face_encoding(self, image_path):
        """Extract simple face encoding using histogram features"""
        try:
            # Load image
            img = cv2.imread(image_path)
            if img is None:
                return None
                
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) > 0:
                # Use the largest face
                (x, y, w, h) = max(faces, key=lambda f: f[2] * f[3])
                face_roi = gray[y:y+h, x:x+w]
                
                # Resize to standard size
                face_roi = cv2.resize(face_roi, (100, 100))
                
                # Create simple histogram-based encoding
                hist = cv2.calcHist([face_roi], [0], None, [256], [0, 256])
                hist = cv2.normalize(hist, hist).flatten()
                
                return hist
            else:
                return None
                
        except Exception as e:
            print(f"Error extracting encoding from {image_path}: {e}")
            return None
    
    def recognize_face(self, frame):
        """Recognize faces in a frame"""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            
            recognized_names = []
            
            for (x, y, w, h) in faces:
                # Extract face
                face_roi = gray[y:y+h, x:x+w]
                face_roi = cv2.resize(face_roi, (100, 100))
                
                # Create encoding
                hist = cv2.calcHist([face_roi], [0], None, [256], [0, 256])
                hist = cv2.normalize(hist, hist).flatten()
                
                # Compare with known faces
                best_match = None
                best_distance = float('inf')
                
                for student_id, known_encoding in self.known_faces.items():
                    # Calculate correlation distance
                    distance = cv2.compareHist(hist, known_encoding, cv2.HISTCMP_CORREL)
                    
                    # Convert correlation to distance (higher correlation = lower distance)
                    distance = 1 - distance
                    
                    if distance < best_distance and distance < 0.3:  # Threshold
                        best_distance = distance
                        best_match = self.face_labels[student_id]
                
                if best_match:
                    recognized_names.append(best_match)
                    # Draw rectangle and name
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.putText(frame, best_match, (x, y-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                else:
                    # Draw rectangle for unknown face
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                    cv2.putText(frame, "Unknown", (x, y-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
            
            return recognized_names, frame
            
        except Exception as e:
            print(f"Error in face recognition: {e}")
            return [], frame
    
    def train_faces(self):
        """Train the face recognition system"""
        print("Training face recognition system...")
        self.load_known_faces()
        print("Training completed!")
        return True

# Test the system
if __name__ == "__main__":
    recognizer = SimpleFaceRecognition()
    recognizer.train_faces()
    
    # Test with camera
    cap = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        names, processed_frame = recognizer.recognize_face(frame)
        
        if names:
            print(f"Recognized: {names}")
        
        cv2.imshow('Face Recognition', processed_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
