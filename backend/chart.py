"""
Chart view assembly — turns one patient's records from the six department
systems into the shapes the chart workspace renders: a unified timeline, a lab
flowsheet (analytes x dates with range status and trend), and the list of
values currently out of range.

Pure functions over already-normalized gateway records: no database, no LLM.
Every number here comes from the encoder, so the screen and the AI prompt can
never disagree about a trend or a range.
"""
import re
from datetime import date, timedelta

from encoder import detect_trends, extract_ner_signals, summarize_latest, _range_status

# How each department's source is named on screen: the same six department
# names the search page uses, one per separate department system. (The page
# states once that these systems are simulated.)
SOURCE_SYSTEMS = {
    "Blood Profile": "Blood Test",
    "MRI": "MRI Scan",
    "X-Ray": "X-Ray",
    "CT Scan": "CT Scan",
    "ECG": "ECG",
    "Treatment": "Treatment",
}

# Rows a clinician scans first come first; anything else follows alphabetically.
_ANALYTE_ORDER = ["WBC", "ANC", "ALC", "Hgb", "PLT", "Blasts", "Creatinine", "ALT", "AST",
                  "CEA", "CA 15-3", "PSA", "TSH"]


TUMOR_MARKERS = ("CEA", "CA 15-3", "PSA")
IMAGING_DEPARTMENTS = ("MRI", "X-Ray", "CT Scan")
_MODIFIED_RE = re.compile(r"\b(?:reduced|delayed|held|interrupted|discontinued)\b", re.IGNORECASE)


def _plain(text):
    """Display text without long dashes: 'Stable — no new lesions' reads as
    'Stable: no new lesions'. The stored record is not changed."""
    return text.replace(" — ", ": ").replace("—", ", ") if isinstance(text, str) else text


def build_timeline(records_by_dept: dict) -> list:
    """Every record from every system as one list, newest first."""
    items = []
    for dept, records in records_by_dept.items():
        for r in records:
            items.append({
                "date": r.get("test_date") or r.get("treatment_date", ""),
                "department": dept,
                "system": SOURCE_SYSTEMS[dept],
                "title": _plain(r.get("test_name") or r.get("treatment_name", "")),
                "result": _plain(r.get("result", "")),
                "medicines": r.get("medicines"),
                "doctor": r.get("doctor", ""),
                "image": r.get("report_image"),
            })
    return sorted(items, key=lambda i: (i["date"], i["department"], i["title"]), reverse=True)


def build_flowsheet(lab_records: list) -> dict:
    """{dates: [oldest..newest], rows: [{analyte, unit, low, high, cells: {date: {value, status}}, trend}]}"""
    rows, dates = {}, set()
    for rec in lab_records:
        date = rec.get("test_date", "")
        for v in rec.get("values") or []:
            row = rows.setdefault(v["analyte"], {
                "analyte": v["analyte"], "unit": v["unit"], "low": v.get("low"), "high": v.get("high"), "cells": {},
            })
            row["cells"][date] = {"value": v["value"], "status": _range_status(float(v["value"]), v.get("low"), v.get("high"))}
            dates.add(date)
    trends = detect_trends(lab_records)
    for name, row in rows.items():
        t = trends.get(name)
        row["trend"] = {"direction": t["trend"], "pct_change": t["pct_change"], "size": t["flag"]} if t else None
    order = {a: i for i, a in enumerate(_ANALYTE_ORDER)}
    return {
        "dates": sorted(dates),
        "rows": sorted(rows.values(), key=lambda r: (order.get(r["analyte"], len(order)), r["analyte"])),
    }


def build_treatments(treatment_records: list) -> list:
    """Treatment course in order given. "Chemotherapy — FOLFOX Cycle 1" splits
    into a category and a name; a result mentioning a reduction, delay or hold
    marks the entry as modified."""
    items = []
    for r in sorted(treatment_records, key=lambda r: r.get("treatment_date", "")):
        category, _, name = r.get("treatment_name", "").partition(" — ")
        result = r.get("result", "")
        items.append({
            "date": r.get("treatment_date", ""),
            "category": category if name else "Treatment",
            "name": _plain(name or category),
            "status": "In progress" if "progress" in result.lower() else "Scheduled" if "scheduled" in result.lower() else "Completed",
            "result": _plain(result),
            "medicines": r.get("medicines"),
            "doctor": r.get("doctor", ""),
            "modified": bool(_MODIFIED_RE.search(result)),
        })
    return items


