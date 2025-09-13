import os, time, json, re
from typing import Dict, Any, Optional
import requests
from datetime import datetime, timezone

SEC_DEFAULT_BASE = "https://data.sec.gov"

def build_session(user_agent: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": user_agent,
        "Accept": "application/json, text/plain, */*",
    })
    return s

class RateLimiter:
    def __init__(self, per_sec: float = 9.0):
        self.min_interval = 1.0 / per_sec if per_sec > 0 else 0.2
        self._last = 0.0
    def wait(self):
        import time
        now = time.perf_counter()
        dt = now - self._last
        if dt < self.min_interval:
            time.sleep(self.min_interval - dt)
        self._last = time.perf_counter()

def ensure_dir(p):
    import pathlib
    p = pathlib.Path(p)
    p.mkdir(parents=True, exist_ok=True)
    return p

def iso_utc(dt_str: str) -> str:
    # SEC acceptanceDatetime is "YYYY-MM-DDTHH:MM:SS.000Z" or "YYYY-MM-DD HH:MM:SS"
    try:
        return datetime.fromisoformat(dt_str.replace("Z","").replace(" ", "T")).replace(tzinfo=timezone.utc).isoformat()
    except Exception:
        return dt_str

def get_env_user_agent(env_key: str) -> str:
    ua = os.environ.get(env_key, "").strip()
    if not ua:
        raise RuntimeError(f"Set environment variable {env_key} to a valid SEC User-Agent, e.g., 'youremail@example.com AlphaUltra/1.0'")
    return ua

def save_json(obj: Dict[str, Any], path):
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
