import io
import json
import pytest

from backend.app.extensions import db
from backend.app.models.assessment import Document, Question
from backend.app.models.competency import Competency
from backend.services.embedder import set_embedder, reset_embedder, FakeEmbedder, embed
from backend.services.llm_client import set_llm_client, reset_llm_client, FakeLLMClient
from backend.services.chunker import (
    split_text_into_chunks,
    build_and_save_document_index
)
from backend.app.blueprints.assessment import is_allowed_file
from backend.services.mcq_generator import (
    generate_mcqs,
    validate_question_schema,
    validate_option_lengths,
    is_passage_in_chunk,
    check_near_duplicates
)


@pytest.fixture(autouse=True)
def setup_test_services():
    """Ensure FakeEmbedder and FakeLLMClient are used for all tests (no external network calls)."""
    fake_embedder = FakeEmbedder()
    set_embedder(fake_embedder)
    fake_llm = FakeLLMClient()
    set_llm_client(fake_llm)
    yield
    reset_embedder()
    reset_llm_client()


@pytest.fixture
def sample_competency(app):
    with app.app_context():
        comp = Competency(
            name="Sampling Methods",
            description="Designs and applies probability sampling schemes (SRS, stratified, cluster, PPS) to official surveys."
        )
        db.session.add(comp)
        db.session.commit()
        return comp.to_dict()


# -------------------------------------------------------------
# 1. Chunker and Text Extraction Tests
# -------------------------------------------------------------

def test_split_text_into_chunks():
    """split_text_into_chunks must split text, respect boundaries, and track page numbers."""
    pages = [
        {
            "page": 1,
            "text": "Paragraph 1: Sampling is the process of selecting a subset. " * 8
        },
        {
            "page": 2,
            "text": "Paragraph 2: Stratified sampling divides the population into strata. " * 8
        }
    ]
    chunks = split_text_into_chunks(pages, chunk_size=300, overlap=50)

    assert len(chunks) >= 2
    # Verify chunks have required keys
    for chunk in chunks:
        assert "chunk_id" in chunk
        assert "page" in chunk
        assert "text" in chunk
        assert len(chunk["text"]) > 0

    # Page tracking preserved
    pages_found = {c["page"] for c in chunks}
    assert 1 in pages_found
    assert 2 in pages_found


# -------------------------------------------------------------
# 2. Document Upload & Validation Tests
# -------------------------------------------------------------

def test_upload_document_permissions(client, learner_token, trainer_token, sample_competency):
    """Learners cannot upload documents (403), but trainers can (201)."""
    file_content = b"Sampling text content for testing purposes.\n\nMore detailed statistical methods."

    # Learner attempt
    res = client.post(
        "/api/documents",
        data={
            "file": (io.BytesIO(file_content), "sampling.txt"),
            "title": "Sampling Docs",
            "competency_id": sample_competency["id"]
        },
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {learner_token}"}
    )
    assert res.status_code == 403

    # Trainer attempt
    res_trainer = client.post(
        "/api/documents",
        data={
            "file": (io.BytesIO(file_content), "sampling.txt"),
            "title": "Sampling Docs",
            "competency_id": sample_competency["id"]
        },
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {trainer_token}"}
    )
    assert res_trainer.status_code == 201
    data = res_trainer.get_json()
    assert data["document"]["title"] == "Sampling Docs"
    assert data["document"]["competency_id"] == sample_competency["id"]
    assert data["chunks_count"] >= 1


def test_upload_validation_rejected_cases(client, trainer_token):
    """Rejects empty files, oversized files, and unsupported file extensions."""
    # 1. Unsupported extension
    res = client.post(
        "/api/documents",
        data={"file": (io.BytesIO(b"binary exe"), "malicious.exe")},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {trainer_token}"}
    )
    assert res.status_code == 400
    assert "Unsupported file type" in res.get_json()["message"]

    # 2. Empty file
    res_empty = client.post(
        "/api/documents",
        data={"file": (io.BytesIO(b""), "empty.txt")},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {trainer_token}"}
    )
    assert res_empty.status_code == 400
    assert "empty" in res_empty.get_json()["message"].lower()

    # 3. Oversized file (> 10MB)
    huge_bytes = b"0" * (10 * 1024 * 1024 + 10)
    res_huge = client.post(
        "/api/documents",
        data={"file": (io.BytesIO(huge_bytes), "large.txt")},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {trainer_token}"}
    )
    assert res_huge.status_code == 400
    assert "exceeds maximum size" in res_huge.get_json()["message"].lower()


