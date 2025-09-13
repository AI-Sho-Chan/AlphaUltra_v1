import argparse, os, re, json
from pathlib import Path
import pandas as pd
import yaml

def read_csv_any(p):
    for enc in ("utf-8-sig","cp932","utf-8"):
        try:
            return pd.read_csv(p, encoding=enc)
        except Exception:
            pass
    # 最後にバイナリ→cp932推定
    return pd.read_csv(p, encoding="cp932", errors="ignore")

def maj_ratio(s, pred):
    tot = s.notna().sum()
    if tot == 0: return 0.0
    ok = sum(1 for x in s.dropna() if pred(str(x).strip()))
    return ok / tot

def guess_cols(df):
    cols = list(df.columns)
    used = set()

    # code: 4～5桁数字が多数
    code = next((c for c in cols if maj_ratio(df[c], lambda v: re.fullmatch(r"\d{4,5}", v) is not None) > 0.6), None)
    if code: used.add(code)

    # url: httpで始まる
    url = next((c for c in cols if c not in used and maj_ratio(df[c], lambda v: v.lower().startswith("http")) > 0.5), None)
    if url: used.add(url)

    # time: HH:MM 形式
    time = next((c for c in cols if c not in used and maj_ratio(df[c], lambda v: re.fullmatch(r"\d{1,2}:\d{2}", v) is not None) > 0.5), None)
    if time: used.add(time)

    # date: YYYY-MM-DD or YYYY/MM/DD
    date = next((c for c in cols if c not in used and maj_ratio(df[c], lambda v: re.match(r"^20\d{2}[-/]\d{2}[-/]\d{2}$", v) is not None) > 0.5), None)
    if date: used.add(date)

    # title: 文字列長の平均が最大（code/url/date/time 以外）
    cand = [c for c in cols if c not in used]
    if cand:
        def avglen(c):
            s = df[c].dropna().astype(str)
            return s.map(len).mean() if len(s) else 0.0
        title = max(cand, key=avglen)
    else:
        title = None

    return {"code": code, "date": date, "time": time, "title": title, "url": url}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/tdnet.yaml")
    ap.add_argument("--input",  default="data/raw/kabutan")
    args = ap.parse_args()

    # config 読み込み（paths.tdnet_root が無ければ既定）
    out_root = Path("data/raw/tdnet")
    try:
        with open(args.config, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        p = (((cfg.get("paths") or {}).get("tdnet_root")) or "data/raw/tdnet")
        out_root = Path(p)
    except Exception:
        pass

    in_root = Path(args.input)
    out_root.mkdir(parents=True, exist_ok=True)
    total = 0

    # 日付フォルダ配下の tdnet.csv を走査
    for day_dir in sorted(in_root.rglob("*")):
        if not day_dir.is_dir(): 
            continue
        csvp = day_dir / "tdnet.csv"
        if not csvp.exists():
            continue
        try:
            df = read_csv_any(csvp)
            if df.empty:
                continue
            cols = guess_cols(df)
            code_c, date_c, time_c, title_c, url_c = cols["code"], cols["date"], cols["time"], cols["title"], cols["url"]
            if not (code_c and (date_c or time_c) and (title_c or url_c)):
                # 必須列が足りない場合はスキップ
                continue

            # 出力日付は date 列が優先。無ければ day_dir 名（フォルダ名）を使う
            # day_dir名が YYYY-MM-DD の前提（crawl出力想定）
            for i, row in df.iterrows():
                code = str(row.get(code_c, "")).strip()
                if not re.fullmatch(r"\d{4,5}", code or ""):
                    continue
                date = str(row.get(date_c, "")).strip() if date_c else day_dir.name
                time = str(row.get(time_c, "")).strip() if time_c else "00:00"
                title= str(row.get(title_c, "")).strip() if title_c else ""
                url  = str(row.get(url_c, "")).strip() if url_c else ""

                if not date:
                    continue
                day = date.replace("/", "-")
                odir = out_root / day
                odir.mkdir(parents=True, exist_ok=True)
                o = {
                    "code": code,
                    "datetime": f"{day} {time}",
                    "title": title,
                    "url": url,
                    "source": "kabutan_tdnet"
                }
                # 一意名
                oname = f"{code}_{i:05d}.json"
                with open(odir / oname, "w", encoding="utf-8") as fo:
                    json.dump(o, fo, ensure_ascii=False)
                total += 1

        except Exception as e:
            print(f"[WARN] skip {csvp}: {e}")

    print(f"[INFO] tdnet ingest done. records={total} out_root={out_root}")
    if total == 0:
        print("[WARN] no records created. Check input folder or CSV headers.")

if __name__ == "__main__":
    main()
