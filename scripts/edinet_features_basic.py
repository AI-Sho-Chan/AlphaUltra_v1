import pandas as pd, yaml
from pathlib import Path
import warnings; warnings.filterwarnings("ignore")

def main(cfg_path):
    cfg = yaml.safe_load(open(cfg_path, "r", encoding="utf-8"))
    csv = Path(cfg["paths"]["edinet_summary"])
    out = Path(cfg["paths"]["out_dir"]); out.mkdir(parents=True, exist_ok=True)

    if not csv.exists():
        (out/"edinet_doc_features.parquet").touch(); print("no edinet_summary.csv"); return

    df = pd.read_csv(csv)
    if df.empty:
        pd.DataFrame(columns=["ticker","date"]).to_parquet(out/"edinet_doc_features.parquet", index=False); return

    # ticker生成（日本株は不明なら MARKET.JP 固定）
    tcol = None
    for c in ["ticker","LocalCode","Code","secCode","issuerEdinetCode"]:
        if c in df.columns: tcol=c; break
    if tcol:
        tick = df[tcol].astype(str)
        if tcol in ["LocalCode","Code","secCode"]:
            tick = tick.str.replace(r"\.0$","",regex=True)+".T"
        df["ticker"] = tick
    else:
        df["ticker"] = "MARKET.JP"

    # date生成
    dcol=None
    for c in ["submitDateTime","submitDateTime_JST","periodEnd","docPublishDate"]:
        if c in df.columns: dcol=c; break
    ts = pd.to_datetime(df[dcol] if dcol else pd.NaT, errors="coerce")
    df["date"] = ts.dt.strftime("%Y-%m-%d").fillna("1970-01-01")

    base = df[["ticker","date"]].copy()
    base["edinet_docs"]=1
    feat = (base.groupby(["ticker","date"], as_index=False)["edinet_docs"].sum())
    feat.to_parquet(out/"edinet_doc_features.parquet", index=False)
    print("rows", len(feat))

if __name__ == "__main__":
    import argparse; ap=argparse.ArgumentParser()
    ap.add_argument("--config", required=True); args=ap.parse_args(); main(args.config)
