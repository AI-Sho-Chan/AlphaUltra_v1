# === Phase-1 refactor shim ===
import sys
from pathlib import Path
sys.path.insert(0, str((Path(__file__).resolve().parents[1]/'src')))
from alphaultra.utils.root import data_dir
from alphaultra.utils.front_matter import strip_front_matter
# -*- coding: utf-8 -*-
"""
run_experiment.py  (drop-in fixed)
- YAML front matter 剥離対応
- config 形状: {exp_id, dataset_key, score_formula} でも {experiments:[{...}]} でもOK
- 参照: data/datasets_registry.yaml の datasets[dataset_key]
- フィルタ: --date_min/--date_max, --mask_csv/--mask_col/--mask_value
- コスト: --cost_bps → turnover_daily と Sharpe(net) を計算
- 指標: precision_at_k / sharpe_annualized / sharpe_annualized_net / turnover_daily / max_drawdown
"""
import argparse, json, math, os, sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


def strip_front_matter(txt: str) -> str:
    """'---' front matter があれば本体だけ返す。無ければそのまま返す。"""
    lines = txt.splitlines()
    if len(lines) >= 3 and lines[0].strip() == "---":
        # front matter をスキップ
        try:
            end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
            body = "\n".join(lines[end + 1 :])
            return body.strip() if body.strip() else "\n"
        except StopIteration:
            return txt
    return txt


def load_yaml_any(path: Path) -> dict:
    ytxt = Path(path).read_text(encoding="utf-8")
    ytxt = strip_front_matter(ytxt)
    data = yaml.safe_load(ytxt)
    if data is None:
        data = {}
    # experiments配列なら先頭要素をexpとみなす。そうでなければ全体をexpとみなす。
    if "experiments" in data and isinstance(data["experiments"], list) and data["experiments"]:
        exp = data["experiments"][0] or {}
        top = data
    else:
        exp = data
        top = {"experiments": [exp]}
    return {"top": top, "exp": exp}


def load_registry(path: Path) -> dict:
    y = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return y or {}


def ensure_datetime(series: pd.Series) -> pd.Series:
    if not np.issubdtype(series.dtype, np.datetime64):
        return pd.to_datetime(series, errors="coerce")
    return series


def build_namespace(df: pd.DataFrame) -> dict:
    """安全な eval 用に数値列を名前空間へ公開（ret5, ret20 など）"""
    ns = {c: df[c] for c in df.columns if pd.api.types.is_numeric_dtype(df[c])}
    # 便利オブジェクト（必要最低限）
    ns["np"] = np
    return ns


def precision_at_k_daily(g: pd.DataFrame, k: int, label_col: str = "fret5") -> float:
    # 上位K取得
    gg = g.sort_values("pred_score", ascending=False).head(k)
    if gg.empty:
        return np.nan
    # 正例: forward 5d return > 0
    return float((gg[label_col] > 0).mean())


