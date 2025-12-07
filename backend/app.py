from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import cv2
import pickle
import pandas as pd
from datetime import datetime
import os
import base64
import numpy as np
from PIL import Image
import io
import json

app = Flask(__name__)
CORS(app)

# Use absolute path directly
import os

# Hardcode the paths that we know work
TRAINER_FILE = r"c:\Users\ashko\OneDrive\Documents\lets see one project\face-attendance\trainer.yml"
ENC_FILE = r"c:\Users\ashko\OneDrive\Documents\lets see one project\face-attendance\encodings.pickle"
ATT_FILE = r"c:\Users\ashko\OneDrive\Documents\lets see one project\face-attendance\attendance.csv"
CASCADE_FILE = r"c:\Users\ashko\OneDrive\Documents\lets see one project\face-attendance\haarcascade_frontalface_default.xml"

print(f"Looking for trainer at: {TRAINER_FILE}")
print(f"Trainer exists: {os.path.exists(TRAINER_FILE)}")

# Load face recognition model
try:
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    
    if not os.path.exists(TRAINER_FILE):
        raise FileNotFoundError(f"Trainer file not found: {TRAINER_FILE}")
    
    recognizer.read(TRAINER_FILE)
    print("✅ Trainer loaded successfully!")
    
except Exception as e:
    print(f"❌ Error loading trainer: {e}")
    exit(1)

# Load labels
with open(ENC_FILE, "rb") as f:
    label_dict = pickle.load(f)

face_cascade = cv2.CascadeClassifier(CASCADE_FILE)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/attendance', methods=['GET'])
def get_attendance():
    if os.path.exists(ATT_FILE):
        df = pd.read_csv(ATT_FILE)
        return jsonify(df.to_dict('records'))
    return jsonify([])

@app.route('/api/recognize', methods=['POST'])
def recognize_face():
    try:
        data = request.json
        image_data = data['image']
        
        # Decode base64 image
        image_data = image_data.split(',')[1]
        decoded = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(decoded))
        image_np = np.array(image)
        
        # Convert to grayscale
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        results = []
        for (x, y, w, h) in faces:
            face_roi = gray[y:y+h, x:x+w]
            label, confidence = recognizer.predict(face_roi)
            
            name = "Unknown"
            if confidence < 100:
                if label in label_dict:
                    name = label_dict[label]
            
            results.append({
                'name': name,
                'confidence': confidence,
                'box': [x, y, w, h]
            })
            
            # Mark attendance if confidence is good
            if name != "Unknown" and confidence < 90:
                mark_attendance(name)
        
        return jsonify({'faces': results})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def mark_attendance(name):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Read existing attendance
    if os.path.exists(ATT_FILE):
        df = pd.read_csv(ATT_FILE)
    else:
        df = pd.DataFrame(columns=["Name", "Timestamp"])
    
    # Check if already marked today
    today = now.split(' ')[0]
    today_records = df[df['Timestamp'].str.contains(today)]
    
    if not today_records[today_records['Name'] == name].empty:
        return
    
    # Add new entry
    df.loc[len(df)] = [name, now]
    df.to_csv(ATT_FILE, index=False)
    print(f"✅ Marked {name} at {now}")

@app.route('/api/students', methods=['GET'])
def get_students():
    return jsonify(list(label_dict.values()))

