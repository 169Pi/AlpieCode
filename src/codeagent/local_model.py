"""
Local GGUF model engine for AlpieCode.

Downloads and caches GGUF models from HuggingFace (`169Pi/Alpie_learn_prototype_GGUF_NEW`).
Runs local inference via `llama-cpp-python` with automatic GPU acceleration / CPU fallback.
Provides an OpenAI-compatible `create_chat_completion` interface.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

CACHE_DIR = Path.home() / ".alpiecode" / "models"
DEFAULT_REPO = "169Pi/Alpie_learn_prototype_GGUF_NEW"
DEFAULT_CTX_SIZE = 32768  # 32k tokens default for fast loading (supports up to 256k)

# Preload WSL NVIDIA CUDA driver if running under WSL
if sys.platform.startswith("linux"):
    try:
        import ctypes
        wsl_cuda = Path("/usr/lib/wsl/lib/libcuda.so.1")
        if wsl_cuda.exists():
            ctypes.CDLL(str(wsl_cuda), mode=ctypes.RTLD_GLOBAL)
    except Exception:
        pass


# ── GPU Auto-Detection ────────────────────────────────────────────────

def detect_gpu() -> int:
    """
    Detect if CUDA/Metal GPU offloading is supported in llama-cpp-python.
    Automatically calculates optimal GPU layer offload to prevent 6GB VRAM OOM crashes.
    """
    if os.environ.get("CUDA_VISIBLE_DEVICES") == "-1":
        return 0

    try:
        import llama_cpp
        if getattr(llama_cpp, "llama_supports_gpu_offload", lambda: False)():
            # Check total VRAM via nvidia-smi
            try:
                import subprocess
                res = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=2
                )
                if res.returncode == 0 and res.stdout.strip():
                    vram_mb = int(res.stdout.strip().split("\n")[0])
                    if vram_mb <= 6500:  # 6GB VRAM GPU (e.g. RTX 3050 Laptop)
                        return 26  # Offload 26 layers to GPU, keep 2.0GB VRAM free to prevent CUDA OOM
            except Exception:
                pass
            return -1  # 8GB+ VRAM, offload all layers
    except Exception:
        pass

    return 0  # CPU fallback


# ── Model Downloader ─────────────────────────────────────────────────

def download_model(repo_id: str = DEFAULT_REPO, token: Optional[str] = None) -> Path:
    """
    Download single GGUF model from HuggingFace using huggingface_hub.
    Saves to ~/.alpiecode/models/ and returns the local Path.
    
    OFFLINE-FIRST: Checks local cache before any network call.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    hf_token = token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")

    # ── STEP 1: Check local cache FIRST (zero network) ───────────────
    local_gguf = list(CACHE_DIR.glob("*.gguf"))
    # Filter out mmproj files for main model
    local_main = [f for f in local_gguf if "mmproj" not in f.name.lower()]
    if local_main:
        return local_main[0]
    if local_gguf:
        return local_gguf[0]

    # ── STEP 2: Model not cached — must download from HuggingFace ────
    try:
        from huggingface_hub import hf_hub_download, list_repo_files
    except ImportError:
        raise RuntimeError(
            "huggingface_hub package is missing. Install it with: pip install huggingface_hub"
        )

    # List files in repo to find the GGUF file
    try:
        files = list_repo_files(repo_id=repo_id, token=hf_token)
        gguf_files = [f for f in files if f.endswith(".gguf")]
    except Exception as e:
        # No cached model AND no internet — clear error with instructions
        raise RuntimeError(
            "\n╭──────────────────────────────────────────────────────────────╮\n"
            "│  GGUF model not found locally and no internet to download.  │\n"
            "│                                                             │\n"
            "│  First-time setup requires internet to download the model.  │\n"
            "│  Connect to internet and run:                               │\n"
            "│    alpiecode init                                           │\n"
            "│                                                             │\n"
            "│  After the one-time download, offline mode works forever.   │\n"
            "╰──────────────────────────────────────────────────────────────╯"
        ) from e

    # Separate main model file from mmproj (vision projector) file
    main_gguf_files = [f for f in gguf_files if "mmproj" not in f.lower()]
    mmproj_files = [f for f in gguf_files if "mmproj" in f.lower()]

    if not main_gguf_files:
        main_gguf_files = gguf_files

    target_file = main_gguf_files[0]
    cached_file = CACHE_DIR / target_file

    if not cached_file.exists():
        print(f"📥 Downloading local model from HuggingFace ({repo_id}/{target_file})...")
        print("   This is a one-time download. Subsequent runs will work 100% offline.")
        try:
            hf_hub_download(
                repo_id=repo_id,
                filename=target_file,
                local_dir=CACHE_DIR,
                token=hf_token,
            )
        except Exception as e:
            err_str = str(e)
            if "403" in err_str or "storage limit" in err_str.lower() or "forbidden" in err_str.lower():
                raise RuntimeError(
                    f"HuggingFace 403 Forbidden Error for repo '{repo_id}':\n"
                    "   'Private repository storage limit reached for 169Pi account.'\n"
                    "   💡 Please ask your 169Pi organization admin to upgrade the HF storage plan or free up space on HuggingFace."
                ) from e
            raise RuntimeError(f"HuggingFace Download Failed for '{repo_id}/{target_file}': {e}") from e

    # Download mmproj file if available (for vision features)
    if mmproj_files:
        mmproj_target = mmproj_files[0]
        mmproj_cached = CACHE_DIR / mmproj_target
        if not mmproj_cached.exists():
            try:
                print(f"📥 Downloading vision projector ({repo_id}/{mmproj_target})...")
                hf_hub_download(
                    repo_id=repo_id,
                    filename=mmproj_target,
                    local_dir=CACHE_DIR,
                    token=hf_token,
                )
            except Exception as e:
                print(f"⚠️ Could not download vision projector ({mmproj_target}): {e}")

    return cached_file


