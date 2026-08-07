"""
Per-user config for AlpieCode.

Resolution order (highest priority first):
  1. Environment variables: HF_TOKEN, ALPIECODE_MODEL_REPO, etc.
  2. ~/.alpiecode/config.json (written by `alpiecode init`)
  3. Built-in defaults (Local GGUF model: 169Pi/Alpie_learn_prototype_GGUF_NEW)
"""

import json
import os
import socket
from dataclasses import dataclass, asdict, fields
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".alpiecode"
CONFIG_PATH = CONFIG_DIR / "config.json"

# Config version — bump this when defaults change to trigger auto-migration
CONFIG_VERSION = 2  # v2: n_ctx upgraded 16384 → 32768

DEFAULTS = {
    "base_url": "http://20.245.200.125:8000/v1",  # Remote VLM server endpoint
    "model": "169Pi/grpo_phase_2_merged",
    "model_repo": "169Pi/Alpie_learn_prototype_GGUF_NEW",
    "api_key": "not-needed",
    "hf_token": None,
    "max_turns": 30,
    "temperature": 0.2,
    "max_tokens": 16384,
    "enable_thinking": True,
    "n_ctx": 32768,  # 32k context window (model supports up to 131k)
    "n_gpu_layers": None,  # None = auto-detect GPU
    "config_version": CONFIG_VERSION,
}


def is_server_reachable(base_url: Optional[str], timeout: float = 0.4) -> bool:
    """Fast network ping check (0.4s max) to see if server endpoint is online."""
    if not base_url:
        return False
    try:
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if not host:
            return False
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def is_internet_available(timeout: float = 1.0) -> bool:
    """Quick check if general internet is available (ping Google DNS)."""
    try:
        with socket.create_connection(("8.8.8.8", 53), timeout=timeout):
            return True
    except Exception:
        return False


@dataclass
class Config:
    base_url: Optional[str] = None
    model: str = "169Pi/grpo_phase_2_merged"          # Server API model name (vLLM)
    model_repo: str = "169Pi/Alpie_learn_prototype_GGUF_NEW"  # HuggingFace repo for offline GGUF
    api_key: str = "not-needed"
    hf_token: Optional[str] = None
    max_turns: int = 30
    temperature: float = 0.2
    max_tokens: int = 16384
    enable_thinking: bool = True
    n_ctx: int = 32768
    n_gpu_layers: Optional[int] = None


def load_config() -> Config:
    data = dict(DEFAULTS)
    needs_save = False
    if CONFIG_PATH.exists():
        try:
            saved_data = json.loads(CONFIG_PATH.read_text())
            # Skip null values so they don't override smart defaults (e.g. base_url)
            data.update({k: v for k, v in saved_data.items() if v is not None})

            # ── Auto-migrate stale configs ────────────────────────────
            saved_version = saved_data.get("config_version", 1)
            if saved_version < CONFIG_VERSION:
                # v1 → v2: n_ctx was 16384, upgrade to 32768
                if saved_data.get("n_ctx") == 16384:
                    data["n_ctx"] = 32768
                data["config_version"] = CONFIG_VERSION
                needs_save = True
        except Exception:
            pass

    # env vars override saved file
    for prefix in ("ALPIECODE_", "CODEAGENT_"):
        if os.environ.get(f"{prefix}BASE_URL"):
            data["base_url"] = os.environ[f"{prefix}BASE_URL"]
        if os.environ.get(f"{prefix}MODEL"):
            data["model"] = os.environ[f"{prefix}MODEL"]
        if os.environ.get(f"{prefix}MODEL_REPO"):
            data["model_repo"] = os.environ[f"{prefix}MODEL_REPO"]
        if os.environ.get(f"{prefix}API_KEY"):
            data["api_key"] = os.environ[f"{prefix}API_KEY"]
    if os.environ.get("HF_TOKEN"):
        data["hf_token"] = os.environ["HF_TOKEN"]
    if os.environ.get("ALPIECODE_CPU") == "1":
        data["n_gpu_layers"] = 0

    # Filter data to only keys present in Config fields
    valid_keys = {f.name for f in fields(Config)}
    filtered_data = {k: v for k, v in data.items() if k in valid_keys}
    cfg = Config(**filtered_data)

    # Auto-save migrated config
    if needs_save:
        try:
            save_config(cfg)
        except Exception:
            pass

    return cfg


def save_config(cfg: Config) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(asdict(cfg), indent=2))


def interactive_init() -> Config:
    current = load_config()
    print("AlpieCode Setup — Local GGUF Model Configuration\n")

    print("AlpieCode uses the 169Pi/Alpie_learn_prototype_GGUF_NEW model from HuggingFace.")
    print("Please enter your HuggingFace user access token (required to download model).\n")

    # Mask token for display (show first 3 + last 3 chars only)
    if current.hf_token:
        t = current.hf_token
        masked = f"{t[:3]}***{t[-3:]}" if len(t) > 6 else "***"
    else:
        masked = "none"
    token_prompt = f"HuggingFace Token [{masked}]: "
    hf_token = input(token_prompt).strip() or current.hf_token

    repo_prompt = f"Model Repo [{current.model_repo}]: "
    model_repo = input(repo_prompt).strip() or current.model_repo

    cfg = Config(
        base_url=current.base_url,
        model=current.model,
        model_repo=model_repo,
        api_key=current.api_key,
        hf_token=hf_token,
        max_turns=current.max_turns,
        temperature=current.temperature,
        max_tokens=current.max_tokens,
        enable_thinking=current.enable_thinking,
        n_ctx=current.n_ctx,
        n_gpu_layers=current.n_gpu_layers,
    )
    save_config(cfg)
    print(f"\n✅ Config saved to {CONFIG_PATH}")

    # Trigger model download test if token provided
    try:
        from .local_model import download_model
        print("\n📥 Testing HuggingFace model download...")
        local_path = download_model(repo_id=cfg.model_repo, token=cfg.hf_token)
        print(f"✅ Model downloaded & cached at: {local_path}")
    except Exception as e:
        print(f"⚠️ Could not download model right now: {e}")
        print("   Model will be downloaded automatically on first task execution.")

    # Pre-install llama-cpp-python binary wheel (so offline mode works immediately)
    try:
        from .local_model import _ensure_llama_cpp
        print("\n⚙️  Setting up offline GGUF engine...")
        _ensure_llama_cpp()
        print("✅ Offline mode ready — works without internet from now on!")
    except Exception as e:
        print(f"⚠️ Could not setup offline engine: {e}")
        print("   It will be installed automatically when needed.")

    return cfg
