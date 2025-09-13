import os, sys, argparse, pathlib, json
import pandas as pd
from typing import List
import sqlite3

# optional deps
try:
    import duckdb; HAVE_DUCKDB=True
except Exception:
    HAVE_DUCKDB=False

try:
    import yaml as _yaml
except Exception:
    _yaml=None

def file_magic(p: pathlib.Path, n: int = 16) -> bytes:
    try:
        with open(p, "rb") as f:
            return f.read(n)
    except Exception:
        return b""

def is_sqlite(p: pathlib.Path) -> bool:
    sig = file_magic(p, 16)
    return sig.startswith(b"SQLite format 3")

def is_duckdb(p: pathlib.Path) -> bool:
    sig = file_magic(p, 6)
    return sig == b"DUCKDB"

def normalize_columns(df: pd.DataFrame, ticker_hint=None):
    cols={c.lower():c for c in df.columns}
    def pick(*names):
        for n in names:
            if n in cols: return cols[n]
        return None
    dcol = pick("date","timestamp","time","datetime")
    if dcol is None: return None
    df = df.rename(columns={dcol:"date"})
    for k in ["open","high","low","close","adj close","adj_close","adjusted_close","volume","ticker","symbol","code"]:
        if (c:=cols.get(k)) and c!=k.replace(" ","_"):
            df = df.rename(columns={c:k.replace(" ","_")})
    if "ticker" not in df.columns:
        if "symbol" in df.columns: df=df.rename(columns={"symbol":"ticker"})
        elif "code" in df.columns: df=df.rename(columns={"code":"ticker"})
        elif ticker_hint is not None: df["ticker"]=ticker_hint
        else: df["ticker"]="UNKNOWN"
    keep = ["date","ticker"]+[k for k in ["open","high","low","close","adj_close","volume"] if k in df.columns]
    df = df[keep].copy()
    df["date"]=pd.to_datetime(df["date"]).dt.tz_localize(None)
    return df.dropna(subset=["date","ticker"])

def read_sqlite(p: pathlib.Path):
    if not is_sqlite(p):
        print(f"[sqlite-skip] {p.name}: not an SQLite file", file=sys.stderr); return []
    try:
        con = sqlite3.connect(p.as_posix()); cur = con.cursor()
        tnames = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        out=[]
        for t in tnames:
            try:
                df = pd.read_sql_query(f"SELECT * FROM {t}", con)
                df = normalize_columns(df, ticker_hint=p.stem.upper())
                if df is not None and len(df): out.append(df)
            except Exception as e:
                print(f"[sqlite-skip] {p.name}:{t} -> {e}", file=sys.stderr)
        con.close(); return out
    except Exception as e:
        print(f"[sqlite-skip] {p.name} -> {e}", file=sys.stderr); return []

