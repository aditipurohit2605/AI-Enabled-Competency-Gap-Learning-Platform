import re
import numpy as np
from backend.services.embedder import embed


def split_into_sentences(text: str) -> list[str]:
    """
    Split profile text into meaningful, clean sentence units.
    Handles line breaks, bullet points, and standard sentence punctuation.
    """
    if not text:
        return []

    raw_lines = text.split("\n")
    sentences = []
    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        # Split on sentence punctuation (. ! ?) followed by whitespace
        parts = re.split(r"(?<=[.!?])\s+", line)
        for part in parts:
            cleaned = part.strip()
            # Remove leading bullet symbols (e.g. •, -, *, 1.)
            cleaned = re.sub(r"^[•\-\*\d+\.]\s*", "", cleaned).strip()
            if len(cleaned) >= 8:
                sentences.append(cleaned)

    return sentences


def estimate_competency_level(evidence_sentences: list[str]) -> tuple[int, list[str]]:
    """
    Estimate proficiency level (1-4 only; level 5 reserved for assessments)
    based on transparent rules evaluated against the evidence sentences:
      - Base: 1 for a mention in the profile
      - +1 for years of experience mentioned
      - +1 for a concrete project or tool named
      - +1 for a certification or training mentioned
    Returns (level, list_of_reasons).
    """
    reasons = ["Base level 1 for verified mention in profile"]
    level = 1
    combined_text = " ".join(evidence_sentences)

    # 1. Check for years of experience
    exp_pattern = re.compile(
        r"(\b\d+\+?\s*(?:years?|yrs?)\b|\b(?:one|two|three|four|five|six|seven|eight|nine|ten)\s*(?:years?|yrs?)\b|"
        r"(?:experience of|worked for)\s+\d+\s*(?:years?|yrs?))",
        re.IGNORECASE
    )
    if exp_pattern.search(combined_text):
        level += 1
        reasons.append("Identified professional experience duration in years (+1)")

    # 2. Check for concrete project, methodology, or named technical tool
    tool_project_pattern = re.compile(
        r"\b(?:project|built|developed|implemented|pipeline|dashboard|system|application|"
        r"model|deployed|conducted|designed|using|used|tool|framework|library|software|"
        r"database|etl|git|docker|sql|python|r|tableau|power\s*bi|excel|spss|stata|"
        r"pandas|numpy|scikit-learn|matplotlib|seaborn|arima|postgre?s?|mysql)\b",
        re.IGNORECASE
    )
    if tool_project_pattern.search(combined_text):
        level += 1
        reasons.append("Identified concrete tools, software, or applied projects (+1)")

    # 3. Check for certification, course, or training
    cert_pattern = re.compile(
        r"\b(?:certified|certification|certificate|course|training|trained|degree|"
        r"diploma|credential|workshop|accreditation|program|igot|karmayogi|bachelor|master|phd)\b",
        re.IGNORECASE
    )
    if cert_pattern.search(combined_text):
        level += 1
        reasons.append("Identified official training, course, or certification (+1)")

    # Cap at level 4 max (Level 5 is reserved for proctored/quiz assessments)
    level = min(4, level)
    return level, reasons


def extract_skills_from_profile(profile_text: str, competencies: list, threshold: float = 0.55) -> list[dict]:
    """
    Extract competencies from a user's profile text:
      - Split text into sentences
      - Embed sentences and competency descriptions
      - Compute cosine similarity and match above threshold
      - Keep best 1-3 evidence sentences
      - Calculate transparent level (1-4) and reasons
    """
    sentences = split_into_sentences(profile_text)
    if not sentences or not competencies:
        return []

    # Prepare competency text representation (name + description)
    comp_descriptions = [
        f"{c.name}: {c.description}" if c.description else c.name
        for c in competencies
    ]

    # Generate normalized embeddings
    sentence_embeddings = embed(sentences)
    comp_embeddings = embed(comp_descriptions)

    # Cosine similarity matrix (since vectors are L2-normalized)
    sim_matrix = np.dot(sentence_embeddings, comp_embeddings.T)

    extracted_skills = []

    for comp_idx, comp in enumerate(competencies):
        comp_sims = sim_matrix[:, comp_idx]

        # Find sentence indices that exceed or meet threshold
        matching_indices = np.where(comp_sims >= threshold)[0]
        if len(matching_indices) == 0:
            continue

        # Sort matches by similarity score descending and pick best 1 to 3
        sorted_matches = sorted(matching_indices, key=lambda idx: comp_sims[idx], reverse=True)
        top_indices = sorted_matches[:3]

        best_similarity = float(comp_sims[sorted_matches[0]])
        evidence_sentences = [sentences[idx] for idx in top_indices]

        # Estimate level and collect transparent explanations
        level, reasons = estimate_competency_level(evidence_sentences)

        extracted_skills.append({
            "competency_id": comp.id,
            "name": comp.name,
            "similarity": round(best_similarity, 3),
            "level": level,
            "evidence": evidence_sentences,
            "reasons": reasons
        })

    # Sort results by similarity descending
    extracted_skills.sort(key=lambda x: x["similarity"], reverse=True)
    return extracted_skills
