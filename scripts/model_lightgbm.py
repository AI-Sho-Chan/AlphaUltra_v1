
import pandas as pd, numpy as np, yaml, json
from pathlib import Path
from sklearn.metrics import roc_auc_score, average_precision_score
import lightgbm as lgb

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def time_based_folds(dates: pd.Series, n_splits: int):
    u = pd.to_datetime(pd.Series(dates.unique())).sort_values().reset_index(drop=True)
    blocks = np.array_split(u, n_splits)
    out = []
    for b in blocks:
        if len(b)==0: continue
        out.append((b.iloc[0], b.iloc[-1]))
    return out

def mask_purged(all_dates, val_start, val_end, purge_days: int, embargo_days: int):
    left = val_start - pd.Timedelta(days=purge_days)
    right = val_end + pd.Timedelta(days=embargo_days)
    return (all_dates < left) | (all_dates > right)

def precision_at_k(y_true, y_score, k_abs=100):
    if len(y_score)==0: return float("nan")
    k = min(k_abs, len(y_score))
    idx = np.argsort(-np.array(y_score))[:k]
    return float(np.mean(np.array(y_true)[idx])) if k>0 else float("nan")

def main(cfg_path: str, override_task: str = None):
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    paths = cfg["paths"]
    train_path = Path(paths["out_dir"]) / "train_dataset.parquet"
    if not train_path.exists():
        raise SystemExit(f"train_dataset not found: {train_path}. Run features_join first.")
    df = pd.read_parquet(train_path)
    df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce").dt.tz_convert("UTC").dt.floor("D")

    task = override_task if override_task else cfg["training"]["task"]
    start = cfg["training"].get("start_date")
    end   = cfg["training"].get("end_date")
    if start: df = df[df["date"]>=pd.to_datetime(start, utc=True)]
    if end:   df = df[df["date"]<=pd.to_datetime(end, utc=True)]

    y = df[task].astype(int)
    id_cols = ["ticker","date"]
    y_cols = ["y_2x","y_10x","ttd_2x","ttd_10x","dd_min_252",
              "rel_1M","rel_3M","rel_12M","hit_rel_1M_10p","hit_rel_3M_20p","hit_rel_12M_50p"]
    feat_cols = [c for c in df.columns if c not in id_cols + y_cols]
    X = df[feat_cols].astype(float)
    dates = df["date"]

    n_splits = int(cfg["training"].get("n_splits",5))
    purge_days = int(cfg["training"].get("purge_days",21))
    embargo_days = int(cfg["training"].get("embargo_days",5))
    topk_abs = int(cfg["training"].get("topk_abs",100))

    folds = time_based_folds(dates, n_splits)
    metrics = []
    oof = pd.DataFrame({"ticker": df["ticker"], "date": dates, task: y, "pred": np.nan})

    params = cfg["lgbm"].copy()
    model = lgb.LGBMClassifier(
        num_leaves=int(params.get("num_leaves",64)),
        learning_rate=float(params.get("learning_rate",0.05)),
        n_estimators=int(params.get("n_estimators",600)),
        subsample=float(params.get("subsample",0.9)),
        colsample_bytree=float(params.get("colsample_bytree",0.8)),
        reg_lambda=float(params.get("reg_lambda",1.0)),
        random_state=int(params.get("random_state",42)),
        objective="binary",
        class_weight="balanced",
        n_jobs=-1
    )

    for i,(vstart,vend) in enumerate(folds, start=1):
        val_mask = (dates>=vstart) & (dates<=vend)
        train_mask = ~val_mask
        train_mask = train_mask & mask_purged(dates, vstart, vend, purge_days, embargo_days)

        X_tr, y_tr = X[train_mask], y[train_mask]
        X_va, y_va = X[val_mask], y[val_mask]
        if X_va.empty or X_tr.empty: continue

        model.fit(X_tr, y_tr)
        pred = model.predict_proba(X_va)[:,1]
        oof.loc[val_mask, "pred"] = pred
        row = {
            "fold": i,
            "val_start": str(vstart)[:10],
            "val_end": str(vend)[:10],
            "auc_roc": float(roc_auc_score(y_va, pred)) if len(np.unique(y_va))>1 else float("nan"),
            "auc_pr": float(average_precision_score(y_va, pred)) if len(y_va)>0 else float("nan"),
            "p_at_k": precision_at_k(y_va.values, pred, k_abs=topk_abs)
        }
        metrics.append(row)

    met = pd.DataFrame(metrics)
    reports_dir = Path(paths["reports_dir"]); ensure_dir(reports_dir)
    out_dir = Path(paths["out_dir"]); ensure_dir(out_dir)

    met.to_csv(reports_dir / f"model_cv_metrics_{task}.csv", index=False)
    oof.to_parquet(out_dir / f"oof_{task}.parquet", index=False)

    try:
        model.fit(X, y)
        imp = pd.DataFrame({
            "feature": feat_cols,
            "gain": model.booster_.feature_importance(importance_type="gain"),
            "split": model.booster_.feature_importance(importance_type="split")
        }).sort_values("gain", ascending=False)
        imp.to_csv(reports_dir / f"feature_importance_{task}.csv", index=False)
    except Exception:
        pass

    summary = {
        "task": task,
        "rows": int(len(df)),
        "features": int(len(feat_cols)),
        "cv_folds": int(len(met)),
        "cv_auc_roc_mean": float(met["auc_roc"].mean()) if not met.empty else None,
        "cv_auc_pr_mean": float(met["auc_pr"].mean()) if not met.empty else None,
        "cv_p_at_k_mean": float(met["p_at_k"].mean()) if not met.empty else None,
    }
    (reports_dir / f"model_cv_summary_{task}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    import argparse
    from sklearn.metrics import roc_auc_score, average_precision_score
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/model.yaml")
    ap.add_argument("--task", default=None)
    args = ap.parse_args()
    main(args.config, args.task)
