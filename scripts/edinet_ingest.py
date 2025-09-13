import os, requests, time, yaml, json, pytz
from datetime import date, timedelta
from pathlib import Path
from utils.io_utils import ensure_dir, now_utc_str
from utils.log_utils import get_logger
logger = get_logger(); JST = pytz.timezone("Asia/Tokyo")

def list_docs(base_url, d: date, api_key: str|None):
    url = f"{base_url}/documents.json"
    params = {"date": d.strftime("%Y-%m-%d"), "type": 2}  # ← 必須
    if "api.edinet-fsa.go.jp" in base_url and api_key:
        params["Subscription-Key"] = api_key
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def main(cfg_path: str):
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    root = Path(cfg["paths"]["root"]); reports = Path(cfg["paths"]["reports"])
    base = cfg["vendor"].get("api_base","https://disclosure2dl.edinet-fsa.go.jp/api/v2")
    api_key = os.environ.get(cfg["vendor"].get("api_key_env",""))
    include_kw = (cfg.get("filters",{}) or {}).get("include_keywords", [])
    days = int(cfg.get("days",7)); sleep = float(cfg.get("rate_limit",{}).get("min_sleep_sec",1.0))
    collected = 0
    for i in range(days):
        day = date.today() - timedelta(days=i)
        try:
            js = list_docs(base, day, api_key)
        except Exception as e:
            logger.warning(f"list_docs fail {day}: {e}"); time.sleep(sleep); continue
        docs = js.get("results") or js.get("documents") or []
        for rec in docs:
            desc = rec.get("docDescription") or ""
            if include_kw and not any(k in desc for k in include_kw):  # フィルタ有効時のみ絞る
                continue
            doc_id = rec.get("docID") or rec.get("docId") or rec.get("docid")
            if not doc_id: continue
            meta = {
                "docID": doc_id,
                "edinetCode": rec.get("edinetCode"),
                "secCode": rec.get("secCode"),
                "filerName": rec.get("filerName"),
                "docTypeCode": rec.get("docTypeCode"),
                "docDescription": desc,
                "submitDateTime": rec.get("submitDateTime"),
                "periodStart": rec.get("periodStart"),
                "periodEnd": rec.get("periodEnd"),
                "asof_ts": now_utc_str(),
                "source": f"{base}/documents.json?date={day}&type=2"
            }
            day_dir = ensure_dir(root / day.strftime("%Y-%m-%d") / doc_id)
            (day_dir / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            collected += 1
        time.sleep(sleep)
    reports.mkdir(parents=True, exist_ok=True)
    (reports/"edinet_status.txt").write_text(f"base={base} collected={collected}", encoding="utf-8")
    logger.info(f"edinet collected meta: {collected}")

if __name__ == "__main__":
    import argparse; ap=argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/edinet.yaml")
    args=ap.parse_args(); main(args.config)
