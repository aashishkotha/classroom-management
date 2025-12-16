import cv2
import numpy as np
import os
import pickle
import sqlite3
from pathlib import Path

class OpenCVFaceRecognition:
    """Face recognition using OpenCV's LBPH (Local Binary Patterns Histograms)"""
    
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        # Cache for user models: {user_id: (recognizer, student_labels)}
        self.active_models = {}
        
    def get_user_model(self, user_id):
        """Get or load model for specific user"""
        if user_id in self.active_models:
            return self.active_models[user_id]
            
        model_path = f'models/user_{user_id}.yml'
        labels_path = f'models/labels_{user_id}.pkl'
        
        if os.path.exists(model_path) and os.path.exists(labels_path):
            try:
                recognizer = cv2.face.LBPHFaceRecognizer_create(
                    radius=1, neighbors=8, grid_x=8, grid_y=8, threshold=500.0
                )
                recognizer.read(model_path)
                with open(labels_path, 'rb') as f:
                    labels = pickle.load(f)
                
                self.active_models[user_id] = (recognizer, labels)
                print(f"✓ Loaded model for User {user_id} ({len(labels)} students)")
                return recognizer, labels
            except Exception as e:
                print(f"⚠ Error loading model for User {user_id}: {e}")
                return None, None
        return None, None

    def train_user_model(self, user_id, student_images_dir='static/student_images'):
        """Train face recognition for a specific user's students"""
        print("=" * 60)
        print(f"🎓 Starting Training for User {user_id}")
        
        from werkzeug.utils import secure_filename
        
        # Get user's students
        try:
            conn = sqlite3.connect('classroom.db')
            cursor = conn.cursor()
            # Join classes to filter by user_id
            query = '''
                SELECT s.id, s.name, s.roll_number 
                FROM students s
                JOIN classes c ON s.class_id = c.id
                WHERE s.is_active = 1 AND c.user_id = ?
            '''
            cursor.execute(query, (user_id,))
            students = cursor.fetchall()
            conn.close()
        except Exception as e:
            print(f"✗ Database error: {e}")
            return False
            
        if not students:
            print("✗ No active students found for this user")
            # Clear existing model if no students
            self.active_models.pop(user_id, None)
            return False, "No active students found. Check if you have added students and they are active."

        faces = []
        labels = []
        student_labels = {}
        total_images = 0
        
        for student_id, student_name, roll_number in students:
            # Use secure_filename to match upload logic
            secure_name = secure_filename(student_name.lower().replace(' ', '_'))
            
            # Try new format: {id}_{name}
            folder_new = f"{student_id}_{secure_name}"
            path_new = os.path.join(student_images_dir, folder_new)
            
            # Try legacy format: {name}
            folder_legacy = secure_name
            path_legacy = os.path.join(student_images_dir, folder_legacy)
            
            student_folder = None
            if os.path.exists(path_new):
                student_folder = path_new
            elif os.path.exists(path_legacy):
                student_folder = path_legacy
            
            if not student_folder:
                # Silently skip if no folder found (might be a student with no photos yet)
                print(f"⚠ No folder for {student_name}")
                continue
                
            image_files = []
            for ext in ['*.jpg', '*.jpeg', '*.png']:
                image_files.extend(list(Path(student_folder).glob(ext)))
                
            if not image_files:
                continue

            count = 0
            for img_path in image_files:
                try:
                    img = cv2.imread(str(img_path))
                    if img is None: continue
                    
                    # Optimization: Resize huge images before processing
                    height, width = img.shape[:2]
                    if width > 800:
                        scale = 800 / width
                        img = cv2.resize(img, (0,0), fx=scale, fy=scale)
                    
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    gray = cv2.equalizeHist(gray)
                    
                    # Detect faces for cropping
                    # Increased scaleFactor to 1.2 for speed
                    detected = self.face_cascade.detectMultiScale(
                        gray, scaleFactor=1.2, minNeighbors=5, minSize=(30, 30)
                    )
                    
                    for (x, y, w, h) in detected:
                        # Resize face to a consistent size for training
                        face_roi = gray[y:y+h, x:x+w]
                        face_roi = cv2.resize(face_roi, (200, 200))
                        faces.append(face_roi)
                        labels.append(student_id)
                        count += 1
                        total_images += 1
                except Exception as e:
                    print(f"✗ Error processing {img_path.name}: {e}")
            
            if count > 0:
                student_labels[student_id] = {
                    'name': student_name, 
                    'roll_number': roll_number,
                    'face_count': count
                }
                print(f"  ✓ Added {student_name}: {count} faces")

        if not faces:
            print("✗ No faces found for training")
            return False, "No valid faces found in images. Please clear and re-upload images."
            
        # Train
        recognizer = cv2.face.LBPHFaceRecognizer_create(
            radius=1, neighbors=8, grid_x=8, grid_y=8, threshold=500.0
        )
        recognizer.train(faces, np.array(labels))
        
        # Save
        os.makedirs('models', exist_ok=True)
        try:
            recognizer.write(f'models/user_{user_id}.yml')
            with open(f'models/labels_{user_id}.pkl', 'wb') as f:
                pickle.dump(student_labels, f)
        except Exception as e:
             return False, f"Error saving model: {e}"
            
        # Update cache
        self.active_models[user_id] = (recognizer, student_labels)
        print(f"✓ Training Complete for User {user_id}")
        return True, "Training completed successfully!"

    def recognize_faces(self, frame, user_id, confidence_threshold=100):
        """Recognize faces in frame using user's model"""
        recognizer, student_labels = self.get_user_model(user_id)
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )
        
        if len(faces) > 0:
            print(f"DEBUG: Detected {len(faces)} faces (Haar)")

        results = []
        for (x, y, w, h) in faces:
            result = {
                'rect': (x, y, w, h),
                'name': "Unknown",
                'student_id': None,
                'confidence': 0.0,
                'raw_confidence': 0.0
            }
            
            if recognizer:
                try:
                    roi = gray[y:y+h, x:x+w]
                    # Must resize to match training size (200x200)
                    roi = cv2.resize(roi, (200, 200))
                    
                    label_id, conf = recognizer.predict(roi)
                    
                    # DEBUG LOG
                    print(f"DEBUG: Predicted ID: {label_id}, Conf: {conf}")

                    # LBPH confidence: Lower is better. 0 = perfect match.
                    # Convert to score (0-100)
                    score = max(0, 100 - conf)
                    
                    if conf < confidence_threshold:
                         if label_id in student_labels:
                            info = student_labels[label_id]
                            result['name'] = info['name']
                            result['student_id'] = label_id
                            result['confidence'] = score
                            result['raw_confidence'] = conf
                except Exception as e:
                    print(f"Prediction Error: {e}")
            
            results.append(result)
            
        return results

    def draw_faces(self, frame, results):
        """Draw bounding boxes and names"""
        for res in results:
            (x, y, w, h) = res['rect']
            name = res['name']
            conf = res['confidence']
            
            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            
            label = f"{name} ({int(conf)}%)" if name != "Unknown" else "Unknown"
            cv2.putText(frame, label, (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        return frame
