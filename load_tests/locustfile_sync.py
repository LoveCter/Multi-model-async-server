"""Locust: load-test POST /v1/{task}/predict."""
import random

from locust import HttpUser, between, task

from common import ALL_CASES, TASKS, files_for


class SyncUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def predict(self):
        name = random.choice(TASKS)
        case = ALL_CASES[name]
        self.client.post(f"/v1/{name}/predict", files=files_for(case), data=case["data"])
