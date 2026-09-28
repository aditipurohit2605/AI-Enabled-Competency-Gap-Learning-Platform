# Karmayogi Platform API Specification

Comprehensive documentation of all REST API endpoints available in the AI-Enabled Competency Gap & Learning Platform.

All endpoints return JSON responses. Protected endpoints require a valid JWT bearer token in the `Authorization` header:
`Authorization: Bearer <token>`

---

## 1. Authentication & Identity (`/api/auth`, `/api/me`)

| Method | Endpoint | Access | Description | Request Body | Response Summary |
|---|---|---|---|---|---|
| `POST` | `/api/auth/register` | Public | Register new user account | `{"name", "email", "password", "role"}` | `201 Created`: `{"token", "user"}` |
| `POST` | `/api/auth/login` | Public (20/min) | Authenticate user & issue JWT | `{"email", "password"}` | `200 OK`: `{"token", "user"}` |
| `GET` | `/api/auth/me` | Authenticated | Current user profile | None | `200 OK`: `{"user"}` |
| `GET` | `/api/me` | Authenticated | Direct identity alias | None | `200 OK`: `{"id", "name", "email", "role", "user"}` |

---

## 2. Competency Framework (`/api/competencies`, `/api/roles`, `/api/prerequisites`)

| Method | Endpoint | Access | Description | Request Body / Params | Response Summary |
|---|---|---|---|---|---|
| `GET` | `/api/competencies` | Authenticated | List all competencies | None | `200 OK`: `{"competencies": [...]}` |
| `GET` | `/api/competencies/<id>` | Authenticated | Single competency details | None | `200 OK`: `{"competency": {...}}` |
| `POST` | `/api/competencies` | Admin | Create new competency | `{"name", "description"}` | `201 Created`: `{"competency": {...}}` |
| `PUT` | `/api/competencies/<id>` | Admin | Update competency | `{"name", "description"}` | `200 OK`: `{"competency": {...}}` |
| `DELETE` | `/api/competencies/<id>` | Admin | Delete competency | None | `200 OK`: `{"message": "..."}` |
| `GET` | `/api/roles` | Authenticated | List all job roles | None | `200 OK`: `{"roles": [...]}` |
| `GET` | `/api/roles/<id>` | Authenticated | Single job role details | None | `200 OK`: `{"role": {...}}` |
| `POST` | `/api/roles` | Admin | Create job role | `{"name", "description"}` | `201 Created`: `{"role": {...}}` |
| `PUT` | `/api/roles/<id>` | Admin | Update job role | `{"name", "description"}` | `200 OK`: `{"role": {...}}` |
| `DELETE` | `/api/roles/<id>` | Admin | Delete job role | None | `200 OK`: `{"message": "..."}` |
| `GET` | `/api/roles/<id>/competencies` | Authenticated | Required competencies for role | None | `200 OK`: `{"role_id", "competencies": [...]}` |
| `POST` | `/api/roles/<id>/competencies` | Admin | Set required level (1-5) | `{"competency_id", "required_level"}` | `200 OK`: `{"competencies": [...]}` |
| `DELETE`| `/api/roles/<id>/competencies/<cid>`| Admin | Remove role requirement | None | `200 OK`: `{"message": "..."}` |
| `GET` | `/api/roles/<id>/framework` | Authenticated | Full role framework tree | None | `200 OK`: `{"role", "competencies": [...]}` |
| `GET` | `/api/prerequisites` | Authenticated | List prerequisite pairs | None | `200 OK`: `{"prerequisites": [...]}` |
| `POST` | `/api/prerequisites` | Admin | Add DAG prerequisite rule | `{"competency_id", "requires_competency_id"}` | `201 Created` / `400 Bad Request (Cycle)` |
| `DELETE`| `/api/prerequisites/<id>` | Admin | Delete prerequisite rule | None | `200 OK`: `{"message": "..."}` |

---

## 3. Learner Profile & Skills (`/api/profile`)

