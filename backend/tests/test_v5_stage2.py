"""
Tests for V5 stage 2: chart assembly (timeline, lab flowsheet, out-of-range list)
built from real seed data, exactly as the gateways would return it.

Run: pytest tests/test_v5_stage2.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date, datetime, timedelta

from chart import build_chart, estimate_upcoming, SOURCE_SYSTEMS
from data.seed import build_seed_data

TODAY = date(2026, 10, 8)
SEED = build_seed_data(today=datetime(2026, 10, 8))
COLLECTION = {"Blood Profile": "blood_profile_records", "MRI": "mri_records", "X-Ray": "xray_records",
              "CT Scan": "ct_scan_records", "ECG": "ecg_records", "Treatment": "treatment_records"}


def chart_for(pid):
    profile = next(p for p in SEED["profiles"] if p["patient_id"] == pid)
    records = {dept: [r for r in SEED[coll] if r["patient_id"] == pid] for dept, coll in COLLECTION.items()}
    logs = [v for v in SEED["visit_logs"] if v["patient_id"] == pid]
    return build_chart(profile, records, today=TODAY, visit_logs=logs), records


def test_timeline_holds_every_record_once_newest_first_with_a_labelled_source():
    chart, records = chart_for("P1002")
    assert len(chart["timeline"]) == sum(len(r) for r in records.values())
    dates = [i["date"] for i in chart["timeline"]]
    assert dates == sorted(dates, reverse=True) and all(dates)
    assert all(i["title"] and i["system"] in SOURCE_SYSTEMS.values() for i in chart["timeline"])
    assert len(set(SOURCE_SYSTEMS.values())) == 6                # six departments, six separate labels
    treatment = next(i for i in chart["timeline"] if i["department"] == "Treatment")
    assert treatment["medicines"] and treatment["system"] == "Treatment"
    assert next(i for i in chart["timeline"] if i["department"] == "Blood Profile")["system"] == "Blood Test"


def test_flowsheet_rows_are_analytes_and_columns_are_dates():
    flow = chart_for("P1002")[0]["flowsheet"]
    assert flow["dates"] == sorted(flow["dates"])
    rows = {r["analyte"]: r for r in flow["rows"]}
    assert [r["analyte"] for r in flow["rows"]][:4] == ["WBC", "ANC", "Hgb", "PLT"]     # clinical order, not alphabetical
    hgb = rows["Hgb"]
    first, last = min(hgb["cells"]), max(hgb["cells"])
    assert hgb["cells"][first] == {"value": 13.4, "status": "IN RANGE"}
    assert hgb["cells"][last] == {"value": 10.2, "status": "LOW"}
    assert hgb["trend"] == {"direction": "↓", "pct_change": -23.9, "size": "MODERATE CHANGE"}
    assert (hgb["unit"], hgb["low"], hgb["high"]) == ("g/dL", 12.0, 17.5)
    ca = rows["CA 15-3"]
    assert [c["status"] for _, c in sorted(ca["cells"].items())] == ["HIGH", "HIGH", "IN RANGE", "IN RANGE"]   # 38, 31, 26, 22
    assert len(hgb["cells"]) == 5                                                       # a count before each cycle, not just two
    assert set(ca["cells"]) <= set(flow["dates"])
    assert rows["ALT"]["trend"] is None                                                 # one reading: no trend


def test_out_of_range_lists_only_latest_readings_outside_their_range():
    out = {o["analyte"]: o for o in chart_for("P1004")[0]["out_of_range"]}
    assert set(out) == {"ANC", "Hgb", "WBC"}                # CEA and PLT are back in range
    assert out["WBC"]["status"] == "LOW" and out["WBC"]["value"] == 1.8 and out["WBC"]["date"]
    lung = {o["analyte"]: o["status"] for o in chart_for("P1001")[0]["out_of_range"]}
    assert lung == {"ANC": "LOW", "CEA": "HIGH", "WBC": "LOW"}


def test_sources_count_only_systems_that_hold_records():
    chart, records = chart_for("P1008")                     # routine screening: labs and one X-ray only
    assert {s["department"] for s in chart["sources"]} == {d for d, r in records.items() if r}
    assert all(s["system"] == SOURCE_SYSTEMS[s["department"]] and s["records"] > 0 for s in chart["sources"])


def test_chart_works_for_a_patient_without_oncology_fields_or_structured_labs():
    chart, _ = chart_for("P1008")
    assert "diagnosis" not in chart["profile"] and chart["profile"]["name"]
    assert isinstance(chart["flowsheet"]["rows"], list) and isinstance(chart["out_of_range"], list)
    empty = build_chart({"patient_id": "X", "name": "No Records"}, {d: [] for d in COLLECTION})
    assert empty["timeline"] == [] and empty["flowsheet"] == {"dates": [], "rows": []} and empty["sources"] == []


def test_chart_route_is_registered_and_requires_a_login():
    import server
    route = next(r for r in server.app.routes if getattr(r, "path", "") == "/api/chart")
    assert "GET" in route.methods
    assert any(d.call is server.get_current_user for d in route.dependant.dependencies)


# ── Findings and treatment course (computed, no model) ──────────────────────

def test_treatments_are_in_order_given_with_category_status_and_modification_flag():
    tx = chart_for("P1004")[0]["treatments"]
    assert [t["date"] for t in tx] == sorted(t["date"] for t in tx)
    assert (tx[0]["category"], tx[0]["name"], tx[0]["status"]) == ("Surgery", "Right hemicolectomy", "Completed")
    assert all(t["doctor"] == "Dr. Smith" and t["medicines"] for t in tx)     # one row answers "what, how much, by whom"
    delayed = [t for t in tx if t["modified"]]
    assert len(delayed) == 1 and "FOLFOX Cycle 3" in delayed[0]["name"]          # "dose delayed 1 week for neutropenia"
    lung = chart_for("P1001")[0]["treatments"]
    assert lung[-1]["status"] == "In progress" and lung[-1]["category"] == "Immunotherapy"


def test_findings_cover_out_of_range_marker_trend_modification_therapy_imaging_and_absent():
    findings = chart_for("P1001")[0]["findings"]
    by_kind = {}
    for f in findings:
        by_kind.setdefault(f["kind"], []).append(f)
    assert {f["title"] for f in by_kind["out_of_range"]} == {
        "ANC 0.9 K/µL is below range", "CEA 5.2 ng/mL is above range", "WBC 2.1 K/µL is below range"}
    assert by_kind["marker_trend"][0]["title"] == "CEA down 58.4%" and "above range" in by_kind["marker_trend"][0]["detail"]
    assert "dose reduced due to neutropenia" in by_kind["treatment_modified"][0]["detail"]
    assert by_kind["current_therapy"][0]["title"] == "Current: Pembrolizumab maintenance"
    assert by_kind["latest_imaging"][0]["title"] == "Latest imaging: Chest X-Ray"   # 2025-10-22, the newest study
    assert by_kind["stated_absent"][0]["detail"] == "Metastasis"
    assert all(f["tone"] in ("attention", "info", "clear") and f["title"] and f["detail"] for f in findings)


def test_findings_never_state_a_ruled_out_condition_as_present_or_add_severity():
    for pid in ("P1001", "P1002", "P1004"):
        for f in chart_for(pid)[0]["findings"]:
            text = (f["title"] + " " + f["detail"]).lower()
            assert "critical" not in text and "severe" not in text
            if f["kind"] != "stated_absent" and f["kind"] != "latest_imaging":
                assert "metasta" not in text and "recurrence" not in text


def test_findings_are_empty_safe():
    assert build_chart({"patient_id": "X", "name": "No Records"}, {d: [] for d in COLLECTION})["findings"] == []
    screening = chart_for("P1008")[0]
    assert all(f["kind"] in ("latest_imaging", "stated_absent", "out_of_range", "marker_trend") for f in screening["findings"])


def test_chart_text_carries_no_long_dashes():
    import json
    for pid in ("P1001", "P1002", "P1004", "P1003", "P1005"):
        chart = chart_for(pid)[0]
        shown = json.dumps([chart["timeline"], chart["treatments"], chart["findings"]], ensure_ascii=False)
        assert "—" not in shown and "--" not in shown, pid
    assert chart_for("P1001")[0]["timeline"][0]["result"] == "Stable: no new lesions"


# ── Seed dates, visits, medications, estimated next doses ────────────────────

def test_curated_timelines_end_a_few_days_before_the_seed_date_and_keep_their_spacing():
    for pid in ("P1001", "P1002", "P1004", "P1008"):
        dates = [i["date"] for i in chart_for(pid)[0]["timeline"]]
        assert max(dates) == "2026-10-02", pid                      # 6 days before the seed date
    cea = {r["analyte"]: r for r in chart_for("P1001")[0]["flowsheet"]["rows"]}["CEA"]["cells"]
    first, last = sorted(cea)[0], sorted(cea)[-1]
    assert (date.fromisoformat(last) - date.fromisoformat(first)).days == 19 * 7   # week 1 to week 20, as before


def test_generated_patients_are_unchanged_by_the_date_shift_and_the_oncologist_field():
    a = build_seed_data(extra_count=20, today=datetime(2026, 10, 8))
    b = build_seed_data(extra_count=20, today=datetime(2027, 3, 1))
    extras = lambda seed, key: [r for r in seed[key] if int(r["patient_id"][1:]) > 1012]
    for key in ("profiles", "blood_profile_records", "treatment_records", "mri_records"):
        assert extras(a, key) == extras(b, key), key


def test_treatment_records_name_the_treating_oncologist_for_demo_patients():
    for pid in ("P1001", "P1002", "P1004"):
        assert {r["doctor"] for r in SEED["treatment_records"] if r["patient_id"] == pid} == {"Dr. Smith"}
    assert len({r["doctor"] for r in SEED["treatment_records"] if r["patient_id"] == "P1003"}) > 1


def test_visits_group_records_by_date_with_the_doctors_involved():
    chart, records = chart_for("P1004")
    visits = chart["visits"]
    assert [v["date"] for v in visits] == sorted({i["date"] for i in chart["timeline"]}, reverse=True)
    assert sum(len(v["items"]) for v in visits) == sum(len(r) for r in records.values())
    surgery = next(v for v in visits if any("hemicolectomy" in i["title"] for i in v["items"]))
    assert "Dr. Smith" in surgery["doctors"]
    assert all(v["doctors"] == sorted(set(v["doctors"])) for v in visits)
    mine = [v for v in visits if "Dr. Smith" in v["doctors"]]
    assert 0 < len(mine) < len(visits)                               # "My consultations" is a real subset


def test_medications_split_current_from_history_as_written_on_the_record():
    meds = chart_for("P1001")[0]["medications"]
    assert meds["current"] == [{"name": "Pembrolizumab", "dose": "200mg IV q3w", "since": meds["current"][0]["since"],
                                "for": "Immunotherapy: Pembrolizumab maintenance"}]
    history = {m["name"]: m for m in meds["history"]}
    assert history["Cisplatin"]["times_given"] == 4 and history["Cisplatin"]["last_dose"] == "75mg/m²"
    assert history["Filgrastim"]["times_given"] == 1
    colorectal = {m["name"] for m in chart_for("P1004")[0]["medications"]["history"]}
    assert {"5-FU", "Oxaliplatin", "Leucovorin", "General anesthesia"} <= colorectal
    assert chart_for("P1004")[0]["medications"]["current"] == []
    assert chart_for("P1008")[0]["medications"] == {"current": [], "history": []}


def test_upcoming_doses_are_estimated_from_the_interval_and_say_so():
    up = chart_for("P1001")[0]["upcoming"]                           # pembrolizumab q3w, in progress
    start = date.fromisoformat(chart_for("P1001")[0]["medications"]["current"][0]["since"])
    first, second = (date.fromisoformat(i["date"]) for i in up["items"])
    assert first >= TODAY and (first - start).days % 21 == 0 and (first - TODAY).days < 21
    assert (second - first).days == 21
    assert "Not a booked appointment" in up["note"] and "Estimated" in up["note"]
    daily = chart_for("P1002")[0]["upcoming"]                        # tamoxifen daily: nothing to estimate
    assert daily["items"] == [] and "no dosing interval" in daily["note"]
    none = chart_for("P1004")[0]["upcoming"]                         # treatment completed
    assert none["items"] == [] and "No treatment is in progress" in none["note"]
    assert estimate_upcoming([], TODAY)["items"] == []


def test_vitals_care_team_and_problems_for_demo_patients_and_absent_for_others():
    chart = chart_for("P1002")[0]
    v = chart["vitals"]
    assert (v["weight_kg"], v["height_cm"], v["bp"]) == (66, 163, "118/74")
    assert v["bsa_m2"] == 1.73                                   # sqrt(163 * 66 / 3600)
    assert v["recorded"] == max(i["date"] for i in chart["timeline"])
    assert chart["care_team"][0] == {"role": "Medical oncologist", "name": "Dr. Smith"}
    labels = [p["label"] for p in chart["problems"]]
    assert labels[0] == "Invasive ductal carcinoma, left breast" and "Anemia" in labels
    assert "Metastasis" not in labels                             # stated as absent, so not a problem
    plain = chart_for("P1008")[0]
    assert plain["vitals"] is None and plain["care_team"] == [] and isinstance(plain["problems"], list)


# ── DocAssist on the chart: section scope and study analysis ─────────────────

def test_deep_query_accepts_a_section_scope_and_defaults_to_none():
    import server
    assert server.DeepQueryRequest(patient_id="P1", question="q").scope == []
    assert server.DeepQueryRequest(patient_id="P1", question="q", scope=["MRI", "CT Scan"]).scope == ["MRI", "CT Scan"]
    assert set(server.DEPARTMENT_GATEWAYS) == set(server.DEPT_KEYWORDS)     # every scope name maps to a gateway


def test_study_analysis_is_physician_only_and_its_prompt_carries_the_report_not_the_url():
    import server
    route = next(r for r in server.app.routes if getattr(r, "path", "") == "/api/analyze-study")
    assert "POST" in route.methods
    assert any(d.call is server.require_physician for d in route.dependant.dependencies)
    record = next(r for r in SEED["ct_scan_records"] if r["patient_id"] == "P1002")
    prompt = server.study_analysis_prompt(record)
    assert record["result"] in prompt and record["test_name"] in prompt
    assert "http" not in prompt and record["report_image"] not in prompt
    assert "Do not diagnose" in prompt and "Against the report:" in prompt


# ── Visit recordings ─────────────────────────────────────────────────────────

def test_transcript_turns_voice_ids_into_stable_role_labels():
    import json, server
    raw = "```json\n" + json.dumps({
        "voices": [{"id": "V1", "role": "Doctor", "basis": "asks the clinical questions"},
                   {"id": "V2", "role": "Patient", "basis": "describes symptoms"},
                   {"id": "V3", "role": "Other", "basis": "daughter"}, {"id": "V4", "role": "Other", "basis": "nurse"},
                   {"id": "V5", "role": "Robot", "basis": ""}],
        "segments": [{"start": "00:00", "voice": "V1", "text": " How have you been since the last cycle? "},
                     {"start": "00:05", "voice": "V2", "text": "Tired. Can I ask, is that normal?"},   # a patient asking is still the patient
                     {"start": "00:11", "voice": "V1", "text": "Yes."}, {"start": "00:13", "voice": "V3", "text": "She naps a lot."},
                     {"start": "00:16", "voice": "V4", "text": "Vitals are done."}, {"start": "00:18", "voice": "V5", "text": "..."},
                     {"start": "00:20", "voice": "V2", "text": "   "}],
        "summary": ["Fatigue discussed"] * 9}) + "\n```"
    t = server.parse_transcript(raw)
    assert [seg["speaker"] for seg in t["segments"]] == ["Doctor", "Patient", "Doctor", "Other 1", "Other 2", "Unclear"]
    assert t["segments"][0]["text"] == "How have you been since the last cycle?"      # trimmed; the empty segment is dropped
    assert len(t["summary"]) == 5 and "labelled by AI" in t["note"]
    assert {sp["label"] for sp in t["speakers"]} == {"Doctor", "Patient", "Other 1", "Other 2", "Unclear"}


def test_transcript_rejects_output_it_cannot_trust():
    import pytest, server
    from fastapi import HTTPException
    for bad in ("not json", "{}", '{"voices": [{"id": "V1", "role": "Doctor"}], "segments": [{"voice": "V9", "text": "hi"}]}',
                '{"voices": [], "segments": []}'):
        with pytest.raises(HTTPException) as err:
            server.parse_transcript(bad)
        assert err.value.status_code == 502


def test_recording_routes_are_physician_only_and_the_prompt_fixes_voice_before_role():
    import server
    for path in ("/api/transcribe-recording", "/api/ask-transcript"):
        route = next(r for r in server.app.routes if getattr(r, "path", "") == path)
        assert any(d.call is server.require_physician for d in route.dependant.dependencies), path
    prompt = server.TRANSCRIBE_PROMPT
    assert prompt.index("Pass 1, voices") < prompt.index("Pass 2, roles")
    assert "keeps its id for the entire recording" in prompt and "ONCE per voice" in prompt
    assert "A\npatient asking a question is still the patient" in prompt or "patient asking a question is still the patient" in prompt


# ── Visit log: the seventh system, ordered steps per visit day ───────────────

def test_visit_log_covers_every_visit_day_and_links_every_record_exactly_once():
    import re
    chart, _ = chart_for("P1001")
    log = chart["visit_log"]
    assert set(log) == {v["date"] for v in chart["visits"]}          # one sequence per visit day
    for day, steps in log.items():
        assert steps[0]["step"] == "Checked in at the front desk" and steps[-1]["step"] == "Checked out"
        linked = [(l["department"], l["title"]) for s in steps for l in s["links"]]
        on_chart = [(i["department"], i["title"]) for i in chart["timeline"] if i["date"] == day]
        assert sorted(linked) == sorted(on_chart), day                # nothing missing, nothing invented
        assert not re.search(r"\b\d{1,2}:\d{2}\b", str(steps)), day   # order only, no clock times
    feb = next(steps for steps in log.values() if any("Cycle 2" in l["title"] for s in steps for l in s["links"]))
    assert [s["step"] for s in feb] == ["Checked in at the front desk", "Vitals recorded", "Blood sample drawn",
                                        "Consultation with Dr. Smith", "Pre-medication given", "Infusion given",
                                        "Observed after the infusion", "Checked out"]
    assert len(next(s for s in feb if s["step"] == "Blood sample drawn")["links"]) == 2     # liver and kidney panels


def test_visit_log_exists_only_where_seeded_and_is_reached_through_the_mpi(tmp_path, monkeypatch):
    from data import visit_system
    assert {v["patient_id"] for v in SEED["visit_logs"]} == {"P1001"}
    assert chart_for("P1002")[0]["visit_log"] == {} and chart_for("P1010")[0]["visit_log"] == {}   # same scenario, not flagged
    assert all(m["visit_local_id"].startswith("VL-") for m in SEED["mpi"])
    assert "visit_log" not in next(p for p in SEED["profiles"] if p["patient_id"] == "P1001")
    monkeypatch.setattr(visit_system, "DB_PATH", tmp_path / "visits.json")
    assert visit_system.query_by_local_id("VL-600000") == []                                  # no store yet
    assert visit_system.reset_and_seed({"VL-600000": SEED["visit_logs"]}) == len(SEED["visit_logs"])
    stored = visit_system.query_by_local_id("VL-600000")
    assert set(stored[0]) == {"visit_date", "steps"}                                          # no canonical patient_id in the store
    visit_system.clear()
    assert visit_system.query_by_local_id("VL-600000") == []
