from datetime import datetime, timezone
from backend.app.extensions import db


class Document(db.Model):
    """Uploaded learning or training material from which questions are generated."""
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    uploader = db.relationship("User", back_populates="documents")
    questions = db.relationship("Question", back_populates="document", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "filename": self.filename,
            "uploaded_by": self.uploaded_by,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Document {self.title}>"


class Question(db.Model):
    """Assessment question generated from documents or created by trainers."""
    __tablename__ = "questions"

    VALID_STATUSES = {"draft", "approved"}

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    text = db.Column(db.Text, nullable=False)
    options = db.Column(db.JSON, nullable=False)  # JSON array of string choices
    correct_index = db.Column(db.Integer, nullable=False)
    explanation = db.Column(db.Text, nullable=True)
    source_passage = db.Column(db.Text, nullable=True)
    difficulty = db.Column(db.String(50), nullable=True, default="medium")
    status = db.Column(db.String(20), nullable=False, default="draft")  # draft | approved

    # Relationships
    document = db.relationship("Document", back_populates="questions")
    quiz_attempts = db.relationship("QuizAttempt", back_populates="question", cascade="all, delete-orphan")

    def __init__(self, text, options, correct_index, document_id=None, explanation=None, source_passage=None, difficulty="medium", status="draft"):
        self.text = text
        self.options = options
        self.correct_index = correct_index
        self.document_id = document_id
        self.explanation = explanation
        self.source_passage = source_passage
        self.difficulty = difficulty
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Allowed statuses are: {', '.join(sorted(self.VALID_STATUSES))}")
        self.status = status

    def to_dict(self, include_correct=True):
        data = {
            "id": self.id,
            "document_id": self.document_id,
            "text": self.text,
            "options": self.options,
            "difficulty": self.difficulty,
            "status": self.status,
            "source_passage": self.source_passage
        }
        if include_correct:
            data["correct_index"] = self.correct_index
            data["explanation"] = self.explanation
        return data

    def __repr__(self):
        return f"<Question id={self.id} status={self.status}>"


class QuizAttempt(db.Model):
    """User response to an assessment question."""
    __tablename__ = "quiz_attempts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    chosen_index = db.Column(db.Integer, nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = db.relationship("User", back_populates="quiz_attempts")
    question = db.relationship("Question", back_populates="quiz_attempts")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "question_id": self.question_id,
            "chosen_index": self.chosen_index,
            "is_correct": self.is_correct,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

    def __repr__(self):
        return f"<QuizAttempt user_id={self.user_id} question_id={self.question_id} is_correct={self.is_correct}>"
