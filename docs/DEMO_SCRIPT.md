# Karmayogi Platform — 5-Minute Live Presentation Script

A concise, step-by-step presentation walkthrough showcasing all core modules of the AI-Enabled Competency Gap & Learning Platform (Ministry of Statistics and Programme Implementation - MoSPI).

---

## ⏱️ Presentation Timing Overview (5 Minutes)

| Time | Phase | Role | Screen / Action | Key Speaking Point |
|---|---|---|---|---|
| **0:00 - 0:45** | 1. Executive Intelligence | **Admin** | `/admin/analytics` | Macro organizational health, top gaps in *Sampling* and *ML*, learner heatmap |
| **0:45 - 1:30** | 2. Semantic Profile Parsing | **Learner** | `/profile` | Paste resume/bio; zero-shot semantic skill extraction with confidence evidence |
| **1:30 - 2:15** | 3. Role Gap Diagnostic | **Learner** | `/gap` | Readiness score, required vs. current proficiency, blocked prerequisite bottlenecks |
| **2:15 - 2:45** | 4. DAG Learning Path | **Learner** | `/path` | Topological course ordering resolving prerequisite dependencies first |
| **2:45 - 3:30** | 5. Document Ingestion & AI Generation | **Trainer** | `/trainer/documents` | Upload PDF/TXT, FAISS chunk retrieval, automated Gemini MCQ synthesis |
| **3:30 - 4:15** | 6. Question Review & Approval | **Trainer** | `/trainer/review` | Card editor, cited text verification, bulk 1-click approval into question pool |
| **4:15 - 4:45** | 7. Adaptive Assessment | **Learner** | `/quiz` | Balanced test session; real-time grading, instantaneous level advancement |
| **4:45 - 5:00** | 8. Closed-Loop Progress | **Learner** | `/history` & `/gap` | Gap closed, historical readiness curve updated, continuous learning cycle |

---

## 🎭 Step-by-Step Walkthrough Guide

### Step 1: Executive Analytics & Heatmap (Admin Perspective)
- **Account**: `admin@example.com` / `admin123`
- **Navigate to**: `http://localhost:5173/admin/analytics`
- **Actions**:
  1. Highlight the **Top KPI Cards**: 25 active learners across MoSPI cadres, average readiness (~55%), and completed assessments.
  2. Point out the **Top 5 Most Common Gaps** bar chart: show that *Sampling Methods* and *Machine Learning Basics* are the two primary institutional bottlenecks.
  3. Scroll through the **Learner Competency Heatmap Matrix**: explain how color gradients ($L0$ through $L5$) give leaders instant visibility into who is qualified and who needs upskilling.
  4. Switch the **Target Role** filter to demonstrate dynamic re-calculation across cadres.
- **Narrative**:
  > *"Leadership currently lacks continuous visibility into workforce competencies. Our executive dashboard instantly surfaces systemic bottlenecks like Sampling Methods across 25 officers and visualizes organizational competency distribution in real time."*

---

### Step 2: Semantic Profile Analysis (Learner Perspective)
- **Account**: Log out, log in as `learner1@example.com` / `learner123`
- **Navigate to**: `http://localhost:5173/profile`
- **Actions**:
  1. Show the bio text area. Click **"Analyze & Extract Skills"** (or paste a custom experience summary).
  2. Watch the semantic extractor identify skills and assign proficiency levels ($L1$ to $L4$) with sentence citations and reasoning evidence.
- **Narrative**:
  > *"Officers don't need to manually fill tedious 100-question surveys. Our embedding pipeline reads their bio or training history, matches evidence to the Karmayogi framework, and transparently explains why a level was assigned."*

---

### Step 3: Diagnostic Gap Report
- **Navigate to**: `http://localhost:5173/gap`
- **Actions**:
  1. Highlight the **Overall Role Readiness Score** (e.g. 52%).
  2. Inspect the **Comparison Chart** showing Current Assessed Level vs. Required Role Level.
  3. Show the **Prerequisite Status** column: note how certain gaps are marked as *"⚠️ Blocked by: Statistics Fundamentals"*, preventing premature enrollment in advanced topics.
- **Narrative**:
  > *"A gap isn't just a number—it has dependencies. Our platform uses Directed Acyclic Graphs (DAGs) to identify root bottlenecks so learners tackle foundational prerequisites before attempting advanced tasks."*

---

### Step 4: Topological Learning Curriculum
- **Navigate to**: `http://localhost:5173/path`
- **Actions**:
  1. Walk through the recommended course path.
  2. Show how the curriculum order respects prerequisite rules using NetworkX topological sorting, ensuring foundational courses come before dependent modules.
- **Narrative**:
  > *"The learning path creates a personalized curriculum that guides the officer step-by-step from beginner to mastery, pulling in missing prerequisites automatically."*

---

### Step 5: Document Ingestion & AI MCQ Generation (Trainer Perspective)
- **Account**: Switch accounts, log in as `trainer@example.com` / `trainer123`
- **Navigate to**: `http://localhost:5173/trainer/documents`
- **Actions**:
  1. Click **"+ Upload Document"**. Drag and drop a training manual (or highlight existing pre-indexed manuals).
  2. Click **"✨ Generate MCQs"** on *Sampling Techniques and Frame Design Manual*.
  3. Select **5 questions**, difficulty **Medium**, and click **"Generate Questions"**.
  4. Note the progress indicator querying Gemini, followed by the result summary showing kept questions and quality validation checks.
- **Narrative**:
  > *"Trainers don't have time to write thousands of test questions. They simply upload existing government manuals. Our RAG engine extracts semantic chunks and generates quality-checked MCQs in seconds."*

---

### Step 6: Review & Approve Questions
- **Navigate to**: `http://localhost:5173/trainer/review`
- **Actions**:
  1. View the newly generated questions in draft status with yellow tags.
  2. Expand a question card: show the editable question text, 4 choices with correct answer radio, explanation, and the read-only **Source Document Citation**.
  3. Click **"✓ Approve All Draft Questions"** and confirm.
- **Narrative**:
  > *"AI assists, but human trainers remain in full control. Trainers verify questions against the exact source passage citations and approve them into the active test bank with one click."*

---

### Step 7: Adaptive Assessment Session
- **Account**: Switch back to `learner1@example.com` / `learner123`
- **Navigate to**: `http://localhost:5173/quiz`
- **Actions**:
  1. Select **Sampling Methods** assessment. Click **"Start Assessment"**.
  2. Walk through the questions. Select answers.
  3. Click **"Submit Assessment"**.
  4. Show the instant result card: **Score 100%**, level upgraded from **L1 $\rightarrow$ L2**.
- **Narrative**:
  > *"Learners validate their skills through targeted assessments. Grading is instantaneous, secure, and dynamically updates their evaluated level."*

---

### Step 8: Closed-Loop Progress Verification
- **Navigate to**: `http://localhost:5173/history` then `http://localhost:5173/gap`
- **Actions**:
  1. On **History & Trend**, show the upward historical readiness curve tracking snapshots over time.
  2. On **Gap Report**, show that the Sampling Methods gap has narrowed and overall readiness percentage has improved!
- **Narrative**:
  > *"The loop is closed: diagnosis $\rightarrow$ curriculum $\rightarrow$ training $\rightarrow$ assessment $\rightarrow$ measurable institutional readiness. This is the future of capability building under Mission Karmayogi."*
