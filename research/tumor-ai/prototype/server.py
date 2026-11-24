"""The review desk: a local web page to upload a CT, watch the AI outline it, review, sign and download.

    .venv/bin/python prototype/server.py          then open http://127.0.0.1:8765

Listens on this computer only (127.0.0.1). Scans stay in prototype/cases/ (git-ignored); no cloud service is used.
Research prototype: public data only until the hospital and the university approve.
"""
import json
import queue
import re
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import List

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

import engine
import levels

CASES = engine.HERE / "cases"
INBOX = engine.HERE / "inbox"
app = FastAPI(title="Tumour outline review desk (research prototype)")
# The patient portal, when it runs on this same computer, may READ a linked patient's result (GET only).
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], allow_methods=["GET"])
PORTAL_ID = r"[A-Za-z0-9_-]{1,40}"
jobs: "queue.Queue[str]" = queue.Queue()
_models = None


def case_dir(cid: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", cid) or not (CASES / cid).is_dir():
        raise HTTPException(404, "no such case")
    return CASES / cid


def status(case: Path) -> dict:
    p = case / "status.json"
    return json.loads(p.read_text()) if p.exists() else {"state": "done", "log": []}


def save_status(case: Path, st: dict):
    tmp = case / "status.tmp"
    tmp.write_text(json.dumps(st))
    tmp.replace(case / "status.json")


def worker():
    """One scan at a time, in arrival order; models are loaded once and kept."""
    global _models
    while True:
        cid = jobs.get()
        case = CASES / cid
        st = status(case)
        st["state"] = "running"

        def log(msg):
            st["log"].append([time.strftime("%H:%M:%S"), msg])
            save_status(case, st)

        try:
            if _models is None:
                log("Loading the models (first scan only)")
                _models = engine.Models()
            engine.run(INBOX / cid, case, _models, log)
            st["state"] = "done"
        except Exception as e:                       # show the reason on the page instead of hanging
            st["state"], st["error"] = "failed", str(e)
            log(f"Stopped: {e}")
        finally:
            src = INBOX / cid                       # the upload is no longer needed: the case folder has the CT
            shutil.rmtree(src) if src.is_dir() else src.unlink(missing_ok=True)
            save_status(case, st)


@app.get("/", response_class=HTMLResponse)
def page():
    return (engine.HERE / "static" / "index.html").read_text()


@app.post("/api/cases")
async def upload(files: List[UploadFile] = File(...)):
    cid = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    inbox = INBOX / cid
    inbox.mkdir(parents=True)
    for i, f in enumerate(files):                    # numbered names: nothing from the browser becomes a path
        with open(inbox / f"{i:05d}", "wb") as out:
            while chunk := await f.read(1 << 20):
                out.write(chunk)
    if len(files) == 1:                              # a single .zip: the engine unpacks it
        (inbox / "00000").rename(inbox.parent / f"{cid}.zip")
        inbox.rmdir()
        (inbox.parent / f"{cid}.zip").rename(inbox)
    case = CASES / cid
    case.mkdir(parents=True)
    save_status(case, {"state": "queued", "log": [[time.strftime("%H:%M:%S"), f"Received {len(files)} file(s)"]],
                       "received": time.strftime("%Y-%m-%d %H:%M")})
    jobs.put(cid)
    return {"id": cid}


@app.get("/api/cases")
def list_cases():
    out = []
    for c in sorted((p for p in CASES.iterdir() if p.is_dir()), reverse=True) if CASES.exists() else []:
        st, s = status(c), c / "summary.json"
        s = json.loads(s.read_text()) if s.exists() else {}
        r = c / "review.json"
        out.append({"id": c.name, "state": st["state"], "patient": s.get("patient"), "received": st.get("received", ""),
                    "review": json.loads(r.read_text())["decision"] if r.exists() else None})
    return out


@app.get("/api/cases/{cid}")
def get_case(cid: str):
    c = case_dir(cid)
    s, r = c / "summary.json", c / "review.json"
    return {"id": cid, "status": status(c), "summary": json.loads(s.read_text()) if s.exists() else None,
            "review": json.loads(r.read_text()) if r.exists() else None}


@app.get("/api/cases/{cid}/{name}.bin")
def volume(cid: str, name: str):
    if name not in ("ct", "ai", "doctor"):
        raise HTTPException(404)
    f = case_dir(cid) / f"{name}.bin"
    if not f.exists():
        raise HTTPException(404)
    return FileResponse(f, media_type="application/octet-stream")


class Review(BaseModel):
    decision: str
    cut: float
    note: str = ""
    reviewer: str = ""


@app.post("/api/cases/{cid}/review")
def review(cid: str, r: Review):
    if r.decision not in ("accepted", "needs changes", "rejected") or r.cut not in engine.CUTS:
        raise HTTPException(400, "unknown decision or cut-off")
    rec = {**r.model_dump(), "note": r.note[:2000], "reviewer": r.reviewer[:60], "signed": time.strftime("%Y-%m-%d %H:%M")}
    (case_dir(cid) / "review.json").write_text(json.dumps(rec, indent=2))
    return rec


@app.get("/api/cases/{cid}/download/{kind}")
def download(cid: str, kind: str, cut: float = engine.DEFAULT_CUT):
    c = case_dir(cid)
    if cut not in engine.CUTS or not (c / "summary.json").exists():
        raise HTTPException(400, "unknown cut-off or case not finished")
    if kind == "rtstruct":
        f = engine.write_rtstruct(c, cut)
    elif kind == "mask":
        f = engine.write_mask(c, cut)
    elif kind == "summary":
        f = c / "summary.json"
    elif kind == "explain":
        s = json.loads((c / "summary.json").read_text())
        f = c / "out" / f"explanations_{s['patient']}_cut{int(cut * 100)}.json"
        f.parent.mkdir(exist_ok=True)
        f.write_text(json.dumps(explained(c, cut), indent=2))
    else:
        raise HTTPException(404)
    return FileResponse(f, filename=f.name)


def explained(c: Path, cut: float) -> dict:
    """The four texts, facts and check notes. The patient text is only given out once the doctor accepted the
    outline at this same cut-off (it describes that outline)."""
    out = levels.build(c, cut)
    r = c / "review.json"
    rev = json.loads(r.read_text()) if r.exists() else None
    ok = bool(rev and rev["decision"] == "accepted" and rev["cut"] == cut)
    out["patient_locked"] = not ok
    if not ok:
        out["patient"], out["notes"]["patient"] = None, []
        out["lock_reason"] = ("Released after sign-off." if not rev or rev["decision"] != "accepted" else
                              f"Released for the accepted outline at {int(rev['cut'] * 100)}%.")
    return out


@app.get("/api/cases/{cid}/explain")
def explain(cid: str, cut: float = engine.DEFAULT_CUT):
    c = case_dir(cid)
    if cut not in engine.CUTS or not (c / "summary.json").exists():
        raise HTTPException(400, "unknown cut-off or case not finished")
    return explained(c, cut)


# ── Link from the patient portal (research demo) ─────────────────────────────────────────────────────────────
# The portal opens /?portal=<its patient id>. Until scans come from the hospital's PACS (needs approval), the linked
# case is a PUBLIC demo scan (samples/*.zip), never that patient's own CT; both pages say so.
def portal_cases(pid: str) -> list:
    if not re.fullmatch(PORTAL_ID, pid):
        raise HTTPException(400, "bad portal patient id")
    out = []
    for c in sorted((p for p in CASES.iterdir() if p.is_dir()), reverse=True) if CASES.exists() else []:
        st = status(c)
        if st.get("portal") != pid:
            continue
        s, r = c / "summary.json", c / "review.json"
        s = json.loads(s.read_text()) if s.exists() else None
        rev = json.loads(r.read_text()) if r.exists() else None
        at = next((x for x in s["per_cut"] if x["cut"] == rev["cut"]), None) if s and rev else None
        out.append({"id": c.name, "state": st["state"], "demo_scan": s and s["patient"], "review": rev,
                    "volume_cc": at and at["cc"], "size_mm": at and at["size_mm"]})
    return out


@app.get("/api/portal/{pid}")
def portal_list(pid: str):
    return portal_cases(pid)


@app.post("/api/portal/{pid}/demo")
def portal_demo(pid: str):
    """Start a demo case for this portal patient from the first public sample (or return the one already there)."""
    have = portal_cases(pid)
    if have:
        return {"id": have[0]["id"]}
    sample = next(iter(sorted((engine.HERE / "samples").glob("*.zip"))), None)
    if not sample:
        raise HTTPException(404, "no demo scan in prototype/samples/")
    cid = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    INBOX.mkdir(exist_ok=True)
    shutil.copy(sample, INBOX / cid)
    case = CASES / cid
    case.mkdir(parents=True)
    save_status(case, {"state": "queued", "portal": pid, "received": time.strftime("%Y-%m-%d %H:%M"),
                       "log": [[time.strftime("%H:%M:%S"), f"Demo scan {sample.stem} for portal patient {pid}"]]})
    jobs.put(cid)
    return {"id": cid}


def main():
    CASES.mkdir(exist_ok=True)
    for c in CASES.iterdir():                        # scans interrupted by a restart: queue them again
        if c.is_dir() and status(c)["state"] in ("queued", "running") and (INBOX / c.name).exists():
            jobs.put(c.name)
    threading.Thread(target=worker, daemon=True).start()
    print("Review desk: http://127.0.0.1:8765  (this computer only; Ctrl+C to stop)")
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")


if __name__ == "__main__":
    main()
