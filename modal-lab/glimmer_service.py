"""Modal app: Muse Glimmer 30B endpoint + per-agent persistent memory.

Two Volumes carry all state; compute is disposable by design:
  glimmer-model-cache  HF weights cache, so cold starts skip the 60GB download
  agent-memory         one append-only JSONL ledger per agent id

Serve:   modal deploy modal-lab/glimmer_service.py
Smoke:   modal run modal-lab/glimmer_service.py   (memory only, no GPU spend)
"""

import json
import subprocess

import modal

app = modal.App("glimmer-lab")

MODEL = "meta-models/Muse-Glimmer-30B"
PORT = 8000

model_cache = modal.Volume.from_name("glimmer-model-cache", create_if_missing=True)
agent_memory = modal.Volume.from_name("agent-memory", create_if_missing=True)

vllm_image = (
    modal.Image.from_registry("vllm/vllm-openai:latest")
    .env({"HF_HOME": "/cache"})
)


@app.function(
    image=vllm_image,
    gpu="A100-80GB",
    volumes={"/cache": model_cache},
    timeout=60 * 30,
    scaledown_window=120,  # idle GPU dies after 2 min; per-second billing stops
)
@modal.concurrent(max_inputs=4)
@modal.web_server(PORT, startup_timeout=60 * 15)
def serve():
    subprocess.Popen(
        [
            "vllm", "serve", MODEL,
            "--served-model-name", "muse-glimmer-30b",
            "--port", str(PORT),
            "--max-model-len", "131072",
        ]
    )


@app.function(volumes={"/memory": agent_memory})
def remember(agent_id: str, record: dict) -> int:
    """Write-through one memory row; returns the agent's row count.

    The commit() is the whole experiment: without it the write is process-RAM
    with a filesystem costume, and dies with the container.
    """
    path = f"/memory/{agent_id}.jsonl"
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")
    agent_memory.commit()
    with open(path) as f:
        return sum(1 for _ in f)


@app.function(volumes={"/memory": agent_memory})
def recall(agent_id: str) -> list[dict]:
    agent_memory.reload()
    try:
        with open(f"/memory/{agent_id}.jsonl") as f:
            return [json.loads(line) for line in f]
    except FileNotFoundError:
        return []


@app.local_entrypoint()
def main():
    """Memory persistence smoke test. Run twice; second run must see run one."""
    n = remember.remote("smoke-agent", {"event": "smoke", "note": "written by modal run"})
    rows = recall.remote("smoke-agent")
    print(f"ledger rows for smoke-agent: {n}")
    print(f"last row: {rows[-1] if rows else None}")
    print("PERSISTED across runs" if n > 1 else "first run; run again to prove persistence")
