"""One server, three models (VQA, OCR, classification), called directly or through a job queue."""
import io
import os
import queue
import time
import uuid
from contextlib import asynccontextmanager
from enum import Enum

import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from PIL import Image

from models import classification, ocr, vqa
from registry import ModelRegistry
from schemas import JobCreated, JobStatus
from worker import start_worker

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
# LOAD_MODE=eager loads all 3 models at startup. Default is lazy: load on first request.
LOAD_ALL_AT_STARTUP = os.getenv("LOAD_MODE", "lazy") == "eager"


class Task(str, Enum):
    vqa = "vqa"
    ocr = "ocr"
    classification = "classification"


registry = ModelRegistry(DEVICE)
registry.register(Task.vqa.value, vqa)
registry.register(Task.ocr.value, ocr)
registry.register(Task.classification.value, classification)

jobs: dict = {}
job_queue: queue.Queue = queue.Queue()


def decode_image(raw: bytes) -> Image.Image:
    return Image.open(io.BytesIO(raw)).convert("RGB")


def read_request(task: Task, upload: UploadFile, question: str):
    """Validate the input. Returns (bytes, PIL image)."""
    if task is Task.vqa and not (question or "").strip():
        raise HTTPException(400, "question must not be empty")
    if not (upload.content_type or "").startswith("image/"):
        raise HTTPException(400, "file must be an image")
    raw = upload.file.read()
    try:
        return raw, decode_image(raw)
    except Exception:
        raise HTTPException(400, "could not decode image")


def run_job(task: str, image_bytes: bytes, question: str) -> dict:
    return registry.run(task, decode_image(image_bytes), question)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if LOAD_ALL_AT_STARTUP:
        for task in Task:
            registry.load(task.value)
    start_worker(job_queue, jobs, run_job)
    yield


app = FastAPI(title="Multi-model async server", lifespan=lifespan)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "device": DEVICE,
        "load_mode": "eager" if LOAD_ALL_AT_STARTUP else "lazy",
        "queue_size": job_queue.qsize(),
    }


@app.get("/v1/models")
def list_models():
    info = {"models": registry.list(), "device": DEVICE}
    if torch.cuda.is_available():
        info["cuda_memory_allocated_mb"] = round(torch.cuda.memory_allocated() / 1e6, 1)
    return info


@app.post("/v1/models/{task}/unload")
def unload_model(task: Task):
    registry.unload(task.value)
    return {"unloaded": task.value, "models": registry.list()}


# These endpoints use `def` (not `async def`) so FastAPI runs them in a thread pool
# and inference does not block the server.
@app.post("/v1/{task}/predict")
def predict(task: Task, image: UploadFile = File(...), question: str = Form(None)):
    _, pil = read_request(task, image, question)
    return registry.run(task.value, pil, question)


@app.post("/v1/{task}/jobs", status_code=202, response_model=JobCreated)
def create_job(
    task: Task,
    image: UploadFile = File(...),
    question: str = Form(None),
    callback_url: str = Form(None),
):
    raw, _ = read_request(task, image, question)
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"job_id": job_id, "task": task.value, "status": "queued"}
    job_queue.put((job_id, task.value, raw, question, callback_url, time.perf_counter()))
    return JobCreated(job_id=job_id, task=task.value, status="queued")


@app.get("/v1/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "unknown job_id")
    return JobStatus(**jobs[job_id])
