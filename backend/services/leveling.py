from datetime import datetime, timezone
from typing import Any
from backend.app.extensions import db
from backend.app.models.assessment import QuizSession, QuizAttempt, Question, GapSnapshot
from backend.app.models.competency import UserSkill
from backend.services.gap import analyze_role_gap

DIFFICULTY_WEIGHTS = {
    "easy": 1,
    "medium": 2,
    "hard": 3
}


def calculate_quiz_score_and_weights(
    questions: list[Question],
    answers: dict[int, int]
) -> dict[str, Any]:
    """
    Compute weighted and simple score percentages from submitted answers.
    answers: {question_id: chosen_index}
    """
    total_weight = 0
    correct_weight = 0
    correct_count = 0
    hard_correct_count = 0
    results = []

    for q in questions:
        diff = (q.difficulty or "medium").lower()
        weight = DIFFICULTY_WEIGHTS.get(diff, 2)
        total_weight += weight

        chosen = answers.get(q.id)
        if chosen is None:
            # Also try string key in case JSON keys are strings
            chosen = answers.get(str(q.id))

        if chosen is not None:
            try:
                chosen = int(chosen)
            except (ValueError, TypeError):
                chosen = -1
        else:
            chosen = -1  # Unanswered counts as wrong

        is_correct = (chosen == q.correct_index)
        if is_correct:
            correct_count += 1
            correct_weight += weight
            if diff == "hard":
                hard_correct_count += 1

        results.append({
            "question_id": q.id,
            "text": q.text,
            "options": q.options,
            "chosen_index": chosen,
            "correct_index": q.correct_index,
            "is_correct": is_correct,
            "explanation": q.explanation,
            "source_passage": q.source_passage,
            "difficulty": diff,
            "weight": weight
        })

    total_q = len(questions)
    weighted_score_pct = (correct_weight / total_weight * 100.0) if total_weight > 0 else 0.0
    simple_score_pct = (correct_count / total_q * 100.0) if total_q > 0 else 0.0

    return {
        "total_questions": total_q,
        "correct_count": correct_count,
        "hard_correct_count": hard_correct_count,
        "total_weight": total_weight,
        "correct_weight": correct_weight,
        "weighted_score_pct": round(weighted_score_pct, 2),
        "simple_score_pct": round(simple_score_pct, 2),
        "question_results": results
    }


def determine_quiz_level(
    weighted_score_pct: float,
    total_questions: int,
    hard_correct_count: int
) -> int:
    """
    Determine raw quiz level (1-5) from weighted score:
      - below 40% -> Level 1
      - 40% to 59.99% -> Level 2
      - 60% to 74.99% -> Level 3
      - 75% to 89.99% -> Level 4
      - 90% or above -> Level 5 (requires >= 5 questions and >= 1 hard question correct; else Level 4)
    """
    if weighted_score_pct < 40.0:
        return 1
    elif weighted_score_pct < 60.0:
        return 2
    elif weighted_score_pct < 75.0:
        return 3
    elif weighted_score_pct < 90.0:
        return 4
    else:  # >= 90.0
        if total_questions >= 5 and hard_correct_count >= 1:
            return 5
        return 4


def blend_competency_level(
    quiz_level: int,
    previous_level: float | None,
    total_questions: int
) -> float:
    """
    Blend quiz level with previous level:
      - Sessions with >= 5 questions: 70% quiz, 30% previous.
      - Sessions with < 5 questions: 40% quiz, 60% previous.
      - Rounded to nearest integer level.
      - Cap: never drop more than 1 level in a single session.
    """
    if previous_level is None or previous_level <= 0:
        return float(quiz_level)

    if total_questions >= 5:
        w_quiz = 0.70
        w_prev = 0.30
    else:
        w_quiz = 0.40
        w_prev = 0.60

    blended = (quiz_level * w_quiz) + (previous_level * w_prev)
    new_level = float(round(blended))

    # Drop cap: cannot drop more than 1 level below previous_level
    if new_level < previous_level - 1.0:
        new_level = previous_level - 1.0

    return max(1.0, min(5.0, new_level))