| Method | Endpoint | Access | Description | Request Body | Response Summary |
|---|---|---|---|---|---|
| `POST` | `/api/profile/analyze` | Authenticated | Semantic text skill extraction | `{"text", "threshold"?}` | `200 OK`: `{"extracted_count", "skills": [...]}` |
| `GET` | `/api/profile/skills` | Authenticated | Get merged profile & quiz skills | None | `200 OK`: `{"skills": [...]}` |
| `POST` | `/api/profile/self-assess` | Authenticated | Self-assess competency level | `{"competency_id", "level"}` | `200 OK`: `{"skill": {...}}` |
| `PUT` | `/api/profile/target-role` | Authenticated | Set learner target job role | `{"role_id"}` | `200 OK`: `{"user": {...}}` |

---

## 4. Diagnostic Gap Analysis & Learning Curriculum (`/api/gap`, `/api/path`)

| Method | Endpoint | Access | Description | Request Query | Response Summary |
|---|---|---|---|---|---|
| `GET` | `/api/gap` | Authenticated | Calculate role competency gaps | `?role_id=<id>` | `200 OK`: `{"readiness_percentage", "competencies": [...]}` |
| `GET` | `/api/path` | Authenticated | Topological DAG curriculum | `?role_id=<id>` | `200 OK`: `{"readiness_percentage", "curriculum": [...]}` |

---

## 5. Assessments & Document Ingestion (`/api/documents`, `/api/questions`, `/api/quiz`)

| Method | Endpoint | Access | Description | Request Body / Query | Response Summary |
|---|---|---|---|---|---|
| `POST` | `/api/documents` | Trainer, Admin | Upload PDF/DOCX/TXT file | `multipart/form-data`: `file`, `title`, `competency_id` | `201 Created`: `{"document", "chunks_count"}` |
| `GET` | `/api/documents` | Trainer, Admin | List uploaded documents | None | `200 OK`: `{"documents": [...]}` |
| `GET` | `/api/documents/<id>` | Trainer, Admin | Document chunk statistics | None | `200 OK`: `{"document": {...}}` |
| `POST` | `/api/documents/<id>/generate`| Trainer, Admin (10/min) | Generate MCQs via Gemini | `{"num_questions", "difficulty", "topic_focus"?}` | `200 OK`: `{"kept", "generated", "rejected"}` |
| `GET` | `/api/documents/<id>/questions`| Trainer, Admin | Document questions | `?status=draft/approved` | `200 OK`: `{"questions": [...]}` |
| `POST` | `/api/documents/<id>/approve-all`| Trainer, Admin | Approve all draft questions | None | `200 OK`: `{"approved_count"}` |
| `GET` | `/api/questions` | Trainer, Admin | Filter questions | `?document_id=<id>&status=<status>` | `200 OK`: `{"count", "questions": [...]}` |
| `PUT` | `/api/questions/<id>` | Trainer, Admin | Edit question options/text | `{"text", "options", "correct_index", "explanation", "difficulty"}` | `200 OK`: `{"question": {...}}` |
| `POST` | `/api/questions/<id>/approve`| Trainer, Admin | Approve question | None | `200 OK`: `{"question": {...}}` |
| `POST` | `/api/questions/<id>/reject` | Trainer, Admin | Reject question | None | `200 OK`: `{"question": {...}}` |
| `POST` | `/api/quiz/<comp_id>/start` | Authenticated | Start quiz assessment session | `{"n": 5}` | `200 OK`: `{"session_id", "questions": [...]}` |
| `POST` | `/api/quiz/session/<id>/submit`| Authenticated | Submit answers & grade | `{"answers": {"<qid>": <index>}}` | `200 OK`: `{"score_pct", "level_before", "level_after"}` |
| `GET` | `/api/quiz/history` | Authenticated | Learner assessment history | None | `200 OK`: `{"sessions": [...], "snapshots": [...]}` |

---

## 6. Executive Administration & Analytics (`/api/admin`)

| Method | Endpoint | Access | Description | Request Query | Response Summary |
|---|---|---|---|---|---|
| `GET` | `/api/admin/analytics` | Admin | Cross-organizational heatmap & KPIs | `?role_id=<id>` | `200 OK`: `{"num_learners", "average_readiness", "top_gaps", "learner_matrix", "quiz_stats"}` |
| `GET` | `/api/admin/users` | Admin | Registered user directory | None | `200 OK`: `{"users": [...]}` |
