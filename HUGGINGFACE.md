# Deploying to Hugging Face Spaces 🚀

Hugging Face Spaces is an excellent free platform with **16GB RAM**, making it perfect for running the **High-Accuracy AI Face Recognition** model which fails on Render's free tier.

## Quick Setup Guide

1.  **Create a Space**:
    *   Go to [huggingface.co/spaces](https://huggingface.co/spaces)
    *   Click **"Create new Space"**.
    *   **Name**: `smart-attendance-app` (or similar).
    *   **SDK**: Select **Docker** (This is important! Do not select Gradio/Streamlit).
    *   **License**: `MIT` or `OpenRAIL`.
    *   **Privacy**: Public or Private.
    *   Click **Create Space**.

2.  **Upload Code**:
    *   You can clone the repo and push, OR upload files directly via the website.
    *   **Easiest Way**:
        *   In your new Space, click **"Files"**.
        *   Click **"Add file"** -> **"Upload files"**.
        *   Drag and drop ALL files from this folder (excluding `venv` and `.git`).
        *   **CRITICAL**: Ensure `Dockerfile`, `requirements.txt`, and `app.py` are uploaded.
    *   Click **"Commit changes"**.

3.  **Wait for Build**:
    *   The "Building" status will appear.
    *   It might take 3-5 minutes to install Dependencies (OpenCV, InsightFace).
    *   Once "Running", your app is live!

## 💡 Why Hugging Face?
*   **High RAM**: 16GB Free (vs 512MB on Render).
*   **AI Support**: Runs the deep learning models smoothly.
*   **Note**: Like Render, the free disk is *ephemeral*. If the Space restarts (after 48hrs of inactivity), the database resets.
    *   BUT, the default user (`aashish` / `1234`) will always be recreated.