def get_user_current_competency_level(user_id: int, competency_id: int) -> float | None:
    """Find current skill level for user and competency across all sources."""
    # Look for quiz source first
    quiz_skill = UserSkill.query.filter_by(
        user_id=user_id,
        competency_id=competency_id,
        source="quiz"
    ).first()
    if quiz_skill:
        return float(quiz_skill.level)

    # Fall back to other sources
    skills = UserSkill.query.filter_by(
        user_id=user_id,
        competency_id=competency_id
    ).all()
    if not skills:
        return None

    levels = [float(s.level) for s in skills]
    return sum(levels) / len(levels)


def save_quiz_result_and_update_level(
    session: QuizSession,
    answers: dict[int, int],
    role_id: int | None = None
) -> dict[str, Any]:
    """
    Process quiz session submission:
      - Grade answers & save QuizAttempt rows
      - Calculate score & apply leveling rules
      - Update UserSkill with source='quiz'
      - Record GapSnapshot if role_id is provided
      - Update and close QuizSession
    """
    # Load questions in session
    questions = Question.query.filter(Question.id.in_(session.question_ids)).all()
    # Preserve order
    q_map = {q.id: q for q in questions}
    ordered_questions = [q_map[qid] for qid in session.question_ids if qid in q_map]

    scoring = calculate_quiz_score_and_weights(ordered_questions, answers)

    # Save attempts
    for res in scoring["question_results"]:
        attempt = QuizAttempt(
            session_id=session.id,
            user_id=session.user_id,
            question_id=res["question_id"],
            chosen_index=res["chosen_index"],
            is_correct=res["is_correct"]
        )
        db.session.add(attempt)

    # Leveling
    quiz_level = determine_quiz_level(
        weighted_score_pct=scoring["weighted_score_pct"],
        total_questions=scoring["total_questions"],
        hard_correct_count=scoring["hard_correct_count"]
    )

    prev_level = session.level_before
    if prev_level is None:
        prev_level = get_user_current_competency_level(session.user_id, session.competency_id)

    new_level = blend_competency_level(
        quiz_level=quiz_level,
        previous_level=prev_level,
        total_questions=scoring["total_questions"]
    )

    # Update UserSkill with source='quiz'
    now = datetime.now(timezone.utc)
    evidence_text = (
        f"Quiz on {now.strftime('%Y-%m-%d')}: "
        f"{scoring['correct_count']}/{scoring['total_questions']} correct ({scoring['weighted_score_pct']}%)"
    )

    user_skill = UserSkill.query.filter_by(
        user_id=session.user_id,
        competency_id=session.competency_id,
        source="quiz"
    ).first()

    if user_skill:
        user_skill.level = new_level
        user_skill.evidence = evidence_text
    else:
        user_skill = UserSkill(
            user_id=session.user_id,
            competency_id=session.competency_id,
            level=new_level,
            evidence=evidence_text,
            source="quiz"
        )
        db.session.add(user_skill)

    # Update session record
    session.submitted_at = now
    session.score_pct = scoring["weighted_score_pct"]
    session.level_before = prev_level
    session.level_after = new_level

    # Record GapSnapshot if role_id provided
    snapshot_data = None
    if role_id:
        snapshot = take_gap_snapshot(session.user_id, role_id)
        if snapshot:
            snapshot_data = snapshot.to_dict()

    db.session.commit()

    return {
        "session_id": session.id,
        "competency_id": session.competency_id,
        "score_pct": scoring["weighted_score_pct"],
        "simple_score_pct": scoring["simple_score_pct"],
        "correct_count": scoring["correct_count"],
        "total_questions": scoring["total_questions"],
        "quiz_level": quiz_level,
        "level_before": prev_level,
        "level_after": new_level,
        "new_level": new_level,
        "question_results": scoring["question_results"],
        "gap_snapshot": snapshot_data
    }


def take_gap_snapshot(user_id: int, role_id: int) -> GapSnapshot | None:
    """Compute current gap analysis for user on role and record a GapSnapshot."""
    analysis = analyze_role_gap(user_id, role_id)
    if not analysis:
        return None

    levels = {c["competency_id"]: c["current_level"] for c in analysis.get("competencies", [])}
    snapshot = GapSnapshot(
        user_id=user_id,
        role_id=role_id,
        readiness_pct=analysis.get("readiness_percentage", 0.0),
        competency_levels=levels
    )
    db.session.add(snapshot)
    return snapshot
