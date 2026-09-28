from datetime import datetime, timezone
from backend.app.extensions import db


class Document(db.Model):
    """Uploaded learning or training material from which questions are generated."""
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    competency_id = db.Column(db.Integer, db.ForeignKey("competencies.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    uploader = db.relationship("User", back_populates="documents")
    competency = db.relationship("Competency", backref="documents")
    questions = db.relationship("Question", back_populates="document", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "filename": self.filename,
            "uploaded_by": self.uploaded_by,
            "competency_id": self.competency_id,
            "competency_name": self.competency.name if self.competency else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Document {self.title}>"


class Question(db.Model):
    """Assessment question generated from documents or created by trainers."""
    __tablename__ = "questions"

    VALID_STATUSES = {"draft", "approved", "rejected"}

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    text = db.Column(db.Text, nullable=False)
    options = db.Column(db.JSON, nullable=False)  # JSON array of string choices
    correct_index = db.Column(db.Integer, nullable=False)
    explanation = db.Column(db.Text, nullable=True)
    source_passage = db.Column(db.Text, nullable=True)
    difficulty = db.Column(db.String(50), nullable=True, default="medium")
    status = db.Column(db.String(20), nullable=False, default="draft")  # draft | approved | rejected

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


class QuizSession(db.Model):
    """Quiz session containing assigned questions and user evaluation results."""
    __tablename__ = "quiz_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    competency_id = db.Column(db.Integer, db.ForeignKey("competencies.id", ondelete="CASCADE"), nullable=False)
    question_ids = db.Column(db.JSON, nullable=False)  # List of question IDs
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=True)
    score_pct = db.Column(db.Float, nullable=True)
    level_before = db.Column(db.Float, nullable=True)
    level_after = db.Column(db.Float, nullable=True)

    # Relationships
    user = db.relationship("User", backref="quiz_sessions")
    competency = db.relationship("Competency", backref="quiz_sessions")
    attempts = db.relationship("QuizAttempt", back_populates="session", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "competency_id": self.competency_id,
            "competency_name": self.competency.name if self.competency else None,
            "question_ids": self.question_ids,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "score_pct": self.score_pct,
            "level_before": self.level_before,
            "level_after": self.level_after,
            "question_count": len(self.question_ids) if self.question_ids else 0
        }

    def __repr__(self):
        return f"<QuizSession id={self.id} user={self.user_id} comp={self.competency_id} score={self.score_pct}>"


class GapSnapshot(db.Model):
    """Snapshot of learner competency levels and role readiness over time."""
    __tablename__ = "gap_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    readiness_pct = db.Column(db.Float, nullable=False)
    taken_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    competency_levels = db.Column(db.JSON, nullable=False)  # Map of comp_id -> current level

    # Relationships
    user = db.relationship("User", backref="gap_snapshots")
    role = db.relationship("Role", backref="gap_snapshots")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "role_name": self.role.name if self.role else None,
            "readiness_pct": self.readiness_pct,
            "taken_at": self.taken_at.isoformat() if self.taken_at else None,
            "competency_levels": self.competency_levels
        }

    def __repr__(self):
        return f"<GapSnapshot user={self.user_id} role={self.role_id} readiness={self.readiness_pct}%>"


class QuizAttempt(db.Model):
    """User response to an assessment question."""
    __tablename__ = "quiz_attempts"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("quiz_sessions.id", ondelete="CASCADE"), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    chosen_index = db.Column(db.Integer, nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    session = db.relationship("QuizSession", back_populates="attempts")
    user = db.relationship("User", back_populates="quiz_attempts")
    question = db.relationship("Question", back_populates="quiz_attempts")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "question_id": self.question_id,
            "chosen_index": self.chosen_index,
            "is_correct": self.is_correct,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

    def __repr__(self):
        return f"<QuizAttempt user_id={self.user_id} question_id={self.question_id} is_correct={self.is_correct}>"
