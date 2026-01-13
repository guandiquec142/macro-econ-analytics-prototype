import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

DB_PATH = os.path.join("rag", "vectorstore")

def get_retriever(k: int = 5):
    """Load or rebuild local Chroma retriever."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError("RAG vectorstore not found—run rag/ingest.py first.")
    
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    return db.as_retriever(search_kwargs={"k": k})

def retrieve_context(query: str, k: int = 5) -> str:
    """Retrieve top-k relevant chunks as context string."""
    try:
        retriever = get_retriever(k=k)
        docs = retriever.invoke(query)
        if not docs:
            return "No relevant expert context found."
        context = "\n\n".join([
            f"Source: {doc.metadata.get('source', 'Unknown')}\n{doc.page_content.strip()}"
            for doc in docs
        ])
        return context
    except Exception as e:
        return f"RAG retrieval error: {str(e)}"