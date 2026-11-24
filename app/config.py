from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List


APP_NAME = "SesYaz"
DATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / APP_NAME
CONFIG_PATH = DATA_DIR / "config.json"
HISTORY_PATH = DATA_DIR / "history.json"

DEFAULT_VOCABULARY = [
    "Claude",
    "Claude Code",
    "Antigravity",
    "Git",
    "GitHub",
    "Vercel",
    "API",
    "TypeScript",
    "React",
    "Next.js",
    "Python",
    "PySide6",
    "WebSocket",
    "bug",
    "commit",
    "push",
    "deploy",
    "branch",
]


def discover_local_gemini_keys() -> List[str]:
    """Read Gemini API keys from environment variables or local .env files."""
    candidates = [
        Path.cwd() / ".env",
        Path.cwd() / ".env.local",
        DATA_DIR / ".env",
    ]
    found: List[str] = []
    for env_var in ("GEMINI_API_KEY", "GEMINI_API_KEYS"):
        raw_env = os.environ.get(env_var, "").strip()
        if raw_env:
            for part in raw_env.split(","):
                tok = part.strip().strip('"').strip("'")
                if tok and tok not in found:
                    found.append(tok)

    key_pattern = re.compile(r"^(?:GEMINI_API_KEYS?|OPENAI_API_KEY)\s*=\s*(.+)$")
    for path in candidates:
        if not path.exists():
            continue
        try:
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                m = key_pattern.match(line)
                if not m:
                    continue
                raw = m.group(1).strip().strip('"').strip("'")
                for part in raw.split(","):
                    token = part.strip()
                    if token and token.startswith(("AQ.", "AIza")) and token not in found:
                        found.append(token)
        except OSError:
            continue
    return found


@dataclass
class AppConfig:
    api_keys: List[str] = field(default_factory=discover_local_gemini_keys)
    ptt_key: str = "rctrl"
    toggle_hotkey: str = "ctrl+shift+space"
    dictation_mode: str = "accurate"      # "accurate" | "polish"
    transcription_mode: str = "verbatim"  # "verbatim" | "smart"
    language_mode: str = "az-tech"        # "az-tech" | "az" | "en" | "auto"
    typing_mode: str = "smart"        # "smart" | "unicode" | "paste"
    auto_enter: bool = False
    device_index: int | None = None
    autostart: bool = True
    sound_cue: bool = True
    pill_position: str = "bottom"     # "bottom" | "top"
    custom_vocabulary: List[str] = field(default_factory=lambda: list(DEFAULT_VOCABULARY))

    @classmethod
    def load(cls) -> "AppConfig":
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        discovered = discover_local_gemini_keys()
        if not CONFIG_PATH.exists():
            cfg = cls(api_keys=discovered)
            cfg.save()
            return cfg
        try:
            raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            cfg = cls()
            for key_name in asdict(cfg).keys():
                if key_name in raw and raw[key_name] is not None:
                    setattr(cfg, key_name, raw[key_name])
            # Merge newly discovered local keys if missing
            merged_keys = list(cfg.api_keys or [])
            for k in discovered:
                if k not in merged_keys:
                    merged_keys.append(k)
            cfg.api_keys = merged_keys
            return cfg
        except Exception:
            return cls(api_keys=discovered)

    def save(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def load_history() -> list[dict]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not HISTORY_PATH.exists():
        return []
    try:
        data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_history(items: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(
        json.dumps(items[:200], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