# ── Local Model Engine Class ──────────────────────────────────────────

def _ensure_llama_cpp():
    """Auto-install pre-compiled binary wheel for llama-cpp-python if missing."""
    try:
        from llama_cpp import Llama
        return Llama
    except ImportError:
        pass

    print("⚙️  Auto-installing pre-compiled local GGUF engine (one-time setup)...")
    import sys
    import subprocess

    is_win = sys.platform == "win32"
    if is_win:
        wheel_url = "https://github.com/abetlen/llama-cpp-python/releases/download/v0.3.34-vulkan/llama_cpp_python-0.3.34-py3-none-win_amd64.whl"
    else:
        wheel_url = "https://github.com/abetlen/llama-cpp-python/releases/download/v0.3.34-vulkan/llama_cpp_python-0.3.34-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl"

    installed = False
    for cmd_base in [["uv", "pip", "install", wheel_url], [sys.executable, "-m", "pip", "install", wheel_url]]:
        try:
            res = subprocess.run(cmd_base, capture_output=True, text=True, timeout=120)
            if res.returncode == 0:
                installed = True
                break
        except Exception:
            continue

    try:
        from llama_cpp import Llama
        print("✅ Pre-compiled local GGUF engine installed successfully!")
        return Llama
    except ImportError:
        raise RuntimeError(
            "\n╭────────────────────────────────────────────────────────────╮\n"
            "│  Failed to auto-install local GGUF engine.               │\n"
            "│  Please check your internet connection for first setup.    │\n"
            "╰────────────────────────────────────────────────────────────╯"
        )


