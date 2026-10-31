"""
Tests for V5 saved work: each doctor's DocAssist work is kept, private by default,
and readable by a colleague only after the owner shares it. Uses a throwaway
database on the local MongoDB; skipped when MongoDB is not running.

Run: pytest tests/test_v5_workspace.py -v
"""
import socket
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient

import server
from auth import create_token

try:
    socket.create_connection(("localhost", 27017), timeout=0.5).close()
except OSError:
    pytest.skip("MongoDB is not running", allow_module_level=True)

TEST_DB = "ips_test_workspace"
AS = {u: {"Authorization": f"Bearer {create_token(u, r)}"}
      for u, r in [("doctor", "PHYSICIAN"), ("doctor2", "PHYSICIAN"), ("nurse", "NURSE")]}


@pytest.fixture
def api(monkeypatch):
    with TestClient(server.app) as client:
        mongo = AsyncIOMotorClient("mongodb://localhost:27017")
        monkeypatch.setattr(server, "db", mongo[TEST_DB])
        client.portal.call(mongo.drop_database, TEST_DB)
        yield client
        client.portal.call(mongo.drop_database, TEST_DB)


def save(api, owner, question):
    return api.portal.call(server.save_work, {"username": owner}, "P1001", "question", question, "An answer.",
                           [{"test_date": "2026-09-01", "test_name": "CT Chest", "result": "not kept"}], "test-model")


def test_work_is_saved_and_private_until_shared(api):
    save(api, "doctor", "What's concerning?")
    mine = api.get("/api/workspace/P1001", headers=AS["doctor"]).json()
    assert [t["question"] for t in mine["mine"]] == ["What's concerning?"]
    assert mine["mine"][0]["records"] == [{"date": "2026-09-01", "name": "CT Chest"}]   # a reference, not a copy
    assert mine["colleagues"] == [{"username": "doctor2", "name": "Dr. Patel"}]

    other = api.get("/api/workspace/P1001", headers=AS["doctor2"]).json()
    assert other["mine"] == [] and other["shared_with_me"] == []

    assert api.put("/api/workspace/P1001/sharing", json={"shared_with": ["doctor2"]}, headers=AS["doctor"]).status_code == 200
    other = api.get("/api/workspace/P1001", headers=AS["doctor2"]).json()
    assert other["shared_with_me"][0]["name"] == "Dr. Smith"
    assert other["shared_with_me"][0]["turns"][0]["question"] == "What's concerning?"
    assert api.get("/api/workspace/P1002", headers=AS["doctor2"]).json()["shared_with_me"] == []   # one patient only

    api.put("/api/workspace/P1001/sharing", json={"shared_with": []}, headers=AS["doctor"])
    assert api.get("/api/workspace/P1001", headers=AS["doctor2"]).json()["shared_with_me"] == []

    log = api.portal.call(lambda: server.db.audit_log.find({"action": {"$exists": True}}, {"_id": 0}).to_list(10))
    assert [e["action"] for e in log] == ["changed sharing", "viewed shared work", "changed sharing"]


def test_sharing_only_with_other_physicians_and_physicians_only(api):
    for bad in (["nurse"], ["doctor"], ["nobody"]):
        assert api.put("/api/workspace/P1001/sharing", json={"shared_with": bad}, headers=AS["doctor"]).status_code == 400
    assert api.get("/api/workspace/P1001", headers=AS["nurse"]).status_code == 403


def test_save_to_chart_needs_review_and_keeps_the_ai_original(api):
    api.portal.call(lambda: server.db.profiles.insert_one({"patient_id": "P1001"}))
    work_id = save(api, "doctor", "What's concerning?")
    url = "/api/chart-notes/P1001"
    assert api.post(url, json={"text": "An answer.", "work_id": work_id}, headers=AS["doctor"]).status_code == 400   # not reviewed
    assert api.post(url, json={"text": "x", "work_id": work_id, "reviewed": True}, headers=AS["doctor2"]).status_code == 404  # not their work
    assert api.post(url, json={"text": "x"}, headers=AS["nurse"]).status_code == 403

    note = api.post(url, json={"text": "An answer, checked.", "work_id": work_id, "reviewed": True}, headers=AS["doctor"]).json()
    assert note["author_name"] == "Dr. Smith" and note["ai"]["original"] == "An answer." and note["ai"]["edited"]
    assert note["ai"]["model"] == "test-model" and note["ai"]["records"] == [{"date": "2026-09-01", "name": "CT Chest"}]
    unchanged = api.post(url, json={"text": "An answer.", "work_id": work_id, "reviewed": True}, headers=AS["doctor"]).json()
    assert unchanged["ai"]["edited"] is False

    assert [n["text"] for n in api.get(url, headers=AS["nurse"]).json()] == ["An answer.", "An answer, checked."]  # the whole care team reads the chart
    assert api.get("/api/workspace/P1001", headers=AS["doctor"]).json()["mine"][0]["note_id"] == unchanged["id"]


def test_decision_trail_says_who_started_it_and_what_changed(api):
    api.portal.call(lambda: server.db.profiles.insert_one({"patient_id": "P1001"}))
    asked = api.portal.call(server.save_work, {"username": "doctor"}, "P1001", "question", "Next step?",
                            "Start carboplatin at full dose.", [], "test-model", "suggestion")
    save(api, "doctor", "Never saved")
    url = "/api/chart-notes/P1001"
    api.post(url, json={"text": "Start carboplatin at reduced dose.", "work_id": asked, "reviewed": True,
                        "reason": "Kidney function"}, headers=AS["doctor"])
    api.post(url, json={"text": "Seen in clinic."}, headers=AS["doctor"])

    out = api.get("/api/decision-trail/P1001", headers=AS["doctor"]).json()
    assert out["summary"] == {"doctor_led": 1, "ai_edited": 1, "ai_unchanged": 0, "ai_answers_not_used": 1}
    own, edited = out["notes"]
    assert own["origin"] == "Doctor-led" and len(own["steps"]) == 1
    assert edited["origin"] == "AI-assisted, doctor edited"
    assert "suggested questions" in edited["steps"][0]["what"] and "Kidney function" in edited["steps"][2]["what"]
    assert ["removed", "full"] in edited["diff"] and ["added", "reduced"] in edited["diff"]
    assert api.get("/api/decision-trail/P1001", headers=AS["nurse"]).status_code == 403


def test_prints_and_downloads_are_audited(api):
    assert api.post("/api/export-log/P1001", json={"what": "printed chart"}, headers=AS["nurse"]).status_code == 200
    assert api.post("/api/export-log/P1001", json={"what": "anything"}, headers=AS["nurse"]).status_code == 400
    log = api.portal.call(lambda: server.db.audit_log.find({}, {"_id": 0}).to_list(10))
    assert [(e["user_id"], e["action"]) for e in log] == [("nurse", "printed chart")]
