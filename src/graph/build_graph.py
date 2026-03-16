from langgraph.graph import StateGraph, END

from src.graph.state import StudyState
from src.graph.nodes import (
    ingest_node,
    generate_question_node,
    answer_node,
    evaluate_node,
    reread_node,
    summarize_node,
)
from src.graph.edges import after_evaluate


def build_study_graph() -> StateGraph:
    graph = StateGraph(StudyState)

    # Add nodes
    graph.add_node("ingest", ingest_node)
    graph.add_node("generate_question", generate_question_node)
    graph.add_node("answer", answer_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("reread", reread_node)
    graph.add_node("summarize", summarize_node)

    # Set entry point
    graph.set_entry_point("ingest")

    # Normal edges
    graph.add_edge("ingest", "generate_question")
    graph.add_edge("generate_question", "answer")
    graph.add_edge("answer", "evaluate")

    # Conditional edge after evaluation
    graph.add_conditional_edges(
        "evaluate",
        after_evaluate,
        {
            "reread": "reread",
            "next_question": "generate_question",
            "summarize": "summarize",
        },
    )

    # Reread loops back to generate question
    graph.add_edge("reread", "generate_question")

    # Summarize ends the graph
    graph.add_edge("summarize", END)

    return graph.compile()