class LocalModel:
    def __init__(self, repo_id: str = DEFAULT_REPO, n_ctx: int = DEFAULT_CTX_SIZE,
                 n_gpu_layers: Optional[int] = None, token: Optional[str] = None):
        self.repo_id = repo_id
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers if n_gpu_layers is not None else detect_gpu()
        self.token = token
        self.model_path: Optional[Path] = None
        self._llm = None

    def ensure_model(self) -> Path:
        """Download model if not present."""
        if not self.model_path or not self.model_path.exists():
            self.model_path = download_model(self.repo_id, token=self.token)
        return self.model_path

    def load(self):
        """Load the model into memory via llama-cpp-python."""
        if self._llm is not None:
            return self._llm

        model_path = self.ensure_model()
        Llama = _ensure_llama_cpp()

        print(f"🧠 Loading local GGUF model: {model_path.name}")
        print(f"   Context Window: {self.n_ctx} tokens | Acceleration: {'GPU (-1)' if self.n_gpu_layers != 0 else 'CPU (0)'}")

        n_threads = max(1, (os.cpu_count() or 4) - 1)
        self._llm = Llama(
            model_path=str(model_path),
            n_ctx=self.n_ctx,
            n_batch=4096,        # Large batch for fast prompt evaluation on GPU
            n_threads=n_threads,  # Maximize multi-threading for CPU layers
            n_gpu_layers=self.n_gpu_layers,
            use_mmap=True,       # Instant memory-mapped loading
            flash_attn=True,     # Flash Attention for faster GPU inference
            verbose=False,
        )
        return self._llm

    def create_chat_completion(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None,
                               temperature: float = 0.2, max_tokens: int = 4096, **kwargs) -> Any:
        """
        Run inference matching OpenAI chat completions interface.
        Returns a dot-accessible structure (resp.choices[0].message).
        """
        llm = self.load()
        
        enable_thinking = kwargs.get("enable_thinking", True)
        
        # When thinking is disabled, inject assistant prefill to skip reasoning tokens
        # This eliminates ~6s of thinking token generation per turn
        if not enable_thinking:
            msgs = list(messages) + [{"role": "assistant", "content": "<think>\n\n</think>\n\n"}]
        else:
            msgs = messages

        params = {
            "messages": msgs,
            "temperature": 0.1 if not enable_thinking else temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            params["tools"] = tools
            params["tool_choice"] = kwargs.get("tool_choice", "auto")

        result_dict = llm.create_chat_completion(**params)
        return _DictWrapper(result_dict)


# ── OpenAI-style Object Wrapper ───────────────────────────────────────

class _DictWrapper:
    """Wraps dictionary output from llama-cpp to allow dot-notation (resp.choices[0].message)."""
    def __init__(self, data: dict):
        self._data = data

    @property
    def choices(self):
        return [_ChoiceWrapper(c) for c in self._data.get("choices", [])]


class _ChoiceWrapper:
    def __init__(self, data: dict):
        self._data = data

    @property
    def message(self):
        return _MessageWrapper(self._data.get("message", {}))


class _MessageWrapper:
    def __init__(self, data: dict):
        self._data = data

    @property
    def content(self):
        return self._data.get("content")

    @property
    def role(self):
        return self._data.get("role", "assistant")

    @property
    def reasoning(self):
        return self._data.get("reasoning") or self._data.get("reasoning_content")

    @property
    def reasoning_content(self):
        return self.reasoning

    @property
    def tool_calls(self):
        raw_tc = self._data.get("tool_calls")
        if not raw_tc:
            return None
        return [_ToolCallWrapper(tc) for tc in raw_tc]


class _ToolCallWrapper:
    def __init__(self, data: dict):
        self._data = data

    @property
    def id(self):
        return self._data.get("id", "call_local")

    @property
    def type(self):
        return self._data.get("type", "function")

    @property
    def function(self):
        return _FunctionWrapper(self._data.get("function", {}))


class _FunctionWrapper:
    def __init__(self, data: dict):
        self._data = data

    @property
    def name(self):
        return self._data.get("name")

    @property
    def arguments(self):
        args = self._data.get("arguments")
        if isinstance(args, dict):
            import json
            return json.dumps(args)
        return args or "{}"
