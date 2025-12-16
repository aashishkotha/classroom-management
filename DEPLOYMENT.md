# 🚀 Deployment Guide

Complete guide for deploying the Smart Attendance System to various platforms.

## 📋 Pre-Deployment Checklist

- [ ] All dependencies in requirements.txt
- [ ] Database initialized
- [ ] Face recognition trained
- [ ] Environment variables configured
- [ ] Static files organized
- [ ] Secret key changed
- [ ] Debug mode disabled

## 🌐 Platform-Specific Guides

---

## 1. Heroku Deployment

### Prerequisites
- Heroku account
- Heroku CLI installed
- Git initialized in project

### Steps

1. **Login to Heroku**
```bash
heroku login
```

2. **Create Heroku App**
```bash
heroku create your-attendance-system
```

3. **Add Buildpacks**
```bash
heroku buildpacks:add --index 1 heroku/python
```

4. **Create Aptfile** (for system dependencies)
Create a file named `Aptfile` in root:
```
cmake
libboost-all-dev
libopenblas-dev
```

5. **Set Environment Variables**
```bash
heroku config:set SECRET_KEY=your-secret-key-here
heroku config:set FLASK_ENV=production
```

6. **Deploy**
```bash
git add .
git commit -m "Deploy to Heroku"
git push heroku main
```

7. **Initialize Database**
```bash
heroku run python database.py
```

8. **Open App**
```bash
heroku open
```

### Important Notes
- Free tier may be slow for face recognition
- Consider upgrading to Hobby tier ($7/month)
- Camera access requires HTTPS (Heroku provides this)

---

## 2. Railway Deployment

### Prerequisites
- Railway account
- GitHub repository

### Steps

1. **Connect GitHub**
   - Go to railway.app
   - Click "New Project"
   - Select "Deploy from GitHub repo"

2. **Configure**
   - Select your repository
   - Railway auto-detects Python

3. **Set Environment Variables**
   - Go to Variables tab
   - Add:
     ```
     SECRET_KEY=your-secret-key
     FLASK_ENV=production
     ```

4. **Deploy**
   - Railway automatically deploys
   - Get your URL from the deployment

5. **Initialize Database**
   - Use Railway CLI or web terminal
   - Run: `python database.py`

### Advantages
- Faster than Heroku free tier
- Better for face recognition
- Easy GitHub integration

---

## 3. Render Deployment

### Prerequisites
- Render account
- GitHub repository

### Steps

1. **Create Web Service**
   - Go to render.com
   - Click "New +" → "Web Service"
   - Connect GitHub repository

2. **Configure Build**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`

3. **Set Environment Variables**
   ```
   SECRET_KEY=your-secret-key
   FLASK_ENV=production
   PYTHON_VERSION=3.10.0
   ```

4. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment

5. **Initialize Database**
   - Use Shell from dashboard
   - Run: `python database.py`

---

## 4. DigitalOcean App Platform

### Prerequisites
- DigitalOcean account
- GitHub repository

### Steps

1. **Create App**
   - Go to Apps section
   - Click "Create App"
   - Connect GitHub

2. **Configure**
   - Detected as Python app
   - Set run command: `gunicorn app:app`

3. **Environment Variables**
   ```
   SECRET_KEY=your-secret-key
   FLASK_ENV=production
   ```

4. **Deploy**
   - Review and create
   - Wait for deployment

---

## 5. AWS (EC2) Deployment

### Prerequisites
- AWS account
- EC2 instance (Ubuntu recommended)

### Steps

1. **Launch EC2 Instance**
   - Ubuntu 22.04 LTS
   - t2.medium or larger (for face recognition)
   - Open ports 80, 443, 22

2. **Connect via SSH**
```bash
ssh -i your-key.pem ubuntu@your-instance-ip
```

3. **Install Dependencies**
```bash
sudo apt update
sudo apt install python3-pip python3-venv nginx
sudo apt install cmake libboost-all-dev
```

4. **Clone Repository**
```bash
git clone your-repo-url
cd your-repo
```

5. **Setup Virtual Environment**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

6. **Configure Gunicorn**
Create `/etc/systemd/system/attendance.service`:
```ini
[Unit]
Description=Attendance System
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/web-app
Environment="PATH=/home/ubuntu/web-app/venv/bin"
ExecStart=/home/ubuntu/web-app/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:8000 app:app

[Install]
WantedBy=multi-user.target
```

7. **Configure Nginx**
Create `/etc/nginx/sites-available/attendance`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static {
        alias /home/ubuntu/web-app/static;
    }
}
```

8. **Enable and Start**
```bash
sudo systemctl enable attendance
sudo systemctl start attendance
sudo systemctl enable nginx
sudo systemctl restart nginx
```

---

## 6. Google Cloud Platform (Cloud Run)

### Prerequisites
- GCP account
- gcloud CLI installed

### Steps

1. **Create Dockerfile**
```dockerfile
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    cmake \
    libboost-all-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
```

2. **Build and Deploy**
```bash
gcloud builds submit --tag gcr.io/PROJECT-ID/attendance
gcloud run deploy --image gcr.io/PROJECT-ID/attendance --platform managed
```

---

## 7. Azure App Service

### Prerequisites
- Azure account
- Azure CLI installed

### Steps

1. **Create App Service**
```bash
az webapp up --name your-attendance-app --runtime "PYTHON:3.10"
```

2. **Configure**
```bash
az webapp config appsettings set --name your-attendance-app \
  --settings SECRET_KEY=your-secret-key FLASK_ENV=production
```

3. **Deploy**
```bash
az webapp deployment source config-local-git --name your-attendance-app
git remote add azure <deployment-url>
git push azure main
```

---

## 🔒 Security Checklist for Production

- [ ] Change SECRET_KEY to random string
- [ ] Set FLASK_ENV=production
- [ ] Disable DEBUG mode
- [ ] Use HTTPS (SSL certificate)
- [ ] Set up firewall rules
- [ ] Regular backups of database
- [ ] Implement rate limiting
- [ ] Add authentication for admin
- [ ] Sanitize all inputs
- [ ] Use environment variables for secrets

---

## 📊 Performance Optimization

### For Better Face Recognition Performance

1. **Use GPU-enabled instances** (if available)
2. **Reduce frame processing rate** (already set to every 3rd frame)
3. **Optimize image sizes** (resize before processing)
4. **Use caching** for face encodings
5. **Consider dedicated face recognition service**

### Database Optimization

1. **Switch to PostgreSQL** for production
2. **Add indexes** on frequently queried columns
3. **Regular vacuum** and analyze
4. **Connection pooling**

---

## 🐛 Troubleshooting Deployment Issues

### Issue: dlib won't install
**Solution:** 
- Use pre-built wheels
- Install cmake first
- Consider using Docker

### Issue: Camera not working
**Solution:**
- Ensure HTTPS is enabled
- Check browser permissions
- May not work on some cloud platforms (use manual attendance)

### Issue: Out of memory
**Solution:**
- Upgrade instance size
- Reduce worker count
- Optimize image processing

### Issue: Slow performance
**Solution:**
- Enable caching
- Use CDN for static files
- Optimize database queries
- Upgrade server tier

---

## 📞 Support

For deployment issues:
1. Check platform-specific documentation
2. Review error logs
3. Test locally first
4. Contact platform support

---

## 🎉 Post-Deployment

After successful deployment:
1. Test all features
2. Train face recognition system
3. Add sample data
4. Monitor performance
5. Set up backups
6. Configure monitoring/alerts

---

**Good luck with your deployment! 🚀**
