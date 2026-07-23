# V2 Progress Log — Federated Department Integration

> This file tracks *this specific initiative* step by step, as it happens.
> Different from the other two docs on purpose:
> - `plan.md` = the overall project roadmap (phases, checkboxes, what's done)
> - `RULES.md` = standing conventions to check before writing any code
> - `V2_PROGRESS.md` (this file) = a running log of *this* architecture change: what we decided, why, what got built, what broke, what got verified. Read this to understand how we got here, not what to do next.

Branch: `feature/department-integration-v2`

---

## Why this exists

The current system (main branch) is one shared MongoDB with 6 collections, all keyed
by the same `patient_id`. That's not how real hospitals work — each department
(EMR, radiology PACS, ECG/MUSE, lab/Sunquest) runs on a different vendor's system,
with its own local patient ID, and departments never query each other's databases
directly. They integrate through a translation layer.

V2's goal: make our architecture actually resemble that, starting with one
department as a pilot before touching the rest.

---

## Step 1 — Scope decision (2026-07-20)

Discussed and decided:
- **Pilot on labs (blood_profile) only**, not all 6 departments at once — lower risk,
  proves the pattern before a bigger rewrite.
- **SQLite, not a second MongoDB database**, for the lab vendor ("Sunquest").
  Real lab vendors are relational systems, not document stores — using Mongo again
  would just be "Mongo talking to Mongo" and wouldn't force real cross-paradigm
  integration work. SQLite is Python stdlib — zero new dependencies.
- **Explicitly out of scope for this pilot**: no HL7/FHIR message simulation, no
  fuzzy/probabilistic patient matching (MPI is exact 1:1 for now), no repeating the
  pattern on the other 5 departments yet.
- Frontend stays untouched — the doctor-facing UI should never know or care that
  labs come from a different system underneath.

## Step 2 — Built the pieces (2026-07-20)

**`backend/data/lab_system.py`** — the simulated vendor's own database code. Plain
SQLite (`sunquest.db`), one table `lab_results`, keyed by `sunquest_id` (the
vendor's own local patient ID — it has no idea what our canonical `patient_id` is).
Functions: `reset_and_seed()`, `clear()`, `query_by_local_id()`, `query_all()`.

**`backend/lab_gateway.py`** — the integration layer. This is the part that mirrors
what a real hospital's integration engine does: look up the patient's vendor-local
ID via the **Master Patient Index (MPI)**, query the vendor system with that ID,
then normalize the result back into the same record shape every other department
already uses (`patient_id`, `name`, `test_name`, `test_date`, `result`, `doctor`,
`report_image`). Two functions: `get_records_for_patient()` (single patient) and
`get_all_records()` (department-wide view, reverse-maps every vendor-local ID back
to a canonical patient_id via the MPI).

**MPI** — a new Mongo collection, `mpi`, one document per patient:
`{"patient_id": "P1001", "sunquest_lab_id": "SQ-90000"}`. Generated at seed time in
`backend/data/seed.py`, alongside the existing patient/record generation.

**`server.py` wiring** — every place that used to do
`db.blood_profile_records.find(...)` directly (`/search`, `/analytics/{id}`,
`/department/{name}`, `/deep-query`) now calls `lab_gateway` instead. Seeding
(`populate_sample_data`) and clearing (`clear_data`) both updated to seed/wipe the
MPI collection and the SQLite file instead of writing labs into Mongo.

## Step 3 — Verified offline (2026-07-20)

Ran the seed pipeline directly (no server) to check the data shape before touching
the live app:
- 500 patients → 500 MPI mappings generated
- 2503 lab records correctly grouped by vendor-local ID and inserted into SQLite
- Spot-checked one patient (`P1001` / James Mitchell → `SQ-90000`) — 6 lab records
  correctly retrieved by local ID, right test names/dates/results attached
- `query_all()` returned all 2503 rows

## Step 4 — End-to-end verification (2026-07-23) — PASSED

Restarted backend, reset + reseeded (500 patients, 500 MPI mappings, 2503 lab
records into SQLite). All verified in the real browser/API, not just offline:
- [x] Patient search (`/api/search?term=P1001`) shows correct blood profile
      results, correctly attributed to the right patient
- [x] Department "Blood Profile" page lists all 2503 records across all patients,
      each with the correct canonical `patient_id` (reverse-mapped from the
      vendor's local ID via MPI) — confirms `get_all_records()` works
- [x] DocAssist AI (`/deep-query`) correctly answers a labs question for P1001 —
      "WBC 2.1, Neutropenia... CEA decreased (12.5 → 5.2 ng/mL)" — pulled entirely
      through the gateway, with evidence cards carrying the right patient_id/name
- [x] No errors in backend logs; `/api/init-data` returned 200 OK

**Labs pilot is proven end-to-end.** Every read path (search, department listing,
AI chat) now goes through MPI + SQLite instead of a direct Mongo query, and the
doctor-facing experience is unchanged.

---

## Step 5 — Decision: extend to all 6 departments, each fully isolated (2026-07-23)

Decided to go beyond a single pilot: **all 6 departments become fully isolated
systems**, each reached only through MPI + a gateway — no direct Mongo queries to
department data anywhere in the app. Explicitly considered and rejected the more
"realistic" consolidated model (one PACS for MRI/X-Ray/CT, Treatment folded into
the central EMR) — user wants maximum isolation per department regardless of how
real hospitals structure it.

**Storage varies by department** (different Python-stdlib persistence mechanism
each, no new dependencies) — deliberately not repeating the same pattern 6 times,
since real vendors aren't built the same way either:
- Labs → SQLite (relational) — done
- MRI → JSON files, one per patient (file-based, mimics PACS/RIS storing studies
  as discrete files) — done
- X-Ray, CT Scan, ECG, Treatment → still to build, each getting a different
  stdlib storage mechanism (candidates: dbm key-value store, csv flat file,
  shelve object store)

**Build order**: one department at a time — build, verify in the real browser/API,
commit — before starting the next. Central EMR (Mongo) keeps profiles + the MPI
collection regardless of how many departments get split out.

## Step 6 — MRI pilot (2026-07-23) — DONE

New: `backend/data/mri_system.py` (JSON-file vendor store, `mri_store/` directory,
one file per `ris_mri_id`), `backend/mri_gateway.py` (same MPI-lookup + normalize
shape as `lab_gateway.py`). MPI now carries both `sunquest_lab_id` and
`ris_mri_id` per patient. Same 4 call sites in `server.py` updated
(`/search`, `/analytics`, `/department`, `/deep-query`), plus seeding/clearing.

Verified end-to-end with 500 patients / 547 MRI records:
- [x] `/search?term=P1001` → correct MRI record (Brain MRI, 2025-01-29)
- [x] `/department/mri` → all 547 records, 0 orphaned (every vendor-local ID
      correctly reverse-mapped to a canonical patient_id)
- [x] `/deep-query` ("what did the brain MRI show?") → correct answer + evidence,
      sourced entirely from the JSON file store via the gateway

## Open questions for later

- X-Ray, CT Scan, ECG, Treatment still on shared Mongo — next 4 departments to
  isolate, one at a time, per Step 5's decision.
