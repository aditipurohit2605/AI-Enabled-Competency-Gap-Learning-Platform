import sys
from pathlib import Path

# Add project root to sys.path so backend imports work properly
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.competency import Role, Competency, RoleCompetency, Prerequisite
from backend.app.models.learning import Course


COMPETENCIES_DATA = [
    {
        "name": "Statistics Fundamentals",
        "description": "Probability distributions, hypothesis testing, confidence intervals, and descriptive metrics."
    },
    {
        "name": "Survey Design",
        "description": "Questionnaire structuring, pilot testing, response bias mitigation, and enumerator guidelines."
    },
    {
        "name": "Sampling Methods",
        "description": "Stratified, cluster, multi-stage sampling techniques and sample size determination."
    },
    {
        "name": "Data Cleaning",
        "description": "Outlier detection, imputation of missing entries, anomaly detection, and schema validation."
    },
    {
        "name": "SQL",
        "description": "Relational queries, aggregations, window functions, and database schema navigation."
    },
    {
        "name": "Python for Data Analysis",
        "description": "Pandas, NumPy, scripting automated ETL pipelines, and reproducible data workflows."
    },
    {
        "name": "Data Visualization",
        "description": "Design principles, Matplotlib, Seaborn, interactive dashboards, and executive reporting."
    },
    {
        "name": "Regression and Forecasting",
        "description": "Linear/logistic regression, time series analysis, ARIMA, and macroeconomic trend forecasting."
    },
    {
        "name": "National Accounts Basics",
        "description": "GDP calculation methodologies, GVA, supply-use tables, and national statistical frameworks."
    },
    {
        "name": "Report Writing",
        "description": "Statistical summaries, policy brief drafting, data storytelling, and stakeholder documentation."
    },
    {
        "name": "Data Governance and Privacy",
        "description": "Data ethics, anonymization protocols, compliance, and confidential data storage policies."
    },
    {
        "name": "Machine Learning Basics",
        "description": "Supervised/unsupervised algorithms, scikit-learn pipelines, evaluation metrics, and feature selection."
    }
]

# (competency_name, requires_competency_name)
PREREQUISITES_DATA = [
    ("Sampling Methods", "Statistics Fundamentals"),
    ("Sampling Methods", "Survey Design"),
    ("Regression and Forecasting", "Statistics Fundamentals"),
    ("Data Cleaning", "SQL"),
    ("Regression and Forecasting", "Data Cleaning"),
    ("Machine Learning Basics", "Python for Data Analysis"),
    ("Machine Learning Basics", "Statistics Fundamentals"),
    ("Data Visualization", "Python for Data Analysis"),
]

# Required levels 1 to 5 per role across the 12 competencies
ROLES_DATA = {
    "Statistical Assistant": {
        "description": "Conducts survey data collection, basic validation, entry, and preliminary tabulations.",
        "levels": {
            "Statistics Fundamentals": 2,
            "Survey Design": 2,
            "Sampling Methods": 2,
            "Data Cleaning": 3,
            "SQL": 2,
            "Python for Data Analysis": 1,
            "Data Visualization": 2,
            "Regression and Forecasting": 1,
            "National Accounts Basics": 1,
            "Report Writing": 2,
            "Data Governance and Privacy": 2,
            "Machine Learning Basics": 1
        }
    },
    "Statistical Officer": {
        "description": "Supervises statistical surveys, computes official indices, and oversees quality assurance.",
        "levels": {
            "Statistics Fundamentals": 4,
            "Survey Design": 4,
            "Sampling Methods": 4,
            "Data Cleaning": 4,
            "SQL": 3,
            "Python for Data Analysis": 2,
            "Data Visualization": 3,
            "Regression and Forecasting": 3,
            "National Accounts Basics": 3,
            "Report Writing": 4,
            "Data Governance and Privacy": 4,
            "Machine Learning Basics": 2
        }
    },
    "Data Analyst": {
        "description": "Builds statistical pipelines, analyzes trends, creates dashboards, and develops predictive models.",
        "levels": {
            "Statistics Fundamentals": 3,
            "Survey Design": 2,
            "Sampling Methods": 3,
            "Data Cleaning": 5,
            "SQL": 4,
            "Python for Data Analysis": 4,
            "Data Visualization": 4,
            "Regression and Forecasting": 4,
            "National Accounts Basics": 2,
            "Report Writing": 3,
            "Data Governance and Privacy": 3,
            "Machine Learning Basics": 3
        }
    },
    "Senior Statistical Officer": {
        "description": "Leads national statistical studies, oversees econometric forecasting, and advises on policy metrics.",
        "levels": {
            "Statistics Fundamentals": 5,
            "Survey Design": 5,
            "Sampling Methods": 5,
            "Data Cleaning": 4,
            "SQL": 4,
            "Python for Data Analysis": 3,
            "Data Visualization": 4,
            "Regression and Forecasting": 5,
            "National Accounts Basics": 5,
            "Report Writing": 5,
            "Data Governance and Privacy": 5,
            "Machine Learning Basics": 3
        }
    }
}

