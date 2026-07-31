"""
Tests for V4 task 2: MedGemma vision adapter + LLM_BACKEND routing for
/analyze-document (previously hardcoded to Gemini regardless of backend).

Run: pytest tests/test_v4_vision.py -v
"""
import sys
import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))


def run(coro):
    return asyncio.run(coro)


# ── generate_vision_response routing ────────────────────────────────────────

def test_ollama_backend_routes_images_to_ollama_vision(monkeypatch):
    import server
    monkeypatch.setattr(server, "LLM_BACKEND", "ollama")
    mock = AsyncMock(return_value="local vision answer")
    monkeypatch.setattr(server, "_ollama_generate_vision", mock)

    result = run(server.generate_vision_response(b"fakeimgbytes", "image/png", "prompt", "sys"))
    mock.assert_called_once_with(b"fakeimgbytes", "prompt", "sys")
    assert result == "local vision answer"


def test_ollama_backend_still_routes_pdfs_to_gemini(monkeypatch):
    """Ollama vision models take image bytes only — PDFs always go to Gemini
    regardless of LLM_BACKEND, until PDF-to-image conversion exists."""
    import server
    monkeypatch.setattr(server, "LLM_BACKEND", "ollama")
    ollama_mock = AsyncMock(return_value="should not be called")
    gemini_mock = AsyncMock(return_value="gemini pdf answer")
    monkeypatch.setattr(server, "_ollama_generate_vision", ollama_mock)
    monkeypatch.setattr(server, "_gemini_generate_vision", gemini_mock)

    result = run(server.generate_vision_response(b"fakepdfbytes", "application/pdf", "prompt", "sys"))
    ollama_mock.assert_not_called()
    gemini_mock.assert_called_once_with(b"fakepdfbytes", "application/pdf", "prompt", "sys")
    assert result == "gemini pdf answer"


def test_gemini_backend_used_by_default(monkeypatch):
    import server
    monkeypatch.setattr(server, "LLM_BACKEND", "gemini")
    mock = AsyncMock(return_value="gemini answer")
    monkeypatch.setattr(server, "_gemini_generate_vision", mock)

    result = run(server.generate_vision_response(b"fakeimgbytes", "image/png", "prompt", "sys"))
    mock.assert_called_once_with(b"fakeimgbytes", "image/png", "prompt", "sys")
    assert result == "gemini answer"


# ── _ollama_generate_vision HTTP payload shape ──────────────────────────────

def test_ollama_vision_sends_image_in_payload(monkeypatch):
    import server
    monkeypatch.setenv("OLLAMA_VISION_MODEL", "medgemma")

    captured = {}

    class FakeResponse:
        def raise_for_status(self): pass
        def json(self): return {"message": {"content": "findings here"}}

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, url, json=None):
            captured["url"] = url
            captured["payload"] = json
            return FakeResponse()

    with patch("httpx.AsyncClient", return_value=FakeClient()):
        result = run(server._ollama_generate_vision(b"rawbytes", "describe this x-ray", "sys msg"))

    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["payload"]["model"] == "medgemma"
    msg = captured["payload"]["messages"][1]
    assert msg["role"] == "user"
    assert msg["content"] == "describe this x-ray"
    assert "images" in msg
    assert len(msg["images"]) == 1
    assert result == "findings here"


def test_ollama_vision_connect_error_gives_clear_message():
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
            run(server._ollama_generate_vision(b"bytes", "prompt", "sys"))
    assert exc.value.status_code == 503
    assert "ollama serve" in exc.value.detail.lower()
