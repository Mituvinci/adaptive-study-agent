ANSWER_PROMPT = """You are a study agent answering a question using retrieved context from a document.

Question: {question}

Retrieved context:
{context}

Instructions:
- Answer the question concisely using ONLY the retrieved context above.
- Cite which chunk you used by referencing its number (e.g., "According to chunk 2...").
- If the context does not contain enough information, say so.

Answer:"""
