import pandas as pd, yaml
from pathlib import Path
import warnings; warnings.filterwarnings("ignore")

def main(cfg_path):
    cfg = yaml.safe_load(open(cfg_path, "r", encoding="utf-8"))
    csv = Path(cfg["paths"]["filings_summary"])
    out = Path(cfg["paths"]["out_dir"]); out.mkdir(parents=True, exist_ok=True)

    if not csv.exists():
        Path(cfg["paths"]["reports_dir"]).mkdir(parents=True, exist_ok=True)
        print("no filings_summary.csv"); (out/"filing_event_features.parquet").touch(); return

    df = pd.read_csv(csv)
    if df.empty:
        pd.DataFrame(columns=["ticker","date"]).to_parquet(out/"filing_event_features.parquet", index=False); return

    # ticker補完（AAPL/MSFTだけ厳密、他は UNKNOWN）
    map_cik = {"0000320193":"AAPL","0000789019":"MSFT"}
    df["ticker"] = df.get("ticker")
    if "cik" in df.columns:
        df["ticker"] = df["ticker"].fillna(df["cik"].map(map_cik))
    df["ticker"] = df["ticker"].fillna("UNKNOWN")

    # date生成
    if "date" not in df.columns:
        ts = pd.to_datetime(df.get("acceptanceDateTime"), errors="coerce")
        df["date"] = ts.dt.strftime("%Y-%m-%d").fillna("1970-01-01")

    base = df[["ticker","date","form"]].dropna()
    if base.empty:
        pd.DataFrame(columns=["ticker","date"]).to_parquet(out/"filing_event_features.parquet", index=False); return

    base = base.sort_values(["ticker","date"])
    base["v"]=1
    feat = (base.pivot_table(index=["ticker","date"], columns="form", values="v", aggfunc="sum", fill_value=0)
                 .reset_index())
    feat.columns = [c if isinstance(c,str) else str(c) for c in feat.columns]
    feat.to_parquet(out/"filing_event_features.parquet", index=False)
    print("rows", len(feat), "cols", len(feat.columns))

if __name__ == "__main__":
    import argparse; ap=argparse.ArgumentParser()
    ap.add_argument("--config", required=True); args=ap.parse_args(); main(args.config)
