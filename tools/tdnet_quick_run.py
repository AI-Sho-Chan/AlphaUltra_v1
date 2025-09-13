import argparse, pathlib, subprocess, sys

ROOT = pathlib.Path(r"C:\AI\AlphaUltra")
RAW  = ROOT/"data/raw/kabutan"
BRZ  = ROOT/"data/bronze/tdnet"

def sh(*args): return subprocess.call(list(args))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--date", required=True)  # YYYY-MM-DD
    ap.add_argument("--src", default=str(RAW))
    ap.add_argument("--out", default=str(BRZ/"tdnet_day.parquet"))
    args=ap.parse_args()

    daydir = pathlib.Path(args.src)/args.date
    files  = list(daydir.glob("*.csv"))+list(daydir.glob("*.tsv"))+list(daydir.glob("*.xlsx"))
    if not files:
        print(f"[tdnet] no files in {daydir}  ← まずここに株探のCSV/TSV/XLSXを置いてください"); sys.exit(2)

    # 1) 日次取り込み
    rc = sh(sys.executable, str(ROOT/"tools"/"ingest_kabutan_tdnet_day.py"),
            "--date", args.date, "--src", args.src, "--out", args.out, "--download-attachments")
    if rc!=0: sys.exit(rc)

    # 2) HTML要約抽出
    inpq = args.out
    outpq= str(BRZ/"tdnet_day_with_html.parquet")
    rc = sh(sys.executable, str(ROOT/"tools"/"tdnet_kabutan_fetch_html.py"),
            "--in-parquet", inpq, "--out-parquet", outpq)
    if rc!=0: sys.exit(rc)

    # 3) イベント特徴を作成
    rc = sh(sys.executable, str(ROOT/"tools"/"tdnet_build_events.py"),
            "--in-parquet", outpq)
    sys.exit(rc)
if __name__=="__main__": main()
