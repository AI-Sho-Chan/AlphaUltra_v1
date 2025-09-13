import json, pathlib, pandas as pd
from datetime import datetime, timezone

ROOT  = pathlib.Path(r"C:\AI\AlphaUltra")
LIVE  = ROOT/"reports/live"
STATE = ROOT/"data/live"
latest = LIVE/"alerts_latest.md"
state  = STATE/"last_top_k.json"
prev   = STATE/"prev_top_k.json"

def main():
    if not state.exists(): 
        print("[delta] no state yet"); return
    cur  = json.loads(state.read_text(encoding="utf-8"))
    prev_list = []
    if prev.exists():
        prev_list = json.loads(prev.read_text(encoding="utf-8")).get("tickers",[])
    cur_list = cur.get("tickers",[])
    add = [t for t in cur_list if t not in prev_list]
    drop= [t for t in prev_list if t not in cur_list]
    if not add and not drop:
        print("[delta] no changes"); return
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    out = LIVE/f"alerts_delta_{now}Z.md"
    lines = ["# Alerts Delta", f"- utc: {datetime.now(timezone.utc).isoformat()}"]
    if add:
        lines += ["","## ADD","| ticker |","|---|"] + [f"| {t} |" for t in add]
    if drop:
        lines += ["","## DROP","| ticker |","|---|"] + [f"| {t} |" for t in drop]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[delta] wrote {out}")
    prev.write_text(json.dumps(cur, ensure_ascii=False), encoding="utf-8")
if __name__=="__main__":
    main()
