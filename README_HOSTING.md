# Classroom Management System - Hosting Guide

## Hosting Options

### 1. Heroku (Recommended for Beginners)

**Prerequisites:**
- Heroku account (free)
- Git installed

**Steps:**
1. **Install Heroku CLI**: https://devcenter.heroku.com/articles/heroku-cli

2. **Login to Heroku**:
   ```bash
   heroku login
   ```

3. **Initialize Git**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```

4. **Create Heroku App**:
   ```bash
   heroku create your-app-name
   ```

5. **Deploy**:
   ```bash
   git push heroku main
   ```

6. **Open App**:
   ```bash
   heroku open
   ```

### 2. PythonAnywhere (Easy Alternative)

**Steps:**
1. Sign up at https://www.pythonanywhere.com/
2. Create a new Web App
3. Choose Flask framework
4. Upload your files
5. Configure the web app

### 3. Vercel (Modern Option)

**Steps:**
1. Install Vercel CLI: `npm i -g vercel`
2. Run: `vercel`
3. Follow the prompts

### 4. Self-Hosting (Advanced)

**For Windows:**
```bash
# Install waitress (production server)
pip install waitress

# Run the app
waitress-serve --host=0.0.0.0 --port=5000 app:app
```

**For Linux/Mac:**
```bash
# Use gunicorn
pip install gunicorn
gunicorn --bind 0.0.0.0:5000 app:app
```

## Important Notes

### Camera Limitations
- **Heroku/PythonAnywhere**: Camera access won't work (no webcam access on cloud servers)
- **Self-hosting**: Camera will work only on local network

### Database
- SQLite database will be created automatically
- For production, consider PostgreSQL

### File Storage
- Student images stored in `static/student_images/`
- Ensure write permissions for the web server

## Environment Variables (Optional)

Create `.env` file:
```
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///classroom.db
```

## Troubleshooting

### Common Issues:
1. **Camera not working**: Expected on cloud hosting
2. **Database errors**: Check file permissions
3. **Import errors**: Verify requirements.txt

### For Production:
- Use HTTPS
- Set up proper logging
- Monitor resources
- Backup database regularly

## Quick Deploy to Heroku

```bash
# Complete deployment commands
git init
git add .
git commit -m "Ready for deployment"
heroku create your-classroom-app
git push heroku main
heroku open
```

Your app will be live at: `https://your-app-name.herokuapp.com`
