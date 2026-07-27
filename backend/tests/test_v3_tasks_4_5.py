"""
Tests for V3 tasks 4-5: LLM_BACKEND routing + Ollama path.

Run: cd backend && pytest tests/test_v3_tasks_4_5.py -v
"""
import sys
import os
import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))


def run(coro):
    return asyncio.run(coro)


# ── Task 4: LLM_BACKEND routing ───────────────────────────────────────────

def test_gemini_backend_called_by_default(monkeypatch):
    import server
    monkeypatch.setattr(server, "LLM_BACKEND", "gemini")
    mock = AsyncMock(return_value="gemini answer")
    monkeypatch.setattr(server, "_gemini_generate", mock)
    result = run(server.generate_response("prompt", "system"))
    mock.assert_called_once_with("prompt", "system")
    assert result == "gemini answer"


def test_ollama_backend_called_when_set(monkeypatch):
    import server
    monkeypatch.setattr(server, "LLM_BACKEND", "ollama")
    mock = AsyncMock(return_value="ollama answer")
    monkeypatch.setattr(server, "_ollama_generate", mock)
    result = run(server.generate_response("prompt", "system"))
    mock.assert_called_once_with("prompt", "system")
    assert result == "ollama answer"


def test_azure_backend_called_when_set(monkeypatch):
    import server
    monkeypatch.setattr(server, "LLM_BACKEND", "azure")
    mock = AsyncMock(return_value="azure answer")
    monkeypatch.setattr(server, "_azure_generate", mock)
    result = run(server.generate_response("prompt", "system"))
    mock.assert_called_once_with("prompt", "system")
    assert result == "azure answer"


# ── Task 5: Ollama HTTP call shape ───────────────────────────────────────

def test_ollama_sends_correct_payload(monkeypatch):
    """Ollama request must include model, messages with system+user roles."""
    import server
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2")

    captured = {}

    class FakeResponse:
        def raise_for_status(self): pass
        def json(self): return {"message": {"content": "test response"}}

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, url, json=None):
            captured["url"] = url
            captured["payload"] = json
            return FakeResponse()

    with patch("httpx.AsyncClient", return_value=FakeClient()):
        result = run(server._ollama_generate("user question", "system msg"))

    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["payload"]["model"] == "llama3.2"
    assert captured["payload"]["stream"] is False
    msgs = captured["payload"]["messages"]
    assert msgs[0] == {"role": "system", "content": "system msg"}
    assert msgs[1] == {"role": "user", "content": "user question"}
    assert result == "test response"


def test_ollama_connect_error_gives_clear_message():
    """If Ollama isn't running, error message must guide the user."""
    import httpx
    from fastapi import HTTPException
    import server

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, *a, **kw):
            raise httpx.ConnectError("connection refused")

    with patch("httpx.AsyncClient", return_value=FakeClient()):
        with pytest.raises(HTTPException) as exc:
            run(server._ollama_generate("q", "sys"))
    assert exc.value.status_code == 503
    assert "ollama serve" in exc.value.detail.lower()
