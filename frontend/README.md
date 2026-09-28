# MoSPI Competency & Learning Platform - Frontend

Vue 3 + Vite frontend application for the AI-Enabled Competency Gap & Learning Platform.

## Technology Stack
- **Framework**: Vue 3 (Composition API, `<script setup>`)
- **Build Tool**: Vite
- **Routing**: Vue Router 4 (with role-based navigation guards)
- **State Management**: Pinia (token and user session persistence)
- **Visualizations**: Chart.js & vue-chartjs (bar comparison charts and readiness trend lines)
- **Styling**: Vanilla CSS design system with curated typography, responsive layouts, and zero heavy UI dependencies

## Project Setup

### 1. Install Dependencies
```bash
npm install
```

### 2. Development Server
Starts the Vite dev server with proxying to the Flask backend on `http://127.0.0.1:5000`:
```bash
npm run dev
```
Open `http://localhost:5173` in your browser.

### 3. Production Build
Compiles and minifies assets for production deployment into the `dist/` directory:
```bash
npm run build
```

### 4. Code Linting
Run ESLint over all Vue and JavaScript source files:
```bash
npm run lint
```

## Available Learner Views
- **/login**: Sign in or register as a learner, trainer, or admin.
- **/dashboard**: Real-time role readiness score, top 3 priority competency gaps, next recommended course, and latest quiz result.
- **/profile**: AI profile text extraction using BAAI embeddings, 1–5 self-assessment forms, and unified competency table with source breakdowns.
- **/gap**: Interactive required vs. current competency bar charts, sorted priority tables, and prerequisite blocker alerts.
- **/path**: Directed Acyclic Graph (DAG) curriculum grouped by Foundation, Core, and Advanced stages with course status tracking (`Planned`, `In Progress`, `Completed`).
- **/quiz**: Adaptive multiple-choice quiz engine with single question progress navigation, diagnostic role evaluations, and instant citation review.
- **/history**: Past quiz attempts list and readiness percentage trajectory line chart.
