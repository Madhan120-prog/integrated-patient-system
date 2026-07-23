"""
Database seeder — generates realistic oncology patient data from curated scenarios.

Usage:
    python data/seed.py                  # Seed with curated patients only (12)
    python data/seed.py --extra 50       # Add 50 extra generated patients on top
"""

import json
import random
import argparse
from pathlib import Path
from datetime import datetime, timedelta

DATA_DIR = Path(__file__).parent

def load_json(path):
    with open(path) as f:
        return json.load(f)

def load_patients():
    return load_json(DATA_DIR / "patients.json")

def load_scenario(name):
    return load_json(DATA_DIR / "scenarios" / f"{name}.json")

def load_medical_images():
    return load_json(DATA_DIR / "medical_images.json")

IMAGES = load_medical_images()

DOCTOR_NAMES = [
    "Dr. Reynolds", "Dr. Patel", "Dr. Kim", "Dr. Okafor", "Dr. Hernandez",
    "Dr. Nakamura", "Dr. Sullivan", "Dr. Abrams", "Dr. Whitfield", "Dr. Zhao",
    "Dr. Montgomery", "Dr. Fischer", "Dr. Kapoor", "Dr. Barnes", "Dr. Nguyen"
]

def get_image(department, test_name):
    dept_images = IMAGES.get(department, {})
    test_images = dept_images.get(test_name)
    if test_images:
        return random.choice(test_images)
    all_dept = [img for imgs in dept_images.values() for img in imgs]
    return random.choice(all_dept) if all_dept else None

def week_to_date(registration_date, week_offset):
    base = datetime.strptime(registration_date, "%Y-%m-%d")
    return (base + timedelta(weeks=week_offset)).strftime("%Y-%m-%d")

def build_records_for_patient(patient):
    scenario = load_scenario(patient["scenario"])
    records = scenario["records"]
    reg_date = patient["registration_date"]
    name = patient["name"]
    pid = patient["patient_id"]

    result = {
        "mri_records": [],
        "xray_records": [],
        "ecg_records": [],
        "blood_profile_records": [],
        "ct_scan_records": [],
        "treatment_records": []
    }

    collection_map = {
        "mri": "mri_records",
        "xray": "xray_records",
        "ecg": "ecg_records",
        "blood_profile": "blood_profile_records",
        "ct_scan": "ct_scan_records",
        "treatment": "treatment_records"
    }

    for dept, dept_records in records.items():
        coll_name = collection_map.get(dept)
        if not coll_name:
            continue

        for rec in dept_records:
            date = week_to_date(reg_date, rec["week_offset"])
            doctor = random.choice(DOCTOR_NAMES)

            if dept == "treatment":
                entry = {
                    "patient_id": pid,
                    "name": name,
                    "treatment_name": rec["treatment_name"],
                    "treatment_date": date,
                    "result": rec["result"],
                    "doctor": doctor,
                    "medicines": rec["medicines"]
                }
            else:
                entry = {
                    "patient_id": pid,
                    "name": name,
                    "test_name": rec["test_name"],
                    "test_date": date,
                    "result": rec["result"],
                    "doctor": doctor,
                }
                img = get_image(dept, rec["test_name"])
                if img:
                    entry["report_image"] = img

            result[coll_name].append(entry)

    return result

EXTRA_SCENARIOS = [
    "lung_cancer", "breast_cancer", "colorectal_cancer",
    "prostate_cancer", "lymphoma", "leukemia",
    "brain_tumor", "routine_screening", "post_treatment_followup"
]

EXTRA_FIRST_NAMES_M = [
    "David", "Richard", "Joseph", "Daniel", "Matthew", "Anthony",
    "Mark", "Steven", "Paul", "Andrew", "Joshua", "Kenneth",
    "George", "Edward", "Brian", "Ronald", "Timothy", "Jason"
]
EXTRA_FIRST_NAMES_F = [
    "Jennifer", "Elizabeth", "Barbara", "Susan", "Jessica", "Margaret",
    "Lisa", "Nancy", "Betty", "Sandra", "Ashley", "Kimberly",
    "Donna", "Emily", "Carol", "Michelle", "Amanda", "Melissa"
]
EXTRA_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
    "Miller", "Davis", "Rodriguez", "Martinez", "Taylor", "Thomas",
    "Moore", "Jackson", "Martin", "Lee", "Walker", "Hall",
    "Allen", "Young", "King", "Wright", "Scott", "Green"
]

