import os
import uuid
from pathlib import Path
from flask import Blueprint, request, jsonify, g
from werkzeug.utils import secure_filename

from backend.app.extensions import db
from backend.app.models.assessment import Document, Question
from backend.app.models.competency import Competency
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
    """List all uploaded documents."""
    docs = Document.query.order_by(Document.created_at.desc()).all()
    res = []
    for d in docs:
        d_dict = d.to_dict()
        d_dict["questions_count"] = Question.query.filter_by(document_id=d.id).count()
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
    doc_dict["questions_count"] = Question.query.filter_by(document_id=doc.id).count()
    return jsonify({"document": doc_dict}), 200


# ---------------------------------------------------------
# Question Generation & Review Endpoints (Trainer/Admin)
# ---------------------------------------------------------

@assessment_bp.route("/documents/<int:document_id>/generate", methods=["POST"])
@role_required("trainer", "admin")
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
        "count": len(draft_questions)
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
