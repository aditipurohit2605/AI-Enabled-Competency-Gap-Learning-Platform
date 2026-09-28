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

## Available Views
- **/login** & **/register**: Sign in or register as a learner, trainer, or admin. Includes theme toggle button.
- **/dashboard**: Real-time role readiness score, top 3 priority competency gaps, next recommended course, and latest quiz result.
- **/profile**: AI profile text extraction using BAAI embeddings, 1–5 self-assessment forms, and unified competency table with source breakdowns.
- **/gap**: Interactive required vs. current competency bar charts, sorted priority tables, and prerequisite blocker alerts.
- **/path**: Directed Acyclic Graph (DAG) curriculum grouped by Foundation, Core, and Advanced stages with course status tracking (`Planned`, `In Progress`, `Completed`).
- **/quiz**: Adaptive multiple-choice quiz engine with single question progress navigation, diagnostic role evaluations, and instant citation review.
- **/history**: Past quiz attempts list and readiness percentage trajectory line chart.
- **/trainer/documents**: Upload curriculum documents, validate size/type, and trigger offline/online MCQ question generation.
- **/trainer/review**: Review draft questions, edit questions/options/explanations, and approve or reject questions.
- **/admin/analytics**: Executive analytics with top 5 competency gap bar chart and full learner × competency proficiency heatmap.
- **/admin/framework**: Competency framework taxonomy editor with cycle detection.
- **/admin/users**: User directory with role filtering.

## Theming System (Light / Dark / System)

The platform includes a comprehensive, accessible dark theme system adhering to WCAG AA contrast standards.

### How Theming Works
1. **Design Tokens**: All colors are defined as CSS custom properties in `src/style.css`. Default values are declared in `:root` (light) and overridden in `[data-theme="dark"]`. Native scrollbars and inputs automatically adjust via `color-scheme`.
2. **State Management & Persistence**:
   - `src/stores/theme.js` maintains the active mode: `'light'`, `'dark'`, or `'system'` (default).
   - Mode is saved in `localStorage` under the key `'karmayogi-theme'`.
   - In `'system'` mode, the app listens to the browser `prefers-color-scheme` media query and updates immediately when the OS setting changes.
3. **FOUC Prevention**: An inline script in `index.html` evaluates the saved theme preference and system query before the app bundle mounts, setting `data-theme` on `<html>` immediately to avoid any flash of unstyled content.
4. **Reactive Visualizations**:
   - Chart.js charts (`GapReport.vue`, `HistoryView.vue`, `AdminAnalytics.vue`) read grid, tooltip, font, and dataset colors from reactive computed properties tied to `themeStore.isDark`.
   - Charts use `:key="themeStore.currentTheme"` to smoothly redraw without layout shift upon theme toggling.
5. **Accessible Heatmap**: The admin heatmap uses a dual-palette matrix ensuring cell text meets WCAG AA contrast requirements in both themes.

### How to Add a New Color Variable
1. Open `frontend/src/style.css`.
2. Add your variable to `:root` with your light-mode color:
   ```css
   :root {
     --color-my-feature: #2563eb;
     --color-my-feature-bg: #eff6ff;
   }
   ```
3. Add the dark-mode override inside `[data-theme="dark"]` (verify WCAG AA $\ge 4.5:1$ contrast against the surface):
   ```css
   [data-theme="dark"] {
     --color-my-feature: #60a5fa;
     --color-my-feature-bg: rgba(59, 130, 246, 0.18);
   }
   ```
4. Use it anywhere in your Vue components or CSS:
   ```css
   .my-element {
     background-color: var(--color-my-feature-bg);
     color: var(--color-my-feature);
   }
   ```

