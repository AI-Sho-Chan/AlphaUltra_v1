import yaml, os, time, json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict
import requests
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from utils.sec_utils import build_session, RateLimiter, ensure_dir, get_env_user_agent, iso_utc, save_json

# Endpoints
# submissions: /submissions/CIK##########.json
# company filings (expanded): /submissions/CIK##########.json has recent filings
# full index or archives not used here for speed.

def date_in_range(dt_iso: str, since: datetime) -> bool:
    try:
        dt = datetime.fromisoformat(dt_iso.replace("Z","")).replace(tzinfo=timezone.utc)
    except Exception:
        return False
    return dt >= since

@retry(wait=wait_exponential(multiplier=1, min=1, max=60),
       stop=stop_after_attempt(5),
       retry=retry_if_exception_type((requests.RequestException,)))
def fetch_json(sess: requests.Session, url: str) -> Dict:
    r = sess.get(url, timeout=30)
    if r.status_code != 200:
        raise requests.RequestException(f"HTTP {r.status_code} for {url}")
    return r.json()

def pick_primary_doc(filing: Dict) -> str:
    # best-effort: prefer "primaryDocument"
    return filing.get("primaryDocument") or ""

def download_primary(sess: requests.Session, base: str, cik: str, accession: str, primary: str, out_dir: Path):
    # Accession no with dashes removed for archives path
    acc_nodash = accession.replace("-", "")
    if not primary:
        return
    url = f"{base}/Archives/edgar/data/{int(cik)}/{acc_nodash}/{primary}"
    resp = sess.get(url, timeout=60)
    if resp.status_code == 200:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / primary).write_bytes(resp.content)

def main(cfg_path: str, days: int, forms: List[str]):
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    ua = get_env_user_agent(cfg["sec"]["user_agent_env"])
    base = cfg["sec"].get("base_url","https://data.sec.gov")
    limiter = RateLimiter(cfg["sec"].get("rate_limit_per_sec",9))

    raw_dir = Path(cfg["paths"]["raw"])
    reports_dir = Path(cfg["paths"]["reports"])
    ensure_dir(raw_dir); ensure_dir(reports_dir)

    sess = build_session(ua)

    since = datetime.now(timezone.utc) - timedelta(days=days)
    target_forms = set(forms or cfg["edgar"]["forms_default"])

    collected = []

    for ticker, cik in cfg["universe"]["us_cik"].items():
        cik10 = str(cik).zfill(10)
        url = f"{base}/submissions/CIK{cik10}.json"
        limiter.wait()
        data = fetch_json(sess, url)
        filings = data.get("filings", {}).get("recent", {})
        count = len(filings.get("accessionNumber", []))
        for i in range(count):
            form = filings["form"][i]
            if form not in target_forms:
                continue
            acc = filings["accessionNumber"][i]
            acc_date = filings.get("acceptanceDateTime", [""]*count)[i]
            dt_iso = iso_utc(acc_date) if acc_date else None
            if not dt_iso or not date_in_range(dt_iso, since):
                continue
            primary = filings.get("primaryDocument", [""]*count)[i]
            company = filings.get("companyName", [""]*count)[i]
            filing_dir = raw_dir / "filings" / "us" / cik10 / acc
            md = {
                "ticker": ticker,
                "cik": cik10,
                "form": form,
                "companyName": company,
                "accessionNumber": acc,
                "acceptanceDateTime": dt_iso,
                "primaryDocument": primary,
                "source": url,
            }
            save_json(md, filing_dir / "metadata.json")
            # try download primary
            limiter.wait()
            try:
                download_primary(sess, base, cik10, acc, primary, filing_dir)
            except Exception:
                pass
            collected.append(md)

    # write summary csv
    import csv
    out_csv = reports_dir / "filings_summary.csv"
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ticker","cik","form","accessionNumber","acceptanceDateTime","primaryDocument","source"])
        w.writeheader()
        for row in sorted(collected, key=lambda r: r["acceptanceDateTime"], reverse=True):
            w.writerow(row)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/filings.yaml")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--forms", nargs="*", default=None)
    args = ap.parse_args()
    main(args.config, args.days, args.forms)