USERS_DATA = [
    {
        "name": "System Administrator",
        "email": "admin@example.com",
        "password": "admin123",
        "role": "admin"
    },
    {
        "name": "Statistical Trainer",
        "email": "trainer@example.com",
        "password": "trainer123",
        "role": "trainer"
    },
    {
        "name": "Aarav Sharma",
        "email": "learner1@example.com",
        "password": "learner123",
        "role": "learner"
    },
    {
        "name": "Priya Patel",
        "email": "learner2@example.com",
        "password": "learner123",
        "role": "learner"
    },
    {
        "name": "Rohan Verma",
        "email": "learner3@example.com",
        "password": "learner123",
        "role": "learner"
    }
]


def seed_database(app=None):
    """
    Idempotent seed function to populate competencies, prerequisites, roles,
    role-competencies, and test users.
    """
    if app is None:
        app = create_app()

    with app.app_context():
        # Ensure schema tables exist
        db.create_all()

        # 1. Seed Competencies
        comp_map = {}
        for comp_data in COMPETENCIES_DATA:
            comp = Competency.query.filter_by(name=comp_data["name"]).first()
            if not comp:
                comp = Competency(name=comp_data["name"], description=comp_data["description"])
                db.session.add(comp)
                db.session.flush()
            else:
                comp.description = comp_data["description"]
            comp_map[comp.name] = comp

        db.session.commit()

        # 2. Seed Prerequisites
        for comp_name, req_name in PREREQUISITES_DATA:
            comp = comp_map.get(comp_name)
            req = comp_map.get(req_name)
            if comp and req:
                existing = Prerequisite.query.filter_by(
                    competency_id=comp.id,
                    requires_competency_id=req.id
                ).first()
                if not existing:
                    prereq = Prerequisite(
                        competency_id=comp.id,
                        requires_competency_id=req.id,
                        validate_cycle=True
                    )
                    db.session.add(prereq)

        db.session.commit()

        # 3. Seed Roles & Role Competencies
        for role_name, role_info in ROLES_DATA.items():
            role = Role.query.filter_by(name=role_name).first()
            if not role:
                role = Role(name=role_name, description=role_info["description"])
                db.session.add(role)
                db.session.flush()
            else:
                role.description = role_info["description"]

            # Map required levels for each competency
            for comp_name, level in role_info["levels"].items():
                comp = comp_map.get(comp_name)
                if comp:
                    rc = RoleCompetency.query.filter_by(role_id=role.id, competency_id=comp.id).first()
                    if not rc:
                        rc = RoleCompetency(role_id=role.id, competency_id=comp.id, required_level=level)
                        db.session.add(rc)
                    else:
                        rc.required_level = level

        # 4. Seed Courses from mock catalogue
        data_courses_path = Path(__file__).resolve().parent / "data" / "courses.json"
        courses_seeded = 0
        if data_courses_path.exists():
            import json
            courses_list = json.loads(data_courses_path.read_text(encoding="utf-8"))
            for c_data in courses_list:
                comp = comp_map.get(c_data["competency"])
                if not comp:
                    continue
                course = Course.query.filter_by(title=c_data["title"]).first()
                if not course:
                    course = Course(
                        title=c_data["title"],
                        description=c_data.get("description", ""),
                        competency_id=comp.id,
                        level=int(c_data["level"]),
                        duration_hours=float(c_data.get("duration_hours", 5.0)),
                        provider=c_data.get("provider", "iGOT Karmayogi"),
                        url=c_data.get("url")
                    )
                    db.session.add(course)
                else:
                    course.description = c_data.get("description", "")
                    course.competency_id = comp.id
                    course.level = int(c_data["level"])
                    course.duration_hours = float(c_data.get("duration_hours", 5.0))
                    course.provider = c_data.get("provider", "iGOT Karmayogi")
                    course.url = c_data.get("url")
                courses_seeded += 1

            db.session.commit()

        # 5. Seed Users
        for user_data in USERS_DATA:
            user = User.query.filter_by(email=user_data["email"]).first()
            if not user:
                user = User(
                    name=user_data["name"],
                    email=user_data["email"],
                    password=user_data["password"],
                    role=user_data["role"]
                )
                db.session.add(user)
            else:
                user.name = user_data["name"]
                user.role = user_data["role"]
                user.set_password(user_data["password"])

        db.session.commit()

        return {
            "competencies_count": len(comp_map),
            "roles_count": len(ROLES_DATA),
            "users_count": len(USERS_DATA),
            "prerequisites_count": len(PREREQUISITES_DATA),
            "courses_count": courses_seeded
        }


def print_credentials():
    """Print the formatted list of test user credentials."""
    print("=" * 80)
    print("       AI-Enabled Competency Gap Platform - Test User Credentials")
    print("=" * 80)
    print(f"{'Role':<10} {'Email':<25} {'Password':<15} {'Name':<25}")
    print("-" * 80)
    for u in USERS_DATA:
        print(f"{u['role']:<10} {u['email']:<25} {u['password']:<15} {u['name']:<25}")
    print("=" * 80)


if __name__ == "__main__":
    print("Seeding database...")
    counts = seed_database()
    print("Seeding complete!")
    print(f"Created/Verified {counts['competencies_count']} competencies, {counts['roles_count']} roles, "
          f"{counts['prerequisites_count']} prerequisites, {counts['users_count']} users.\n")
    print_credentials()
