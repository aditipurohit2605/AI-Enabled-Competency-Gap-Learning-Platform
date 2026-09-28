from backend.app.extensions import db


class Course(db.Model):
    """Recommended or available learning resource associated with a competency and level."""
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    competency_id = db.Column(db.Integer, db.ForeignKey("competencies.id", ondelete="CASCADE"), nullable=False)
    level = db.Column(db.Integer, nullable=False)  # Target level (1-5)
    url = db.Column(db.String(500), nullable=True)

    # Relationship
    competency = db.relationship("Competency", back_populates="courses")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "competency_id": self.competency_id,
            "level": self.level,
            "url": self.url,
            "competency_name": self.competency.name if self.competency else None
        }

    def __repr__(self):
        return f"<Course {self.title} (Level {self.level})>"