def read_duckdb(p: pathlib.Path):
    if not HAVE_DUCKDB:
        print(f"[duckdb-skip] {p.name}: duckdb not installed", file=sys.stderr); return []
    if not is_duckdb(p):
        print(f"[duckdb-skip] {p.name}: not a DuckDB file", file=sys.stderr); return []
    try:
        con = duckdb.connect(p.as_posix(), read_only=True)
        tnames = [r[0] for r in con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='main'").fetchall()]
        out=[]
        for t in tnames:
            try:
                df = con.execute(f"SELECT * FROM {t}").fetchdf()
                df = normalize_columns(df, ticker_hint=p.stem.upper())
                if df is not None and len(df): out.append(df)
            except Exception as e:
                print(f"[duckdb-skip] {p.name}:{t} -> {e}", file=sys.stderr)
        con.close(); return out
    except Exception as e:
        print(f"[duckdb-skip] {p.name} -> {e}", file=sys.stderr); return []

def read_parquet(p: pathlib.Path):
    try:
        df = pd.read_parquet(p)
        df = normalize_columns(df, ticker_hint=p.stem.upper())
        return [df] if df is not None else []
    except Exception as e:
        print(f"[parquet-skip] {p.name} -> {e}", file=sys.stderr); return []

def read_csv(p: pathlib.Path):
    try:
        df = pd.read_csv(p)
        df = normalize_columns(df, ticker_hint=p.stem.upper())
        return [df] if df is not None else []
    except Exception as e:
        print(f"[csv-skip] {p.name} -> {e}", file=sys.stderr); return []

def find_sources(root: pathlib.Path) -> List[pathlib.Path]:
    exts = [".db",".sqlite",".duckdb",".parquet",".csv"]
    out=[]
    for ext in exts:
        out += list(root.rglob(f"*{ext}"))
    return out

def write_registry(dataset_name: str, feat_out: pathlib.Path, lab_out: pathlib.Path):
    if _yaml is None:
        print("[warn] PyYAML not installed; registry update skipped", file=sys.stderr); return
    reg = pathlib.Path("data/datasets_registry.yaml")
    data = {"datasets":{}}
    if reg.exists():
        try:
            data = _yaml.safe_load(reg.read_text(encoding="utf-8")) or {"datasets":{}}
        except Exception:
            data = {"datasets":{}}
    data.setdefault("datasets",{})[dataset_name] = {
        "features_path": str(feat_out.as_posix()),
        "labels_path":   str(lab_out.as_posix())
    }
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text(_yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"[registry] updated: {reg}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dir", required=True)
    ap.add_argument("--dataset-name", default="yahoo_default")
    ap.add_argument("--out-bronze", default="data/bronze")
    ap.add_argument("--out-gold", default="data/gold")
    args = ap.parse_args()

    ROOT = pathlib.Path(args.source_dir)
    bronze = pathlib.Path(args.out_bronze)/args.dataset_name
    gold   = pathlib.Path(args.out_gold)/args.dataset_name
    bronze.mkdir(parents=True, exist_ok=True); gold.mkdir(parents=True, exist_ok=True)

    parts=[]
    for p in find_sources(ROOT):
        try:
            if   p.suffix in [".db",".sqlite"]: 
                parts += (read_sqlite(p) if p.suffix==".sqlite" or is_sqlite(p) else (read_duckdb(p) if is_duckdb(p) else []))
            elif p.suffix==".duckdb":          
                parts += read_duckdb(p)
            elif p.suffix==".parquet":         
                parts += read_parquet(p)
            elif p.suffix==".csv":             
                parts += read_csv(p)
        except Exception as e:
            print(f"[skip] {p.name} -> {e}", file=sys.stderr)

    if parts:
        df = pd.concat(parts, ignore_index=True).drop_duplicates().sort_values(["ticker","date"])
        bronze_out = bronze/"ohlcv.parquet"; df.to_parquet(bronze_out, index=False)
        print(f"[bronze] {bronze_out} rows={len(df)}")

        feat = df.copy()
        if "close" in feat.columns:
            feat["ret5"]  = feat.groupby("ticker")["close"].pct_change(5)
            feat["ret20"] = feat.groupby("ticker")["close"].pct_change(20)
        feat["vol_z"] = feat.groupby("ticker")["volume"].transform(lambda s:(s - s.mean())/(s.std(ddof=0)+1e-9)) if "volume" in feat.columns else 0.0

        lab = feat[["ticker","date"]].copy()
        if "close" in feat.columns:
            lab["fret5"] = feat.groupby("ticker")["close"].pct_change(-5)
        else:
            lab["fret5"] = pd.NA
    else:
        print("[import] no usable tables found; writing EMPTY gold for pipeline continuity", file=sys.stderr)
        feat = pd.DataFrame({
            "date":   pd.to_datetime([]),
            "ticker": pd.Series([], dtype="object"),
            "open":   pd.Series([], dtype="float64"),
            "high":   pd.Series([], dtype="float64"),
            "low":    pd.Series([], dtype="float64"),
            "close":  pd.Series([], dtype="float64"),
            "adj_close": pd.Series([], dtype="float64"),
            "volume": pd.Series([], dtype="float64"),
            "ret5":   pd.Series([], dtype="float64"),
            "ret20":  pd.Series([], dtype="float64"),
            "vol_z":  pd.Series([], dtype="float64"),
        })
        lab = pd.DataFrame({
            "ticker": pd.Series([], dtype="object"),
            "date":   pd.to_datetime([]),
            "fret5":  pd.Series([], dtype="float64"),
        })

    feat_out = gold/"features.parquet"; lab_out  = gold/"labels.parquet"
    feat.to_parquet(feat_out, index=False); lab.to_parquet(lab_out, index=False)
    print(f"[gold] features={feat_out} labels={lab_out}")

    write_registry(args.dataset_name, feat_out, lab_out)

if __name__=="__main__":
    main()
