"""Data shared by the locustfiles. Set the TASKS environment variable to choose which models to test."""
import os
from pathlib import Path

SAMPLES = Path(__file__).parent.parent / "samples"


def _case(filename, mime, data):
    return {"filename": filename, "mime": mime, "data": data, "bytes": (SAMPLES / filename).read_bytes()}


ALL_CASES = {
    "vqa": _case("coco_000000039769.jpg", "image/jpeg", {"question": "How many cats are there?"}),
    "ocr": _case("sign_text.png", "image/png", {}),
    "classification": _case("coco_000000039769.jpg", "image/jpeg", {}),
}

# e.g. TASKS="ocr" or TASKS="vqa,ocr". If unset, all 3 are tested.
TASKS = [t.strip() for t in os.getenv("TASKS", ",".join(ALL_CASES)).split(",") if t.strip()]


def files_for(case):
    return {"image": (case["filename"], case["bytes"], case["mime"])}
