from werkzeug.security import generate_password_hash, check_password_hash
from backend.app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    VALID_ROLES = {"learner", "trainer", "admin"}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False, default="learner")
    password_hash = db.Column(db.String(255), nullable=False)

    # Relationships
    skills = db.relationship("UserSkill", back_populates="user", cascade="all, delete-orphan")
    documents = db.relationship("Document", back_populates="uploader", cascade="all, delete-orphan")
    quiz_attempts = db.relationship("QuizAttempt", back_populates="user", cascade="all, delete-orphan")

    def __init__(self, name, email, password=None, role="learner"):
        self.name = name.strip()
        self.email = email.strip().lower()
        if role not in self.VALID_ROLES:
            raise ValueError(f"Invalid role '{role}'. Allowed roles are: {', '.join(sorted(self.VALID_ROLES))}")
        self.role = role
        if password:
            self.set_password(password)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role
        }

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"