def build_findings(records_by_dept: dict, latest_values: dict, trends: dict, treatments: list) -> list:
    """Key findings, every one computed from the records — no model involved.
    tone: "attention" (out of range, treatment modified) | "info" | "clear" (stated as absent)."""
    findings = []
    for name, v in sorted(latest_values.items()):
        if v["status"] == "IN RANGE":
            continue
        t = trends.get(name)
        since = date.fromisoformat(t["dates"][0]).strftime("%b %d, %Y") if t else ""
        change = f' Changed {t["trend"]} {abs(t["pct_change"])}% since {since}.' if t else ""
        findings.append({
            "tone": "attention", "kind": "out_of_range", "date": v["date"],
            "title": f'{name} {v["display"]} is {"below" if v["status"] == "LOW" else "above"} range',
            "detail": f'Reference range {v["low"]} to {v["high"]}.{change}',
        })
    for name in TUMOR_MARKERS:
        t = trends.get(name)
        if t:
            findings.append({
                "tone": "info", "kind": "marker_trend", "date": t["dates"][1],
                "title": f'{name} {"down" if t["pct_change"] < 0 else "up"} {abs(t["pct_change"])}%',
                "detail": f'From {t["first_val"]} to {t["last_val"]}. Latest reading is '
                          f'{ {"IN RANGE": "in range", "LOW": "below range", "HIGH": "above range"}.get(t["status"], "unranged") }.',
            })
    for t in treatments:
        if t["modified"]:
            findings.append({"tone": "attention", "kind": "treatment_modified", "date": t["date"],
                             "title": f'{t["category"]} modified', "detail": f'{t["name"]}: {t["result"]}'})
    current = next((t for t in reversed(treatments) if t["status"] == "In progress"), None)
    if current:
        findings.append({"tone": "info", "kind": "current_therapy", "date": current["date"],
                         "title": f'Current: {current["name"]}', "detail": current["medicines"] or current["result"]})
    imaging = [r for d in IMAGING_DEPARTMENTS for r in records_by_dept.get(d, [])]
    if imaging:
        last = max(imaging, key=lambda r: r.get("test_date", ""))
        findings.append({"tone": "info", "kind": "latest_imaging", "date": last["test_date"],
                         "title": f'Latest imaging: {last["test_name"]}', "detail": _plain(last["result"])})
    ruled_out = extract_ner_signals([r for recs in records_by_dept.values() for r in recs])["ruled_out"]
    if ruled_out:
        findings.append({"tone": "clear", "kind": "stated_absent", "date": "",
                         "title": "Stated as absent in the records", "detail": ", ".join(ruled_out).capitalize()})
    return findings


def build_visits(timeline: list) -> list:
    """Every date with at least one record is one visit: who was involved and
    what was done. Derived from the records; nothing is added."""
    by_date = {}
    for item in timeline:
        by_date.setdefault(item["date"], []).append(item)
    return [
        {
            "date": date,
            "doctors": sorted({i["doctor"] for i in items if i["doctor"]}),
            "items": [{k: i[k] for k in ("department", "system", "title", "result", "doctor")} for i in items],
        }
        for date, items in sorted(by_date.items(), reverse=True)
    ]


_DRUG_DOSE_RE = re.compile(r"^(.*?)(?:\s+(\d.*))?$")


def build_medications(treatments: list) -> dict:
    """Medications as written on the treatment records. `current` comes from
    treatment still in progress; `history` is every drug with its last date."""
    def parse(entry):
        name, dose = _DRUG_DOSE_RE.match(entry.strip()).groups()
        return name.strip(), dose or ""

    current, history = [], {}
    for t in treatments:
        if not t["medicines"] or t["medicines"] == "N/A":
            continue
        for entry in t["medicines"].split(", "):
            name, dose = parse(entry)
            if not name:
                continue
            row = history.setdefault(name, {"name": name, "times_given": 0})
            row.update(last_dose=dose, last_given=t["date"], last_for=f'{t["category"]}: {t["name"]}')
            row["times_given"] += 1
            if t["status"] == "In progress":
                current.append({"name": name, "dose": dose, "since": t["date"], "for": f'{t["category"]}: {t["name"]}'})
    return {"current": current, "history": sorted(history.values(), key=lambda r: r["last_given"], reverse=True)}


