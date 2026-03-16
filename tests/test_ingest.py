from src.tools.ingest import chunk_text


def test_chunk_text_basic():
    text = " ".join(f"word{i}" for i in range(100))
    chunks = chunk_text(text, chunk_size=20, overlap=5)
    assert len(chunks) > 1
    assert all(len(c.split()) <= 20 for c in chunks)


def test_chunk_text_overlap():
    words = [f"w{i}" for i in range(50)]
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size=10, overlap=3)
    # Second chunk should start 7 words in (10 - 3 overlap)
    second_words = chunks[1].split()
    assert second_words[0] == "w7"


def test_chunk_text_empty():
    chunks = chunk_text("", chunk_size=10, overlap=2)
    assert chunks == []
