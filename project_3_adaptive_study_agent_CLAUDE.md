# Adaptive Study Agent — CLAUDE.md
## Project Intelligence File for Claude Code

> This file is read by Claude Code at the start of every session.
> It contains everything Claude needs to work on this project without re-explanation.

---

## No emojis. No pushing to GitHub.
## At the end of every session write a work_summary_DDMMYYYY.md file.

---

## What This Project Is

A single-agent self-directed learning system built with LangGraph. The agent ingests
documents (research papers, textbook chapters, notes), builds a local vector store,
then enters a self-testing loop — quizzing itself, evaluating its answers, and deciding
whether to re-read or move on. The loop continues until a mastery threshold is reached.

This is a portfolio project. It is NOT connected to MOSAIC technically.
The conceptual link is this: MOSAIC asks whether retrieval improves classification
across specialist agents. This project asks whether retrieval improves self-assessment
accuracy within a single agent feedback loop. Same question, different scale.

**This is intentionally simple. Do not over-engineer it.**

---

## The Core Loop (LangGraph State Machine)

```
          ┌─────────────────────────────┐
          │         START               │
          │   User provides document    │
          └──────────────┬──────────────┘
                         │
                         ▼
          ┌─────────────────────────────┐
          │         INGEST              │
          │  Parse document             │
          │  Chunk into passages        │
          │  Embed → ChromaDB           │
          └──────────────┬──────────────┘
                         │
                         ▼
          ┌─────────────────────────────┐
          │       GENERATE QUESTION     │
          │  Query ChromaDB for a chunk │
          │  LLM generates question     │
          │  from retrieved passage     │
          └──────────────┬──────────────┘
                         │
                         ▼
          ┌─────────────────────────────┐
          │          ANSWER             │
          │  Agent retrieves relevant   │
          │  chunks from ChromaDB       │
          │  LLM generates answer       │
          └──────────────┬──────────────┘
                         │
                         ▼
          ┌─────────────────────────────┐
          │          EVALUATE           │
          │  LLM grades own answer      │
          │  Score: 0.0 – 1.0           │
          │  Updates session state      │
          └──────────────┬──────────────┘
                         │
               ┌─────────┴──────────┐
               │   Conditional edge  │
               │  score < threshold? │
               └─────────┬──────────┘
                    │           │
                   YES          NO
                    │           │
                    ▼           ▼
          ┌──────────────┐  ┌──────────────────┐
          │   RE-READ    │  │  enough questions │
          │  Retrieve +  │  │  answered?        │
          │  re-study    │  └────────┬─────────┘
          │  weak chunk  │       YES │    NO
          └──────┬───────┘           │     │
                 │                   ▼     ▼
                 │           ┌────────────────┐
                 └──────────►│   NEXT QUESTION│
                             └───────┬────────┘
                                     │
                             (loop back to
                           GENERATE QUESTION)
                                     │
                              mastery reached
                                     │
                                     ▼
                             ┌───────────────┐
                             │   SUMMARIZE   │
                             │  Write session│
                             │  report .md   │
                             └───────────────┘
```

---

## LangGraph Concepts Used

**State:** A TypedDict passed between all nodes. Never use global variables.

```python
class StudyState(TypedDict):
    document_path: str
    chunks: list[str]
    questions_asked: int
    questions_correct: int
    current_question: str
    current_answer: str
    current_score: float
    weak_chunks: list[str]        # chunks the agent struggled with
    session_history: list[dict]   # full Q&A log
    mastery_reached: bool
```

**Nodes:** Python functions that take state, return updated state.
- ingest_node
- generate_question_node
- answer_node
- evaluate_node
- reread_node
- summarize_node

**Edges:** Connections between nodes.
- Normal edges: always go to next node
- Conditional edges: route based on state (score < threshold → reread, else → next question)

**The conditional edge is the most important LangGraph concept in this project.**
Everything else is just nodes calling LLMs.

---

## Project Structure

```
adaptive_study_agent/
├── CLAUDE.md                        ← You are here
├── src/
│   ├── graph/
│   │   ├── state.py                 ← StudyState TypedDict
│   │   ├── nodes.py                 ← All node functions
│   │   ├── edges.py                 ← Conditional edge logic
│   │   └── build_graph.py           ← Assembles the StateGraph
│   ├── tools/
│   │   ├── ingest.py                ← PDF/text chunking + ChromaDB insert
│   │   └── retriever.py             ← ChromaDB query wrapper
│   ├── prompts/
│   │   ├── question_prompt.py       ← Generate question from passage
│   │   ├── answer_prompt.py         ← Answer question using retrieved context
│   │   └── evaluate_prompt.py       ← Grade answer 0.0-1.0 with reasoning
│   └── main.py                      ← Entry point
├── output/
│   └── session_reports/             ← Markdown report per session
├── data/
│   └── documents/                   ← Drop PDFs or .txt files here
├── pyproject.toml
├── .env
└── README.md
```

