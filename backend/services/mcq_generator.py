import difflib
import logging
import os
import re
from typing import Any
import numpy as np

from backend.app.extensions import db
from backend.app.models.assessment import Document, Question
from backend.services.chunker import load_document_index, search_document_chunks
from backend.services.embedder import embed
from backend.services.llm_client import get_llm_client

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """Normalize whitespace and lowercase for reliable substring/fuzzy checking."""
    return " ".join(text.lower().split())


def is_passage_in_chunk(passage: str, chunk_text: str, threshold: float = 0.80) -> bool:
    """
    Check if the source_passage actually appears in the chunk text.
    Allows for minor formatting/whitespace variations (fuzzy match).
    """
    if not passage or not chunk_text:
        return False

    norm_passage = normalize_text(passage)
    norm_chunk = normalize_text(chunk_text)

    # 1. Direct normalized substring check
    if norm_passage in norm_chunk:
        return True

    # 2. SequenceMatcher longest match ratio
    matcher = difflib.SequenceMatcher(None, norm_passage, norm_chunk)
    match = matcher.find_longest_match(0, len(norm_passage), 0, len(norm_chunk))
    if match.size >= int(len(norm_passage) * threshold):
        return True

    # 3. Overall ratio check on passage
    # Find best window in chunk of length len(norm_passage)
    pass_len = len(norm_passage)
    if len(norm_chunk) >= pass_len:
        best_ratio = 0.0
        step = max(1, pass_len // 4)
        for i in range(0, len(norm_chunk) - pass_len + 1, step):
            window = norm_chunk[i : i + pass_len]
            ratio = difflib.SequenceMatcher(None, norm_passage, window).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                if best_ratio >= threshold:
                    return True

    return False


def validate_option_lengths(options: list[str]) -> tuple[bool, str | None]:
    """
    Validate that options are balanced and lengths are not wildly disparate.
    Catches telltale distractors that give away answers.
    """
    lengths = [len(opt.strip()) for opt in options]
    min_len = min(lengths)
    max_len = max(lengths)

    if min_len == 0:
        return False, "Option list contains empty choice"

    # Only flag if there is a substantial absolute difference (> 25 chars)
    # AND relative difference exceeds 3.5x
    if (max_len - min_len) > 25 and (max_len > 3.5 * min_len):
        return False, f"Option lengths are wildly disparate (min {min_len} chars, max {max_len} chars)"

    return True, None


def validate_question_schema(q: dict[str, Any]) -> tuple[bool, str | None]:
    """
    Validate basic JSON schema requirements for an MCQ.
    """
    text = q.get("question")
    if not text or not isinstance(text, str) or len(text.strip()) < 5:
        return False, "Question text missing or too short"

    options = q.get("options")
    if not isinstance(options, list) or len(options) != 4:
        return False, f"Options must be a list of exactly 4 choices (got {len(options) if isinstance(options, list) else type(options)})"

    for opt in options:
        if not isinstance(opt, str) or not opt.strip():
            return False, "All options must be non-empty strings"

    # Distinct check
    lowered_options = [o.strip().lower() for o in options]
    if len(set(lowered_options)) != 4:
        return False, "All 4 options must be distinct"

    # Check for forbidden clichés
    forbidden_patterns = [
        r"\ball of the above\b",
        r"\bnone of the above\b",
        r"\bboth a and b\b",
        r"\bboth b and c\b"
    ]
    for opt in lowered_options:
        for pattern in forbidden_patterns:
            if re.search(pattern, opt):
                return False, f"Option contains forbidden phrase '{opt}'"

    correct_index = q.get("correct_index")
    if not isinstance(correct_index, int) or not (0 <= correct_index <= 3):
        return False, f"correct_index must be an integer between 0 and 3 (got {correct_index})"

    source_passage = q.get("source_passage")
    if not source_passage or not isinstance(source_passage, str) or len(source_passage.strip()) < 5:
        return False, "source_passage missing or too short"

    explanation = q.get("explanation")
    if not explanation or not isinstance(explanation, str):
        return False, "explanation missing"

    return True, None


def check_near_duplicates(
    candidate_vec: np.ndarray,
    existing_vecs: list[np.ndarray],
    threshold: float = 0.90
) -> tuple[bool, float]:
    """
    Check if candidate question embedding is too similar to any existing question embedding.
    """
    if not existing_vecs:
        return False, 0.0

    existing_matrix = np.array(existing_vecs)
    # Cosine similarity is dot product for unit-normalized vectors
    sims = np.dot(existing_matrix, candidate_vec)
    max_sim = float(np.max(sims))
    if max_sim >= threshold:
        return True, max_sim
    return False, max_sim


def verify_with_second_pass(
    llm_client,
    source_passage: str,
    question_text: str,
    options: list[str],
    expected_index: int
) -> tuple[bool, int, str]:
    """
    Optional verifier LLM pass:
    Sends ONLY the source_passage and question (no correct_index) to the LLM to independently solve it.
    Returns (matches, chosen_index, explanation).
    """
    options_text = "\n".join([f"{i}. {opt}" for i, opt in enumerate(options)])
    verify_prompt = f"""You are an objective assessment validator.
Read the following passage and answer the multiple-choice question using ONLY the facts directly stated in the passage.

[PASSAGE]
{source_passage}

[QUESTION]
{question_text}

[OPTIONS]
{options_text}

Respond in strict JSON with keys:
- "chosen_index": (integer 0, 1, 2, or 3)
- "rationale": "Brief rationale citing the passage"
"""
    try:
        result = llm_client.generate_json(verify_prompt)
        if isinstance(result, dict) and "chosen_index" in result:
            chosen = int(result["chosen_index"])
            matches = (chosen == expected_index)
            return matches, chosen, result.get("rationale", "")
    except Exception as e:
        logger.warning(f"Verifier pass encountered error: {e}")

    return False, -1, "Verifier evaluation failed or differed"


def generate_mcqs(
    document_id: int,
    num_questions: int = 5,
    difficulty: str = "medium",
    topic_focus: str | None = None,
    verify: bool | None = None
) -> dict[str, Any]:
    """
    Generate validated multiple choice questions from an uploaded document.
    Saves approved questions to the database with status='draft'.
    """
    document = db.session.get(Document, document_id)
    if not document:
        raise ValueError(f"Document with id {document_id} not found")

    num_questions = max(1, min(20, num_questions))
    difficulty = difficulty.lower()
    if difficulty not in ("easy", "medium", "hard", "mixed"):
        difficulty = "medium"

    # Load chunk data and FAISS index
    index, chunks = load_document_index(document_id)
    if not chunks:
        raise ValueError(f"No indexed text chunks found for document {document_id}")

    # Determine whether to verify
    if verify is None:
        verify = os.getenv("ENABLE_MCQ_VERIFIER", "false").lower() in ("true", "1", "yes")

    # Select candidate chunks
    selected_chunks = []
    if topic_focus and topic_focus.strip():
        search_results = search_document_chunks(document_id, topic_focus, top_k=min(len(chunks), num_questions * 2))
        selected_chunks = search_results if search_results else chunks
    else:
        # Sample chunks evenly spread across the document
        total_chunks = len(chunks)
        sample_count = min(total_chunks, max(num_questions, 3))
        indices = [int(i * (total_chunks - 1) / max(1, sample_count - 1)) for i in range(sample_count)]
        selected_chunks = [chunks[i] for i in sorted(set(indices))]

    # Load existing question embeddings for this document to avoid duplicates
    existing_db_questions = Question.query.filter_by(document_id=document_id).all()
    existing_texts = [q.text for q in existing_db_questions]
    existing_vecs = list(embed(existing_texts)) if existing_texts else []

    llm_client = get_llm_client()

    generated_total = 0
    rejections: list[dict[str, Any]] = []
    kept_questions: list[Question] = []
    accepted_vecs: list[np.ndarray] = list(existing_vecs)

    # Process chunks until target reached or chunks exhausted
    for chunk in selected_chunks:
        if len(kept_questions) >= num_questions:
            break

        chunk_text = chunk.get("text", "")
        if len(chunk_text.strip()) < 50:
            continue

        needed = min(2, num_questions - len(kept_questions))
        diff_instruction = f"difficulty: {difficulty}" if difficulty != "mixed" else "a mix of easy, medium, and hard difficulty"

        prompt = f"""You are an assessment author creating questions for official statistical personnel.
Based STRICTLY on the source text below, generate {needed} high-quality multiple choice question(s).

[SOURCE TEXT]
{chunk_text}

Rules:
1. Use ONLY facts directly stated in the source text. Do not invent or assume outside facts.
2. Provide exactly one clearly correct answer and 3 plausible distractors of similar length and grammatical structure.
3. Absolutely NO 'all of the above', 'none of the above', 'both A and B', or tricky wording.
4. 'source_passage' MUST be an exact verbatim sentence or short passage copied directly from the SOURCE TEXT that proves the correct answer.
5. Set {diff_instruction}.

Return a JSON object in this exact schema:
{{
  "questions": [
    {{
      "question": "Question text?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_index": 0,
      "explanation": "Clear explanation citing the passage",
      "source_passage": "Verbatim sentence copied from source text",
      "difficulty": "easy|medium|hard"
    }}
  ]
}}
"""
        try:
            response = llm_client.generate_json(prompt)
        except Exception as e:
            logger.error(f"Error calling LLM for chunk {chunk.get('chunk_id')}: {e}")
            continue

        candidate_list = []
        if isinstance(response, dict) and "questions" in response:
            candidate_list = response["questions"]
        elif isinstance(response, list):
            candidate_list = response

        for cand in candidate_list:
            if len(kept_questions) >= num_questions:
                break

            generated_total += 1
            q_text = cand.get("question", "")

            # 1. Schema check
            valid, err = validate_question_schema(cand)
            if not valid:
                rejections.append({"question": q_text, "reason": f"Schema validation: {err}"})
                continue

            # 2. Option lengths check
            valid_len, len_err = validate_option_lengths(cand["options"])
            if not valid_len:
                rejections.append({"question": q_text, "reason": f"Option balance: {len_err}"})
                continue

            # 3. Source passage check
            if not is_passage_in_chunk(cand["source_passage"], chunk_text):
                rejections.append({
                    "question": q_text,
                    "reason": f"Source passage '{cand['source_passage'][:60]}...' does not appear in source chunk"
                })
                continue

            # 4. Duplicate check via embedding cosine similarity
            cand_vec = embed([q_text])[0]
            is_dup, sim = check_near_duplicates(cand_vec, accepted_vecs, threshold=0.90)
            if is_dup:
                rejections.append({
                    "question": q_text,
                    "reason": f"Duplicate question detected (similarity {sim:.2f} >= 0.90)"
                })
                continue

            # 5. Optional verification pass
            if verify:
                matches, chosen, rationale = verify_with_second_pass(
                    llm_client=llm_client,
                    source_passage=cand["source_passage"],
                    question_text=q_text,
                    options=cand["options"],
                    expected_index=cand["correct_index"]
                )
                if not matches:
                    rejections.append({
                        "question": q_text,
                        "reason": f"Verifier disagreement: claimed index {cand['correct_index']} but verifier chose {chosen} ({rationale})"
                    })
                    continue

            # Question passed all checks!
            accepted_vecs.append(cand_vec)
            q_obj = Question(
                document_id=document_id,
                text=cand["question"],
                options=cand["options"],
                correct_index=cand["correct_index"],
                explanation=cand.get("explanation"),
                source_passage=cand.get("source_passage"),
                difficulty=cand.get("difficulty", difficulty if difficulty != "mixed" else "medium"),
                status="draft"
            )
            db.session.add(q_obj)
            kept_questions.append(q_obj)

    # Commit saved draft questions
    if kept_questions:
        db.session.commit()

    return {
        "generated": generated_total,
        "kept": len(kept_questions),
        "rejected": len(rejections),
        "rejections": rejections,
        "questions": [q.to_dict(include_correct=True) for q in kept_questions]
    }
