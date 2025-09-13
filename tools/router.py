import os, time, shutil, re
from pathlib import Path
from datetime import datetime

try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML is required. Run: python -m pip install pyyaml")

ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "sandbox" / "in"
ROUTED = ROOT / "sandbox" / "routed"

# Extensions for which front matter is stripped when type==script
STRIP_FOR_EXEC_EXTS = {".py", ".ps1", ".sh"}

DEFAULTS = {
    ("doc","edinet","ingestion"): "docs/design",
    ("doc","tdnet","ingestion"):  "docs/design",
    ("doc","news","ingestion"):   "docs/design",
    ("doc","features","analysis"):"docs/design",
    ("doc","model","analysis"):   "docs/design",
    ("doc","eval","analysis"):    "docs/design",
    ("script","edinet","ingestion"): "src/ingestion",
    ("script","tdnet","ingestion"):  "src/ingestion",
    ("script","yahoo","ingestion"):  "src/ingestion",
    ("script","features","analysis"): "src/features",
    ("script","model","training"):    "src/models",
    ("script","eval","evaluation"):   "src/evaluation",
    ("data","edinet","ingestion"):    "data/raw/edinet",
    ("data","tdnet","ingestion"):     "data/raw/tdnet",
    ("data","yahoo","ingestion"):     "data/raw/yahoo",
    ("report","eval","report"):       "reports/research",
    ("log","*", "*"):                 "logs/app",
}

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*", re.DOTALL)

def parse_front_matter(text):
    m = FM_RE.match(text)
    if not m:
        return None
    y = yaml.safe_load(m.group(1))
    return y.get("alphaultra", None) if isinstance(y, dict) else None

def decide_target(meta):
    tgt = meta.get("target_dir")
    if tgt and tgt != "auto":
        return tgt
    exp_id = meta.get("experiment_id")
    if exp_id:
        return f"experiments/{exp_id}"
    key = (meta.get("type"), meta.get("topic"), meta.get("task"))
    if key in DEFAULTS:
        return DEFAULTS[key]
    for (t, c, k), v in DEFAULTS.items():
        if (t in (meta.get("type"), "*")) and (c in (meta.get("topic"), "*")) and (k in (meta.get("task"), "*")):
            return v
    return "docs"

def strip_front_matter_if_needed(text, dest_path, meta):
    """
    If a script file contains YAML front matter, strip it so the file is directly executable.
    Non-script destinations (e.g., docs) keep the front matter.
    """
    ext = dest_path.suffix.lower()
    if meta.get("type") != "script":
        return text
    if ext not in STRIP_FOR_EXEC_EXTS:
        return text
    m = FM_RE.match(text)
    if not m:
        return text
    return text[m.end():].lstrip()

def route_file(p: Path):
    txt = p.read_text(encoding="utf-8", errors="ignore")
    meta = parse_front_matter(txt)
    if not meta:
        raise ValueError("No alphaultra front matter found")
    rel = decide_target(meta)
    dest_dir = ROOT / rel
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / p.name

    if dest.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = dest_dir / f"{stamp}_{p.name}"

    txt2 = strip_front_matter_if_needed(txt, dest, meta)
    if txt2 is not None and txt2 != txt:
        dest.write_text(txt2, encoding="utf-8")
        (ROUTED).mkdir(parents=True, exist_ok=True)
        try:
            p.rename(ROUTED / p.name)
        except Exception:
            try:
                p.unlink()
            except Exception:
                pass
    else:
        shutil.move(str(p), str(dest))

    return str(dest)

def main():
    INBOX.mkdir(parents=True, exist_ok=True)
    (ROUTED / "_errors").mkdir(parents=True, exist_ok=True)
    print(f"[router] watching {INBOX}")
    while True:
        for p in list(INBOX.glob("*")):
            if p.is_file():
                try:
                    dest = route_file(p)
                    with open(ROUTED / "routed.log", "a", encoding="utf-8") as f:
                        f.write(f"{datetime.now().isoformat()} | {p.name} -> {dest}\n")
                except Exception as e:
                    err = ROUTED / "_errors" / p.name
                    try:
                        shutil.move(str(p), str(err))
                    except Exception:
                        pass
                    with open(ROUTED / "errors.log", "a", encoding="utf-8") as f:
                        f.write(f"{datetime.now().isoformat()} | {p.name} | {e}\n")
        time.sleep(2)

if __name__ == "__main__":
    main()