---

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Agent framework | LangGraph | Stateful loops + conditional branching |
| LLM | claude-sonnet-4-20250514 | Question gen, answering, evaluation |
| Embeddings | OpenAI text-embedding-3-small | Cheap, good enough for text chunks |
| Vector store | ChromaDB (local) | No Docker needed, embedded, simple |
| Document parsing | PyMuPDF (fitz) | PDF support |
| Package manager | UV | Consistent with other projects |

---

## Configuration

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...           # for embeddings only

# Tunable constants in src/graph/build_graph.py
MASTERY_THRESHOLD = 0.75        # score needed to skip re-read
MIN_QUESTIONS = 10              # minimum questions before mastery check
MAX_REREAD_CYCLES = 3           # max times agent re-reads same chunk
CHUNK_SIZE = 500                # tokens per chunk
CHUNK_OVERLAP = 50
TOP_K_RETRIEVAL = 3             # chunks retrieved per question
```

---

## Prompts — Critical Details

### Question generation prompt
- Input: one retrieved chunk (passage)
- Output: one specific, answerable question about that chunk
- Constraint: question must be answerable from the document alone
- Do NOT ask opinion questions or questions requiring outside knowledge

### Answer prompt
- Input: question + top-k retrieved chunks as context
- Output: concise answer grounded in retrieved text
- Constraint: agent must cite which chunk it used

### Evaluation prompt
- Input: question + agent's answer + original source chunk
- Output: score (0.0–1.0) + one-sentence reasoning
- This is self-grading — instruct the LLM to be honest, not generous
- Score 1.0 = complete and accurate
- Score 0.5 = partially correct
- Score 0.0 = wrong or hallucinated

---

## Key Rules

1. NEVER hardcode API keys — always read from .env
2. NEVER skip the evaluate node — self-grading is the whole point
3. NEVER let the agent loop forever — MAX_REREAD_CYCLES hard limit per chunk
4. State is the single source of truth — no global variables, no side effects
5. ChromaDB collection is per-session — clear between runs unless --persist flag set
6. All session output goes to output/session_reports/ with timestamp
7. temperature=0.0 on evaluate_node — grading must be deterministic
8. temperature=0.7 on generate_question_node — variety in questions

---

## Commands

```bash
# Setup
uv sync

# Run with a document
uv run python src/main.py --doc data/documents/attention_is_all_you_need.pdf

# Run with mastery threshold override
uv run python src/main.py --doc data/documents/myfile.pdf --threshold 0.8

# Run tests
uv run pytest tests/ -v
```

---

## Output Format

Each session produces a markdown report in output/session_reports/:

```markdown
# Study Session Report
Date: 2026-03-12
Document: attention_is_all_you_need.pdf

## Summary
- Questions asked: 14
- Questions correct (score >= 0.75): 11
- Final mastery score: 0.81
- Re-read cycles triggered: 3

## Weak Areas
- Multi-head attention computation
- Positional encoding formula

## Q&A Log
### Q1
Question: What is the purpose of the scaling factor in dot-product attention?
Answer: ...
Score: 0.9
...
```

---

## Portfolio Framing (for README.md)

The README must make this one point clearly:

> MOSAIC (separate research project) tests whether 12 specialist agents sharing a
> vector database improves rare-condition classification — collective knowledge at scale.
> This project is the single-agent version of the same question: can one agent use
> retrieval to improve its own understanding iteratively? The feedback loop here is
> what Phase 1C of MOSAIC implements collectively across 12 agents.

Do not overclaim a technical connection. The connection is conceptual and motivational.

---

## What This Project Is NOT

- Not connected to MOSAIC's Qdrant instance
- Not a production system
- Not a replacement for actual studying
- Not a RAG chatbot (there is no human in the loop during the study session)

---

## Author

Halima Akhter — PhD Candidate, Computer Science
Specialization: ML, Deep Learning, Bioinformatics
GitHub: https://github.com/Mituvinci

---

*Last updated: March 2026 | Adaptive Study Agent v1*