# -------------------------------------------------------------
# 3. Code Validation for Questions
# -------------------------------------------------------------

def test_validate_question_schema():
    """Schema validator must reject missing fields, != 4 options, duplicate options, and forbidden clichés."""
    valid_q = {
        "question": "What is the primary advantage of Stratified Random Sampling?",
        "options": [
            "Reduces sampling variance within strata",
            "Eliminates all non-sampling errors completely",
            "Requires no prior sampling frame",
            "Guarantees zero logistical expense"
        ],
        "correct_index": 0,
        "explanation": "Stratification groups homogenous units together, reducing intra-stratum variance.",
        "source_passage": "Stratified sampling reduces sampling variance.",
        "difficulty": "medium"
    }
    is_valid, err = validate_question_schema(valid_q)
    assert is_valid is True
    assert err is None

    # Less than 4 options
    bad_options = dict(valid_q, options=["A", "B", "C"])
    valid, err = validate_question_schema(bad_options)
    assert valid is False
    assert "exactly 4 choices" in err

    # Duplicate options
    dup_options = dict(valid_q, options=["Choice A", "Choice A", "Choice C", "Choice D"])
    valid, err = validate_question_schema(dup_options)
    assert valid is False
    assert "must be distinct" in err

    # Out of range correct_index
    bad_idx = dict(valid_q, correct_index=4)
    valid, err = validate_question_schema(bad_idx)
    assert valid is False
    assert "correct_index must be an integer between 0 and 3" in err

    # Forbidden cliché "All of the above"
    cliche_q = dict(valid_q, options=["Option 1", "Option 2", "Option 3", "All of the above"])
    valid, err = validate_question_schema(cliche_q)
    assert valid is False
    assert "forbidden phrase" in err


def test_validate_option_lengths():
    """Rejects questions where option lengths are wildly disparate."""
    # Balanced lengths
    balanced = ["Simple Random Sampling", "Stratified Sampling", "Cluster Sampling", "Systematic Sampling"]
    valid, err = validate_option_lengths(balanced)
    assert valid is True

    # Wildly disparate lengths (e.g. 8 chars vs 90 chars)
    disparate = [
        "Yes",
        "No",
        "Maybe",
        "This is an extraordinarily long and verbose correct answer that gives itself away immediately"
    ]
    valid, err = validate_option_lengths(disparate)
    assert valid is False
    assert "Option lengths are wildly disparate" in err


def test_source_passage_verification():
    """source_passage must actually appear in the chunk text."""
    chunk_text = (
        "Stratified sampling divides a heterogeneous population into mutually exclusive, "
        "homogeneous subgroups termed strata. Independent random samples are then drawn from each stratum."
    )
    valid_passage = "Stratified sampling divides a heterogeneous population into mutually exclusive, homogeneous subgroups termed strata."
    assert is_passage_in_chunk(valid_passage, chunk_text) is True

    fake_passage = "Machine learning algorithms always outperform traditional statistical methods in all circumstances."
    assert is_passage_in_chunk(fake_passage, chunk_text) is False


def test_duplicate_rejection():
    """Near-duplicate questions with similarity > 0.90 must be detected and rejected."""
    existing_texts = ["What is the primary benefit of stratified random sampling in official statistics?"]
    existing_vecs = list(embed(existing_texts))

    # Identical or near-identical question
    candidate_vec = embed(["What is the primary benefit of stratified random sampling in official statistics?"])[0]
    is_dup, sim = check_near_duplicates(candidate_vec, existing_vecs, threshold=0.90)
    assert is_dup is True
    assert sim >= 0.99

    # Distinct question
    distinct_vec = embed(["How do non-sampling errors differ from sampling errors in national surveys?"])[0]
    is_dup2, sim2 = check_near_duplicates(distinct_vec, existing_vecs, threshold=0.90)
    assert is_dup2 is False
    assert sim2 < 0.90


