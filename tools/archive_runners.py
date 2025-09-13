import pathlib, shutil

ROOT = pathlib.Path("C:/AI/AlphaUltra/tools")
ARC = ROOT / "archive"
ARC.mkdir(parents=True, exist_ok=True)
moved = 0
for p in ROOT.glob("*_run_experiment.py"):
    try:
        shutil.move(str(p), ARC / p.name)
        moved += 1
    except Exception:
        pass
print(f"[archive] moved {moved} runner(s) to archive")

