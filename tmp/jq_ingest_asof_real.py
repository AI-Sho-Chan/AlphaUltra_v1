# tmp/jq_ingest_asof_real.py
import os, json, pathlib, pandas as pd, numpy as np, requests

FE = r"tmp/features_tdnet_q4_work.parquet"      # 2600キー（ticker, eff_date, y_2x）
PX = r"data/proc/prices/jp_prices_std_compat_q4p.parquet"
IDTOK = r".secrets/jq_id_token.txt"

def auth_header():
    if not os.path.exists(IDTOK): return None
    tok = open(IDTOK, encoding="utf-8").read().strip()
    return {"Authorization": f"Bearer {tok}"}

def get_json(url, params=None, timeout=15):
    h = auth_header()
    if not h: return None
    try:
        r = requests.get(url, headers=h, params=params or {}, timeout=timeout)
        if r.status_code!=200: return None
        return r.json()
    except Exception:
        return None

# 1) 必要最低のエンドポイント（★あなたの環境の実パスに差し替え）
# 例: 決算サマリ as-of（コード・日付指定 or 期間指定）。無ければ次へ。
ENDPOINTS = [
  # "https://api.jquants.com/v1/ir/summary?code={code}&date={date}",
  # "https://api.jpx-jquants.com/v1/ir/summary?code={code}&date={date}",
]

# 2) 2600キーと価格の読み込み
fe = pd.read_parquet(FE, columns=["ticker","eff_date","y_2x"])
fe["ticker"]=fe["ticker"].astype(str); fe["eff_date"]=pd.to_datetime(fe["eff_date"]).dt.normalize()
px = pd.read_parquet(PX, columns=["ticker","eff_date","adj_close","volume"])
px["ticker"]=px["ticker"].astype(str); px["eff_date"]=pd.to_datetime(px["eff_date"]).dt.normalize()
px = px.sort_values(["ticker","eff_date"])

# 3) as-of財務の収集（雛形：成功したエンドポイントだけ使う）
rows=[]
codes = fe["ticker"].unique().tolist()
dates = sorted(fe["eff_date"].unique())
for code in codes[:]:    # 必要なら上限を掛ける
    for date in dates[:]:
        hit=None
        for u in ENDPOINTS:
            url = u.format(code=code, date=str(date.date()))
            js  = get_json(url)
            if js:
                hit = js; break
        if not hit: continue
        # ★JSON→行データのマッピング（最低3指標を抽出）
        # 例: {"eps_yoy":..., "rev_yoy":..., "op_yoy":...}
        rec = {"ticker":code, "asof":pd.to_datetime(date)}
        for k in ("eps_yoy","rev_yoy","op_yoy"):
            if k in hit: rec[k]=hit[k]
        rows.append(rec)

if rows:
    jq = pd.DataFrame(rows).dropna()
else:
    jq = pd.DataFrame(columns=["ticker","asof","eps_yoy","rev_yoy","op_yoy"])

# 4) 直前営業日スナップ（m:1）
maps=[]
for t,grp in fe.groupby("ticker", sort=False):
    d = jq.loc[jq["ticker"]==t,"asof"].drop_duplicates().sort_values().to_numpy()
    if d.size==0: continue
    e = grp["eff_date"].to_numpy()
    idx = np.searchsorted(d, e, side="right")-1
    ok  = idx>=0
    if not ok.any(): continue
    maps.append(pd.DataFrame({"ticker":t,"eff_date":e[ok],"asof":d[idx[ok]]}))

fnd = fe.copy()
if maps and not jq.empty:
    snap = pd.concat(maps, ignore_index=True)
    fnd  = fnd.merge(snap, on=["ticker","eff_date"], how="inner", validate="m:1") \
              .merge(jq, on=["ticker","asof"], how="left", validate="m:1")

# 5) 価格の最小特徴も併用（既存と同じ）
g = px.groupby("ticker",group_keys=False)
px["mom63"] = px["adj_close"]/g["adj_close"].shift(63) - 1.0
px["vol20"] = g["adj_close"].transform(lambda s:s.pct_change().rolling(20,min_periods=20).std())
px["v_lq"]  = g["volume"].transform(lambda s:s.rolling(20,min_periods=20).mean())
pxu = px[["ticker","eff_date","mom63","vol20","v_lq"]].dropna().drop_duplicates(["ticker","eff_date"])
fnd = fnd.merge(pxu, on=["ticker","eff_date"], how="left", validate="m:1")

# 6) 仕上げ（NaN除去→保存）。失敗時は空で早期returnにする。
need = [c for c in ("eps_yoy","rev_yoy","op_yoy","mom63","vol20","v_lq") if c in fnd.columns]
if need:
    fnd = fnd.dropna(subset=need)
out = pathlib.Path(r"tmp/features_fnd_2600.parquet")
out.parent.mkdir(parents=True, exist_ok=True)
fnd.to_parquet(out, index=False)
print({"fnd_rows":len(fnd),"cols":list(fnd.columns)[:10]})
