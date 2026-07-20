"""Fix specific bad image matches found during manual review."""
import json
import time
from resolve_images import search_and_resolve

FIXES = {
    ("mri", "Abdominal MRI"): "abdominal MRI liver kidney axial scan",
    ("ecg", "Stress ECG"): "electrocardiogram exercise treadmill trace",
    ("ecg", "Holter Monitor"): "electrocardiogram rhythm strip trace",
    ("ecg", "Event Monitor"): "electrocardiogram rhythm strip trace",
}

if __name__ == "__main__":
    with open("data/medical_images.json") as f:
        data = json.load(f)

    for (dept, test), query in FIXES.items():
        print(f"Fixing: {dept}/{test} -> '{query}'")
        urls = search_and_resolve(query, count=2)
        print(f"  found {len(urls)}: {urls}")
        if urls:
            data[dept][test] = urls
        with open("data/medical_images.json", "w") as f:
            json.dump(data, f, indent=2)
        time.sleep(4)

    print("Done.")
