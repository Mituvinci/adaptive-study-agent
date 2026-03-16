import random
import re

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from src.graph.state import StudyState
from src.tools.ingest import ingest_document
from src.tools.retriever import retrieve_chunks
from src.prompts.question_prompt import QUESTION_PROMPT
from src.prompts.answer_prompt import ANSWER_PROMPT
from src.prompts.evaluate_prompt import EVALUATE_PROMPT


# Module-level vectorstore reference, set during ingest
_vectorstore = None


def get_vectorstore():
    return _vectorstore


def ingest_node(state: StudyState) -> dict:
    global _vectorstore
    chunks, vectorstore = ingest_document(state["document_path"])
    _vectorstore = vectorstore
    print(f"Ingested {len(chunks)} chunks from {state['document_path']}")
    return {
        "chunks": chunks,
        "questions_asked": 0,
        "questions_correct": 0,
        "weak_chunks": [],
        "session_history": [],
        "mastery_reached": False,
    }


def generate_question_node(state: StudyState) -> dict:
    chunks = state["chunks"]
    weak = state.get("weak_chunks", [])

    # Prefer weak chunks if any, otherwise pick random
    if weak:
        passage = random.choice(weak)
    else:
        passage = random.choice(chunks)

    llm = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0.7)
    prompt = QUESTION_PROMPT.format(passage=passage)
    response = llm.invoke([HumanMessage(content=prompt)])
    question = response.content.strip()

    print(f"\nQ{state['questions_asked'] + 1}: {question}")
    return {"current_question": question}


def answer_node(state: StudyState) -> dict:
    vectorstore = get_vectorstore()
    question = state["current_question"]

    retrieved = retrieve_chunks(vectorstore, question)
    context = "\n\n".join(
        f"[Chunk {i+1}]: {chunk}" for i, chunk in enumerate(retrieved)
    )

    llm = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0.3)
    prompt = ANSWER_PROMPT.format(question=question, context=context)
    response = llm.invoke([HumanMessage(content=prompt)])
    answer = response.content.strip()

    print(f"Answer: {answer[:200]}...")
    return {"current_answer": answer}


def evaluate_node(state: StudyState) -> dict:
    vectorstore = get_vectorstore()
    question = state["current_question"]
    answer = state["current_answer"]

    # Retrieve the most relevant source chunk for grading
    source_chunks = retrieve_chunks(vectorstore, question, top_k=1)
    source = source_chunks[0] if source_chunks else ""

    llm = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0.0)
    prompt = EVALUATE_PROMPT.format(question=question, answer=answer, source=source)
    response = llm.invoke([HumanMessage(content=prompt)])
    result = response.content.strip()

    # Parse score
    score = 0.0
    reasoning = ""
    for line in result.split("\n"):
        if line.startswith("Score:"):
            match = re.search(r"[\d.]+", line)
            if match:
                score = float(match.group())
        elif line.startswith("Reasoning:"):
            reasoning = line.replace("Reasoning:", "").strip()

    questions_asked = state["questions_asked"] + 1
    questions_correct = state["questions_correct"] + (1 if score >= 0.75 else 0)

    # Track weak chunks
    weak_chunks = list(state.get("weak_chunks", []))
    if score < 0.75:
        weak_chunks.append(source)

    # Log to session history
    history = list(state.get("session_history", []))
    history.append({
        "question": question,
        "answer": answer,
        "score": score,
        "reasoning": reasoning,
    })

    print(f"Score: {score} | {reasoning}")
    return {
        "current_score": score,
        "questions_asked": questions_asked,
        "questions_correct": questions_correct,
        "weak_chunks": weak_chunks,
        "session_history": history,
    }


def reread_node(state: StudyState) -> dict:
    print("Re-reading weak chunk for reinforcement...")
    # The re-read simply keeps the weak chunk in state so the next
    # question generation will prioritize it. No additional action needed.
    return {}


def summarize_node(state: StudyState) -> dict:
    print("\nMastery reached. Generating session report...")
    return {"mastery_reached": True}
