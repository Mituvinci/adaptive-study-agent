import os

import fitz
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma


CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def extract_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap
    return chunks


def ingest_document(file_path: str, collection_name: str = "study_session") -> tuple[list[str], Chroma]:
    text = extract_text(file_path)
    chunks = chunk_text(text)

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
    )

    vectorstore.add_texts(
        texts=chunks,
        metadatas=[{"chunk_index": i, "source": file_path} for i in range(len(chunks))],
    )

    return chunks, vectorstore
