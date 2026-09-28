from datetime import datetime, timezone
from backend.app.extensions import db


class Course(db.Model):
    """Recommended or available learning resource associated with a competency and level."""
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    competency_id = db.Column(db.Integer, db.ForeignKey("competencies.id", ondelete="CASCADE"), nullable=False)
    level = db.Column(db.Integer, nullable=False)  # Target level (1-5)
    duration_hours = db.Column(db.Float, nullable=False, default=5.0)
    provider = db.Column(db.String(120), nullable=False, default="iGOT Karmayogi")
    url = db.Column(db.String(500), nullable=True)

    # Relationships
    competency = db.relationship("Competency", back_populates="courses")
    progress_records = db.relationship("UserCourseProgress", back_populates="course", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "competency_id": self.competency_id,
            "competency_name": self.competency.name if self.competency else None,
            "level": self.level,
            "duration_hours": self.duration_hours,
            "provider": self.provider,
            "url": self.url
        }

    def __repr__(self):
        return f"<Course {self.title} (Level {self.level})>"


class UserCourseProgress(db.Model):
    """Tracks learner progress on assigned or recommended courses."""
    __tablename__ = "user_course_progress"

    VALID_STATUSES = {"planned", "in_progress", "completed"}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="planned")  # planned | in_progress | completed
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    user = db.relationship("User", backref="course_progress")
    course = db.relationship("Course", back_populates="progress_records")

    __table_args__ = (
        db.UniqueConstraint("user_id", "course_id", name="uq_user_course_progress"),
    )

    def __init__(self, user_id, course_id, status="planned"):
        self.user_id = user_id
        self.course_id = course_id
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Allowed statuses: {', '.join(sorted(self.VALID_STATUSES))}")
        self.status = status

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "course_id": self.course_id,
            "course_title": self.course.title if self.course else None,
            "status": self.status,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<UserCourseProgress user_id={self.user_id} course_id={self.course_id} status={self.status}>"
