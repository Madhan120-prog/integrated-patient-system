"""
One-off script: resolve real, working Wikimedia Commons image URLs for each
medical test type by searching the Commons API and fetching actual imageinfo.
Run once, paste verified output into medical_images.json.
"""
import urllib.request
import urllib.parse
import json
import time

API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "IntegratedPatientSystem/1.0 (educational demo project)"}

def fetch_json(url, retries=4):
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            raise

BLACKLIST_WORDS = [
    "concrete", "practitioner", "ultrasound", "sonograph",
    "1912", "1895", "1896", "wellcome", "book", "engraving"
]

def search_and_resolve(query, count=2):
    params = {
        "action": "query", "list": "search", "srsearch": query,
        "srnamespace": "6", "format": "json", "srlimit": str(count * 3)
    }
    url = API + "?" + urllib.parse.urlencode(params)
    data = fetch_json(url)

    titles = [item["title"] for item in data.get("query", {}).get("search", [])]
    resolved = []
    for title in titles:
        if len(resolved) >= count:
            break
        if not any(title.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png"]):
            continue
        if any(word in title.lower() for word in BLACKLIST_WORDS):
            continue
        info_params = {
            "action": "query", "titles": title, "prop": "imageinfo",
            "iiprop": "url", "iiurlwidth": "500", "format": "json"
        }
        info_url = API + "?" + urllib.parse.urlencode(info_params)
        try:
            info_data = fetch_json(info_url)
            pages = info_data.get("query", {}).get("pages", {})
            for page in pages.values():
                imageinfo = page.get("imageinfo")
                if imageinfo:
                    thumb = imageinfo[0].get("thumburl")
                    if thumb:
                        resolved.append(thumb)
        except Exception as e:
            print(f"  skip {title}: {e}")
        time.sleep(0.5)
    return resolved

QUERIES = {
    ("mri", "Brain MRI"): "brain MRI scan axial",
    ("mri", "Spine MRI"): "spine MRI sagittal",
    ("mri", "Breast MRI"): "breast MRI",
    ("mri", "Abdominal MRI"): "MRI liver abdomen axial radiology",
    ("mri", "Pelvic MRI"): "pelvis MRI scan",
    ("xray", "Chest X-Ray"): "chest x-ray radiograph normal",
    ("xray", "Bone X-Ray"): "hand x-ray radiograph",
    ("xray", "Pelvis X-Ray"): "pelvis x-ray radiograph",
    ("xray", "Dental X-Ray"): "dental x-ray radiograph",
    ("ecg", "Resting ECG"): "ECG sinus rhythm tracing",
    ("ecg", "Stress ECG"): "electrocardiogram tracing rhythm strip",
    ("ecg", "Holter Monitor"): "ECGpedia rhythm tracing electrocardiogram",
    ("ecg", "Event Monitor"): "ECGpedia rhythm tracing electrocardiogram",
    ("ct_scan", "Chest CT Scan"): "chest CT scan axial",
    ("ct_scan", "Abdominal CT Scan"): "abdominal CT scan axial",
    ("ct_scan", "Head CT Scan"): "head CT scan brain axial",
    ("ct_scan", "Pelvic CT Scan"): "pelvis CT scan axial",
    ("blood_profile", "Complete Blood Count"): "complete blood count hematology analyzer",
    ("blood_profile", "Lipid Profile"): "blood serum sample vial laboratory",
    ("blood_profile", "Liver Function Test"): "blood sample vial clinical laboratory",
    ("blood_profile", "Kidney Function Test"): "blood collection tube phlebotomy",
    ("blood_profile", "Tumor Marker Panel"): "blood sample centrifuge laboratory",
    ("blood_profile", "Thyroid Panel"): "blood serum vial rack laboratory",
}

if __name__ == "__main__":
    import os
    OUT_FILE = "data/medical_images.json"
    result = {}
    if os.path.exists(OUT_FILE):
        with open(OUT_FILE) as f:
            result = json.load(f)

    for (dept, test), query in QUERIES.items():
        if result.get(dept, {}).get(test):
            print(f"Skip (already have): {dept}/{test}")
            continue
        print(f"Searching: {dept}/{test} -> '{query}'")
        try:
            urls = search_and_resolve(query, count=2)
        except Exception as e:
            print(f"  FAILED: {e}")
            urls = []
        print(f"  found {len(urls)} images")
        result.setdefault(dept, {})[test] = urls
        with open(OUT_FILE, "w") as f:
            json.dump(result, f, indent=2)
        time.sleep(4)

    print("\nDone. Written to data/medical_images.json")
