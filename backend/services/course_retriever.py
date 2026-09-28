import faiss
import numpy as np
from backend.app.extensions import db
from backend.app.models.learning import Course
from backend.app.models.competency import Competency
from backend.services.embedder import embed


class CourseRetriever:
    """
    FAISS-based semantic retriever for learning resources.
    Builds an IndexFlatIP over course title + description,
    filters by competency and level window, and ranks by similarity.
    """

    def __init__(self):
        self.index = None
        self.course_ids = []
        self.course_vectors = None
        self.course_data = {}
        self._is_indexed = False

    def build_index(self, courses: list[Course] | None = None):
        """Build or rebuild FAISS index over courses."""
        if courses is None:
            courses = Course.query.all()

        if not courses:
            self.index = None
            self.course_ids = []
            self.course_vectors = None
            self.course_data = {}
            self._is_indexed = True
            return

        self.course_ids = [c.id for c in courses]
        self.course_data = {c.id: c.to_dict() for c in courses}

        texts = [f"{c.title}: {c.description or ''}" for c in courses]
        embeddings = embed(texts)  # (N, D) float32 normalized vectors

        self.course_vectors = embeddings
        dim = embeddings.shape[1]

        # Inner Product on L2-normalized vectors represents Cosine Similarity
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings)
        self._is_indexed = True

    def find_courses(
        self,
        competency_id: int,
        target_level: float,
        current_level: float = 0.0,
        top_k: int = 3,
        exclude_course_ids: list[int] | set[int] | None = None
    ) -> list[dict]:
        """
        Find and rank courses for a competency:
          1. First filter by competency and level range (above current_level, up to target_level)
          2. Rank by similarity to query: '<competency name> level <target>'
          3. Return top_k matching courses
        """
        if not self._is_indexed or self.index is None:
            self.build_index()

        exclude_set = set(exclude_course_ids or [])

        # Fetch competency details
        comp = db.session.get(Competency, competency_id)
        comp_name = comp.name if comp else f"Competency {competency_id}"

        # Fetch all courses for this competency from DB or cache
        all_comp_courses = Course.query.filter_by(competency_id=competency_id).all()
        if not all_comp_courses:
            return []

        # Filter out excluded (e.g. completed) courses
        available_courses = [c for c in all_comp_courses if c.id not in exclude_set]
        if not available_courses:
            return []

        # Level range filtering: courses above current_level up to target_level
        # e.g., current = 1, target = 3 -> courses with level 2 or 3
        candidates = [
            c for c in available_courses
            if current_level < c.level <= target_level
        ]

        # If strict range yielded no courses (e.g. coarse discrete levels), fallback gracefully
        if not candidates and target_level > current_level:
            # Fallback 1: courses up to target_level
            candidates = [c for c in available_courses if c.level <= target_level]
            # Fallback 2: courses at least closest to target_level
            if not candidates:
                candidates = [c for c in available_courses if c.level == round(target_level)]
            if not candidates:
                candidates = available_courses

        if not candidates:
            return []

        # If we have candidates, rank them by semantic query similarity
        target_int = int(round(target_level))
        query_text = f"{comp_name} level {target_int}"
        query_vec = embed([query_text])  # (1, D)

        candidate_scored = []
        for c in candidates:
            if c.id in self.course_ids and self.course_vectors is not None:
                idx = self.course_ids.index(c.id)
                vec = self.course_vectors[idx]
                sim = float(np.dot(query_vec[0], vec))
            else:
                sim = 0.5

            course_dict = c.to_dict()
            course_dict["similarity"] = round(sim, 3)
            candidate_scored.append(course_dict)

        # Rank by similarity descending
        candidate_scored.sort(key=lambda x: x["similarity"], reverse=True)

        # Select top_k
        selected = candidate_scored[:top_k]

        # Order selected courses easiest to hardest (ascending by level, then duration)
        selected.sort(key=lambda x: (x["level"], x["duration_hours"]))

        return selected


# Singleton instance
_COURSE_RETRIEVER: CourseRetriever | None = None


def get_course_retriever() -> CourseRetriever:
    """Get or initialize the course retriever singleton."""
    global _COURSE_RETRIEVER
    if _COURSE_RETRIEVER is None:
        _COURSE_RETRIEVER = CourseRetriever()
    return _COURSE_RETRIEVER


def find_courses(
    competency_id: int,
    target_level: float,
    current_level: float = 0.0,
    top_k: int = 3,
    exclude_course_ids: list[int] | set[int] | None = None
) -> list[dict]:
    """Helper function to find courses via the singleton retriever."""
    return get_course_retriever().find_courses(
        competency_id=competency_id,
        target_level=target_level,
        current_level=current_level,
        top_k=top_k,
        exclude_course_ids=exclude_course_ids
    )


def rebuild_course_index():
    """Trigger index rebuild (e.g. after courses are seeded or modified)."""
    get_course_retriever().build_index()
