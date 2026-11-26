# Multi-model async server

A FastAPI server that hosts three models, callable directly (sync) or through a job queue, with Locust load tests.

| Task | Model | Input |
|---|---|---|
| `vqa` | `dandelin/vilt-b32-finetuned-vqa` | image + `question` (English) |
| `ocr` | `microsoft/trocr-small-printed` | image with **one line** of printed text |
| `classification` | `google/vit-base-patch16-224` | image, returns top-3 labels |

## Project layout

```
app.py                 # API
registry.py            # load / run / unload models, one lock per model
worker.py              # one background thread that processes jobs
schemas.py             # job data types
models/                # vqa.py, ocr.py, classification.py
client.py              # calls all 3 models in both ways
webhook_receiver.py    # receives the callback when a job finishes
load_tests/            # locustfile_sync, locustfile_jobs, run_locust, gpu_monitor
samples/               # test images
```

## Installation

Python 3.10 or newer.

```bash
git clone https://github.com/<your-username>/multimodel-async-server.git
cd multimodel-async-server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows (PowerShell), create and activate the environment with:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

For GPU use on Windows, `pip` may install a CPU-only build of PyTorch. Inside the activated environment, install the CUDA build first, using the command from https://pytorch.org/get-started/locally/, then install the requirements.

## Run

Run all commands from the project root. Shell examples use PowerShell.

```powershell
# Terminal 1. Default is lazy: a model loads on its first request
uvicorn app:app --host 0.0.0.0 --port 8000

# or load all 3 models at startup (recommended for load testing)
$env:LOAD_MODE="eager"; uvicorn app:app --host 0.0.0.0 --port 8000

# Terminal 2
python client.py
```

On Linux or macOS, use `LOAD_MODE=eager uvicorn app:app --host 0.0.0.0 --port 8000`.

Interactive API docs: http://localhost:8000/docs

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/{task}/predict` | run and return the result immediately |
| POST | `/v1/{task}/jobs` | returns `202` and a `job_id` |
| GET | `/v1/jobs/{job_id}` | job status and result |
| GET | `/v1/models` | which models are loaded and their memory use |
| POST | `/v1/models/{task}/unload` | free a model from memory |
| GET | `/health` | server status and queue length |

```powershell
curl.exe -X POST http://localhost:8000/v1/vqa/predict -F "image=@samples/coco_000000039769.jpg" -F "question=How many cats are there?"
curl.exe -X POST http://localhost:8000/v1/ocr/jobs -F "image=@samples/sign_text.png"
curl.exe http://localhost:8000/v1/jobs/<job_id>
```

On Linux or macOS, use `curl` instead of `curl.exe`.

### Webhook

```powershell
# separate terminal
uvicorn webhook_receiver:app --port 9000

curl.exe -X POST http://localhost:8000/v1/classification/jobs -F "image=@samples/coco_000000039769.jpg" -F "callback_url=http://localhost:9000/webhook"
```

## Load testing

The server must be running in another terminal.

```powershell
python load_tests/run_locust.py sync      # 1, 5, 10, 20 users, 60 seconds each
python load_tests/run_locust.py jobs

python load_tests/run_locust.py sync --users 1 5 --time 30s

# test a single model
$env:TASKS="ocr"; python load_tests/run_locust.py sync
Remove-Item Env:TASKS

# log GPU utilization and memory in a separate terminal, Ctrl+C to stop
python load_tests/gpu_monitor.py
```

Web UI (http://localhost:8089):

```powershell
locust -f load_tests/locustfile_sync.py --host http://localhost:8000
```

CSV results are written to `results/`.

### Reading the results

- Sync: compare `Average`, `95%`, `req/s` and failures per endpoint.
- Jobs: look at the `job_total [task]` rows, the time from submit to result. Do not compare `submit` or `poll` with sync, and ignore the `Aggregated` row because it mixes in the polling requests.
- `latency_ms` in a response covers inference only. A job's `queue_ms` is the time it waited in the queue.

## Docker

```powershell
docker build -t multimodel-async .
docker run --rm -p 8000:8000 -v "$env:USERPROFILE\.cache\huggingface:/root/.cache/huggingface" multimodel-async
# GPU: add --gpus all
```

## Current limitations

- Jobs are kept in memory: they are lost on restart, and the `jobs` dict grows with every job.
- Run **one** uvicorn process only. With `--workers`, each process has its own queue and polling returns 404.
- A single worker processes jobs one by one, so a fast job waits behind a slow one.
- `callback_url` is not validated, so do not expose this server to the internet.

## Experiments to try

1. One worker per model, compared on `job_total` with the single-worker version.
2. `LOAD_MODE=lazy` against `eager` on the first request.
3. A maximum queue length that returns `429` when full.

## Credits

Based on parts 02 (async jobs), 03 (multi-model server) and 04 (load testing) of
[dangnha/vqa-deployment-in-production](https://github.com/dangnha/vqa-deployment-in-production).

The COCO sample image comes from the COCO 2017 validation set (https://cocodataset.org), under a Creative Commons license.
