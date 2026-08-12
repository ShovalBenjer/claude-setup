"""Modal app: Muse Glimmer 30B endpoint (GPU; needs a payment method on the account).

Deploy: modal deploy modal-lab/glimmer_endpoint.py
First cold start downloads ~60GB of weights into the cache Volume; later cold
starts skip it. scaledown_window kills the idle GPU after 2 minutes, so cost
is per-second of actual use.
"""

import subprocess

import modal

app = modal.App("glimmer-endpoint")

MODEL = "meta-models/Muse-Glimmer-30B"
PORT = 8000

model_cache = modal.Volume.from_name("glimmer-model-cache", create_if_missing=True)

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