def max_drawdown_from_returns(daily_ret: pd.Series) -> float:
    # 累積
    equity = (1.0 + daily_ret.fillna(0)).cumprod()
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(dd.min()) if len(dd) else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--registry", default=str(data_dir()/ "datasets_registry.yaml"))
    ap.add_argument("--k", type=int, default=50)
    ap.add_argument("--date_min", default=None)
    ap.add_argument("--date_max", default=None)
    ap.add_argument("--mask_csv", default=None)
    ap.add_argument("--mask_col", default=None)
    ap.add_argument("--mask_value", default=None)
    ap.add_argument("--cost_bps", type=float, default=0.0)
    args = ap.parse_args()

    cfg_path = Path(args.config)
    exp_dir = cfg_path.parent
    exp_id_guess = exp_dir.name

    # 出力系
    metrics_path = exp_dir / "metrics.json"
    err_path = exp_dir / "error.log"
    runlog_path = exp_dir / "run.log"
    cfg_used_path = exp_dir / "config.used.yaml"

    def log_err(msg: str, exc: Exception | None = None):
        ts = datetime.now().isoformat()
        with open(err_path, "a", encoding="utf-8") as f:
            f.write(f"{ts} | ERROR: {msg}\n")
            if exc:
                import traceback

                traceback.print_exc(file=f)

    try:
        loaded = load_yaml_any(cfg_path)
        top, exp = loaded["top"], loaded["exp"]

        # dataset_key
        ds_key = (
            exp.get("dataset_key")
            or (exp.get("data") or {}).get("dataset_key")
            or (exp.get("data") or {}).get("dataset")
            or "yahoo_default"
        )

        # exp_id
        exp_id = exp.get("exp_id") or exp_id_guess

        # score
        score_expr = (
            (exp.get("features") or {}).get("score_formula")
            or exp.get("score_formula")
            or "ret5"
        )

        # レジストリ
        reg_path = Path(args.registry)
        if not reg_path.exists():
            raise FileNotFoundError(f"registry not found: {reg_path}")
        reg = load_registry(reg_path)
        if "datasets" not in reg or ds_key not in reg["datasets"]:
            raise KeyError(f"dataset_key not in registry: '{ds_key}'")

        ds = reg["datasets"][ds_key]
        f_path = Path(ds["features_path"])
        l_path = Path(ds["labels_path"])
        if not f_path.exists() or not l_path.exists():
            raise FileNotFoundError(f"gold parquet missing: {f_path} / {l_path}")

        # 入力
        feat = pd.read_parquet(f_path)
        lab = pd.read_parquet(l_path)

        # 型揃え
        feat["date"] = ensure_datetime(feat["date"])
        lab["date"] = ensure_datetime(lab["date"])

        # 期間フィルタ
        if args.date_min:
            d0 = pd.to_datetime(args.date_min)
            feat = feat[feat["date"] >= d0]
            lab = lab[lab["date"] >= d0]
        if args.date_max:
            d1 = pd.to_datetime(args.date_max)
            feat = feat[feat["date"] <= d1]
            lab = lab[lab["date"] <= d1]

        # レジームマスク
        if args.mask_csv and args.mask_col and args.mask_value:
            m = pd.read_csv(args.mask_csv)
            m["date"] = ensure_datetime(m["date"])
            feat = feat.merge(m[["date", args.mask_col]], on="date", how="left")
            feat = feat[feat[args.mask_col] == args.mask_value].drop(columns=[args.mask_col])
            lab = lab.merge(m[["date", args.mask_col]], on="date", how="left")
            lab = lab[lab[args.mask_col] == args.mask_value].drop(columns=[args.mask_col])

        # マージ
        df = feat.merge(lab[["date", "ticker", "fret5"]], on=["date", "ticker"], how="inner")

        # スコア計算（安全 eval）
        try:
            ns = build_namespace(df)
            df["pred_score"] = eval(score_expr, {"__builtins__": None}, ns)
        except Exception as e:
            log_err(f"{e}")
            # 失敗時は stub metrics を出して終了
            stub = {
                "timestamp": datetime.now().isoformat(),
                "exp_id": exp_id,
                "dataset": ds_key,
                "k": int(args.k),
                "signal_metrics": {"precision_at_k": 0.0},
                "portfolio_metrics": {
                    "sharpe_annualized": 0.0,
                    "sharpe_annualized_net": 0.0,
                    "turnover_daily": 0.0,
                    "cost_bps": float(args.cost_bps),
                    "max_drawdown": 0.0,
                },
                "notes": f"STUB due to score_expr error: {score_expr}",
            }
            metrics_path.parent.mkdir(parents=True, exist_ok=True)
            metrics_path.write_text(json.dumps(stub, indent=2), encoding="utf-8")
            print("DONE: run_experiment.py")
            return

        # 日別に上位Kを選んで集計
        k = int(args.k)
        by_date = []
        selected_prev = set()
        for d, g in df.groupby("date"):
            gg = g.sort_values("pred_score", ascending=False).head(k)
            if gg.empty:
                continue
            # p@k（日次）
            p_at_k_d = float((gg["fret5"] > 0).mean())
            # リターン（日次・gross）
            ret_g = float(gg["fret5"].mean())
            # ターンオーバー
            sel = set(gg["ticker"].astype(str).tolist())
            if selected_prev:
                turn = len(sel.symmetric_difference(selected_prev)) / k
            else:
                turn = 0.0
            selected_prev = sel
            by_date.append((d, p_at_k_d, ret_g, turn))

        if not by_date:
            raise RuntimeError("no data after filters")

        dd = pd.DataFrame(by_date, columns=["date", "p_at_k", "ret_gross", "turnover"])
        dd = dd.sort_values("date")
        cost = float(args.cost_bps) / 10000.0
        dd["ret_net"] = dd["ret_gross"] - dd["turnover"] * cost

        # 指標
        precision_at_k = float(dd["p_at_k"].mean())
        def ann_sharpe(x: pd.Series) -> float:
            x = x.dropna()
            if len(x) < 2 or x.std(ddof=1) == 0:
                return 0.0
            return float((x.mean() / x.std(ddof=1)) * math.sqrt(252))

        sharpe_g = ann_sharpe(dd["ret_gross"])
        sharpe_n = ann_sharpe(dd["ret_net"])
        maxdd = max_drawdown_from_returns(dd["ret_net"])
        to_daily = float(dd["turnover"].mean())

        # 出力
        out = {
            "timestamp": datetime.now().isoformat(),
            "exp_id": exp_id,
            "dataset": ds_key,
            "k": k,
            "signal_metrics": {
                "precision_at_k": precision_at_k,
            },
            "portfolio_metrics": {
                "sharpe_annualized": sharpe_g,
                "sharpe_annualized_net": sharpe_n,
                "turnover_daily": to_daily,
                "cost_bps": float(args.cost_bps),
                "max_drawdown": maxdd,
            },
            "notes": f"score = {score_expr}",
        }
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
        # config snapshot
        cfg_used_path.write_text(yaml.safe_dump(loaded["top"], allow_unicode=True, sort_keys=False), encoding="utf-8")
        # run.log 追記
        with open(runlog_path, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} | exp_id={exp_id} k={k} cost_bps={args.cost_bps}\n")

        print("DONE: run_experiment.py")

    except Exception as e:
        log_err(str(e), e)
        # 失敗でもDONEは表示（外側のPS1が後続を回せるように）
        print("DONE: run_experiment.py")


if __name__ == "__main__":
    main()


