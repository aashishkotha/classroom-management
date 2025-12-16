# 🚀 Quick Start Guide

## Get Started in 5 Minutes!

### Option 1: Automated Setup (Recommended)

**Windows:**
```bash
setup.bat
```

**Linux/Mac:**
```bash
chmod +x setup.sh
./setup.sh
```

### Option 2: Manual Setup

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   ```

2. **Activate it:**
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

3. **Install packages:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize database:**
   ```bash
   python database.py
   ```

5. **Run the app:**
   ```bash
   python app.py
   ```

6. **Open browser:**
   ```
   http://localhost:5000
   ```

## First Steps After Installation

### 1. Create Your First Class
- Click "Classes" in sidebar
- Click "Add New Class"
- Enter: Name, Subject, Teacher, Room
- Click "Create Class"

### 2. Add Students
- Click "Students" in sidebar
- Click "Add Student"
- Fill in student details
- **Upload 5-10 clear photos** of the student
- Click "Add Student"

### 3. Train the System
- Click "Train System" in sidebar
- Wait for training to complete (1-5 minutes)
- You'll see a success message

### 4. Mark Attendance
- Click "Attendance" in sidebar
- Select your class
- Allow camera access
- Students will be automatically recognized!

## 📸 Photo Tips for Best Results

✅ **DO:**
- Use well-lit photos
- Take photos from different angles
- Ensure face is clearly visible
- Use recent photos
- Upload 5-10 photos per student

❌ **DON'T:**
- Use blurry photos
- Include multiple people
- Use photos with sunglasses/masks
- Use photos from far away

## 🔧 Troubleshooting

### Camera Not Working?
1. Check browser permissions
2. Close other apps using camera
3. Try a different browser
4. Restart the application

### Face Recognition Not Working?
1. Retrain the system
2. Add more/better photos
3. Ensure good lighting
4. Check camera angle

### Installation Failed?
**If dlib fails on Windows:**
1. Install Visual Studio Build Tools
2. Install CMake: `pip install cmake`
3. Try again: `pip install dlib`

**Alternative:** Use the simple recognition fallback (already included)

## 📞 Need Help?

Check the full README.md for detailed documentation!

---

**Happy Teaching! 🎓**
