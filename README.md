# Smart Attendance System with Classroom Management

A comprehensive, AI-powered attendance system with face recognition and complete classroom management features.

## 🌟 Features

### 📸 **Smart Attendance**
- **Real-time Face Recognition** using advanced dlib-based algorithms
- **Automatic Attendance Marking** when students are recognized
- **Manual Attendance** option for backup
- **Live Camera Feed** with face detection overlay

### 🏫 **Classroom Management**
- **Multiple Classes** support with subjects and schedules
- **Student Management** with detailed profiles
- **Class-wise Attendance** tracking
- **Teacher Assignment** and room allocation

### 📊 **Analytics & Reporting**
- **Real-time Dashboard** with statistics
- **Attendance Rate** calculation
- **Present/Absent** tracking
- **Historical Records** by date and class

### 🎨 **Modern UI/UX**
- **Premium Design** with gradient themes
- **Responsive Layout** for all devices
- **Smooth Animations** and transitions
- **Intuitive Navigation** with sidebar

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- Webcam/Camera
- Windows/Linux/Mac OS

### Step 1: Clone or Navigate to Project
```bash
cd "c:\Users\ashko\OneDrive\Documents\lets see one project\web-app"
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv
```

### Step 3: Activate Virtual Environment
**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### Step 4: Install Dependencies
```bash
pip install -r requirements.txt
```

**Note:** If `dlib` installation fails, you may need to install CMake first:
```bash
pip install cmake
```

For Windows users, you might need to install Visual Studio Build Tools.

### Step 5: Initialize Database
```bash
python database.py
```

## 🎯 Usage

### Running the Application

1. **Start the Flask Server:**
```bash
python app.py
```

2. **Open your browser and navigate to:**
```
http://localhost:5000
```

### First-Time Setup

1. **Create a Class:**
   - Go to "Classes" → "Add New Class"
   - Enter class details (name, subject, teacher, etc.)

2. **Add Students:**
   - Go to "Students" → "Add Student"
   - Fill in student details
   - Upload 5-10 clear photos of the student's face
   - **Important:** Photos should be well-lit and show the face clearly

3. **Train the System:**
   - Click "Train System" in the sidebar
   - Wait for training to complete (this may take a few minutes)
   - You'll see a success message when done

4. **Mark Attendance:**
   - Go to "Attendance"
   - Select the class
   - Allow camera access
   - Students will be automatically recognized and marked present

## 📁 Project Structure

```
web-app/
├── app.py                          # Main Flask application
├── database.py                     # Database operations
├── face_recognition_system.py     # Face recognition logic
├── requirements.txt                # Python dependencies
├── classroom.db                    # SQLite database
├── face_encodings.pkl             # Trained face data
├── static/
│   ├── css/                       # Custom styles
│   ├── student_images/            # Student photos
│   └── uploads/                   # Uploaded files
└── templates/
    ├── base.html                  # Base template
    ├── index.html                 # Dashboard
    ├── classes.html               # Class management
    ├── students.html              # Student management
    ├── attendance.html            # Attendance page
    ├── add_class.html             # Add class form
    ├── add_student.html           # Add student form
    └── edit_student.html          # Edit student form
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
DATABASE_URL=sqlite:///classroom.db
```

### Camera Settings
If the default camera doesn't work, modify `app.py`:
```python
# Change camera index (0, 1, or 2)
camera = cv2.VideoCapture(0)  # Try 1 or 2 if 0 doesn't work
```

## 🌐 Deployment

### Deploy to Heroku

1. **Install Heroku CLI**

2. **Login to Heroku:**
```bash
heroku login
```

3. **Create Heroku App:**
```bash
heroku create your-app-name
```

4. **Add Buildpacks:**
```bash
heroku buildpacks:add --index 1 heroku/python
heroku buildpacks:add --index 2 https://github.com/heroku/heroku-buildpack-apt
```

5. **Create Aptfile** (for system dependencies):
```
cmake
libboost-all-dev
```

6. **Deploy:**
```bash
git add .
git commit -m "Deploy to Heroku"
git push heroku main
```

### Deploy to Railway/Render

1. Connect your GitHub repository
2. Set environment variables
3. Deploy automatically

**Note:** Face recognition requires significant processing power. Consider using a paid tier for production.

## 🛠️ Troubleshooting

### Camera Not Working
- **Check permissions:** Ensure browser has camera access
- **Try different camera index:** Change from 0 to 1 or 2 in code
- **Check if camera is in use:** Close other applications using the camera

### Face Recognition Not Accurate
- **Retrain the system:** Add more photos and retrain
- **Better lighting:** Ensure good lighting conditions
- **Clear photos:** Use high-quality, clear photos
- **Multiple angles:** Add photos from different angles

### Installation Issues
- **dlib fails:** Install CMake and Visual Studio Build Tools (Windows)
- **OpenCV issues:** Try `pip install opencv-python-headless`
- **Memory errors:** Close other applications

## 📝 API Endpoints

### Statistics
```
GET /api/stats
```
Returns system statistics (total students, classes, attendance)

### Attendance by Date
```
GET /api/attendance/<date>
```
Returns attendance records for a specific date (format: YYYY-MM-DD)

## 🔒 Security Notes

- Change the `SECRET_KEY` in production
- Use HTTPS in production
- Implement user authentication for sensitive operations
- Regularly backup the database
- Store face encodings securely

## 📚 Technologies Used

- **Backend:** Flask (Python)
- **Database:** SQLite
- **Face Recognition:** dlib, face_recognition library
- **Computer Vision:** OpenCV
- **Frontend:** Bootstrap 5, HTML5, CSS3, JavaScript
- **Icons:** Font Awesome 6

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License.

## 👨‍💻 Support

For issues and questions:
- Create an issue on GitHub
- Contact: your-email@example.com

## 🎓 Credits

Developed with ❤️ for educational institutions and organizations.

---

**Version:** 2.0.0  
**Last Updated:** December 2024
