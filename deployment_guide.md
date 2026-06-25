# 🌐 Full Deployment Guide: Groq Chatbot with Persistent Memory

This guide contains step-by-step instructions to deploy your Python backend on **Render** and your React frontend on **Vercel**.

---

## 📦 Part 1: Uploading your Code to GitHub

Before deploying to Render or Vercel, you need to upload your project codebase to a GitHub repository.

1. **Create a GitHub Account** (if you don't have one): Go to [github.com](https://github.com) and sign up.
2. **Create a New Repository**:
   - Click the **"+"** icon in the top-right corner and select **"New repository"**.
   - Name your repository (e.g., `groq-memory-chatbot`).
   - Choose **Private** (recommended to protect your API keys).
   - Do **NOT** initialize with a README, `.gitignore`, or license (we have already created these).
   - Click **"Create repository"**.
3. **Upload your Code**:
   Open a terminal in your project root folder (`d:\Program_files_3\Internship_DecodeLabs\project1-chatbot`) and run the following commands:
   ```bash
   git init
   git add .
   git commit -m "Initialize secure Groq chatbot with database memory"
   git branch -M main
   git remote add origin https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPOSITORY_NAME.git
   git push -u origin main
   ```
   *(Note: replace `YOUR_GITHUB_USERNAME` and `YOUR_REPOSITORY_NAME` with your actual GitHub details).*

---

## 🖥️ Part 2: Backend Deployment on Render (render.com)

Render will host your Python Flask API and run the SQLite database automatically.

1. **Sign Up / Log In**: Go to [Render](https://render.com) and log in using your GitHub account.
2. **Create a New Web Service**:
   - Click the blue **"New +"** button in the dashboard and select **"Web Service"**.
   - Connect your GitHub repository.
3. **Configure Service Settings**:
   - **Name**: `groq-chatbot-backend`
   - **Environment**: `Python 3`
   - **Root Directory**: `backend` (⚠️ Important: set this to the backend sub-folder)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app` (This uses the `gunicorn` package we added)
4. **Configure Environment Variables**:
   Click the **"Advanced"** button or go to the **"Environment"** tab, then   - Under **"Environment Variables"**, click add:
     - `GROQ_API_KEY` = *(paste your Groq key here — from your .env file)*
     - `JWT_SECRET` = `any_long_random_secret_password_here` (This secures user logins)
     - `HINDSIGHT_API_KEY` = *(paste your Hindsight key here — from your .env file)*
5. **Deploy**:
   Click **"Create Web Service"**. Render will build and deploy the backend.
   - Once completed, copy the live URL (e.g., `https://groq-chatbot-backend.onrender.com`). You will need this for the frontend!

---

## 🎨 Part 3: Frontend Deployment on Vercel (vercel.com)

Vercel will host your fast React user interface and connect it to your backend API.

1. **Sign Up / Log In**: Go to [Vercel](https://vercel.com) and log in with your GitHub account.
2. **Import Project**:
   - Click **"Add New"** -> **"Project"**.
   - Import your GitHub repository.
3. **Configure Framework & Root Directory**:
   - **Framework Preset**: Select `Vite` (Vercel usually autodetects this).
   - **Root Directory**: Click "Edit" and choose the `frontend` folder (⚠️ Important: set this to the frontend sub-folder).
4. **Configure Environment Variables**:
   Expand the **"Environment Variables"** section and add:
   - `VITE_API_BASE` = `https://your-backend-service-url.onrender.com/api` (⚠️ Replace with the actual URL you copied from Render).
5. **Deploy**:
   Click **"Deploy"**. Vercel will compile the React code and give you a public URL (e.g., `https://project1-chatbot.vercel.app`) to access your app from any browser!

---

## ⚠️ Important Production Considerations

*   **Database Lifespan**: SQLite stores data in a local file (`chatbot.db`). In the free tier of Render, the server restarts periodically, which will reset the database. If you want permanent storage that survives server restarts in production, you can switch SQLite to a free **PostgreSQL database** (Render offers a free PostgreSQL instance, and you just update the connection URL).
*   **Security**: Ensure your frontend Vercel URL is added as an environment variable `FRONTEND_URL` on Render to protect your API from being called by unauthorized sites.
