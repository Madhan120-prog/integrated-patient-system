"""
Tests for V4 task 1: RAG over the 6 federated department databases.

Pure functions (record_to_text, build_record_id) are tested directly.
retrieve_relevant_records/build_rag_index are tested with the embedding
model and Chroma collection mocked out — no real model download or vector
store needed, consistent with how the rest of this test suite mocks the LLM
backends rather than hitting them for real.

Run: pytest tests/test_v4_rag.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import rag


# ── record_to_text ─────────────────────────────────────────────────────────────

def test_record_to_text_standard_department():
    record = {"test_name": "Tumor Marker Panel", "test_date": "2025-09-01",
              "result": "CA 15-3 normalized (22 U/mL)"}
    text = rag.record_to_text(record, "Blood Profile")
    assert "Blood Profile" in text
    assert "Tumor Marker Panel" in text
    assert "2025-09-01" in text
    assert "CA 15-3 normalized" in text


def test_record_to_text_treatment_department_uses_different_fields():
    record = {"treatment_name": "Chemotherapy — Paclitaxel Cycle 1", "treatment_date": "2025-09-02",
              "result": "Completed", "medicines": "Paclitaxel 80mg/m² weekly"}
    text = rag.record_to_text(record, "Treatment")
    assert "Paclitaxel Cycle 1" in text
    assert "2025-09-02" in text
    assert "Paclitaxel 80mg/m² weekly" in text


# ── build_record_id ────────────────────────────────────────────────────────────

def test_build_record_id_deterministic():
    id1 = rag.build_record_id("P1002", "Blood Profile", 0)
    id2 = rag.build_record_id("P1002", "Blood Profile", 0)
    assert id1 == id2


def test_build_record_id_unique_per_index():
    id0 = rag.build_record_id("P1002", "Blood Profile", 0)
    id1 = rag.build_record_id("P1002", "Blood Profile", 1)
    assert id0 != id1


def test_build_record_id_unique_per_patient():
    a = rag.build_record_id("P1001", "Blood Profile", 0)
    b = rag.build_record_id("P1002", "Blood Profile", 0)
    assert a != b


# ── retrieve_relevant_records (mocked embedding + Chroma) ──────────────────────

class _FakeEmbeddings(list):
    """Mimics the numpy array real sentence-transformers returns — just
    needs .tolist() since that's the only method rag.py calls on it."""
    def tolist(self):
        return list(self)


class _FakeModel:
    def encode(self, texts):
        return _FakeEmbeddings([0.1, 0.2, 0.3] for _ in texts)


class _FakeCollection:
    def __init__(self, query_result=None):
        self._query_result = query_result or {"documents": [[]], "metadatas": [[]]}
        self.last_where = None
        self.upsert_calls = []  # list of batch sizes, one entry per upsert() call
        self.all_upserted_ids = []

    def query(self, query_embeddings, n_results, where, include=None):
        self.last_where = where
        return self._query_result

    def upsert(self, ids, embeddings, documents, metadatas):
        self.upserted = {"ids": ids, "documents": documents, "metadatas": metadatas}
        self.upsert_calls.append(len(ids))
        self.all_upserted_ids.extend(ids)


def test_retrieve_filters_by_patient_id(monkeypatch):
    fake_collection = _FakeCollection({
        "documents": [["Blood Profile — WBC (2025-01-01): normal"]],
        "metadatas": [[{"patient_id": "P1002", "department": "Blood Profile", "date": "2025-01-01"}]],
        "distances": [[0.1]],
    })
    monkeypatch.setattr(rag, "_get_collection", lambda: fake_collection)
    monkeypatch.setattr(rag, "_get_embedding_model", lambda: _FakeModel())

    rag.retrieve_relevant_records("what's her wbc", "P1002", top_k=6)
    assert fake_collection.last_where == {"patient_id": "P1002"}


def test_retrieve_returns_parsed_records(monkeypatch):
    fake_collection = _FakeCollection({
        "documents": [["Blood Profile — WBC (2025-01-01): normal"]],
        "metadatas": [[{"patient_id": "P1002", "department": "Blood Profile", "date": "2025-01-01"}]],
        "distances": [[0.1]],
    })
    monkeypatch.setattr(rag, "_get_collection", lambda: fake_collection)
    monkeypatch.setattr(rag, "_get_embedding_model", lambda: _FakeModel())

    results = rag.retrieve_relevant_records("what's her wbc", "P1002", top_k=6)
    assert len(results) == 1
    assert results[0]["department"] == "Blood Profile"
    assert results[0]["text"] == "Blood Profile — WBC (2025-01-01): normal"


