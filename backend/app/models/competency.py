import networkx as nx
from backend.app.extensions import db


class CycleDetectedError(ValueError):
    """Raised when adding a prerequisite creates a circular dependency."""
    pass


class SelfReferenceError(ValueError):
    """Raised when a competency lists itself as a prerequisite."""
    pass


def check_for_prerequisite_cycle(competency_id, requires_competency_id):
    """
    Check if adding the dependency (requires_competency_id -> competency_id)
    would create a cycle in the prerequisite graph.
    Raises SelfReferenceError if competency_id == requires_competency_id.
    Raises CycleDetectedError if a cycle is created.
    """
    if competency_id == requires_competency_id:
        raise SelfReferenceError("A competency cannot require itself as a prerequisite.")

    # Load existing prerequisite edges from database
    existing_pairs = db.session.query(
        Prerequisite.requires_competency_id,
        Prerequisite.competency_id
    ).all()

    G = nx.DiGraph()
    for req_id, comp_id in existing_pairs:
        G.add_edge(req_id, comp_id)

    # Add the proposed edge: requires_competency_id must precede competency_id
    G.add_edge(requires_competency_id, competency_id)

    if not nx.is_directed_acyclic_graph(G):
        try:
            cycles = list(nx.simple_cycles(G))
            cycle_desc = " -> ".join(map(str, cycles[0])) if cycles else ""
            msg = f"Adding this prerequisite creates a circular dependency: {cycle_desc}"
        except Exception:
            msg = "Adding this prerequisite creates a circular dependency."
        raise CycleDetectedError(msg)


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
    prerequisites = db.relationship(
        "Prerequisite",
        foreign_keys="[Prerequisite.competency_id]",
        back_populates="competency",
        cascade="all, delete-orphan"
    )
    required_by = db.relationship(
        "Prerequisite",
        foreign_keys="[Prerequisite.requires_competency_id]",
        back_populates="requires_competency",
        cascade="all, delete-orphan"
    )

    def to_dict(self, include_prerequisites=False):
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description
        }
        if include_prerequisites:
            data["prerequisites"] = [
                {
                    "id": p.requires_competency.id,
                    "name": p.requires_competency.name
                }
                for p in self.prerequisites if p.requires_competency
            ]
        return data

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
    level = db.Column(db.Float, nullable=False)  # Current level (1.0 to 5.0)
    evidence = db.Column(db.Text, nullable=True)  # Matched sentences, reasons, or test notes
    source = db.Column(db.String(50), nullable=False, default="profile")  # 'profile' | 'self' | 'quiz'

    # Relationships
    user = db.relationship("User", back_populates="skills")
    competency = db.relationship("Competency", back_populates="user_skills")

    __table_args__ = (
        db.UniqueConstraint("user_id", "competency_id", "source", name="uq_user_competency_source"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "competency_id": self.competency_id,
            "level": self.level,
            "evidence": self.evidence,
            "source": self.source,
            "competency_name": self.competency.name if self.competency else None
        }

    def __repr__(self):
        return f"<UserSkill user_id={self.user_id} competency_id={self.competency_id} level={self.level} source={self.source}>"


class Prerequisite(db.Model):
    """Prerequisite dependency: competency_id requires requires_competency_id to be acquired first."""
    __tablename__ = "prerequisites"

    id = db.Column(db.Integer, primary_key=True)
    competency_id = db.Column(db.Integer, db.ForeignKey("competencies.id", ondelete="CASCADE"), nullable=False)
    requires_competency_id = db.Column(db.Integer, db.ForeignKey("competencies.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    competency = db.relationship("Competency", foreign_keys=[competency_id], back_populates="prerequisites")
    requires_competency = db.relationship("Competency", foreign_keys=[requires_competency_id], back_populates="required_by")

    __table_args__ = (
        db.UniqueConstraint("competency_id", "requires_competency_id", name="uq_prerequisite"),
    )

    def __init__(self, competency_id, requires_competency_id, validate_cycle=True):
        self.competency_id = competency_id
        self.requires_competency_id = requires_competency_id
        if validate_cycle:
            check_for_prerequisite_cycle(competency_id, requires_competency_id)

    def to_dict(self):
        return {
            "id": self.id,
            "competency_id": self.competency_id,
            "requires_competency_id": self.requires_competency_id,
            "competency_name": self.competency.name if self.competency else None,
            "requires_competency_name": self.requires_competency.name if self.requires_competency else None
        }

    def __repr__(self):
        return f"<Prerequisite competency_id={self.competency_id} requires={self.requires_competency_id}>"
