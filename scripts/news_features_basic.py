import pandas as pd, yaml, json
from pathlib import Path
import warnings; warnings.filterwarnings("ignore")

def load_news(root:Path):
    if not root.exists(): return pd.DataFrame()
    rows=[]
    for p in list(root.glob("*.json"))[:5000]:
        try: rows.append(json.loads(p.read_text(encoding="utf-8")))
        except: pass
    return pd.DataFrame(rows)

def main(cfg_path):
    cfg = yaml.safe_load(open(cfg_path, "r", encoding="utf-8"))
    root = Path(cfg["paths"]["news_root"])
    out  = Path(cfg["paths"]["out_dir"]); out.mkdir(parents=True, exist_ok=True)

    df = load_news(root)
    if df is None or df.empty:
        pd.DataFrame(columns=["ticker","date"]).to_parquet(out/"news_dict_features.parquet", index=False); return

    # ticker/date
    if "ticker" in df.columns:
        df["ticker"]=df["ticker"].fillna("MARKET")
    else:
        df["ticker"]="MARKET"
    ts = pd.to_datetime(df.get("publishedAt") or df.get("date"), errors="coerce")
    df["date"] = ts.dt.strftime("%Y-%m-%d").fillna("1970-01-01")

    # 単純辞書特徴（見出し長、NEUタグ数などがあれば加点）
    df["headline_len"] = df.get("title", "").astype(str).str.len()
    feat = (df.groupby(["ticker","date"], as_index=False)
              .agg(news_cnt=("title","count"), headline_len_avg=("headline_len","mean")))
    feat.to_parquet(out/"news_dict_features.parquet", index=False)
    print("rows", len(feat))

if __name__ == "__main__":
    import argparse; ap=argparse.ArgumentParser()
    ap.add_argument("--config", required=True); args=ap.parse_args(); main(args.config)
