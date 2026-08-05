"""
Per-user config for AlpieCode.

Resolution order (highest priority first):
  1. Environment variables: HF_TOKEN, ALPIECODE_MODEL_REPO, etc.
  2. ~/.alpiecode/config.json (written by `alpiecode init`)
  3. Built-in defaults (Local GGUF model: 169Pi/Alpie_learn_prototype_GGUF_NEW)
"""

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".alpiecode"
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULTS = {
    "model_repo": "169Pi/Alpie_learn_prototype_GGUF_NEW",
    "hf_token": None,
    "max_turns": 30,
    "temperature": 0.2,
    "max_tokens": 16384,
    "enable_thinking": True,
    "n_ctx": 32768,  # 32k context window (loads in ~2s; configurable up to 256k)
    "n_gpu_layers": None,  # None = auto-detect GPU
}


@dataclass
class Config:
    model_repo: str = "169Pi/Alpie_learn_prototype_GGUF_NEW"
    hf_token: Optional[str] = None
    max_turns: int = 30
    temperature: float = 0.2
    max_tokens: int = 16384
    enable_thinking: bool = True
    n_ctx: int = 32768
    n_gpu_layers: Optional[int] = None

    # Legacy fields compatibility
    base_url: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None


def load_config() -> Config:
    data = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            data.update(json.loads(CONFIG_PATH.read_text()))
        except Exception:
            pass

    # env vars override saved file
    if os.environ.get("HF_TOKEN"):
        data["hf_token"] = os.environ["HF_TOKEN"]
    if os.environ.get("ALPIECODE_MODEL_REPO"):
        data["model_repo"] = os.environ["ALPIECODE_MODEL_REPO"]
    if os.environ.get("ALPIECODE_CPU") == "1":
        data["n_gpu_layers"] = 0

    return Config(**data)


def save_config(cfg: Config) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(asdict(cfg), indent=2))


def interactive_init() -> Config:
    current = load_config()
    print("AlpieCode Setup — Local GGUF Model Configuration\n")

    print("AlpieCode uses the 169Pi/Alpie_learn_prototype_GGUF_NEW model from HuggingFace.")
    print("Please enter your HuggingFace user access token (required to download model).\n")

    token_prompt = f"HuggingFace Token [{current.hf_token or 'none'}]: "
    hf_token = input(token_prompt).strip() or current.hf_token

    repo_prompt = f"Model Repo [{current.model_repo}]: "
    model_repo = input(repo_prompt).strip() or current.model_repo

    cfg = Config(
        model_repo=model_repo,
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

    return cfg
