from backend.app.extensions import db


class Role(db.Model):
    """Job role within an organization (e.g., Frontend Developer, Data Engineer)."""
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)

    # Relationships
    role_competencies = db.relationship("RoleCompetency", back_populates="role", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description
        }

    def __repr__(self):
        return f"<Role {self.name}>"


class Competency(db.Model):
    """Competency/skill domain (e.g., Python Programming, System Design)."""
    __tablename__ = "competencies"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)

    # Relationships
    role_competencies = db.relationship("RoleCompetency", back_populates="competency", cascade="all, delete-orphan")
    user_skills = db.relationship("UserSkill", back_populates="competency", cascade="all, delete-orphan")
    courses = db.relationship("Course", back_populates="competency", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description
        }

    def __repr__(self):
        return f"<Competency {self.name}>"


class RoleCompetency(db.Model):
    """Mapping between a job role and its required competency with expected proficiency level (1-5)."""
    __tablename__ = "role_competencies"

    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    competency_id = db.Column(db.Integer, db.ForeignKey("competencies.id", ondelete="CASCADE"), nullable=False)
    required_level = db.Column(db.Integer, nullable=False)  # 1 to 5

    # Relationships
    role = db.relationship("Role", back_populates="role_competencies")
    competency = db.relationship("Competency", back_populates="role_competencies")

    __table_args__ = (
        db.UniqueConstraint("role_id", "competency_id", name="uq_role_competency"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "role_id": self.role_id,
            "competency_id": self.competency_id,
            "required_level": self.required_level,
            "competency_name": self.competency.name if self.competency else None
        }

    def __repr__(self):
        return f"<RoleCompetency role_id={self.role_id} competency_id={self.competency_id} level={self.required_level}>"


class UserSkill(db.Model):
    """Current competency level and evidence for a specific user."""
    __tablename__ = "user_skills"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    competency_id = db.Column(db.Integer, db.ForeignKey("competencies.id", ondelete="CASCADE"), nullable=False)
    level = db.Column(db.Integer, nullable=False)  # Current level (1-5)
    evidence = db.Column(db.Text, nullable=True)  # Quiz score, certificate, trainer evaluation

    # Relationships
    user = db.relationship("User", back_populates="skills")
    competency = db.relationship("Competency", back_populates="user_skills")

    __table_args__ = (
        db.UniqueConstraint("user_id", "competency_id", name="uq_user_competency"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "competency_id": self.competency_id,
            "level": self.level,
            "evidence": self.evidence,
            "competency_name": self.competency.name if self.competency else None
        }

    def __repr__(self):
        return f"<UserSkill user_id={self.user_id} competency_id={self.competency_id} level={self.level}>"
