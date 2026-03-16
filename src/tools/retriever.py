from langchain_chroma import Chroma


TOP_K_RETRIEVAL = 3


def retrieve_chunks(vectorstore: Chroma, query: str, top_k: int = TOP_K_RETRIEVAL) -> list[str]:
    results = vectorstore.similarity_search(query, k=top_k)
    return [doc.page_content for doc in results]
