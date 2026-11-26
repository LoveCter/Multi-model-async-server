"""Run headless Locust at several user counts. Works on Windows and Linux.

Examples: python load_tests/run_locust.py sync
          python load_tests/run_locust.py jobs --users 1 5 --time 30s
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent

parser = argparse.ArgumentParser()
parser.add_argument("mode", choices=["sync", "jobs"])
parser.add_argument("--users", type=int, nargs="+", default=[1, 5, 10, 20])
parser.add_argument("--time", default="60s")
parser.add_argument("--host", default=os.getenv("BASE_URL", "http://localhost:8000"))
args = parser.parse_args()

results = HERE.parent / "results"
results.mkdir(exist_ok=True)
tag = os.getenv("TASKS", "all").replace(",", "-")

for n in args.users:
    print(f"=== {args.mode} [{tag}] users={n} ===", flush=True)
    # No check=True: Locust exits non-zero when requests fail, and we still want the next run.
    subprocess.run([
        sys.executable, "-m", "locust",
        "-f", str(HERE / f"locustfile_{args.mode}.py"),
        "--host", args.host, "--headless",
        "-u", str(n), "-r", str(n), "-t", args.time,
        "--csv", str(results / f"{args.mode}_{tag}_u{n}"),
    ])
