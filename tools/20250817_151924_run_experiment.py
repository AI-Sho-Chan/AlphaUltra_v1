import argparse, json, os, yaml, pathlib, datetime, sys, re, traceback
import pandas as pd

tools = pathlib.Path("C:/AI/AlphaUltra/tools")
if tools.exists():
    sys.path.insert(0, str(tools))
from schema_validate import main as schema_check
from metrics import precision_at_k, portfolio_5d_returns, sharpe_from_5d, max_drawdown_from_5d

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*", re.DOTALL)


def load_yaml_maybe_with_fm(p: pathlib.Path):
    txt = pathlib.Path(p).read_text(encoding="utf-8")
    m = FM_RE.match(txt)
    return yaml.safe_load(m.group(1) if m else txt)


def find_latest_config(exp_root: pathlib.Path):
    cands = list(exp_root.rglob("*.yaml"))
    if not cands:
        raise FileNotFoundError("no config.yaml found under experiments/")
    return sorted(cands, key=lambda q: q.stat().st_mtime, reverse=True)[0]


def ensure_dir(p: pathlib.Path):
    pathlib.Path(p).mkdir(parents=True, exist_ok=True)


def load_gold(features_path, labels_path):
    f = pd.read_parquet(features_path)
    y = pd.read_parquet(labels_path)
    for col in ["date", "ticker"]:
        if col not in f.columns or col not in y.columns:
            raise ValueError(f"features/labels must include '{col}'")
    f["date"] = pd.to_datetime(f["date"])
    y["date"] = pd.to_datetime(y["date"])
    return pd.merge(f, y, on=["date", "ticker"], how="inner")


def safe_write_json(path: pathlib.Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", help="path to experiment config yaml")
    ap.add_argument("--registry", default="C:/AI/AlphaUltra/data/datasets_registry.yaml")
    ap.add_argument("--k", type=int, default=None)
    args = ap.parse_args()

    proj = pathlib.Path("C:/AI/AlphaUltra")
    try:
        cfg_path = pathlib.Path(args.config) if args.config else find_latest_config(proj / "experiments")
        cfg = load_yaml_maybe_with_fm(cfg_path)
        schema_check(str(cfg_path))
        exp = cfg["experiments"][0]
        exp_id = exp["exp_id"]
        exp_dir = proj / "experiments" / exp_id
        ensure_dir(exp_dir / "figures")
        ensure_dir(exp_dir / "artifacts")

        # runner info
        (exp_dir / "runner_info.txt").write_text(
            f"cfg={cfg_path}\nexp_id={exp_id}\nregistry={args.registry}\n", encoding="utf-8"
        )

        reg = load_yaml_maybe_with_fm(args.registry)
        ds_key = exp.get("data", {}).get("dataset", "jp_default")
        ds = reg["datasets"][ds_key]
        df = load_gold(ds["features_path"], ds["labels_path"])

        # score
        allowed = {"zscore_scs", "zscore_sent", "vol_bucket", "scs", "sent", "vol"}
        expr = (exp.get("features") or {}).get(
            "score_formula", "0.7*zscore_scs + 0.3*zscore_sent - 0.1*vol_bucket"
        )
        ns = {c: df[c].astype(float) for c in df.columns if c in allowed}
        df = df.copy()
        df["pred_score"] = eval(expr, {"__builtins__": {}}, ns)

        # K: CLI > config
        k_cfg = 50
        for s in (exp.get("evaluation", {}).get("signal", []) or []):
            if isinstance(s, str) and s.startswith("precision@"):
                try:
                    k_cfg = int(s.split("@")[1])
                except Exception:
                    pass
        K = args.k if args.k is not None else k_cfg

        label_col = exp.get("targets", {}).get("label_cols", {}).get("5d", "target_5d")
        df_ev = df[["date", "ticker", "pred_score", label_col]].dropna()
        p_at_k = precision_at_k(df_ev, k=K, label_col=label_col)
        ret5 = portfolio_5d_returns(df_ev, k=K, label_col=label_col)
        sharpe = sharpe_from_5d(ret5)
        maxdd = max_drawdown_from_5d(ret5)

        now = datetime.datetime.now().isoformat()
        metrics = {
            "timestamp": now,
            "exp_id": exp_id,
            "dataset": ds_key,
            "k": K,
            "signal_metrics": {"precision_at_k": float(p_at_k)},
            "portfolio_metrics": {
                "sharpe_annualized": float(sharpe),
                "max_drawdown": float(maxdd),
                "turnover": 0.0,
            },
            "notes": f"score from config: {expr}",
        }
        safe_write_json(exp_dir / "metrics.json", metrics)
        with (exp_dir / "run.log").open("a", encoding="utf-8") as f:
            f.write(f"{now} | RUN OK | cfg={cfg_path}\n")
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
    except Exception as e:
        exp_id = locals().get("exp_id", "EXP_UNKNOWN")
        exp_dir = proj / "experiments" / exp_id
        ensure_dir(exp_dir)
        err = f"{datetime.datetime.now().isoformat()} | ERROR: {e}\n{traceback.format_exc()}"
        (exp_dir / "error.log").write_text(err, encoding="utf-8")
        stub = {
            "timestamp": datetime.datetime.now().isoformat(),
            "exp_id": exp_id,
            "dataset": "unknown",
            "k": args.k,
            "signal_metrics": {"precision_at_k": 0.0},
            "portfolio_metrics": {"sharpe_annualized": 0.0, "max_drawdown": 0.0, "turnover": 0.0},
            "notes": f"ERROR: {str(e)}",
        }
        safe_write_json(exp_dir / "metrics.json", stub)
        print(err, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

