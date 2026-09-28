import pytest
from backend.app import create_app
from backend.app.config import TestingConfig
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.utils.auth import generate_token


@pytest.fixture
def app():
    """Create and configure a clean testing app instance with an in-memory SQLite database."""
    test_app = create_app(config_object=TestingConfig)

    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client for HTTP requests."""
    return app.test_client()


@pytest.fixture
def learner_user(app):
    """Create a default learner user in the database."""
    with app.app_context():
        user = User(
            name="Alice Learner",
            email="alice@example.com",
            password="password123",
            role="learner"
        )
        db.session.add(user)
        db.session.commit()
        return user.to_dict()


@pytest.fixture
def trainer_user(app):
    """Create a trainer user in the database."""
    with app.app_context():
        user = User(
            name="Bob Trainer",
            email="bob@example.com",
            password="password123",
            role="trainer"
        )
        db.session.add(user)
        db.session.commit()
        return user.to_dict()


@pytest.fixture
def admin_user(app):
    """Create an admin user in the database."""
    with app.app_context():
        user = User(
            name="Carol Admin",
            email="carol@example.com",
            password="password123",
            role="admin"
        )
        db.session.add(user)
        db.session.commit()
        return user.to_dict()


@pytest.fixture
def learner_token(app, learner_user):
    """JWT token for the learner user."""
    with app.app_context():
        user = db.session.get(User, learner_user["id"])
        return generate_token(user)


@pytest.fixture
def trainer_token(app, trainer_user):
    """JWT token for the trainer user."""
    with app.app_context():
        user = db.session.get(User, trainer_user["id"])
        return generate_token(user)


@pytest.fixture
def admin_token(app, admin_user):
    """JWT token for the admin user."""
    with app.app_context():
        user = db.session.get(User, admin_user["id"])
        return generate_token(user)
