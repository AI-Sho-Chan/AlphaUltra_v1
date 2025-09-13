import runpy, pathlib, sys

ROOT = pathlib.Path("C:/AI/AlphaUltra")
candidates = [
    ROOT / "tools/features_engineer.py",
    ROOT / "tools/features_engineering_impl.py",
]
for p in candidates:
    if p.exists():
        runpy.run_path(str(p))
        print(f"[features] delegated -> {p}")
        sys.exit(0)
raise SystemExit("No features implementation found (expected tools/features_engineer.py)")