_INTERVAL_RE = re.compile(r"\bq(\d)w\b|\b(weekly)\b", re.IGNORECASE)


def estimate_upcoming(treatments: list, today: date, count: int = 2) -> dict:
    """Next expected doses, ESTIMATED from the dosing interval written on the
    treatment in progress (e.g. "q3w"). These are not booked appointments: the
    record holds no schedule, and the screen says so."""
    current = next((t for t in reversed(treatments) if t["status"] == "In progress"), None)
    if not current:
        return {"items": [], "note": "No treatment is in progress, so no schedule can be estimated."}
    m = _INTERVAL_RE.search(current["medicines"] or "")
    if not m:
        return {"items": [], "note": f'{current["name"]} has no dosing interval on record that maps to visits.'}
    weeks = int(m.group(1)) if m.group(1) else 1
    due = date.fromisoformat(current["date"])
    while due < today:
        due += timedelta(weeks=weeks)
    return {
        "items": [{"date": (due + timedelta(weeks=weeks * n)).isoformat(), "title": current["name"],
                   "basis": f'Every {weeks} week{"s" if weeks > 1 else ""} from {date.fromisoformat(current["date"]).strftime("%b %d, %Y")}'} for n in range(count)],
        "note": "Estimated from the dosing interval on the treatment record. Not a booked appointment.",
    }


def build_vitals(profile: dict):
    """Latest recorded vitals, plus body surface area (Mosteller formula) since
    chemotherapy doses on the record are written per square metre."""
    v = profile.get("vitals")
    if not v:
        return None
    return {**v, "bsa_m2": round((v["height_cm"] * v["weight_kg"] / 3600) ** 0.5, 2)}


def build_problems(profile: dict, records_by_dept: dict) -> list:
    """The diagnosis on the profile, then every condition the records state as
    present (negated mentions are excluded by the encoder)."""
    problems = [{"label": profile["diagnosis"], "source": "Diagnosis on record"}] if profile.get("diagnosis") else []
    stated = extract_ner_signals([r for recs in records_by_dept.values() for r in recs])["diagnoses"]
    return problems + [{"label": d.capitalize(), "source": "Stated in a record"} for d in stated]


_LINK_DEPARTMENT = {"blood_profile": "Blood Profile", "mri": "MRI", "xray": "X-Ray", "ct_scan": "CT Scan",
                    "ecg": "ECG", "treatment": "Treatment"}


def build_visit_log(visit_logs: list) -> dict:
    """{date: [step]} from the visit log system. Each step is what happened next
    that day; `links` name the department records made at that step, using the
    same department and title the timeline carries, so the screen can join them."""
    return {
        day["visit_date"]: [
            {
                "step": step["step"], "by": step.get("by", ""), "detail": step.get("detail", ""),
                "links": [{"department": _LINK_DEPARTMENT[d], "title": _plain(name)} for d, name in step.get("links", [])],
            }
            for step in day["steps"]
        ]
        for day in visit_logs or []
    }


def build_chart(profile: dict, records_by_dept: dict, today: date = None, visit_logs: list = None) -> dict:
    labs = records_by_dept.get("Blood Profile", [])
    latest_values = summarize_latest(labs)["latest_values"]
    treatments = build_treatments(records_by_dept.get("Treatment", []))
    timeline = build_timeline(records_by_dept)
    return {
        "profile": profile,
        "vitals": build_vitals(profile),
        "care_team": profile.get("care_team", []),
        "problems": build_problems(profile, records_by_dept),
        "visits": build_visits(timeline),
        "visit_log": build_visit_log(visit_logs),
        "medications": build_medications(treatments),
        "upcoming": estimate_upcoming(treatments, today or date.today()),
        "findings": build_findings(records_by_dept, latest_values, detect_trends(labs), treatments),
        "treatments": treatments,
        "tumor_markers": list(TUMOR_MARKERS),
        "timeline": timeline,
        "flowsheet": build_flowsheet(labs),
        "out_of_range": [
            {"analyte": name, **v} for name, v in sorted(latest_values.items()) if v["status"] != "IN RANGE"
        ],
        "sources": [
            {"department": dept, "system": SOURCE_SYSTEMS[dept], "records": len(records)}
            for dept, records in records_by_dept.items() if records
        ],
    }