# -------------------------------------------------------------
# 4. MCQ Generator & Verifier Pass Tests
# -------------------------------------------------------------

def test_mcq_generation_verifier_agreement_and_disagreement(app, sample_competency):
    """Verifier pass keeps questions when verifier agrees, drops when verifier disagrees."""
    with app.app_context():
        # Setup document and chunks
        doc = Document(
            title="Sampling Theory",
            filename="sampling_theory.txt",
            uploaded_by=1,
            competency_id=sample_competency["id"]
        )
        db.session.add(doc)
        db.session.commit()

        passage = "Stratified sampling reduces sampling variance because intra-stratum variance is small."
        chunk = {
            "chunk_id": 0,
            "page": 1,
            "text": f"Introduction to Survey Methods.\n\n{passage}\n\nConclusion."
        }
        build_and_save_document_index(doc.id, [chunk])

        fake_client = FakeLLMClient()
        set_llm_client(fake_client)

        # 1. When verifier disagrees: candidate claims correct_index=0, but verifier picks 2
        fake_client.queue_response({
            "questions": [
                {
                    "question": "Why does stratified sampling reduce variance?",
                    "options": [
                        "Intra-stratum variance is small",
                        "No sample frame is necessary",
                        "Non-sampling errors are zero",
                        "Sample size is unbounded"
                    ],
                    "correct_index": 0,
                    "explanation": "Because intra-stratum variance is small.",
                    "source_passage": passage,
                    "difficulty": "medium"
                }
            ]
        })
        # Verifier response disagreeing (picks index 2)
        fake_client.queue_response({"chosen_index": 2, "rationale": "Different rationale"})

        res_disagree = generate_mcqs(doc.id, num_questions=1, verify=True)
        assert res_disagree["kept"] == 0
        assert res_disagree["rejected"] == 1
        assert "Verifier disagreement" in res_disagree["rejections"][0]["reason"]

        # 2. When verifier agrees: candidate claims index=0, verifier picks index=0
        fake_client.queue_response({
            "questions": [
                {
                    "question": "Why does stratified sampling reduce variance?",
                    "options": [
                        "Intra-stratum variance is small",
                        "No sample frame is necessary",
                        "Non-sampling errors are zero",
                        "Sample size is unbounded"
                    ],
                    "correct_index": 0,
                    "explanation": "Because intra-stratum variance is small.",
                    "source_passage": passage,
                    "difficulty": "medium"
                }
            ]
        })
        fake_client.queue_response({"chosen_index": 0, "rationale": "Directly stated"})

        res_agree = generate_mcqs(doc.id, num_questions=1, verify=True)
        assert res_agree["kept"] == 1
        assert res_agree["rejected"] == 0
        saved_q = Question.query.filter_by(document_id=doc.id).first()
        assert saved_q is not None
        assert saved_q.status == "draft"


# -------------------------------------------------------------
# 5. Trainer Review & Learner View Integration Tests
# -------------------------------------------------------------

