from pathlib import Path
import pandas as pd, re, json

SRC = Path(r"C:\AI\AlphaUltra_v1\tmp\kabutan_exports")
OUT = Path(r"C:\AI\AlphaUltra_v1\data\proc\features_tdnet\tdnet_events_raw.parquet")
OUT.parent.mkdir(parents=True, exist_ok=True)

rows=[]
csvs = list(SRC.rglob("*.csv")) + list(SRC.rglob("*.CSV"))
for fp in csvs:
    try:
        df=pd.read_csv(fp, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df=pd.read_csv(fp, encoding="cp932")
    cols={c.lower().strip():c for c in df.columns}
    def pick(*ks):
        for k in ks:
            if k in cols: return cols[k]
        return None
    c_code=pick("コード","code","銘柄コード")
    c_dt  =pick("掲載日時","published_at","日時","date","time")
    c_tit =pick("タイトル","title")
    if not (c_code and c_dt and c_tit): 
        continue
    x=df[[c_code,c_dt,c_tit]].copy().rename(columns={c_code:"code",c_dt:"published_at_jst",c_tit:"title"})
    x["code4"]=x["code"].astype(str).str.extract(r"(\d{4})", expand=False)
    x=x[x["code4"].notna()].copy()
    x["ticker"]=x["code4"]+".T"
    x["published_at_jst"]=pd.to_datetime(x["published_at_jst"], errors="coerce")
    x=x[x["published_at_jst"].notna()].copy()
    x["date"]=x["published_at_jst"].dt.normalize()
    def ge(t):
        t=str(t)
        if re.search("自社株買|自己株式", t): return "buyback"
        if re.search("上方修正", t): return "guidance_up"
        if re.search("増資|第三者割当|CB", t): return "offering"
        if re.search("決算", t, flags=re.I): return "earnings"
        if re.search("新製品|発売|承認", t): return "product"
        return "other"
    x["event_type"]=x["title"].map(ge)
    rows.append(x[["ticker","code4","title","published_at_jst","date","event_type"]])

out = pd.concat(rows, ignore_index=True).drop_duplicates(subset=["ticker","title","published_at_jst"]) if rows else \
      pd.DataFrame(columns=["ticker","code4","title","published_at_jst","date","event_type"])
out.to_parquet(OUT, index=False)

res = {
  "csv_files": len(csvs),
  "rows": int(len(out)),
  "tickers": 0 if out.empty else int(out["ticker"].nunique()),
  "min_date": None if out.empty else str(out["date"].min().date()),
  "max_date": None if out.empty else str(out["date"].max().date())
}
print(json.dumps(res, ensure_ascii=False))
