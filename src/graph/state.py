from typing import TypedDict


class StudyState(TypedDict):
    document_path: str
    chunks: list[str]
    questions_asked: int
    questions_correct: int
    current_question: str
    current_answer: str
    current_score: float
    weak_chunks: list[str]
    session_history: list[dict]
    mastery_reached: bool
