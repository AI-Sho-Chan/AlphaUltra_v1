import re, json, hashlib, unicodedata as ud
from pathlib import Path
import pandas as pd

SRC=Path(r"C:\AI\AlphaUltra_v1\data\raw\kabutan")
DST=Path(r"C:\AI\AlphaUltra_v1\data\raw\tdnet"); DST.mkdir(parents=True, exist_ok=True)

PRICE_KEYS={"open","high","low","close","始値","高値","安値","終値"}

def N(x):
    if x is None: return ""
    if isinstance(x,float) and pd.isna(x): return ""
    return ud.normalize("NFKC", str(x)).strip()

def folder_ymd(p:Path):
    s=str(p)
    m=re.search(r"(20\d{2})[-_/](\d{2})[-_/](\d{2})", s)
    if m: return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    parts=p.parts
    for i in range(len(parts)-2):
        if re.fullmatch(r"20\d{2}", parts[i]) and re.fullmatch(r"\d{2}", parts[i+1]) and re.fullmatch(r"\d{2}", parts[i+2]):
            return f"{parts[i]}-{parts[i+1]}-{parts[i+2]}"
    m=re.search(r"(20\d{2})(\d{2})(\d{2})", s)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None

# 2013–2024 のCSVだけ対象
files=[p for p in SRC.rglob("*.csv") if re.search(r"[\\/](2013|2014|2015|2016|2017|2018|2019|2020|2021|2022|2023|2024)[\\/]", str(p))]
w=0; uniq=set(); by_year={}
for fp in files:
    try:
        try: df=pd.read_csv(fp, encoding="utf-8-sig")
        except UnicodeDecodeError: df=pd.read_csv(fp, encoding="cp932")
    except Exception:
        continue

    # 価格テーブル除外
    low={N(c).lower() for c in df.columns}
    if len(PRICE_KEYS & low)>=3:
        continue

    ymd=folder_ymd(fp)
    if not ymd: 
        continue
    fill_dt=pd.to_datetime(ymd+" 15:00:00")

    for _,row in df.iterrows():
        # 行全体をNFKC化して4桁コードを探す（先頭に市場コード等が無くても拾う）
        all_txt=" ".join(N(v) for v in row.values)
        m=re.search(r"(?<!\d)(\d{4})(?!\d)", all_txt)
        if not m: 
            continue
        code4=m.group(1)
        ticker=f"{code4}.T"

        # 日時：列に無くてもフォルダ日付で補完
        dt=fill_dt
        # よくある日時列名を網羅的に探索
        for k in ["掲載日時","発表日時","開示日時","公表日時","更新日時","日時","date","datetime","published","timestamp","掲載日","発表日","開示日","公表日","日付"]:
            if k in row.index:
                v=N(row[k]); 
                if v:
                    try:
                        cand=pd.to_datetime(v, errors="coerce")
                        if pd.notna(cand): dt=cand; break
                    except: pass
        d=str(pd.to_datetime(dt).normalize().date())
        y,m,dd=d.split("-")
        outdir=DST/y/m/dd; outdir.mkdir(parents=True, exist_ok=True)

        # タイトル候補（なければ本文や最長テキスト）
        title=None
        for k in ["タイトル","件名","見出し","表題","題名","開示内容","headline","subject","title","本文","内容","テキスト","body","detail","description"]:
            if k in row.index:
                t=N(row[k])
                if len(t)>=2: title=t; break
        if not title:
            # 最長テキスト
            texts=[N(v) for v in row.values if len(N(v))>=2]
            if not texts: 
                continue
            title=max(texts, key=len)

        sid=hashlib.sha1(f"{ticker}|{pd.to_datetime(dt).strftime('%Y-%m-%d %H:%M:%S')}|{title}".encode("utf-8")).hexdigest()[:16]
        out=outdir/f"{ticker}_{sid}.json"
        if out.exists(): 
            continue

        rec={"ticker":ticker,"code4":code4,"title":title,
             "published_at_jst": pd.to_datetime(dt).strftime("%Y-%m-%d %H:%M:%S"),
             "date": d, "event_type":"other","source":"kabutan"}
        # URL類があれば付加
        for k in ["url","詳細url","記事url","リンク","detail_url","URL","Url","pdf","pdf_url","PDF"]:
            if k in row.index:
                v=N(row[k])
                if v: rec[k.replace("URL","url").replace("Url","url")]=v

        out.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        w+=1; uniq.add(ticker); by_year[y]=by_year.get(y,0)+1

# サマリ
paths=list(DST.rglob("*.json"))
def ymd_of(p):
    m=re.search(r"(20\d{2})[\\/](\d{2})[\\/](\d{2})", str(p))
    return "-".join(m.groups()) if m else None
dates=sorted([ymd_of(p) for p in paths if ymd_of(p)])
print({"json_files": len(paths), "tickers": len(uniq),
       "date_min": dates[0] if dates else None, "date_max": dates[-1] if dates else None,
       "by_year": dict(sorted(by_year.items()))})
