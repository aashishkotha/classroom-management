import cv2
import numpy as np
import os
import sqlite3
from datetime import datetime
import pickle
from pathlib import Path

class ArcFaceRecognition:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.known_faces = {}
        self.face_embeddings = {}
        self.threshold = 0.6  # Similarity threshold
        
    def load_known_faces(self):
        """Load known faces from database and images"""
        try:
            # Get database connection
            conn = sqlite3.connect('classroom.db')
            cursor = conn.cursor()
            
            # Get all active students
            cursor.execute('SELECT id, name FROM students WHERE is_active = 1')
            students = cursor.fetchall()
            
            for student_id, name in students:
                # Get student images
                student_folder = f'static/student_images/{name.lower()}'
                if os.path.exists(student_folder):
                    embeddings = []
                    
                    # Process each image
                    for img_file in os.listdir(student_folder):
                        if img_file.endswith(('.jpg', '.jpeg', '.png')):
                            img_path = os.path.join(student_folder, img_file)
                            embedding = self.extract_face_embedding(img_path)
                            if embedding is not None:
                                embeddings.append(embedding)
                    
                    if embeddings:
                        # Average multiple embeddings for better accuracy
                        avg_embedding = np.mean(embeddings, axis=0)
                        self.known_faces[name] = avg_embedding
            
            conn.close()
            print(f"Loaded {len(self.known_faces)} known faces")
            return True
            
        except Exception as e:
            print(f"Error loading known faces: {e}")
            return False
    
    def extract_face_embedding(self, image_path):
        """Extract face embedding using ArcFace-like approach"""
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                return None
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) == 0:
                return None
            
            # Get the largest face
            face = max(faces, key=lambda x: x[2] * x[3])
            x, y, w, h = face
            
            # Extract face ROI
            face_roi = gray[y:y+h, x:x+w]
            
            # Resize to standard size
            face_resized = cv2.resize(face_roi, (112, 112))
            
            # Create ArcFace-like embedding (simplified version)
            embedding = self.create_arcface_embedding(face_resized)
            
            return embedding
            
        except Exception as e:
            print(f"Error extracting embedding from {image_path}: {e}")
            return None
    
    def create_arcface_embedding(self, face_img):
        """Create ArcFace-style embedding (simplified version)"""
        try:
            # Normalize the face image
            face_normalized = face_img.astype(np.float32) / 255.0
            
            # Create multi-scale features
            features = []
            
            # Different kernel sizes for multi-scale analysis
            kernel_sizes = [3, 5, 7, 9]
            
            for kernel_size in kernel_sizes:
                # Apply Gaussian blur at different scales
                blurred = cv2.GaussianBlur(face_normalized, (kernel_size, kernel_size), 0)
                
                # Calculate gradients (edge features)
                grad_x = cv2.Sobel(blurred, cv2.CV_64F, 1, 0, ksize=3)
                grad_y = cv2.Sobel(blurred, cv2.CV_64F, 0, 1, ksize=3)
                
                # Gradient magnitude
                grad_mag = np.sqrt(grad_x**2 + grad_y**2)
                
                # Local Binary Pattern-like features
                lbp = self.calculate_lbp(face_normalized)
                
                # Histogram of gradients
                hist_grad = cv2.calcHist([grad_mag.astype(np.uint8)], [0], None, [32], [0, 256])
                hist_lbp = cv2.calcHist([lbp], [0], None, [32], [0, 256])
                
                # Combine features
                combined = np.concatenate([
                    hist_grad.flatten(),
                    hist_lbp.flatten(),
                    [np.mean(grad_mag), np.std(grad_mag)]
                ])
                
                features.extend(combined)
            
            # Create final embedding vector
            embedding = np.array(features)
            
            # Normalize embedding (L2 normalization)
            embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
            
            return embedding
            
        except Exception as e:
            print(f"Error creating ArcFace embedding: {e}")
            # Return random embedding as fallback
            return np.random.rand(256)
    
    def calculate_lbp(self, image, radius=1, neighbors=8):
        """Calculate Local Binary Pattern"""
        try:
            h, w = image.shape
            lbp = np.zeros((h, w), dtype=np.uint8)
            
            for i in range(radius, h - radius):
                for j in range(radius, w - radius):
                    center = image[i, j]
                    
                    binary = 0
                    for n in range(neighbors):
                        # Calculate neighbor position
                        angle = 2 * np.pi * n / neighbors
                        x = i + radius * np.cos(angle)
                        y = j + radius * np.sin(angle)
                        
                        # Bilinear interpolation
                        x1, y1 = int(x), int(y)
                        x2, y2 = min(x1 + 1, h - 1), min(y1 + 1, w - 1)
                        
                        dx, dy = x - x1, y - y1
                        neighbor_val = (1 - dx) * (1 - dy) * image[x1, y1] + \
                                      dx * (1 - dy) * image[x2, y1] + \
                                      (1 - dx) * dy * image[x1, y2] + \
                                      dx * dy * image[x2, y2]
                        
                        if neighbor_val >= center:
                            binary |= (1 << n)
                    
                    lbp[i, j] = binary
            
            return lbp
            
        except Exception as e:
            print(f"Error calculating LBP: {e}")
            return np.zeros_like(image, dtype=np.uint8)
    
    def recognize_face(self, frame):
        """Recognize faces in frame using ArcFace embeddings"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            
            recognized_names = []
            results = []
            
            for (x, y, w, h) in faces:
                # Extract face ROI
                face_roi = gray[y:y+h, x:x+w]
                
                # Resize to standard size
                face_resized = cv2.resize(face_roi, (112, 112))
                
                # Create embedding
                embedding = self.create_arcface_embedding(face_resized)
                
                # Compare with known faces
                best_match = "Unknown"
                best_similarity = 0
                
                for name, known_embedding in self.known_faces.items():
                    # Calculate cosine similarity
                    similarity = np.dot(embedding, known_embedding)
                    
                    if similarity > best_similarity and similarity > self.threshold:
                        best_match = name
                        best_similarity = similarity
                
                recognized_names.append(best_match)
                
                # Draw rectangle and name
                color = (0, 255, 0) if best_match != "Unknown" else (0, 0, 255)
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                
                # Add label with confidence
                label = f"{best_match} ({best_similarity:.2f})" if best_match != "Unknown" else "Unknown"
                cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
                
                results.append({
                    'name': best_match,
                    'confidence': best_similarity,
                    'box': [x, y, w, h]
                })
            
            return recognized_names, frame, results
            
        except Exception as e:
            print(f"Error in face recognition: {e}")
            return [], frame, []
    
    def train_faces(self):
        """Train face recognition model"""
        print("Training ArcFace recognition model...")
        
        # Load known faces
        success = self.load_known_faces()
        
        if success:
            print(f"Training completed! {len(self.known_faces)} faces loaded.")
            return True
        else:
            print("Training failed!")
            return False
    
    def save_embeddings(self, filename='arcface_embeddings.pkl'):
        """Save face embeddings to file"""
        try:
            with open(filename, 'wb') as f:
                pickle.dump(self.known_faces, f)
            print(f"Embeddings saved to {filename}")
        except Exception as e:
            print(f"Error saving embeddings: {e}")
    
    def load_embeddings(self, filename='arcface_embeddings.pkl'):
        """Load face embeddings from file"""
        try:
            if os.path.exists(filename):
                with open(filename, 'rb') as f:
                    self.known_faces = pickle.load(f)
                print(f"Embeddings loaded from {filename}")
                return True
        except Exception as e:
            print(f"Error loading embeddings: {e}")
        return False

# Test the ArcFace recognition
if __name__ == "__main__":
    recognizer = ArcFaceRecognition()
    
    # Train the model
    if recognizer.train_faces():
        print("ArcFace model trained successfully!")
        
        # Save embeddings
        recognizer.save_embeddings()
        
        # Test with camera
        cap = cv2.VideoCapture(0)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Recognize faces
            names, processed_frame, results = recognizer.recognize_face(frame)
            
            # Display results
            cv2.imshow('ArcFace Recognition', processed_frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
    else:
        print("Failed to train ArcFace model")
