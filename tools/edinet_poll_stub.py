import argparse, pathlib, json, time
# キー取得まではスタブ。新規提出有無だけの疑似ポーリング。
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2024-01-01")
    ap.add_argument("--out", default=r"C:\AI\AlphaUltra\data\raw\edinet")
    args = ap.parse_args()
    out = pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out/"last_poll.json").write_text(json.dumps({"since":args.since,"status":"stub"}), encoding="utf-8")
    print("[edinet] stub poll wrote last_poll.json")
if __name__=="__main__": main()
