from src.graph.edges import after_evaluate


def _make_state(**overrides):
    base = {
        "document_path": "test.pdf",
        "chunks": ["chunk1", "chunk2"],
        "questions_asked": 5,
        "questions_correct": 3,
        "current_question": "What is X?",
        "current_answer": "X is Y.",
        "current_score": 0.8,
        "weak_chunks": [],
        "session_history": [],
        "mastery_reached": False,
    }
    base.update(overrides)
    return base


def test_low_score_triggers_reread():
    state = _make_state(current_score=0.5, weak_chunks=["c1"])
    assert after_evaluate(state) == "reread"


def test_high_score_continues_to_next_question():
    state = _make_state(current_score=0.9, questions_asked=5)
    assert after_evaluate(state) == "next_question"


def test_mastery_reached_after_min_questions():
    state = _make_state(
        current_score=0.9,
        questions_asked=10,
        questions_correct=8,
    )
    assert after_evaluate(state) == "summarize"


def test_no_mastery_if_ratio_too_low():
    state = _make_state(
        current_score=0.9,
        questions_asked=10,
        questions_correct=5,
    )
    assert after_evaluate(state) == "next_question"


def test_reread_limit_exceeded_goes_to_next():
    state = _make_state(
        current_score=0.3,
        weak_chunks=["c1", "c2", "c3", "c4"],
    )
    assert after_evaluate(state) == "next_question"
