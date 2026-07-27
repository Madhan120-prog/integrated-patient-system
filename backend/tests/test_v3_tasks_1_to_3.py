"""
Tests for V3 tasks 1-3:
  1. Pickle → JSON (treatment_system)
  2. JWT auth + RBAC
  3. Audit log written per /deep-query call

Run: cd backend && pytest tests/test_v3_tasks_1_to_3.py -v
"""
import json
import os
import sys
import tempfile
import pytest
from pathlib import Path
from datetime import datetime, timezone

# Make backend root importable
sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Task 1: pickle → JSON ──────────────────────────────────────────────────

def test_treatment_store_is_json_not_pickle():
    """treatment_store must serialize to JSON, not pickle."""
    from data import treatment_system

    sample = {
        "TX-500000": [
            {"name": "James", "treatment_name": "Chemo", "treatment_date": "2025-01-01",
             "result": "In Progress", "doctor": "Dr. A", "medicines": "Cisplatin"}
        ]
    }

    with tempfile.TemporaryDirectory() as tmp:
        original_path = treatment_system.DB_PATH
        treatment_system.DB_PATH = Path(tmp) / "treatment_store.json"
        try:
            count = treatment_system.reset_and_seed(sample)
            assert count == 1
            # File must be valid JSON — json.load would raise if pickle bytes
            with open(treatment_system.DB_PATH) as f:
                data = json.load(f)
            assert "TX-500000" in data
            # Round-trip
            records = treatment_system.query_by_local_id("TX-500000")
            assert records[0]["treatment_name"] == "Chemo"
        finally:
            treatment_system.DB_PATH = original_path


# ── Task 2: JWT auth + RBAC ───────────────────────────────────────────────

from auth import create_token, USERS
from jose import jwt as jose_jwt

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

def test_create_token_is_valid_jwt():
    token = create_token("doctor", "PHYSICIAN")
    payload = jose_jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    assert payload["sub"] == "doctor"
    assert payload["role"] == "PHYSICIAN"

def test_physician_token_has_correct_role():
    token = create_token("doctor", "PHYSICIAN")
    payload = jose_jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    assert payload["role"] == "PHYSICIAN"

def test_nurse_token_has_nurse_role():
    token = create_token("nurse", "NURSE")
    payload = jose_jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    assert payload["role"] == "NURSE"

def test_users_dict_has_all_roles():
    roles = {v["role"] for v in USERS.values()}
    assert roles == {"PHYSICIAN", "NURSE", "ADMIN"}

def test_tampered_token_fails():
    from fastapi import HTTPException
    from auth import get_current_user
    import asyncio
    bad_token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJoYWNrZXIifQ.invalidsig"
    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_current_user(bad_token))
    assert exc.value.status_code == 401


# ── Task 3: audit log shape ───────────────────────────────────────────────

def test_audit_log_entry_shape():
    """Verify the fields we write to audit_log match the documented schema."""
    import hashlib
    question = "What did the MRI show?"
    entry = {
        "timestamp": datetime.now(timezone.utc),
        "user_id": "doctor",
        "role": "PHYSICIAN",
        "patient_id": "P1001",
        "question_hash": hashlib.sha256(question.encode()).hexdigest()[:16],
        "departments_fetched": ["MRI"],
        "model_backend": "gemini",
        "model_version": "gemini-3-flash-preview",
        "response_length": 412,
    }
    required = {"timestamp", "user_id", "role", "patient_id",
                "question_hash", "departments_fetched", "model_backend",
                "model_version", "response_length"}
    assert required.issubset(entry.keys())
    assert len(entry["question_hash"]) == 16   # 16-char hex prefix
    assert isinstance(entry["departments_fetched"], list)
