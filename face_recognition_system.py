import cv2
import numpy as np
import os
import pickle
import face_recognition
import sqlite3
from datetime import datetime
from pathlib import Path

class AdvancedFaceRecognition:
    """Advanced face recognition using face_recognition library (dlib-based)"""
    
    def __init__(self, encodings_file='face_encodings.pkl'):
        self.encodings_file = encodings_file
        self.known_encodings = []
        self.known_names = []
        self.known_ids = []
        self.load_encodings()
    
    def load_encodings(self):
        """Load face encodings from pickle file"""
        if os.path.exists(self.encodings_file):
            try:
                with open(self.encodings_file, 'rb') as f:
                    data = pickle.load(f)
                    self.known_encodings = data.get('encodings', [])
                    self.known_names = data.get('names', [])
                    self.known_ids = data.get('ids', [])
                print(f"✓ Loaded {len(self.known_encodings)} face encodings")
            except Exception as e:
                print(f"Error loading encodings: {e}")
                self.known_encodings = []
                self.known_names = []
                self.known_ids = []
        else:
            print("No encodings file found. Please train the system first.")
    
    def save_encodings(self):
        """Save face encodings to pickle file"""
        try:
            data = {
                'encodings': self.known_encodings,
                'names': self.known_names,
                'ids': self.known_ids
            }
            with open(self.encodings_file, 'wb') as f:
                pickle.dump(data, f)
            print(f"✓ Saved {len(self.known_encodings)} face encodings")
            return True
        except Exception as e:
            print(f"Error saving encodings: {e}")
            return False
    
    def train_from_images(self, student_images_dir='static/student_images'):
        """Train face recognition from student images"""
        print("=" * 50)
        print("Starting Face Recognition Training...")
        print("=" * 50)
        
        if not os.path.exists(student_images_dir):
            print(f"Error: Directory {student_images_dir} not found")
            return False
        
        # Get student data from database
        conn = sqlite3.connect('classroom.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, name FROM students WHERE is_active = 1')
        students = cursor.fetchall()
        conn.close()
        
        if not students:
            print("No active students found in database")
            return False
        
        # Reset encodings
        self.known_encodings = []
        self.known_names = []
        self.known_ids = []
        
        total_images = 0
        total_faces = 0
        
        for student_id, student_name in students:
            student_folder = os.path.join(student_images_dir, student_name.lower().replace(' ', '_'))
            
            if not os.path.exists(student_folder):
                print(f"⚠ No images found for {student_name}")
                continue
            
            print(f"\nProcessing {student_name}...")
            
            # Get all image files
            image_files = []
            for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']:
                image_files.extend(Path(student_folder).glob(ext))
            
            if not image_files:
                print(f"  ⚠ No image files found in {student_folder}")
                continue
            
            student_encodings = []
            
            for img_path in image_files:
                try:
                    # Load image
                    image = face_recognition.load_image_file(str(img_path))
                    
                    # Detect faces and get encodings
                    face_locations = face_recognition.face_locations(image, model='hog')
                    face_encodings = face_recognition.face_encodings(image, face_locations)
                    
                    if len(face_encodings) > 0:
                        # Use the first face found
                        encoding = face_encodings[0]
                        student_encodings.append(encoding)
                        total_images += 1
                        total_faces += 1
                        print(f"  ✓ Processed {img_path.name}")
                    else:
                        print(f"  ✗ No face detected in {img_path.name}")
                
                except Exception as e:
                    print(f"  ✗ Error processing {img_path.name}: {e}")
            
            # Add all encodings for this student
            if student_encodings:
                for encoding in student_encodings:
                    self.known_encodings.append(encoding)
                    self.known_names.append(student_name)
                    self.known_ids.append(student_id)
                print(f"  ✓ Added {len(student_encodings)} face encoding(s) for {student_name}")
        
        print("\n" + "=" * 50)
        print(f"Training Complete!")
        print(f"Total Images Processed: {total_images}")
        print(f"Total Face Encodings: {total_faces}")
        print(f"Students Trained: {len(set(self.known_names))}")
        print("=" * 50)
        
        # Save encodings
        if self.known_encodings:
            return self.save_encodings()
        else:
            print("No face encodings were created. Please check your images.")
            return False
    
    def recognize_faces(self, frame, tolerance=0.6):
        """
        Recognize faces in a frame
        
        Args:
            frame: BGR image from OpenCV
            tolerance: How much distance between faces to consider a match (lower = more strict)
        
        Returns:
            List of (name, student_id, location) tuples
        """
        if not self.known_encodings:
            return []
        
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Resize frame for faster processing (optional)
        small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.5, fy=0.5)
        
        # Detect faces
        face_locations = face_recognition.face_locations(small_frame, model='hog')
        face_encodings = face_recognition.face_encodings(small_frame, face_locations)
        
        recognized_faces = []
        
        for face_encoding, face_location in zip(face_encodings, face_locations):
            # Compare with known faces
            matches = face_recognition.compare_faces(
                self.known_encodings, 
                face_encoding, 
                tolerance=tolerance
            )
            
            name = "Unknown"
            student_id = None
            confidence = 0
            
            # Calculate face distances
            face_distances = face_recognition.face_distance(self.known_encodings, face_encoding)
            
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                
                if matches[best_match_index]:
                    name = self.known_names[best_match_index]
                    student_id = self.known_ids[best_match_index]
                    confidence = 1 - face_distances[best_match_index]
            
            # Scale back up face locations
            top, right, bottom, left = face_location
            top *= 2
            right *= 2
            bottom *= 2
            left *= 2
            
            recognized_faces.append({
                'name': name,
                'student_id': student_id,
                'location': (top, right, bottom, left),
                'confidence': confidence
            })
        
        return recognized_faces
    
    def draw_faces(self, frame, recognized_faces):
        """Draw rectangles and labels on recognized faces"""
        for face in recognized_faces:
            top, right, bottom, left = face['location']
            name = face['name']
            confidence = face['confidence']
            
            # Choose color based on recognition
            if name == "Unknown":
                color = (0, 0, 255)  # Red for unknown
                label = "Unknown"
            else:
                color = (0, 255, 0)  # Green for known
                label = f"{name} ({confidence*100:.1f}%)"
            
            # Draw rectangle
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            
            # Draw label background
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            
            # Draw label text
            cv2.putText(
                frame, 
                label, 
                (left + 6, bottom - 6), 
                cv2.FONT_HERSHEY_DUPLEX, 
                0.6, 
                (255, 255, 255), 
                1
            )
        
        return frame