MEMPHIS_STREETS = [
    "Poplar Ave", "Union Ave", "Beale St", "Madison Ave", "Main St",
    "Lamar Ave", "Summer Ave", "Central Ave", "Highland St", "Cooper St",
    "Walnut Grove Rd", "Germantown Pkwy", "Winchester Rd", "Shelby Dr",
    "Elvis Presley Blvd", "Airways Blvd", "Getwell Rd", "Perkins Rd",
    "Ridgeway Rd", "Colonial Rd", "Kirby Pkwy", "Bartlett Blvd"
]

MEMPHIS_ZIPS = [
    "38103", "38104", "38105", "38106", "38107", "38108",
    "38109", "38111", "38112", "38114", "38116", "38117",
    "38118", "38119", "38120", "38122", "38125", "38127",
    "38128", "38133", "38134", "38135", "38138", "38139"
]

def generate_extra_patients(count, start_id=1013):
    patients = []
    for i in range(count):
        pid = f"P{start_id + i}"
        gender = random.choice(["Male", "Female"])
        if gender == "Male":
            first = random.choice(EXTRA_FIRST_NAMES_M)
        else:
            first = random.choice(EXTRA_FIRST_NAMES_F)
        last = random.choice(EXTRA_LAST_NAMES)
        name = f"{first} {last}"

        street_num = random.randint(100, 9999)
        street = random.choice(MEMPHIS_STREETS)
        zipcode = random.choice(MEMPHIS_ZIPS)

        scenario = random.choice(EXTRA_SCENARIOS)
        age_ranges = {
            "lung_cancer": (50, 78),
            "breast_cancer": (35, 70),
            "colorectal_cancer": (45, 80),
            "prostate_cancer": (55, 80),
            "lymphoma": (20, 60),
            "leukemia": (18, 45),
            "brain_tumor": (30, 75),
            "routine_screening": (30, 70),
            "post_treatment_followup": (35, 75)
        }
        age_min, age_max = age_ranges.get(scenario, (25, 75))

        reg_base = datetime(2024, 6, 1)
        reg_offset = random.randint(0, 400)
        reg_date = (reg_base + timedelta(days=reg_offset)).strftime("%Y-%m-%d")

        patients.append({
            "patient_id": pid,
            "name": name,
            "age": random.randint(age_min, age_max),
            "gender": gender,
            "blood_group": random.choice(["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]),
            "address": f"{street_num} {street}, Memphis, TN {zipcode}",
            "phone": f"(901) 555-{random.randint(1000, 9999):04d}",
            "registration_date": reg_date,
            "scenario": scenario
        })
    return patients

def build_seed_data(extra_count=0):
    random.seed(42)
    patients = load_patients()

    if extra_count > 0:
        patients.extend(generate_extra_patients(extra_count))

    all_records = {
        "profiles": [],
        "mri_records": [],
        "xray_records": [],
        "ecg_records": [],
        "blood_profile_records": [],
        "ct_scan_records": [],
        "treatment_records": [],
        "mpi": []  # canonical patient_id -> each vendor system's own local ID
    }

    for i, patient in enumerate(patients):
        profile = {k: v for k, v in patient.items() if k != "scenario"}
        all_records["profiles"].append(profile)
        all_records["mpi"].append({
            "patient_id": patient["patient_id"],
            "sunquest_lab_id": f"SQ-{90000 + i}",
            "ris_mri_id": f"RIS-{100000 + i}",
            "xray_local_id": f"XR-{200000 + i}",
            "ct_local_id": f"CT-{300000 + i}",
            "ecg_local_id": f"ECG-{400000 + i}",
            "treatment_local_id": f"TX-{500000 + i}"
        })

        patient_records = build_records_for_patient(patient)
        for coll, recs in patient_records.items():
            all_records[coll].extend(recs)

    return all_records

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate seed data for the patient system")
    parser.add_argument("--extra", type=int, default=0, help="Number of extra generated patients beyond the curated 12")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file (default: print stats)")
    args = parser.parse_args()

    data = build_seed_data(extra_count=args.extra)

    print(f"Patients: {len(data['profiles'])}")
    for coll, records in data.items():
        if coll != "profiles":
            print(f"  {coll}: {len(records)} records")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(data, f, indent=2)
        print(f"\nWritten to {args.output}")
