"""One background thread: take jobs from the queue, run the right model, call the webhook if given."""
import queue
import threading
import time

import requests


def start_worker(job_queue: queue.Queue, jobs: dict, run_fn):
    """run_fn(task, image_bytes, question) -> result dict."""

    def loop():
        while True:
            job_id, task, image_bytes, question, callback_url, queued_at = job_queue.get()
            queue_ms = (time.perf_counter() - queued_at) * 1000
            base = {"job_id": job_id, "task": task, "queue_ms": queue_ms}
            # Assign a new dict (no in-place edits) so readers never see a half-updated job.
            jobs[job_id] = {**base, "status": "processing"}
            try:
                result = run_fn(task, image_bytes, question)
                jobs[job_id] = {**base, "status": "completed", "result": result}
            except Exception as e:
                print(f"Job {job_id} ({task}) failed: {e!r}")
                jobs[job_id] = {**base, "status": "failed", "error": str(e)}
            if callback_url:
                try:
                    requests.post(callback_url, json=jobs[job_id], timeout=5)
                except Exception as e:
                    print(f"Webhook {callback_url} failed: {e!r}")
            job_queue.task_done()

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return t