# Fallback: Simple OpenCV-based recognition (if face_recognition fails)
class SimpleFaceRecognition:
    """Fallback simple face recognition using OpenCV"""
    
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.known_faces = {}
        self.face_labels = {}
        self.is_trained = False
    
    def train_from_images(self, student_images_dir='static/student_images'):
        """Train using LBPH face recognizer"""
        print("Training Simple Face Recognition...")
        
        # Get student data
        conn = sqlite3.connect('classroom.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, name FROM students WHERE is_active = 1')
        students = cursor.fetchall()
        conn.close()
        
        faces = []
        labels = []
        
        for student_id, student_name in students:
            student_folder = os.path.join(student_images_dir, student_name.lower().replace(' ', '_'))
            
            if not os.path.exists(student_folder):
                continue
            
            self.face_labels[student_id] = student_name
            
            for img_file in os.listdir(student_folder):
                if img_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    img_path = os.path.join(student_folder, img_file)
                    
                    try:
                        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                        if img is None:
                            continue
                        
                        # Detect face
                        detected_faces = self.face_cascade.detectMultiScale(img, 1.3, 5)
                        
                        for (x, y, w, h) in detected_faces:
                            face_roi = img[y:y+h, x:x+w]
                            face_roi = cv2.resize(face_roi, (200, 200))
                            faces.append(face_roi)
                            labels.append(student_id)
                    
                    except Exception as e:
                        print(f"Error processing {img_path}: {e}")
        
        if faces:
            self.recognizer.train(faces, np.array(labels))
            self.is_trained = True
            print(f"✓ Trained with {len(faces)} face samples")
            return True
        else:
            print("✗ No faces found for training")
            return False
    
    def recognize_faces(self, frame):
        """Recognize faces in frame"""
        if not self.is_trained:
            return []
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        
        recognized_faces = []
        
        for (x, y, w, h) in faces:
            face_roi = gray[y:y+h, x:x+w]
            face_roi = cv2.resize(face_roi, (200, 200))
            
            label, confidence = self.recognizer.predict(face_roi)
            
            # Lower confidence = better match (it's actually distance)
            if confidence < 100:
                name = self.face_labels.get(label, "Unknown")
                student_id = label
            else:
                name = "Unknown"
                student_id = None
            
            recognized_faces.append({
                'name': name,
                'student_id': student_id,
                'location': (y, x+w, y+h, x),
                'confidence': max(0, 1 - confidence/100)
            })
        
        return recognized_faces
    
    def draw_faces(self, frame, recognized_faces):
        """Draw rectangles and labels"""
        for face in recognized_faces:
            top, right, bottom, left = face['location']
            name = face['name']
            
            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.putText(
                frame, 
                name, 
                (left + 6, bottom - 6), 
                cv2.FONT_HERSHEY_DUPLEX, 
                0.6, 
                color, 
                1
            )
        
        return frame

if __name__ == "__main__":
    # Test training
    recognizer = AdvancedFaceRecognition()
    recognizer.train_from_images()
