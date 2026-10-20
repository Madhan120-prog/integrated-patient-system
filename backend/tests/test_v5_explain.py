"""V5: one finding explained at four levels, from one fact sheet built in code."""
from datetime import datetime

import explain
from data.seed import build_seed_data

SEED = build_seed_data(today=datetime(2026, 10, 8))
PROFILES = {p["patient_id"]: p for p in SEED["profiles"]}
COLLECTIONS = {"CT Scan": "ct_scan_records", "MRI": "mri_records", "Blood Profile": "blood_profile_records", "Treatment": "treatment_records"}


def records(pid):
    return {dept: [r for r in SEED[coll] if r["patient_id"] == pid] for dept, coll in COLLECTIONS.items()}


FACTS = explain.build_facts(PROFILES["P1001"], records("P1001"))
BY_LABEL = {f["label"]: f["value"] for f in FACTS}


def test_only_patients_with_pathology_and_molecular_results_get_levels():
    assert explain.available(PROFILES["P1001"])
    assert not explain.available(PROFILES["P1002"]) and not explain.available(None)


def test_fact_sheet_comes_from_the_record_with_a_source_for_each_fact():
    assert BY_LABEL["Grade"].startswith("Grade 3") and "KRAS G12C" in BY_LABEL["Molecular tests"]
    assert BY_LABEL["CEA (tumour marker)"] == "12.5 → 9.1 → 6.8 → 5.2 ng/mL, reference 0 to 5.0"
    assert BY_LABEL["Chemotherapy"] == "4 cycles of Cisplatin/Pemetrexed"
    assert any("3.2cm" in v for v in BY_LABEL.values()) and all(f["source"] for f in FACTS)


def test_saved_explanation_has_four_levels_and_passes_its_own_checks():
    out = explain.assemble(explain.saved("P1001"), FACTS, "saved")
    assert [lvl["id"] for lvl in out["levels"]] == ["patient", "physician", "lab", "drug"]
    assert all(lvl["notes"] == [] for lvl in out["levels"]), [lvl["notes"] for lvl in out["levels"]]
    assert out["levels"][3]["text"].startswith("Patient-specific:")


def test_checks_flag_numbers_not_in_the_record_and_outlook_for_the_patient():
    assert explain.check("physician", "Primary is 4.7 cm with CEA 5.2.", FACTS) == ["Contains a number not in the record (4.7). Check before using."]
    assert explain.check("patient", "Five-year survival is good.", FACTS)[0].startswith("Mentions outlook")
    assert explain.check("physician", "Discuss survival with the team.", FACTS) == []   # only the patient level


def test_model_reply_is_read_only_when_all_four_levels_are_there():
    good = 'Sure: {"patient": "a", "physician": "b", "lab": "c", "drug": "d"} done'
    assert explain.parse(good) == {"patient": "a", "physician": "b", "lab": "c", "drug": "d"}
    assert explain.parse('{"patient": "a", "physician": "b"}') is None
    assert explain.parse("not json") is None and explain.parse(None) is None
