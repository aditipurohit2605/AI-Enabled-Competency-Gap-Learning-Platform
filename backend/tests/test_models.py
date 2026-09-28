import pytest
from datetime import datetime, timezone
from backend.app.extensions import db
from backend.app.models import (
    User,
    Role,
    Competency,
    RoleCompetency,
    UserSkill,
    Course,
    Document,
    Question,
    QuizAttempt
)


def test_user_model(app):
    """Test User creation, password hashing, and validation."""
    with app.app_context():
        user = User(name="Test User", email="user@test.com", password="mypassword", role="learner")
        db.session.add(user)
        db.session.commit()

        assert user.id is not None
        assert user.check_password("mypassword") is True
        assert user.check_password("wrongpassword") is False
        assert user.role == "learner"
        assert user.to_dict()["email"] == "user@test.com"

        # Invalid role should raise ValueError
        with pytest.raises(ValueError):
            User(name="Invalid", email="invalid@test.com", password="password", role="guest")


def test_role_and_competency_models(app):
    """Test Role, Competency, and RoleCompetency models."""
    with app.app_context():
        role = Role(name="Backend Engineer", description="Builds server-side architectures")
        comp = Competency(name="Python", description="Python programming language")
        db.session.add_all([role, comp])
        db.session.commit()

        assert role.id is not None
        assert comp.id is not None

        role_comp = RoleCompetency(role_id=role.id, competency_id=comp.id, required_level=4)
        db.session.add(role_comp)
        db.session.commit()

        assert role_comp.id is not None
        assert role_comp.required_level == 4
        assert role_comp.role.name == "Backend Engineer"
        assert role_comp.competency.name == "Python"
        assert role_comp.to_dict()["required_level"] == 4


def test_user_skill_model(app):
    """Test UserSkill model linking user, competency, level, and evidence."""
    with app.app_context():
        user = User(name="Skill User", email="skill@test.com", password="password123")
        comp = Competency(name="SQL", description="Relational databases")
        db.session.add_all([user, comp])
        db.session.commit()

        user_skill = UserSkill(
            user_id=user.id,
            competency_id=comp.id,
            level=3,
            evidence="Passed SQL certification quiz with 90%"
        )
        db.session.add(user_skill)
        db.session.commit()

        assert user_skill.id is not None
        assert user_skill.level == 3
        assert "90%" in user_skill.evidence
        assert user_skill.user.email == "skill@test.com"
        assert user_skill.competency.name == "SQL"


def test_course_model(app):
    """Test Course model linking title, description, competency_id, level, and url."""
    with app.app_context():
        comp = Competency(name="Docker", description="Containerization basics")
        db.session.add(comp)
        db.session.commit()

        course = Course(
            title="Docker for Beginners",
            description="Introduction to containers and Docker compose",
            competency_id=comp.id,
            level=1,
            url="https://learning.example.com/docker-101"
        )
        db.session.add(course)
        db.session.commit()

        assert course.id is not None
        assert course.level == 1
        assert course.competency.name == "Docker"
        assert course.to_dict()["title"] == "Docker for Beginners"


def test_document_question_and_quiz_attempt_models(app):
    """Test Document, Question (options JSON, status), and QuizAttempt models."""
    with app.app_context():
        trainer = User(name="Trainer Tim", email="tim@test.com", password="password123", role="trainer")
        learner = User(name="Learner Leo", email="leo@test.com", password="password123", role="learner")
        db.session.add_all([trainer, learner])
        db.session.commit()

        # Document
        doc = Document(
            title="Flask Security Best Practices",
            filename="flask_security.pdf",
            uploaded_by=trainer.id
        )
        db.session.add(doc)
        db.session.commit()

        assert doc.id is not None
        assert doc.uploader.name == "Trainer Tim"

        # Question with JSON options
        question = Question(
            document_id=doc.id,
            text="Which HTTP header protects against clickjacking?",
            options=["X-Frame-Options", "X-Content-Type-Options", "Authorization", "Accept"],
            correct_index=0,
            explanation="X-Frame-Options prevents clickjacking by restricting frame embedding.",
            source_passage="Use X-Frame-Options: DENY or SAMEORIGIN.",
            difficulty="medium",
            status="approved"
        )
        db.session.add(question)
        db.session.commit()

        assert question.id is not None
        assert question.options == ["X-Frame-Options", "X-Content-Type-Options", "Authorization", "Accept"]
        assert question.status == "approved"
        assert question.document.title == "Flask Security Best Practices"

        # Question with invalid status should raise ValueError
        with pytest.raises(ValueError):
            Question(
                text="Invalid question?",
                options=["A", "B"],
                correct_index=0,
                status="published"  # invalid status
            )

        # QuizAttempt
        attempt = QuizAttempt(
            user_id=learner.id,
            question_id=question.id,
            chosen_index=0,
            is_correct=True,
            timestamp=datetime.now(timezone.utc)
        )
        db.session.add(attempt)
        db.session.commit()

        assert attempt.id is not None
        assert attempt.is_correct is True
        assert attempt.user.email == "leo@test.com"
        assert attempt.question.text == "Which HTTP header protects against clickjacking?"
