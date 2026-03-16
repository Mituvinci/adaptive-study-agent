import argparse
import os
from datetime import datetime

from dotenv import load_dotenv

from src.graph.build_graph import build_study_graph
from src.graph.state import StudyState


load_dotenv()


def write_session_report(state: StudyState) -> str:
    now = datetime.now()
    filename = f"session_{now.strftime('%Y%m%d_%H%M%S')}.md"
    filepath = os.path.join("output", "session_reports", filename)

    questions_asked = state["questions_asked"]
    questions_correct = state["questions_correct"]
    mastery_score = questions_correct / questions_asked if questions_asked > 0 else 0.0
    reread_count = len(state.get("weak_chunks", []))
    doc_name = os.path.basename(state["document_path"])

    # Find weak areas from low-scoring questions
    weak_areas = []
    for entry in state.get("session_history", []):
        if entry["score"] < 0.75:
            weak_areas.append(entry["question"])

    lines = [
        "# Study Session Report",
        f"Date: {now.strftime('%Y-%m-%d')}",
        f"Document: {doc_name}",
        "",
        "## Summary",
        f"- Questions asked: {questions_asked}",
        f"- Questions correct (score >= 0.75): {questions_correct}",
        f"- Final mastery score: {mastery_score:.2f}",
        f"- Re-read cycles triggered: {reread_count}",
        "",
        "## Weak Areas",
    ]

    if weak_areas:
        for area in weak_areas:
            lines.append(f"- {area}")
    else:
        lines.append("- None")

    lines.extend(["", "## Q&A Log"])

    for i, entry in enumerate(state.get("session_history", []), 1):
        lines.extend([
            f"### Q{i}",
            f"Question: {entry['question']}",
            f"Answer: {entry['answer']}",
            f"Score: {entry['score']}",
            f"Reasoning: {entry['reasoning']}",
            "",
        ])

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filepath


def main():
    parser = argparse.ArgumentParser(description="Adaptive Study Agent")
    parser.add_argument("--doc", required=True, help="Path to document (PDF or TXT)")
    parser.add_argument("--threshold", type=float, default=0.75, help="Mastery threshold (0.0-1.0)")
    parser.add_argument("--persist", action="store_true", help="Persist ChromaDB between runs")
    args = parser.parse_args()

    if not os.path.exists(args.doc):
        print(f"Error: File not found: {args.doc}")
        return

    # Update mastery threshold if overridden
    if args.threshold != 0.75:
        from src.graph import edges
        edges.MASTERY_THRESHOLD = args.threshold

    print(f"Starting study session with: {args.doc}")
    print(f"Mastery threshold: {args.threshold}")
    print("-" * 50)

    graph = build_study_graph()

    initial_state: StudyState = {
        "document_path": args.doc,
        "chunks": [],
        "questions_asked": 0,
        "questions_correct": 0,
        "current_question": "",
        "current_answer": "",
        "current_score": 0.0,
        "weak_chunks": [],
        "session_history": [],
        "mastery_reached": False,
    }

    final_state = graph.invoke(initial_state)

    report_path = write_session_report(final_state)
    print(f"\nSession report saved to: {report_path}")


if __name__ == "__main__":
    main()
