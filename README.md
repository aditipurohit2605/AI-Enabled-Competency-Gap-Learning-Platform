# AI-Enabled Competency Gap & Learning Platform

An AI-driven competency management, diagnostic evaluation, and personalized learning platform tailored for official statistics personnel (Ministry of Statistics and Programme Implementation - MoSPI / SIH26101).

---

## Architecture Overview

- **Backend**: Python 3.13 / Flask 3 application factory with SQLAlchemy, NetworkX DAG prerequisite cycle detection, BAAI/bge-small semantic embedding model, FAISS inner-product vector indexing, and Gemini GenAI question generation.
- **Frontend**: Vue 3 (Composition API) + Vite with Pinia state management, Vue Router role guards, Chart.js visualizations, and responsive Vanilla CSS design system.

---

## Running Backend and Frontend Together

### 1. Prerequisites
- **Python**: 3.10+ (tested on Python 3.13)
- **Node.js**: v18+ (tested on Node v24)
- **Git**

---

### 2. Backend Setup & Startup

1. Open a terminal in the root directory:
   ```bash
   pip install -r backend/requirements.txt
   ```

2. Seed database with competencies, roles, prerequisites, and courses:
   ```bash
   python backend/seed.py
   ```

3. Start the Flask API server:
   ```bash
   python -m backend.wsgi
   ```
   The backend API will run at `http://127.0.0.1:5000`.

---

### 3. Frontend Setup & Startup

1. Open a second terminal window and navigate to the `frontend/` directory:
   ```bash
   cd frontend
   npm install
   ```

2. Start the Vite development server:
   ```bash
   npm run dev
   ```
   Open `http://localhost:5173` in your web browser.

---

### 4. Running Backend Tests

Run pytest across all backend unit and integration suites:
```bash
python -m pytest
```

---

### 5. Running Frontend Build & Lint

From the `frontend/` folder:
```bash
npm run lint    # Run ESLint over Vue/JS files
npm run build   # Compile production bundle
```

---

## Seeded Demo Credentials

| Role | Email | Password | Access |
|---|---|---|---|
| **Learner** | `learner1@example.com` | `learner123` | Dashboard, Skills, Gap Reports, Learning Path, Quizzes, History |
| **Trainer** | `trainer@example.com` | `trainer123` | Document Upload, Chunking, MCQ Generation, Question Approval |
| **Administrator** | `admin@example.com` | `admin123` | Full access across all platform modules |
