"""
Per-user config for AlpieCode.

Resolution order (highest priority first):
  1. Environment variables: ALPIECODE_BASE_URL / CODEAGENT_BASE_URL, etc.
  2. ~/.alpiecode/config.json (written by `alpiecode init`)
  3. Built-in defaults (your VLM endpoint)
"""

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path

CONFIG_DIR = Path.home() / ".alpiecode"
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULTS = {
    "base_url": "http://20.245.200.125:8000/v1",
    "model": "169Pi/grpo_phase_2_merged",
    "api_key": "not-needed",
    "max_turns": 30,
    "temperature": 0.2,
    "max_tokens": 16384,
    "enable_thinking": True,
}


@dataclass
class Config:
    base_url: str
    model: str
    api_key: str
    max_turns: int = 30
    temperature: float = 0.2
    max_tokens: int = 16384
    enable_thinking: bool = True


def load_config() -> Config:
    data = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        data.update(json.loads(CONFIG_PATH.read_text()))
    # env vars win over the saved file (support ALPIECODE_* and CODEAGENT_*)
    for env_prefix in ("ALPIECODE_", "CODEAGENT_"):
        if os.environ.get(f"{env_prefix}BASE_URL"):
            data["base_url"] = os.environ[f"{env_prefix}BASE_URL"]
        if os.environ.get(f"{env_prefix}MODEL"):
            data["model"] = os.environ[f"{env_prefix}MODEL"]
        if os.environ.get(f"{env_prefix}API_KEY"):
            data["api_key"] = os.environ[f"{env_prefix}API_KEY"]
    return Config(**data)


def save_config(cfg: Config) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(asdict(cfg), indent=2))


def interactive_init() -> Config:
    current = load_config()
    print("AlpieCode setup — press enter to keep the current/default value.\n")

    base_url = input(f"vLLM/OpenAI-compatible base_url [{current.base_url}]: ").strip() or current.base_url
    model = input(f"served model name [{current.model}]: ").strip() or current.model
    api_key = input(f"api key (blank if none) [{current.api_key}]: ").strip() or current.api_key

    cfg = Config(base_url=base_url, model=model, api_key=api_key, max_turns=current.max_turns,
                 temperature=current.temperature, max_tokens=current.max_tokens)
    save_config(cfg)
    print(f"\nSaved to {CONFIG_PATH}")
    return cfg