def test_trainer_review_flow_and_learner_quiz_isolation(client, trainer_token, learner_token, sample_competency):
    """
    Test full lifecycle:
    1. Upload document as trainer
    2. Generate questions
    3. Trainer edits and approves
    4. Learner queries quiz: sees ONLY approved questions, without answers/explanations
    """
    file_text = (
        "In probability sampling, every unit has a known, non-zero probability of being selected. "
        "Simple Random Sampling gives each unit an equal chance."
    )
    # 1. Upload document
    upload_res = client.post(
        "/api/documents",
        data={
            "file": (io.BytesIO(file_text.encode("utf-8")), "probability_sampling.txt"),
            "title": "Probability Sampling Manual",
            "competency_id": sample_competency["id"]
        },
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {trainer_token}"}
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.get_json()["document"]["id"]

    # 2. Generate questions
    fake_client = FakeLLMClient()
    fake_client.queue_response({
        "questions": [
            {
                "question": "What defines probability sampling in survey design?",
                "options": [
                    "Known, non-zero selection chance",
                    "Subjective quota-based selection",
                    "Convenient volunteer participant pool",
                    "Zero chance for rural populations"
                ],
                "correct_index": 0,
                "explanation": "Every unit has a known non-zero probability.",
                "source_passage": "In probability sampling, every unit has a known, non-zero probability of being selected.",
                "difficulty": "easy"
            },
            {
                "question": "What is true about Simple Random Sampling?",
                "options": [
                    "Units have equal selection chances",
                    "Units are grouped by income strata",
                    "Primary sampling units are selected",
                    "Only convenient units are surveyed"
                ],
                "correct_index": 0,
                "explanation": "Simple Random Sampling gives each unit an equal chance.",
                "source_passage": "Simple Random Sampling gives each unit an equal chance.",
                "difficulty": "easy"
            }
        ]
    })
    set_llm_client(fake_client)

    gen_res = client.post(
        f"/api/documents/{doc_id}/generate",
        json={"num_questions": 2, "difficulty": "easy"},
        headers={"Authorization": f"Bearer {trainer_token}"}
    )
    assert gen_res.status_code == 200
    assert gen_res.get_json()["result"]["kept"] == 2

    # Verify questions are in draft status
    q_list_res = client.get(
        f"/api/documents/{doc_id}/questions?status=draft",
        headers={"Authorization": f"Bearer {trainer_token}"}
    )
    assert q_list_res.status_code == 200
    draft_questions = q_list_res.get_json()["questions"]
    assert len(draft_questions) == 2
    q1_id = draft_questions[0]["id"]
    q2_id = draft_questions[1]["id"]

    # Learner views quiz before approval: MUST BE EMPTY
    learner_quiz_before = client.get(
        f"/api/quiz/{sample_competency['id']}",
        headers={"Authorization": f"Bearer {learner_token}"}
    )
    assert learner_quiz_before.status_code == 200
    assert learner_quiz_before.get_json()["count"] == 0

    # 3. Trainer edits Q1
    edit_res = client.put(
        f"/api/questions/{q1_id}",
        json={"difficulty": "medium", "explanation": "Updated official explanation"},
        headers={"Authorization": f"Bearer {trainer_token}"}
    )
    assert edit_res.status_code == 200
    assert edit_res.get_json()["question"]["difficulty"] == "medium"

    # 4. Trainer approves Q1 and rejects Q2
    app_res = client.post(
        f"/api/questions/{q1_id}/approve",
        headers={"Authorization": f"Bearer {trainer_token}"}
    )
    assert app_res.status_code == 200
    assert app_res.get_json()["question"]["status"] == "approved"

    rej_res = client.post(
        f"/api/questions/{q2_id}/reject",
        headers={"Authorization": f"Bearer {trainer_token}"}
    )
    assert rej_res.status_code == 200
    assert rej_res.get_json()["question"]["status"] == "rejected"

    # 5. Learner views quiz now:
    # - Must contain ONLY Q1
    # - Must NOT contain Q2 (rejected)
    # - Must NOT include correct_index or explanation
    learner_quiz_after = client.get(
        f"/api/quiz/{sample_competency['id']}",
        headers={"Authorization": f"Bearer {learner_token}"}
    )
    assert learner_quiz_after.status_code == 200
    quiz_data = learner_quiz_after.get_json()
    assert quiz_data["count"] == 1
    delivered_q = quiz_data["questions"][0]
    assert delivered_q["id"] == q1_id
    assert "correct_index" not in delivered_q
    assert "explanation" not in delivered_q
    assert "options" in delivered_q
    assert len(delivered_q["options"]) == 4

    # 6. Trainer approve-all test on a new draft question
    fake_client.queue_response({
        "questions": [
            {
                "question": "What is another probability sampling design?",
                "options": ["Cluster sampling", "Quota sampling", "Purposive selection", "Convenience sample"],
                "correct_index": 0,
                "explanation": "Cluster sampling is probability-based.",
                "source_passage": "In probability sampling, every unit has a known, non-zero probability of being selected.",
                "difficulty": "medium"
            }
        ]
    })
    client.post(
        f"/api/documents/{doc_id}/generate",
        json={"num_questions": 1},
        headers={"Authorization": f"Bearer {trainer_token}"}
    )
    approve_all_res = client.post(
        f"/api/documents/{doc_id}/approve-all",
        headers={"Authorization": f"Bearer {trainer_token}"}
    )
    assert approve_all_res.status_code == 200
    assert approve_all_res.get_json()["count"] >= 1
