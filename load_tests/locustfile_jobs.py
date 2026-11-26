"""Locust: submit a job, poll until done, report the total time as a job_total metric."""
import random
import time

from locust import HttpUser, between, task

from common import ALL_CASES, TASKS, files_for

POLL_INTERVAL_S = 0.1  # models are fast; slow polling would skew the numbers
TIMEOUT_S = 60


class JobUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def submit_and_poll(self):
        name = random.choice(TASKS)
        case = ALL_CASES[name]
        t0 = time.perf_counter()
        r = self.client.post(
            f"/v1/{name}/jobs",
            files=files_for(case),
            data=case["data"],
            name=f"/v1/{name}/jobs [submit]",
        )
        if r.status_code != 202:
            return
        job_id = r.json()["job_id"]

        status = "timeout"
        while time.perf_counter() - t0 < TIMEOUT_S:
            s = self.client.get(f"/v1/jobs/{job_id}", name="/v1/jobs/[id] [poll]")
            if s.status_code != 200:
                status = f"poll HTTP {s.status_code}"
                break
            status = s.json()["status"]
            if status in ("completed", "failed"):
                break
            time.sleep(POLL_INTERVAL_S)

        self.environment.events.request.fire(
            request_type="JOB",
            name=f"job_total [{name}]",
            response_time=(time.perf_counter() - t0) * 1000,
            response_length=0,
            exception=None if status == "completed" else Exception(status),
            context={},
        )
