EVALUATE_PROMPT = """You are a strict evaluator grading an agent's answer against a source passage.

Question: {question}

Agent's answer: {answer}

Source passage (ground truth): {source}

Grade the answer on a scale of 0.0 to 1.0:
- 1.0 = complete and accurate, fully supported by the source
- 0.5 = partially correct, missing key details or slightly inaccurate
- 0.0 = wrong, hallucinated, or not supported by the source

Be honest and strict. Do not be generous.

Respond in exactly this format:
Score: <number>
Reasoning: <one sentence>"""
