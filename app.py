"""Gradio UI for the Adaptive Study Agent."""

import os
import shutil
import tempfile
from datetime import datetime

import gradio as gr
from dotenv import load_dotenv

load_dotenv()

from src.graph.build_graph import build_study_graph
from src.graph.state import StudyState
from src.graph import edges


def build_report_md(state: StudyState) -> str:
    """Build a markdown session report from the final graph state."""
    now = datetime.now()
    questions_asked = state["questions_asked"]
    questions_correct = state["questions_correct"]
    mastery_score = questions_correct / questions_asked if questions_asked > 0 else 0.0
    reread_count = len(state.get("weak_chunks", []))
    doc_name = os.path.basename(state["document_path"])

    weak_areas = []
    for entry in state.get("session_history", []):
        if entry["score"] < 0.75:
            weak_areas.append(entry["question"])

    lines = [
        "# Study Session Report",
        f"**Date:** {now.strftime('%Y-%m-%d %H:%M')}",
        f"**Document:** {doc_name}",
        "",
        "## Summary",
        f"- Questions asked: **{questions_asked}**",
        f"- Questions correct (score >= 0.75): **{questions_correct}**",
        f"- Final mastery score: **{mastery_score:.2f}**",
        f"- Re-read cycles triggered: **{reread_count}**",
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
        score_label = "pass" if entry["score"] >= 0.75 else "FAIL"
        lines.extend([
            f"### Q{i} [{score_label}]",
            f"**Question:** {entry['question']}",
            "",
            f"**Answer:** {entry['answer']}",
            "",
            f"**Score:** {entry['score']}  ",
            f"**Reasoning:** {entry['reasoning']}",
            "",
            "---",
            "",
        ])

    return "\n".join(lines)


def run_study_session(file, mastery_threshold, progress=gr.Progress(track_tqdm=False)):
    """Run the adaptive study graph and yield progress updates + final report."""
    if file is None:
        yield "Please upload a document first.", ""
        return

    # Gradio 5 returns a filepath string; Gradio 4 returned an object with .name
    file_path = file if isinstance(file, str) else file.name
    ext = os.path.splitext(file_path)[1]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    shutil.copy2(file_path, tmp.name)
    doc_path = tmp.name

    edges.MASTERY_THRESHOLD = mastery_threshold

    progress(0, desc="Building study graph...")
    yield "Building study graph...", ""

    graph = build_study_graph()

    initial_state: StudyState = {
        "document_path": doc_path,
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

    progress(0.05, desc="Ingesting document...")
    yield "Ingesting document...", ""

    status_lines = []
    last_state = initial_state

    for event in graph.stream(initial_state, stream_mode="updates"):
        for node_name, node_output in event.items():
            if isinstance(node_output, dict):
                last_state = {**last_state, **node_output}

            if node_name == "ingest":
                n = len(last_state.get("chunks", []))
                msg = f"Ingested {n} chunks."
                status_lines.append(msg)

            elif node_name == "generate_question":
                q = last_state.get("current_question", "")
                qnum = last_state.get("questions_asked", 0) + 1
                msg = f"**Q{qnum}:** {q}"
                status_lines.append(msg)

            elif node_name == "answer":
                ans = last_state.get("current_answer", "")
                msg = f"Answer: {ans[:200]}..."
                status_lines.append(msg)

            elif node_name == "evaluate":
                s = last_state.get("current_score", 0.0)
                asked = last_state.get("questions_asked", 0)
                correct = last_state.get("questions_correct", 0)
                msg = f"Score: {s} | Progress: {correct}/{asked} correct"
                status_lines.append(msg)
                ratio = asked / max(edges.MIN_QUESTIONS, asked + 1)
                progress(ratio, desc=f"Q{asked} scored {s}")

            elif node_name == "reread":
                msg = "Re-reading weak chunk for reinforcement..."
                status_lines.append(msg)

            elif node_name == "summarize":
                msg = "Mastery reached! Generating report..."
                status_lines.append(msg)

            yield "\n\n".join(status_lines), ""

    report = build_report_md(last_state)

    try:
        os.unlink(doc_path)
    except OSError:
        pass

    yield "\n\n".join(status_lines) + "\n\n**Session complete!**", report


with gr.Blocks(title="Adaptive Study Agent") as demo:
    gr.Markdown("# Adaptive Study Agent")
    gr.Markdown(
        "Upload a PDF or TXT document and the agent will quiz itself, "
        "evaluate answers, and re-read weak areas until mastery is reached."
    )

    with gr.Row():
        with gr.Column(scale=1):
            file_input = gr.File(
                label="Upload Document (PDF or TXT)",
                file_types=[".pdf", ".txt"],
                type="filepath",
            )
            threshold_slider = gr.Slider(
                minimum=0.5,
                maximum=1.0,
                value=0.75,
                step=0.05,
                label="Mastery Threshold",
            )
            start_btn = gr.Button("Start Study Session", variant="primary")

        with gr.Column(scale=2):
            status_output = gr.Markdown(label="Progress", value="*Waiting to start...*")

    gr.Markdown("---")
    report_output = gr.Markdown(label="Session Report", value="")

    start_btn.click(
        fn=run_study_session,
        inputs=[file_input, threshold_slider],
        outputs=[status_output, report_output],
    )

if __name__ == "__main__":
    demo.queue().launch()
