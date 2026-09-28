# ☁️ Cloud Deployment Guide

This guide provides step-by-step instructions to deploy the **Karmayogi AI-Enabled Competency Gap & Learning Platform** to production cloud hosting platforms.

---

## 🚀 Option 1: 1-Click Blueprint Deploy on Render (Recommended)

Render provides free hosting for both the Python Flask web service and the static Vue 3 frontend using the included [`render.yaml`](../render.yaml) blueprint.

### Steps:
1. **Push your code to GitHub** (make sure your repo is public or linked to your Render account).
2. Go to [dashboard.render.com](https://dashboard.render.com/) and sign in with GitHub.
3. Click **"New +"** in the top navigation and select **"Blueprint"**.
4. Select your repository: `AI-Enabled-Competency-Gap-Learning-Platform`.
5. Render will automatically parse `render.yaml` and show:
   - **`karmayogi-competency-api`** (Python Web Service running Gunicorn & Flask).
   - **`karmayogi-competency-web`** (Vue 3 Static Site).
6. Click **"Apply"**.
7. Render will automatically:
   - Install Python dependencies and build the database (`seed_demo.py`).
   - Generate secure random values for `SECRET_KEY` and `JWT_SECRET_KEY`.
   - Build the frontend bundle and serve it over global CDN with HTTPS.

---

## ⚡ Option 2: Decoupled Deploy (Backend on Render + Frontend on Vercel)

For ultra-fast global CDN delivery, you can host the frontend on **Vercel** and the backend API on **Render**.

### Step 1: Deploy Backend on Render
1. Go to [Render Dashboard](https://dashboard.render.com/) $\rightarrow$ **"New +"** $\rightarrow$ **"Web Service"**.
2. Connect your GitHub repository.
3. Configure the service settings:
   - **Name**: `karmayogi-competency-api`
   - **Runtime**: `Python 3`
   - **Branch**: `main`
   - **Build Command**:
     ```bash
     pip install -r backend/requirements.txt && python backend/seed_demo.py
     ```
   - **Start Command**:
     ```bash
     gunicorn -w 2 -b 0.0.0.0:$PORT backend.wsgi:app
     ```
   - **Plan**: Free
4. In the **Environment Variables** section, add:
   - `FLASK_APP`: `backend.wsgi:app`
   - `FLASK_ENV`: `production`
   - `SECRET_KEY`: *(click Generate or enter a 32-character random string)*
   - `JWT_SECRET_KEY`: *(click Generate or enter a 32-character random string)*
   - `CORS_ORIGINS`: `*` *(or your Vercel domain once deployed)*
   - `DATABASE_URL`: `sqlite:///instance/competency_platform.db`
5. Click **"Deploy Web Service"**.
6. Copy your deployed backend URL: `https://karmayogi-competency-api.onrender.com`.

---

### Step 2: Deploy Frontend on Vercel
1. Go to [vercel.com](https://vercel.com/) and log in with GitHub.
2. Click **"Add New..."** $\rightarrow$ **"Project"**.
3. Import your repository: `AI-Enabled-Competency-Gap-Learning-Platform`.
4. Configure the project:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click "Edit" and select `frontend`.
5. Expand **Environment Variables**:
   - **Key**: `VITE_API_URL`
   - **Value**: `https://karmayogi-competency-api.onrender.com/api` *(replace with your actual Render URL)*
6. Click **"Deploy"**.
7. In ~60 seconds, Vercel will provide your live URL (e.g. `https://karmayogi-platform.vercel.app`).

---

## 🐘 Production PostgreSQL Migration (Optional)

By default, the platform runs on SQLite for lightweight demo deployments. For high-concurrency production deployments with thousands of officers:

1. Provision a free managed PostgreSQL database on [Render](https://render.com/docs/databases), [Neon](https://neon.tech/), or [Supabase](https://supabase.com/).
2. Copy the PostgreSQL connection string URI (e.g., `postgresql://user:password@hostname:5432/dbname`).
3. Set the `DATABASE_URL` environment variable on your backend web service:
   ```ini
   DATABASE_URL=postgresql://user:password@hostname:5432/dbname
   ```
4. The application automatically initializes tables and runs `seed_demo.py` on the connected PostgreSQL database during deployment!

---

## 🔒 Post-Deployment Security Checklist

- [ ] Ensure `FLASK_ENV=production` is set in production environment variables.
- [ ] Confirm `SECRET_KEY` and `JWT_SECRET_KEY` are long, random secrets.
- [ ] Restrict `CORS_ORIGINS` to your production frontend domain (e.g., `https://karmayogi-platform.vercel.app`).
- [ ] Verify that Google Gemini API key (`GEMINI_API_KEY`) is provided if live AI question generation is desired.
