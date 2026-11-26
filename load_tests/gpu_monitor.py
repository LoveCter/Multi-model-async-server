"""Log GPU utilization and memory to results/nvidia_smi.csv every second. Stop with Ctrl+C."""
import subprocess
from pathlib import Path

results = Path(__file__).parent.parent / "results"
results.mkdir(exist_ok=True)
cmd = [
    "nvidia-smi",
    "--query-gpu=timestamp,utilization.gpu,memory.used,memory.total",
    "--format=csv", "-l", "1",
]
with open(results / "nvidia_smi.csv", "w") as out:
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    try:
        for line in proc.stdout:
            print(line, end="")
            out.write(line)
            out.flush()
    except KeyboardInterrupt:
        pass
    finally:
        proc.terminate()
