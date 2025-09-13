import sys, yaml

REQ_TOP_KEYS = {"project_meta", "experiments"}
REQ_EXP_KEYS = {"exp_id","hypothesis","data","features","targets","models","validation","evaluation"}

def main(path):
    with open(path, "r", encoding="utf-8") as f:
        y = yaml.safe_load(f)
    missing = REQ_TOP_KEYS - set(y.keys())
    if missing:
        print(f"[SCHEMA] missing top keys: {missing}"); sys.exit(2)
    for i, exp in enumerate(y["experiments"]):
        miss = REQ_EXP_KEYS - set(exp.keys())
        if miss:
            print(f"[SCHEMA] experiments[{i}] missing: {miss}"); sys.exit(2)
    print("[SCHEMA] OK")

if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv)>1 else None
    if not p:
        print("usage: python schema_validate.py <config.yaml>"); sys.exit(1)
    main(p)

