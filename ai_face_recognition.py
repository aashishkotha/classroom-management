import cv2
import numpy as np
import os
import pickle
import sqlite3
from pathlib import Path
from insightface.app import FaceAnalysis

class AIFaceRecognition:
    """
    High-Accuracy Face Recognition using InsightFace (ArcFace).
    Uses 'buffalo_s' model (lightweight, ~512MB RAM usage).
    """
    
    def __init__(self):
        # Initialize InsightFace
        # allowed_modules=['detection', 'recognition'] to save memory
        self.app = FaceAnalysis(name='buffalo_s', allowed_modules=['detection', 'recognition'])
        # Prepare using CPU (ctx_id=0 for GPU, -1 for CPU, but InsightFace usually auto-detects)
        # On Render Free Tier/Standard Cloud, usually CPU.
        try:
            self.app.prepare(ctx_id=0, det_size=(640, 640))
            print("[OK] InsightFace 'buffalo_s' loaded on GPU/CPU")
        except:
            self.app.prepare(ctx_id=-1, det_size=(640, 640))
            print("[OK] InsightFace 'buffalo_s' loaded on CPU")
            
        # Cache: {user_id: {student_id: [embedding_vector]}}
        self.active_embeddings = {}
        
    def get_user_embeddings(self, user_id):
        """Load embeddings for a specific user"""
        if user_id in self.active_embeddings:
            return self.active_embeddings[user_id]
            
        emb_path = f'models/embeddings_{user_id}.pkl'
        if os.path.exists(emb_path):
            try:
                with open(emb_path, 'rb') as f:
                    embeddings = pickle.load(f)
                self.active_embeddings[user_id] = embeddings
                print(f"[OK] Loaded {len(embeddings)} students for User {user_id}")
                return embeddings
            except Exception as e:
                print(f"[ERROR] Error loading embeddings: {e}")
                return {}
        return {}
        
    def train_user_model(self, user_id, student_images_dir='static/student_images'):
        """
        'Train' by extracting face embeddings from images.
        We average multiple images of a student to create a robust 'prototype' vector.
        """
        print(f"🎓 Starting AI Analysis for User {user_id}")
        
        # Get active students from DB
        try:
            conn = sqlite3.connect('classroom.db')
            cursor = conn.cursor()
            query = '''
                 SELECT s.id, s.name 
                 FROM students s
                 JOIN classes c ON s.class_id = c.id
                 WHERE s.is_active = 1 AND c.user_id = ?
            '''
            students = cursor.execute(query, (user_id,)).fetchall()
            conn.close()
        except:
             return False, "Database error"
             
        if not students:
             self.active_embeddings.pop(user_id, None)
             return False, "No active students found."
             
        student_embeddings = {} # {student_id: {'name': name, 'vector': np.array}}
        
        for s_id, s_name in students:
            # Find folder
            from werkzeug.utils import secure_filename
            secure_name = secure_filename(s_name.lower().replace(' ', '_'))
            folder_new = f"{s_id}_{secure_name}"
            
            # Simple path check
            path = os.path.join(student_images_dir, folder_new)
            if not os.path.exists(path):
                # Legacy check
                path = os.path.join(student_images_dir, secure_name)
                if not os.path.exists(path):
                    continue
            
            # Process images
            vectors = []
            image_files = list(Path(path).glob('*.*'))
            
            for img_path in image_files:
                if img_path.suffix.lower() not in ['.jpg', '.jpeg', '.png']: continue
                
                try:
                    img = cv2.imread(str(img_path))
                    if img is None: continue
                    
                    # InsightFace detection
                    faces = self.app.get(img)
                    
                    if len(faces) > 0:
                        # Take the largest face
                        face = max(faces, key=lambda x: (x.bbox[2]-x.bbox[0]) * (x.bbox[3]-x.bbox[1]))
                        # Normalize vector
                        embedding = face.embedding
                        vectors.append(embedding)
                except Exception as e:
                    print(f"Skip {img_path.name}: {e}")
                    
            if vectors:
                # Average vectors for stable ID
                mean_vector = np.mean(vectors, axis=0)
                # Normalize again (important for cosine similarity)
                from numpy.linalg import norm
                mean_vector = mean_vector / norm(mean_vector)
                
                student_embeddings[s_id] = {
                    'name': s_name,
                    'vector': mean_vector,
                    'count': len(vectors)
                }
                print(f"  [OK] Processed {s_name}: {len(vectors)} samples")
                
        # Save
        if not student_embeddings:
            return False, "No faces found in student images."
            
        os.makedirs('models', exist_ok=True)
        try:
            with open(f'models/embeddings_{user_id}.pkl', 'wb') as f:
                pickle.dump(student_embeddings, f)
            self.active_embeddings[user_id] = student_embeddings
            return True, "Analysis Complete! System updated."
        except Exception as e:
            return False, f"Save Error: {e}"

    def recognize_faces(self, frame, user_id, threshold=0.5): # 0.5 is good for ArcFace cosine
        """
        Recognize faces using Cosine Similarity
        """
        embeddings = self.get_user_embeddings(user_id)
        if not embeddings:
            return []
            
        # Detect faces in current frame
        faces = self.app.get(frame)
        results = []
        
        for face in faces:
            # Bounding box
            bbox = face.bbox.astype(int)
            vector = face.embedding
             
            # Compare with all students
            best_score = -1.0
            best_match = None
            
            for s_id, data in embeddings.items():
                target_vector = data['vector']
                
                # Cosine Similarity: dot(A, B) / (norm(A)*norm(B))
                # Vectors from InsightFace are usually normalized, so just dot product
                score = np.dot(vector, target_vector)
                
                if score > best_score:
                    best_score = score
                    best_match = data
                    best_id = s_id
            
            # Determine match
            res = {
                'rect': (bbox[0], bbox[1], bbox[2]-bbox[0], bbox[3]-bbox[1]),
                'name': "Unknown",
                'student_id': None,
                'confidence': 0.0
            }
            
            if best_score > threshold and best_match:
                res['name'] = best_match['name']
                res['student_id'] = best_id
                res['confidence'] = int(best_score * 100)
            
            # Optional: Return 'raw_confidence' for debugging
            res['raw_confidence'] = best_score
            results.append(res)
            
        return results