@app.route('/api/reset/status', methods=['GET'])
def get_reset_status():
    """Get reset status and configuration"""
    try:
        config_file = r"c:\Users\ashko\OneDrive\Documents\lets see one project\face-attendance\reset_config.json"
        att_file = ATT_FILE
        log_file = r"c:\Users\ashko\OneDrive\Documents\lets see one project\face-attendance\reset_log.csv"
        
        # Load config
        config = {
            "auto_reset": {"enabled": False, "time": "00:00", "frequency": "daily"},
            "manual_reset": {"require_confirmation": True, "log_resets": True}
        }
        
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
        
        # Get attendance stats
        stats = {"today": 0, "total": 0}
        if os.path.exists(att_file):
            df = pd.read_csv(att_file)
            today = datetime.now().strftime("%Y-%m-%d")
            stats["today"] = len(df[df['Timestamp'].str.contains(today)])
            stats["total"] = len(df)
        
        # Get recent resets
        recent_resets = []
        if os.path.exists(log_file):
            log_df = pd.read_csv(log_file)
            recent_resets = log_df.tail(5).to_dict('records')
        
        return jsonify({
            "config": config,
            "stats": stats,
            "recent_resets": recent_resets
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset/daily', methods=['POST'])
def reset_daily_attendance():
    """Reset today's attendance"""
    try:
        att_file = ATT_FILE
        log_file = r"c:\Users\ashko\OneDrive\Documents\lets see one project\face-attendance\reset_log.csv"
        
        print(f"🔍 Looking for attendance file at: {att_file}")
        print(f"📁 File exists: {os.path.exists(att_file)}")
        
        if not os.path.exists(att_file):
            return jsonify({'error': 'No attendance file found'}), 404
        
        df = pd.read_csv(att_file)
        today = datetime.now().strftime("%Y-%m-%d")
        
        print(f"📅 Today's date: {today}")
        print(f"📊 Current records: {len(df)}")
        print(f"📋 Records before reset:")
        print(df.to_string())
        
        # Remove today's records - more robust date matching
        df_filtered = df[~df['Timestamp'].str.contains(today, na=False)]
        
        print(f"📊 Records after filtering: {len(df_filtered)}")
        
        if len(df_filtered) < len(df):
            # Save the filtered data
            df_filtered.to_csv(att_file, index=False)
            removed_count = len(df) - len(df_filtered)
            
            print(f"✅ Removed {removed_count} records for today")
            
            # Log the reset
            if not os.path.exists(log_file):
                pd.DataFrame(columns=["Timestamp", "Reset Type", "Details"]).to_csv(log_file, index=False)
            
            log_df = pd.read_csv(log_file)
            log_df.loc[len(log_df)] = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "web_daily", f"Removed {removed_count} records"]
            log_df.to_csv(log_file, index=False)
            
            return jsonify({
                'success': True,
                'message': f'Reset {removed_count} attendance records for today',
                'removed_count': removed_count
            })
        else:
            print("❌ No records found for today to reset")
            return jsonify({
                'success': False,
                'message': 'No attendance records found for today'
            })
            
    except Exception as e:
        print(f"❌ Error in reset_daily_attendance: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset/all', methods=['POST'])
def reset_all_attendance():
    """Clear all attendance records"""
    try:
        att_file = ATT_FILE
        log_file = r"c:\Users\ashko\OneDrive\Documents\lets see one project\face-attendance\reset_log.csv"
        
        print(f"🔍 Clearing attendance file at: {att_file}")
        
        # Create empty CSV with headers
        pd.DataFrame(columns=["Name", "Timestamp"]).to_csv(att_file, index=False)
        
        print("✅ Cleared all attendance records")
        
        # Log the reset
        if not os.path.exists(log_file):
            pd.DataFrame(columns=["Timestamp", "Reset Type", "Details"]).to_csv(log_file, index=False)
        
        log_df = pd.read_csv(log_file)
        log_df.loc[len(log_df)] = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "web_full", "Cleared all records"]
        log_df.to_csv(log_file, index=False)
        
        return jsonify({
            'success': True,
            'message': 'All attendance records cleared'
        })
        
    except Exception as e:
        print(f"❌ Error in reset_all_attendance: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset/config', methods=['GET', 'POST'])
def reset_config():
    """Get or update reset configuration"""
    try:
        config_file = r"c:\Users\ashko\OneDrive\Documents\lets see one project\face-attendance\reset_config.json"
        
        if request.method == 'GET':
            # Load config
            default_config = {
                "auto_reset": {"enabled": False, "time": "00:00", "frequency": "daily"},
                "manual_reset": {"require_confirmation": True, "log_resets": True}
            }
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    return jsonify(json.load(f))
            else:
                return jsonify(default_config)
        
        elif request.method == 'POST':
            # Save config
            config = request.json
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            return jsonify({
                'success': True,
                'message': 'Configuration saved successfully'
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Face Attendance Web App...")
    print(f" Students: {list(label_dict.values())}")
    print("🌐 Open http://localhost:5000 in your browser")
    
    app.run(debug=True, host='0.0.0.0', port=5000)