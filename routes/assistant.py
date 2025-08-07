from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
# from langchain.chat_models import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
#from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

from models.journal import JournalEntry
from models.repository import Commit, Repository
from models.wellness_snapshot import WellnessSnapshot
from datetime import datetime, timedelta
import os
from extensions import get_embeddings_model, cache

assistant_bp = Blueprint('assistant', __name__, url_prefix='/assistant')

VECTOR_DIR = os.path.join(os.getcwd(), 'vector_stores')


def _get_vectordb(user_id: int):
    """Return (or create) the Chroma vector store for the user."""
    user_dir = os.path.join(VECTOR_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    embeddings = cache.get('embeddings_model') or get_embeddings_model()
    return Chroma(persist_directory=user_dir, embedding_function=embeddings)

def _build_documents(user_id: int):
    """Gather commits, journals, repositories, and wellness snapshots into LangChain Documents."""
    docs = []

    since = datetime.utcnow() - timedelta(days=90)

    # Commits
    commits = (
        Commit.query.join(Repository)
        .filter(Repository.user_id == user_id, Commit.timestamp >= since)
        .all()
    )
    for c in commits:
        docs.append(
            Document(
                page_content=f"[{c.repository.name}] {c.message}",
                metadata={
                    "type": "commit",
                    "repo": c.repository.name if c.repository else "unknown",
                    "timestamp": c.timestamp.isoformat(),
                },
            )
        )

    # Journal entries
    entries = (
        JournalEntry.query.filter_by(user_id=user_id)
        .filter(JournalEntry.created_at >= since)
        .all()
    )
    for e in entries:
        docs.append(
            Document(
                page_content=e.content,
                metadata={
                    "type": "journal",
                    "title": e.title,
                    "timestamp": e.created_at.isoformat(),
                    "sentiment": e.sentiment_label or "neutral"
                },
            )
        )

    # Wellness Snapshots
    snapshots = (
        WellnessSnapshot.query.filter_by(user_id=user_id)
        .filter(WellnessSnapshot.snapshot_date >= since.date())
        .order_by(WellnessSnapshot.snapshot_date.desc())
        .all()
    )
    for snap in snapshots:
        summary = snap.to_summary()
        docs.append(
            Document(
                page_content=summary,
                metadata={
                    "type": "wellness",
                    "snapshot_date": snap.snapshot_date.isoformat(),
                    "burnout_risk": snap.burnout_risk,
                    "wellness_score": snap.wellness_score,
                },
            )
        )

    # Repository summaries
    repos = Repository.query.filter_by(user_id=user_id).all()
    for repo in repos:
        description = repo.description or "No description provided."
        summary = (
            f"Repository: {repo.name}\n"
            f"Description: {description}\n"
            f"Commit frequency: {repo.commit_frequency} per day\n"
            f"Avg sentiment: {repo.avg_sentiment}\n"
            f"Burnout risk: {repo.burnout_risk}\n"
            f"Total commits: {repo.total_commits}\n"
            f"Authors: {repo.total_authors}"
        )
        docs.append(
            Document(
                page_content=summary,
                metadata={
                    "type": "repository",
                    "repo": repo.name,
                    "burnout_risk": repo.burnout_risk,
                    "commit_frequency": repo.commit_frequency,
                },
            )
        )

    return docs



@assistant_bp.route('/reindex', methods=['POST'])
@login_required
def reindex():
    """Rebuild the user's vector store."""
    # Fully remove existing vector store to avoid stale collection errors
    user_dir = os.path.join(VECTOR_DIR, str(current_user.id))
    if os.path.exists(user_dir):
        import shutil
        shutil.rmtree(user_dir)

    vectordb = _get_vectordb(current_user.id)

    docs = _build_documents(current_user.id)
    if docs:
        vectordb.add_documents(docs)
        vectordb.persist()
    return jsonify({"status": "ok", "documents_indexed": len(docs)})


@assistant_bp.route('/chat', methods=['POST'])
@login_required
def chat():
    user_msg = request.json.get('message', '')
    if not user_msg:
        return jsonify({"error": "message required"}), 400

    vectordb = _get_vectordb(current_user.id)
    retriever = vectordb.as_retriever(search_kwargs={"k": 15})
    print("Retrieved documents:", retriever)

    # Set up LLM
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=gemini_key, temperature=0.3)
    else:
        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)

    # Custom prompt to encourage grounded answers
    QA_PROMPT = PromptTemplate(
        input_variables=["context", "question"],
        template=(
            "You are DevWell Assistant, an AI helping a developer reflect on their activity. "
            "Use ONLY the information in the context below to answer the question. "
            "If the context is empty or insufficient, reply with 'I don't have enough information from your recent activity to answer that.'\n\n"
            "Context:\n{context}\n\nQuestion: {question}\nAnswer:"),
    )

    qa = RetrievalQA.from_chain_type(
        llm,
        chain_type="stuff",
        retriever=retriever,
        chain_type_kwargs={"prompt": QA_PROMPT},
    )

    answer = ""
    answer = qa.run(user_msg)
    print("Answer:", answer)
    return jsonify({"answer": answer})
