from src.graph.state import StudyState


MASTERY_THRESHOLD = 0.75
MIN_QUESTIONS = 10
MAX_REREAD_CYCLES = 3


def after_evaluate(state: StudyState) -> str:
    score = state["current_score"]
    questions_asked = state["questions_asked"]
    weak_chunks = state.get("weak_chunks", [])

    # If score is below threshold and we haven't exceeded reread limit
    if score < MASTERY_THRESHOLD and len(weak_chunks) <= MAX_REREAD_CYCLES:
        return "reread"

    # Check if mastery is reached
    if questions_asked >= MIN_QUESTIONS:
        correct_ratio = state["questions_correct"] / questions_asked
        if correct_ratio >= MASTERY_THRESHOLD:
            return "summarize"

    # Continue with next question
    return "next_question"
