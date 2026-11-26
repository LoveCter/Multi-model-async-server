"""Call all 3 models in both ways: sync and job (submit, then poll)."""
import os
import time
from pathlib import Path

import requests

BASE = os.getenv("BASE_URL", "http://localhost:8000")
SAMPLES = Path(__file__).parent / "samples"
CASES = [
    ("vqa", "coco_000000039769.jpg", "image/jpeg", {"question": "How many cats are there?"}),
    ("ocr", "sign_text.png", "image/png", {}),
    ("classification", "coco_000000039769.jpg", "image/jpeg", {}),
]


def post(url, filename, mime, data):
    with open(SAMPLES / filename, "rb") as f:
        r = requests.post(url, files={"image": (filename, f, mime)}, data=data, timeout=600)
    if not r.ok:
        raise SystemExit(f"{url} -> {r.status_code}: {r.text}\nCheck the log in the server terminal.")
    return r.json()


print("=== sync ===")
for task, filename, mime, data in CASES:
    t0 = time.perf_counter()
    body = post(f"{BASE}/v1/{task}/predict", filename, mime, data)
    print(f"{task} ({(time.perf_counter() - t0) * 1000:.0f}ms): {body}")

print("=== jobs ===")
for task, filename, mime, data in CASES:
    t0 = time.perf_counter()
    job_id = post(f"{BASE}/v1/{task}/jobs", filename, mime, data)["job_id"]
    while True:
        job = requests.get(f"{BASE}/v1/jobs/{job_id}", timeout=30).json()
        if job["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)
    print(f"{task} ({(time.perf_counter() - t0) * 1000:.0f}ms): {job}")

print("=== models ===")
print(requests.get(f"{BASE}/v1/models", timeout=30).json())
