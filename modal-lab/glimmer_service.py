"""Modal app: per-agent persistent memory (free tier, no GPU).

The agent-memory Volume carries all state; compute is disposable by design.
Smoke:   modal run modal-lab/glimmer_service.py   (run twice; second run must
         see run one's rows)
The GPU endpoint lives in glimmer_endpoint.py and needs a payment method on
the Modal account: Modal refuses to register an A100 function without one,
which is why the two apps are separate files.
"""

import json

import modal

app = modal.App("glimmer-lab")

agent_memory = modal.Volume.from_name("agent-memory", create_if_missing=True)


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