def test_retrieve_empty_results_returns_empty_list(monkeypatch):
    fake_collection = _FakeCollection({"documents": [[]], "metadatas": [[]], "distances": [[]]})
    monkeypatch.setattr(rag, "_get_collection", lambda: fake_collection)
    monkeypatch.setattr(rag, "_get_embedding_model", lambda: _FakeModel())

    results = rag.retrieve_relevant_records("anything", "P9999", top_k=6)
    assert results == []


def test_retrieve_drops_results_past_max_distance(monkeypatch):
    """Regression test: an off-topic message ('how are you doing today?')
    still got real patient records injected before this threshold existed,
    because nearest-neighbor search always returns its top-K closest vectors
    even when none of them are actually relevant to the question."""
    fake_collection = _FakeCollection({
        "documents": [["Blood Profile — WBC (2025-01-01): normal", "Treatment — Chemo (2025-01-01): done"]],
        "metadatas": [[
            {"patient_id": "P1002", "department": "Blood Profile", "date": "2025-01-01"},
            {"patient_id": "P1002", "department": "Treatment", "date": "2025-01-01"},
        ]],
        "distances": [[0.2, 1.4]],  # first is close, second is far past MAX_DISTANCE
    })
    monkeypatch.setattr(rag, "_get_collection", lambda: fake_collection)
    monkeypatch.setattr(rag, "_get_embedding_model", lambda: _FakeModel())

    results = rag.retrieve_relevant_records("how are you doing today?", "P1002", top_k=6)
    assert len(results) == 1
    assert results[0]["department"] == "Blood Profile"


def test_retrieve_all_results_past_threshold_returns_empty(monkeypatch):
    fake_collection = _FakeCollection({
        "documents": [["MRI — Brain scan (2025-01-01): normal"]],
        "metadatas": [[{"patient_id": "P1002", "department": "MRI", "date": "2025-01-01"}]],
        "distances": [[1.9]],
    })
    monkeypatch.setattr(rag, "_get_collection", lambda: fake_collection)
    monkeypatch.setattr(rag, "_get_embedding_model", lambda: _FakeModel())

    results = rag.retrieve_relevant_records("totally unrelated small talk", "P1002", top_k=6)
    assert results == []


# ── build_rag_index (mocked) ────────────────────────────────────────────────────

def test_build_rag_index_counts_all_records(monkeypatch):
    fake_collection = _FakeCollection()
    monkeypatch.setattr(rag, "_get_collection", lambda: fake_collection)
    monkeypatch.setattr(rag, "_get_embedding_model", lambda: _FakeModel())

    records_by_department = {
        "Blood Profile": [
            {"patient_id": "P1002", "test_name": "CBC", "test_date": "2025-01-01", "result": "normal"},
            {"patient_id": "P1002", "test_name": "CBC", "test_date": "2025-02-01", "result": "normal"},
        ],
        "Treatment": [
            {"patient_id": "P1002", "treatment_name": "Chemo", "treatment_date": "2025-01-01",
             "result": "Completed", "medicines": "Paclitaxel"},
        ],
    }
    count = rag.build_rag_index(records_by_department)
    assert count == 3
    assert len(fake_collection.upserted["ids"]) == 3


def test_build_rag_index_empty_input_returns_zero(monkeypatch):
    fake_collection = _FakeCollection()
    monkeypatch.setattr(rag, "_get_collection", lambda: fake_collection)
    monkeypatch.setattr(rag, "_get_embedding_model", lambda: _FakeModel())

    count = rag.build_rag_index({"Blood Profile": []})
    assert count == 0


def test_build_rag_index_chunks_large_batches(monkeypatch):
    """Regression test: a real seed (500 patients x 6 departments) produced
    7129 records in one call, but Chroma's upsert() rejects batches over its
    max size (5461 in the version tested) — hit this live before it was fixed."""
    fake_collection = _FakeCollection()
    monkeypatch.setattr(rag, "_get_collection", lambda: fake_collection)
    monkeypatch.setattr(rag, "_get_embedding_model", lambda: _FakeModel())

    records = [
        {"patient_id": f"P{i}", "test_name": "CBC", "test_date": "2025-01-01", "result": "normal"}
        for i in range(2500)
    ]
    count = rag.build_rag_index({"Blood Profile": records})

    assert count == 2500
    assert len(fake_collection.all_upserted_ids) == 2500
    assert all(size <= 1000 for size in fake_collection.upsert_calls)
    assert len(fake_collection.upsert_calls) > 1
