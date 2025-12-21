# Use Python 3.10
FROM python:3.10-slim

# Install system dependencies for OpenCV and building packages
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    gcc \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set up user (Hugging Face Spaces runs as ID 1000)
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copy requirements and install
COPY --chown=user requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=user . .

# Create directories and set permissions
RUN mkdir -p static/uploads static/student_images models && \
    touch classroom.db && \
    chmod -R 777 static models classroom.db

# Expose port 7860 (Standard for HF Spaces)
EXPOSE 7860

# Run with Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:7860", "app:app"]
