import os
import random
import uuid
from pathlib import Path
from flask import Blueprint, request, jsonify, g
from werkzeug.utils import secure_filename

from backend.app.extensions import db, limiter
from backend.app.models.assessment import Document, Question, QuizAttempt, QuizSession, GapSnapshot
from backend.app.models.competency import Competency, Role, RoleCompetency
from backend.app.utils.auth import role_required
from backend.services.chunker import (
    ensure_storage_dirs,
    extract_document_pages,
    split_text_into_chunks,
    build_and_save_document_index,
    load_document_index,
    UPLOADS_DIR
)
from backend.services.mcq_generator import generate_mcqs
from backend.services.leveling import (
    save_quiz_result_and_update_level,
    get_user_current_competency_level,
    take_gap_snapshot
)

assessment_bp = Blueprint("assessment", __name__, url_prefix="/api")

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".text"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB in bytes


def is_allowed_file(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


# ---------------------------------------------------------
# Document Ingestion Endpoints (Trainer/Admin only)
# ---------------------------------------------------------

@assessment_bp.route("/documents", methods=["POST"])
@role_required("trainer", "admin")
def upload_document():
    """
    Upload and ingest training document (PDF, DOCX, or TXT, max 10MB).
    Extracts text, chunks it, builds a FAISS index, and creates a Document record.
    """
    ensure_storage_dirs()

    if "file" not in request.files:
        return jsonify({"error": "Bad Request", "message": "No file part in request"}), 400

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"error": "Bad Request", "message": "No file selected"}), 400

    original_filename = file.filename
    if not is_allowed_file(original_filename):
        return jsonify({
            "error": "Bad Request",
            "message": f"Unsupported file type. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        }), 400

    # Read and check size
    file_bytes = file.read()
    if len(file_bytes) == 0:
        return jsonify({"error": "Bad Request", "message": "Uploaded file is empty"}), 400
    if len(file_bytes) > MAX_FILE_SIZE:
        return jsonify({
            "error": "Bad Request",
            "message": f"File exceeds maximum size limit of 10 MB (received {len(file_bytes)} bytes)"
        }), 400

    title = request.form.get("title") or Path(original_filename).stem
    competency_id = request.form.get("competency_id")
    comp_id_int = None
    if competency_id:
        try:
            comp_id_int = int(competency_id)
            if not db.session.get(Competency, comp_id_int):
                return jsonify({"error": "Bad Request", "message": f"Competency {comp_id_int} does not exist"}), 400
        except ValueError:
            return jsonify({"error": "Bad Request", "message": "competency_id must be an integer"}), 400

    # Save to disk
    safe_name = secure_filename(original_filename)
    stored_filename = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    file_path = UPLOADS_DIR / stored_filename
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # Extract text
    try:
        pages = extract_document_pages(file_path)
    except Exception as e:
        if file_path.exists():
            file_path.unlink()
        return jsonify({"error": "Processing Error", "message": f"Failed to extract text from file: {e}"}), 400

    if not pages or not any(p.get("text", "").strip() for p in pages):
        if file_path.exists():
            file_path.unlink()
        return jsonify({"error": "Bad Request", "message": "Document contains no extractable text"}), 400

    # Chunk text
    chunks = split_text_into_chunks(pages, chunk_size=800, overlap=100)

    # Create Document row
    doc = Document(
        title=title,
        filename=stored_filename,
        uploaded_by=g.current_user.id
    )
    if comp_id_int:
        doc.competency_id = comp_id_int

    db.session.add(doc)
    db.session.commit()

    # Build and persist FAISS index
    build_and_save_document_index(doc.id, chunks)

    return jsonify({
        "message": "Document uploaded and indexed successfully",
        "document": doc.to_dict(),
        "chunks_count": len(chunks)
    }), 201


@assessment_bp.route("/documents", methods=["GET"])
@role_required("trainer", "admin")
def list_documents():
    """List all uploaded documents with question counts by status."""
    docs = Document.query.order_by(Document.created_at.desc()).all()
    res = []
    for d in docs:
        d_dict = d.to_dict()
        draft_c = Question.query.filter_by(document_id=d.id, status="draft").count()
        approved_c = Question.query.filter_by(document_id=d.id, status="approved").count()
        rejected_c = Question.query.filter_by(document_id=d.id, status="rejected").count()
        d_dict["draft_count"] = draft_c
        d_dict["approved_count"] = approved_c
        d_dict["rejected_count"] = rejected_c
        d_dict["questions_count"] = draft_c + approved_c + rejected_c
        res.append(d_dict)
    return jsonify({"documents": res}), 200


@assessment_bp.route("/documents/<int:document_id>", methods=["GET"])
@role_required("trainer", "admin")
def get_document(document_id):
    """Get single document details with chunk and question statistics."""
    doc = db.session.get(Document, document_id)
    if not doc:
        return jsonify({"error": "Not Found", "message": f"Document {document_id} not found"}), 404

    _, chunks = load_document_index(document_id)
    doc_dict = doc.to_dict()
    doc_dict["chunks_count"] = len(chunks)
    draft_c = Question.query.filter_by(document_id=doc.id, status="draft").count()
    approved_c = Question.query.filter_by(document_id=doc.id, status="approved").count()
    rejected_c = Question.query.filter_by(document_id=doc.id, status="rejected").count()
    doc_dict["draft_count"] = draft_c
    doc_dict["approved_count"] = approved_c
    doc_dict["rejected_count"] = rejected_c
    doc_dict["questions_count"] = draft_c + approved_c + rejected_c
    return jsonify({"document": doc_dict}), 200


@assessment_bp.route("/questions", methods=["GET"])
@role_required("trainer", "admin")
def list_questions():
    """
    List questions across all documents or filtered by document_id and/or status.
    Available to trainers and admins only.
    """
    query = Question.query
    doc_id = request.args.get("document_id")
    if doc_id:
        try:
            query = query.filter_by(document_id=int(doc_id))
        except (ValueError, TypeError):
            pass
    status_filter = request.args.get("status")
    if status_filter and status_filter.lower() != "all":
        query = query.filter_by(status=status_filter.lower())

    questions = query.order_by(Question.id.desc()).all()
    return jsonify({
        "count": len(questions),
        "questions": [q.to_dict(include_correct=True) for q in questions]
    }), 200


# ---------------------------------------------------------
# Question Generation & Review Endpoints (Trainer/Admin)
# ---------------------------------------------------------

@assessment_bp.route("/documents/<int:document_id>/generate", methods=["POST"])
@role_required("trainer", "admin")
@limiter.limit("10 per minute")
def generate_questions_for_document(document_id):
    """
    Generate multiple-choice questions from an uploaded document using LLM.
    Saves approved questions to database in 'draft' status.
    """
    doc = db.session.get(Document, document_id)
    if not doc:
        return jsonify({"error": "Not Found", "message": f"Document {document_id} not found"}), 404

    data = request.get_json(silent=True) or {}
    num_questions = data.get("num_questions", 5)
    try:
        num_questions = int(num_questions)
    except (ValueError, TypeError):
        return jsonify({"error": "Bad Request", "message": "num_questions must be an integer"}), 400

    difficulty = data.get("difficulty", "medium")
    topic_focus = data.get("topic_focus")

    try:
        result = generate_mcqs(
            document_id=document_id,
            num_questions=num_questions,
            difficulty=difficulty,
            topic_focus=topic_focus
        )
    except Exception as e:
        return jsonify({"error": "Generation Error", "message": str(e)}), 400

    return jsonify({
        "message": f"Generated {result['kept']} questions in draft status",
        "result": result
    }), 200


@assessment_bp.route("/documents/<int:document_id>/questions", methods=["GET"])
@role_required("trainer", "admin")
def get_document_questions(document_id):
    """
    Get questions for a document, optionally filtered by status (draft, approved, rejected).
    """
    doc = db.session.get(Document, document_id)
    if not doc:
        return jsonify({"error": "Not Found", "message": f"Document {document_id} not found"}), 404

    status_filter = request.args.get("status")
    query = Question.query.filter_by(document_id=document_id)
    if status_filter:
        query = query.filter_by(status=status_filter.lower())

    questions = query.order_by(Question.id.asc()).all()
    return jsonify({
        "document_id": document_id,
        "count": len(questions),
        "questions": [q.to_dict(include_correct=True) for q in questions]
    }), 200


@assessment_bp.route("/questions/<int:question_id>", methods=["PUT"])
@role_required("trainer", "admin")
def edit_question(question_id):
    """
    Edit question fields (text, options, correct_index, explanation, difficulty, status).
    """
    question = db.session.get(Question, question_id)
    if not question:
        return jsonify({"error": "Not Found", "message": f"Question {question_id} not found"}), 404

    data = request.get_json(silent=True) or {}

    if "text" in data:
        new_text = str(data["text"]).strip()
        if not new_text:
            return jsonify({"error": "Bad Request", "message": "Question text cannot be empty"}), 400
        question.text = new_text

    if "options" in data:
        new_options = data["options"]
        if not isinstance(new_options, list) or len(new_options) != 4:
            return jsonify({"error": "Bad Request", "message": "Options must be a list of 4 choices"}), 400
        question.options = new_options

    if "correct_index" in data:
        try:
            c_idx = int(data["correct_index"])
            if not (0 <= c_idx <= 3):
                raise ValueError()
            question.correct_index = c_idx
        except ValueError:
            return jsonify({"error": "Bad Request", "message": "correct_index must be an integer between 0 and 3"}), 400

    if "explanation" in data:
        question.explanation = str(data["explanation"])

    if "difficulty" in data:
        question.difficulty = str(data["difficulty"]).lower()

    if "status" in data:
        new_status = str(data["status"]).lower()
        if new_status not in Question.VALID_STATUSES:
            return jsonify({
                "error": "Bad Request",
                "message": f"Invalid status '{new_status}'. Allowed: {', '.join(sorted(Question.VALID_STATUSES))}"
            }), 400
        question.status = new_status

    db.session.commit()
    return jsonify({
        "message": "Question updated successfully",
        "question": question.to_dict(include_correct=True)
    }), 200


@assessment_bp.route("/questions/<int:question_id>/approve", methods=["POST"])
@role_required("trainer", "admin")
def approve_question(question_id):
    """Mark a question as approved for quizzes."""
    question = db.session.get(Question, question_id)
    if not question:
        return jsonify({"error": "Not Found", "message": f"Question {question_id} not found"}), 404

    question.status = "approved"
    db.session.commit()
    return jsonify({
        "message": "Question approved",
        "question": question.to_dict(include_correct=True)
    }), 200


@assessment_bp.route("/questions/<int:question_id>/reject", methods=["POST"])
@role_required("trainer", "admin")
def reject_question(question_id):
    """Mark a question as rejected."""
    question = db.session.get(Question, question_id)
    if not question:
        return jsonify({"error": "Not Found", "message": f"Question {question_id} not found"}), 404

    question.status = "rejected"
    db.session.commit()
    return jsonify({
        "message": "Question rejected",
        "question": question.to_dict(include_correct=True)
    }), 200


@assessment_bp.route("/documents/<int:document_id>/approve-all", methods=["POST"])
@role_required("trainer", "admin")
def approve_all_questions_for_document(document_id):
    """Approve all draft questions for a given document."""
    doc = db.session.get(Document, document_id)
    if not doc:
        return jsonify({"error": "Not Found", "message": f"Document {document_id} not found"}), 404

    draft_questions = Question.query.filter_by(document_id=document_id, status="draft").all()
    for q in draft_questions:
        q.status = "approved"

    db.session.commit()
    return jsonify({
        "message": f"Approved {len(draft_questions)} questions",
        "count": len(draft_questions),
        "approved_count": len(draft_questions)
    }), 200


# ---------------------------------------------------------
# Learner Quiz Delivery Endpoint (Login required, any role)
# ---------------------------------------------------------

@assessment_bp.route("/quiz/<int:competency_id>", methods=["GET"])
@role_required()  # Any authenticated user (learner, trainer, admin)
def get_quiz_questions(competency_id):
    """
    Get approved questions for a competency without answers or explanations.
    Learners never see draft/rejected questions, correct_index, or explanations.
    """
    comp = db.session.get(Competency, competency_id)
    if not comp:
        return jsonify({"error": "Not Found", "message": f"Competency {competency_id} not found"}), 404

    n = request.args.get("n", 10)
    try:
        n = max(1, min(50, int(n)))
    except (ValueError, TypeError):
        n = 10

    # Query approved questions linked to this competency via documents
    doc_ids = [d.id for d in Document.query.filter_by(competency_id=competency_id).all()]
    if not doc_ids:
        return jsonify({
            "competency_id": competency_id,
            "competency_name": comp.name,
            "count": 0,
            "questions": []
        }), 200

    approved_questions = (
        Question.query
        .filter(Question.document_id.in_(doc_ids), Question.status == "approved")
        .limit(n)
        .all()
    )

    return jsonify({
        "competency_id": competency_id,
        "competency_name": comp.name,
        "count": len(approved_questions),
        "questions": [q.to_dict(include_correct=False) for q in approved_questions]
    }), 200


def _balance_questions_by_difficulty(questions: list[Question], n: int) -> list[Question]:
    """
    Select n questions balanced across available difficulty levels (easy, medium, hard).
    """
    if len(questions) <= n:
        shuffled = list(questions)
        random.shuffle(shuffled)
        return shuffled

    by_diff = {"easy": [], "medium": [], "hard": []}
    for q in questions:
        diff = (q.difficulty or "medium").lower()
        if diff in by_diff:
            by_diff[diff].append(q)
        else:
            by_diff["medium"].append(q)

    for k in by_diff:
        random.shuffle(by_diff[k])

    selected: list[Question] = []
    diff_keys = ["easy", "medium", "hard"]

    while len(selected) < n and any(by_diff[k] for k in diff_keys):
        for k in diff_keys:
            if by_diff[k] and len(selected) < n:
                selected.append(by_diff[k].pop(0))

    random.shuffle(selected)
    return selected


# ---------------------------------------------------------
# Quiz Sessions & Evaluation Endpoints (Learner / Any Role)
# ---------------------------------------------------------

@assessment_bp.route("/quiz/<int:competency_id>/start", methods=["POST"])
@role_required()
def start_quiz_session(competency_id):
    """
    Start a quiz session with n approved questions (random, balanced across difficulty).
    Avoids questions answered correctly in the user's last 2 sessions where possible.
    Returns session_id and questions without correct_index or explanation.
    Fails if fewer than 3 approved questions exist.
    """
    comp = db.session.get(Competency, competency_id)
    if not comp:
        return jsonify({"error": "Not Found", "message": f"Competency {competency_id} not found"}), 404

    data = request.get_json(silent=True) or {}
    requested_n = data.get("n", 5)
    try:
        requested_n = int(requested_n)
    except (ValueError, TypeError):
        requested_n = 5

    # Get all approved questions for this competency
    doc_ids = [d.id for d in Document.query.filter_by(competency_id=competency_id).all()]
    if not doc_ids:
        approved_questions = []
    else:
        approved_questions = (
            Question.query
            .filter(Question.document_id.in_(doc_ids), Question.status == "approved")
            .all()
        )

    if len(approved_questions) < 3:
        return jsonify({
            "error": "Insufficient Questions",
            "message": f"Fewer than 3 approved questions exist for competency '{comp.name}' (found {len(approved_questions)}). Please ask a trainer to generate and approve questions first."
        }), 400

    target_n = min(len(approved_questions), max(3, requested_n))

    # Find questions answered correctly in the user's last 2 sessions
    recent_sessions = (
        QuizSession.query
        .filter_by(user_id=g.current_user.id, competency_id=competency_id)
        .filter(QuizSession.submitted_at.isnot(None))
        .order_by(QuizSession.submitted_at.desc())
        .limit(2)
        .all()
    )
    recent_correct_ids = {
        attempt.question_id
        for s in recent_sessions
        for attempt in s.attempts
        if attempt.is_correct
    }

    preferred = [q for q in approved_questions if q.id not in recent_correct_ids]
    fallback = [q for q in approved_questions if q.id in recent_correct_ids]

    if len(preferred) >= target_n:
        selected_questions = _balance_questions_by_difficulty(preferred, target_n)
    else:
        # Take all preferred, then fill the remainder from fallback
        needed_from_fallback = target_n - len(preferred)
        selected_preferred = _balance_questions_by_difficulty(preferred, len(preferred))
        selected_fallback = _balance_questions_by_difficulty(fallback, needed_from_fallback)
        selected_questions = selected_preferred + selected_fallback
        random.shuffle(selected_questions)

    # Record previous skill level
    prev_level = get_user_current_competency_level(g.current_user.id, competency_id)

    session = QuizSession(
        user_id=g.current_user.id,
        competency_id=competency_id,
        question_ids=[q.id for q in selected_questions],
        level_before=prev_level
    )
    db.session.add(session)
    db.session.commit()

    return jsonify({
        "message": "Quiz session started",
        "session_id": session.id,
        "competency_id": competency_id,
        "competency_name": comp.name,
        "level_before": prev_level,
        "question_count": len(selected_questions),
        "questions": [q.to_dict(include_correct=False) for q in selected_questions]
    }), 201


@assessment_bp.route("/quiz/session/<int:session_id>/submit", methods=["POST"])
@role_required()
def submit_quiz_session(session_id):
    """
    Submit answers for a quiz session:
      - Validates ownership (only owner can submit)
      - Idempotent: a second call returns the saved result without double-counting
      - Unanswered questions count as wrong
      - Saves QuizAttempt rows, computes score, updates level, takes GapSnapshot
      - Returns question results with explanations and the new competency level
    """
    session = db.session.get(QuizSession, session_id)
    if not session:
        return jsonify({"error": "Not Found", "message": f"Quiz session {session_id} not found"}), 404

    if session.user_id != g.current_user.id:
        return jsonify({"error": "Forbidden", "message": "You cannot submit another user's quiz session"}), 403

    # Idempotent double-submit safety: return already saved results
    if session.submitted_at is not None:
        attempts = QuizAttempt.query.filter_by(session_id=session.id).all()
        q_results = []
        for att in attempts:
            q = att.question
            q_results.append({
                "question_id": att.question_id,
                "text": q.text if q else None,
                "options": q.options if q else [],
                "chosen_index": att.chosen_index,
                "correct_index": q.correct_index if q else None,
                "is_correct": att.is_correct,
                "explanation": q.explanation if q else None,
                "source_passage": q.source_passage if q else None,
                "difficulty": q.difficulty if q else None
            })
        return jsonify({
            "message": "Quiz session already submitted",
            "session_id": session.id,
            "competency_id": session.competency_id,
            "score_pct": session.score_pct,
            "level_before": session.level_before,
            "level_after": session.level_after,
            "new_level": session.level_after,
            "question_results": q_results
        }), 200

    data = request.get_json(silent=True) or {}
    answers = data.get("answers", {})

    role_id = data.get("role_id") or request.args.get("role_id")
    if role_id is not None:
        try:
            role_id = int(role_id)
        except (ValueError, TypeError):
            role_id = None

    result = save_quiz_result_and_update_level(session, answers, role_id=role_id)

    return jsonify({
        "message": "Quiz submitted successfully",
        "result": result
    }), 200


@assessment_bp.route("/quiz/history", methods=["GET"])
@role_required()
def get_quiz_history():
    """
    Get the authenticated user's submitted quiz sessions, newest first.
    Includes score, level change, and question count.
    """
    sessions = (
        QuizSession.query
        .filter_by(user_id=g.current_user.id)
        .filter(QuizSession.submitted_at.isnot(None))
        .order_by(QuizSession.submitted_at.desc())
        .all()
    )
    return jsonify({
        "history": [s.to_dict() for s in sessions]
    }), 200


@assessment_bp.route("/progress/gap-trend", methods=["GET"])
@role_required()
def get_gap_trend():
    """
    Get timeline of GapSnapshots for a role over time for trend charts.
    """
    role_id = request.args.get("role_id")
    if not role_id:
        return jsonify({"error": "Bad Request", "message": "role_id query parameter is required"}), 400

    try:
        role_id_int = int(role_id)
    except ValueError:
        return jsonify({"error": "Bad Request", "message": "role_id must be an integer"}), 400

    role = db.session.get(Role, role_id_int)
    if not role:
        return jsonify({"error": "Not Found", "message": f"Role {role_id_int} not found"}), 404

    snapshots = (
        GapSnapshot.query
        .filter_by(user_id=g.current_user.id, role_id=role_id_int)
        .order_by(GapSnapshot.taken_at.asc())
        .all()
    )

    return jsonify({
        "role_id": role_id_int,
        "role_name": role.name,
        "count": len(snapshots),
        "snapshots": [s.to_dict() for s in snapshots]
    }), 200


# ---------------------------------------------------------
# Diagnostic Mode Endpoints (Learner / Any Role)
# ---------------------------------------------------------

@assessment_bp.route("/diagnostic/start", methods=["POST"])
@role_required()
def start_diagnostic():
    """
    Builds one session per required competency of the role (3 questions each,
    only competencies that have at least 3 approved questions).
    Competencies without enough questions are reported as 'not assessed', not as level 0.
    """
    data = request.get_json(silent=True) or {}
    role_id = request.args.get("role_id") or data.get("role_id")
    if not role_id:
        return jsonify({"error": "Bad Request", "message": "role_id parameter is required"}), 400

    try:
        role_id_int = int(role_id)
    except ValueError:
        return jsonify({"error": "Bad Request", "message": "role_id must be an integer"}), 400

    role = db.session.get(Role, role_id_int)
    if not role:
        return jsonify({"error": "Not Found", "message": f"Role {role_id_int} not found"}), 404

    role_competencies = RoleCompetency.query.filter_by(role_id=role_id_int).all()
    if not role_competencies:
        return jsonify({"error": "Bad Request", "message": f"Role {role.name} has no competencies configured"}), 400

    sessions = []
    not_assessed = []

    for rc in role_competencies:
        comp_id = rc.competency_id
        comp = rc.competency

        doc_ids = [d.id for d in Document.query.filter_by(competency_id=comp_id).all()]
        if not doc_ids:
            approved = []
        else:
            approved = (
                Question.query
                .filter(Question.document_id.in_(doc_ids), Question.status == "approved")
                .all()
            )

        if len(approved) >= 3:
            selected = _balance_questions_by_difficulty(approved, 3)
            prev_level = get_user_current_competency_level(g.current_user.id, comp_id)

            sess = QuizSession(
                user_id=g.current_user.id,
                competency_id=comp_id,
                question_ids=[q.id for q in selected],
                level_before=prev_level
            )
            db.session.add(sess)
            db.session.flush()

            sessions.append({
                "session_id": sess.id,
                "competency_id": comp_id,
                "competency_name": comp.name if comp else None,
                "required_level": rc.required_level,
                "questions": [q.to_dict(include_correct=False) for q in selected]
            })
        else:
            not_assessed.append({
                "competency_id": comp_id,
                "competency_name": comp.name if comp else None,
                "required_level": rc.required_level,
                "status": "not assessed",
                "reason": f"Only {len(approved)} approved question(s) exist; minimum 3 required."
            })

    db.session.commit()

    return jsonify({
        "role_id": role.id,
        "role_name": role.name,
        "sessions": sessions,
        "not_assessed": not_assessed
    }), 200


@assessment_bp.route("/diagnostic/submit", methods=["POST"])
@role_required()
def submit_diagnostic():
    """
    Submits answers for all diagnostic sessions at once.
    Body format:
    {
      "role_id": <id>,
      "sessions": [
        {"session_id": <id>, "answers": {<question_id>: <chosen_index>}}
      ]
    }
    """
    data = request.get_json(silent=True) or {}
    role_id = data.get("role_id") or request.args.get("role_id")
    if not role_id:
        return jsonify({"error": "Bad Request", "message": "role_id is required"}), 400

    try:
        role_id_int = int(role_id)
    except ValueError:
        return jsonify({"error": "Bad Request", "message": "role_id must be an integer"}), 400

    role = db.session.get(Role, role_id_int)
    if not role:
        return jsonify({"error": "Not Found", "message": f"Role {role_id_int} not found"}), 404

    session_submissions = data.get("sessions", [])
    if not isinstance(session_submissions, list):
        return jsonify({"error": "Bad Request", "message": "sessions must be a list of session objects"}), 400

    results = []
    for sub in session_submissions:
        sess_id = sub.get("session_id")
        answers = sub.get("answers", {})

        sess = db.session.get(QuizSession, sess_id)
        if not sess or sess.user_id != g.current_user.id:
            continue

        if sess.submitted_at is not None:
            continue

        res = save_quiz_result_and_update_level(sess, answers, role_id=None)
        results.append(res)

    # Take comprehensive GapSnapshot for the role
    snapshot = take_gap_snapshot(g.current_user.id, role_id_int)
    if snapshot:
        db.session.commit()

    return jsonify({
        "message": f"Processed {len(results)} diagnostic session(s)",
        "role_id": role_id_int,
        "role_name": role.name,
        "session_results": results,
        "gap_snapshot": snapshot.to_dict() if snapshot else None
    }), 200
