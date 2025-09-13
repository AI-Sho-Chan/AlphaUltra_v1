import json, shutil
from pathlib import Path

ROOT = Path("data/raw/filings/us")

def desired_dir(meta_path: Path):
    d = json.loads(meta_path.read_text(encoding="utf-8"))
    cik = str(d.get("cik") or "").zfill(10)
    acc = d.get("accessionNumber")
    if not cik or not acc:
        return None
    return ROOT / cik / acc

def main():
    moved, skipped = 0, 0
    metas = list(ROOT.glob("**/metadata.json"))
    for m in metas:
        target = desired_dir(m)
        if target is None:
            print(f"skip(no keys): {m}")
            skipped += 1
            continue
        cur = m.parent
        if cur == target:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            # already repaired elsewhere
            skipped += 1
            continue
        print(f"MOVE {cur}  ->  {target}")
        shutil.move(str(cur), str(target))
        moved += 1
    print(f"done. moved={moved} skipped={skipped} total_meta={len(metas)}")

if __name__ == "__main__":
    main()
