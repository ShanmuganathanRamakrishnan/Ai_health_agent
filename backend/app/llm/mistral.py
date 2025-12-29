"""
Mistral 7B Instruct model interface via llama-cpp-python.
Supports GPU acceleration via CUDA when available.
"""

from pathlib import Path
from threading import Lock
from typing import Optional

from llama_cpp import Llama

# -------------------------------
# Model configuration
# -------------------------------
MODEL_FILENAME = "mistral-7b-instruct.Q4_K_M.gguf"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / MODEL_FILENAME

# Generation parameters
TEMPERATURE = 0.2
MAX_TOKENS = 256
TOP_P = 0.9
N_CTX = 2048

# CPU control (important for laptops)
N_THREADS = 4

# -------------------------------
# Lazy-loaded model state
# -------------------------------
_model: Optional[Llama] = None
_model_lock = Lock()


def _load_model() -> Llama:
    """
    Load the Mistral model exactly once.
    Thread-safe and CPU-safe.
    """
    global _model

    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:
            return _model

        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model file not found: {MODEL_PATH}. "
                "Please download the Mistral 7B Instruct GGUF model."
            )

        _model = Llama(
            model_path=str(MODEL_PATH),
            n_ctx=N_CTX,
            n_threads=N_THREADS,
            n_gpu_layers=-1,  # Enable full GPU offload
            verbose=False,
        )

        return _model


def generate(prompt: str) -> str:
    """
    Generate text from a prompt using Mistral 7B Instruct.
    """
    if not prompt or not prompt.strip():
        return ""

    model = _load_model()

    output = model(
        prompt,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        top_p=TOP_P,
    )

    return output["choices"][0]["text"].strip()
