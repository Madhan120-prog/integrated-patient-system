"""
RAG over the 6 federated department databases — semantic retrieval to
complement the keyword-based smart-context router in server.py.

Why this exists: keyword matching misses synonyms ("blood cell count" won't
match the "wbc" keyword), so a real question can silently fetch zero
departments. This module embeds every record at seed time and does a
patient-scoped similarity search at query time, as a fallback specifically
for questions the keyword classifier can't place.

Local embeddings (sentence-transformers) and a local vector store (Chroma) —
no external API call, consistent with the project's on-prem/PHI-never-leaves-
the-machine story. Patient record text should not hit a cloud embedding API
even "just for search."

Security-critical: every query MUST filter by patient_id before/during
ranking, never after. Searching across all patients' embeddings and trusting
similarity alone to keep them separate would be a real cross-patient PHI leak.
"""
import os
from pathlib import Path

CHROMA_DIR = Path(__file__).parent / "data" / "chroma_store"
COLLECTION_NAME = "patient_records"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# Cosine distance ranges [0, 2], 0 = identical direction. Chroma's nearest-
# neighbor search always returns the top-K closest vectors regardless of how
# close they actually are — it has no built-in "nothing is relevant" case.
# Verified live: a casual message ("how are you doing today?") that missed
# the greeting detector still got real patient records injected, because
# retrieval had no relevance floor. This threshold is that floor — anything
# less similar than this is treated as "no relevant match," same as an empty
# result. Heuristic, not derived from a formula — tune down (stricter) if
# off-topic messages still pull data, tune up (looser) if real questions
# start coming back empty.
MAX_DISTANCE = 0.75

_embedding_model = None
_chroma_client = None
_collection = None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def _get_collection():
    global _chroma_client, _collection
    if _collection is None:
        import chromadb
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        # cosine space must be set at creation time — sentence embeddings are
        # compared by direction, not raw distance, and this makes MAX_DISTANCE
        # a meaningful, bounded threshold instead of an unbounded L2 value.
        _collection = _chroma_client.get_or_create_collection(
            COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )
    return _collection


# ── Record → text (pure, no ML — easily testable) ──────────────────────────────

def record_to_text(record: dict, department: str) -> str:
    """Build one embeddable text string per record. Treatment records use a
    different field shape (treatment_name/treatment_date/medicines) than the
    other five departments (test_name/test_date/result) — normalize both into
    one consistent sentence so they embed comparably."""
    if department == "Treatment":
        name = record.get("treatment_name", "")
        date = record.get("treatment_date", "")
        detail = record.get("result", "")
        medicines = record.get("medicines", "")
        return f"{department} — {name} ({date}): {detail}. Medicines: {medicines}".strip()
    name = record.get("test_name", "")
    date = record.get("test_date", "")
    detail = record.get("result", "")
    return f"{department} — {name} ({date}): {detail}".strip()


def build_record_id(patient_id: str, department: str, index: int) -> str:
    """Deterministic, stable ID for upsert — records have no persistent ID of
    their own, so this is generated from position within a patient+department
    group. Stable across rebuilds as long as seed data stays deterministic."""
    return f"{patient_id}::{department}::{index}"


# ── Index building ──────────────────────────────────────────────────────────────

def build_rag_index(records_by_department: dict) -> int:
    """records_by_department: {"MRI": [...], "Blood Profile": [...], ...} —
    already-normalized records from get_all_records() on each gateway, each
    with patient_id attached. Returns the number of records indexed."""
    collection = _get_collection()
    model = _get_embedding_model()

    documents, metadatas, ids = [], [], []
    for department, records in records_by_department.items():
        counters = {}
        for record in records:
            patient_id = record["patient_id"]
            idx = counters.get(patient_id, 0)
            counters[patient_id] = idx + 1
            documents.append(record_to_text(record, department))
            metadatas.append({
                "patient_id": patient_id,
                "department": department,
                "date": record.get("test_date") or record.get("treatment_date", ""),
            })
            ids.append(build_record_id(patient_id, department, idx))

    if not documents:
        return 0

    # Chroma caps upsert() at a max batch size (varies by version/hardware,
    # seen 5461 in testing) — chunk well under that rather than hardcoding
    # its exact limit, which isn't part of Chroma's public contract.
    BATCH_SIZE = 1000
    embeddings = model.encode(documents).tolist()
    for start in range(0, len(documents), BATCH_SIZE):
        end = start + BATCH_SIZE
        collection.upsert(
            ids=ids[start:end],
            embeddings=embeddings[start:end],
            documents=documents[start:end],
            metadatas=metadatas[start:end],
        )
    return len(documents)


def reset_index():
    """Drop and recreate the collection — call before a full reseed so a
    stale index from a previous run's data doesn't linger."""
    global _collection
    import chromadb
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    _collection = client.get_or_create_collection(COLLECTION_NAME)


# ── Query-time retrieval ──────────────────────────────────────────────────────

def retrieve_relevant_records(question: str, patient_id: str, top_k: int = 6) -> list[dict]:
    """Patient-scoped semantic search — the where filter runs at query time,
    not as a post-filter, so this never ranks against another patient's data.

    Results past MAX_DISTANCE are dropped — nearest-neighbor search always
    returns its top-K closest vectors even when none of them are actually
    relevant, so this is what lets an off-topic message correctly get back
    "nothing relevant" instead of whatever happened to be closest."""
    collection = _get_collection()
    model = _get_embedding_model()
    query_embedding = model.encode([question]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        where={"patient_id": patient_id},
        include=["documents", "metadatas", "distances"],
    )
    if not results["documents"] or not results["documents"][0]:
        return []
    return [
        {"text": doc, **meta}
        for doc, meta, distance in zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0]
        )
        if distance <= MAX_DISTANCE
    ]
