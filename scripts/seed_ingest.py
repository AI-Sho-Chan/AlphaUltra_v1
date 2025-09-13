import re, pandas as pd, pathlib as P
# 入力CSV（無ければサンプルを自動生成）
src = P.Path(r"C:\AI\AlphaUltra_v1\tmp\kabutan_exports\seed_tdnet.csv")
src.parent.mkdir(parents=True, exist_ok=True)
if not src.exists():
    src.write_text(
        "コード,掲載日時,タイトル\n"
        "7203,2021-02-10 15:00:00,決算短信\n"
        "9107,2021-05-10 15:00:00,上方修正\n"
        "6502,2020-11-06 15:00:00,自社株買い\n"
        "6758,2019-09-10 15:00:00,新製品発表\n"
        "9984,2020-03-27 15:00:00,増資の実施\n", encoding="utf-8-sig")

# 出力先
out_dir = P.Path(r"C:\AI\AlphaUltra_v1\data\proc\features_tdnet")
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "tdnet_events_raw.parquet"

# 変換
df = pd.read_csv(src, encoding="utf-8-sig")
df["code4"] = df["コード"].astype(str).str.extract(r"(\d{4})", expand=False)
df = df[df["code4"].notna()].copy()
df["ticker"] = df["code4"] + ".T"
df["published_at_jst"] = pd.to_datetime(df["掲載日時"], errors="coerce")
df = df[df["published_at_jst"].notna()].copy()
df["date"] = df["published_at_jst"].dt.normalize()

def ge(t):
    t = str(t)
    if re.search("自社株買|自己株式", t): return "buyback"
    if re.search("上方修正", t): return "guidance_up"
    if re.search("増資|第三者割当|CB", t): return "offering"
    if re.search("決算", t, re.I): return "earnings"
    if re.search("新製品|発売|承認", t): return "product"
    return "other"

df["event_type"] = df["タイトル"].map(ge)
out = df[["ticker","code4","タイトル","published_at_jst","date","event_type"]].rename(columns={"タイトル":"title"})
out.to_parquet(out_path.as_posix(), index=False)
print({"rows": int(len(out)), "min_date": str(out["date"].min().date()), "max_date": str(out["date"].max().date())})
