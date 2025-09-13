import pathlib, subprocess, json, time, csv, itertools
from datetime import datetime

ROOT=pathlib.Path(r"C:\AI\AlphaUltra")
RUN = ROOT/"tools"/"run_experiment.py"
EXP = ROOT/"experiments"
OUT = ROOT/"reports"/"compare"
OUT.mkdir(parents=True, exist_ok=True)

# 固定条件（必要なら書き換え）
DATE_MIN="2025-06-24"; DATE_MAX="2025-08-24"; K_LIST=[50]
COST_BPS=10

# 探索空間
modes = ["add","gate"]                               # 加算 or ゲート
add_scales  = [0.5, 1.0, 2.0, 5.0]                   # ret20-ret5 + s*(0.5*novelty_z+0.5*size_raw_z)
gate_scales = [5, 10, 15, 20, 30]                    # (ret20-ret5)*(1 + s*event_strength)

def make_cfg(exp_dir: pathlib.Path, formula: str, exp_id: str):
    cfg = f"""---
project_meta: {{ name: {exp_id}, dataset: yahoo_default }}
experiments:
  - exp_id: {exp_id}
    data: {{ dataset: yahoo_default }}
    features: {{ score_formula: "{formula}" }}
    targets: {{ label_col: fret5 }}
    validation: {{ type: cv, folds: 1 }}
    models: []
    hypothesis: sweep
    evaluation: {{ metrics: [precision_at_k, sharpe_annualized, max_drawdown] }}
"""
    exp_dir.mkdir(parents=True, exist_ok=True)
    (exp_dir/"config.yaml").write_text(cfg, encoding="utf-8")

def run_one(exp_id: str):
    cfg = EXP/exp_id/"config.yaml"
    cmd = ["python", str(RUN), "--config", str(cfg),
           "--k", str(K_LIST[0]),
           "--date_min", DATE_MIN, "--date_max", DATE_MAX,
           "--cost_bps", str(COST_BPS)]
    subprocess.run(cmd, check=False)

def read_metrics(exp_id: str):
    f = EXP/exp_id/"metrics.json"
    if not f.exists(): return None
    m = json.loads(f.read_text(encoding="utf-8"))
    P = m["portfolio_metrics"]; S = m["signal_metrics"]
    return {
        "exp":exp_id, "k":m.get("k",K_LIST[0]),
        "p_at_k":S.get("precision_at_k",0.0),
        "sharpe":P.get("sharpe_annualized",0.0),
        "sharpe_net":P.get("sharpe_annualized_net",0.0),
        "maxDD":P.get("max_drawdown",0.0),
        "turnover":P.get("turnover_daily",0.0)
    }

def main():
    stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    exp_ids=[]
    # 生成：加算系
    for s in add_scales:
        formula=f"ret20 - ret5 + {s}*(0.5*novelty_z + 0.5*size_raw_z)"
        exp_id=f"SWP_{stamp}_ADD_{s}".replace(".","p")
        make_cfg(EXP/exp_id, formula, exp_id); exp_ids.append(exp_id)
    # 生成：ゲート系
    for s in gate_scales:
        formula=f"(ret20 - ret5) * (1 + {s}*event_strength)"
        exp_id=f"SWP_{stamp}_GATE_{s}"
        make_cfg(EXP/exp_id, formula, exp_id); exp_ids.append(exp_id)

    # 実行
    for eid in exp_ids:
        run_one(eid)

    # 収集
    rows=[r for eid in exp_ids if (r:=read_metrics(eid))]
    rows_sorted=sorted(rows, key=lambda x:(x["sharpe_net"],x["p_at_k"]), reverse=True)

    # 保存
    csvp=OUT/f"sweep_{stamp}.csv"
    with open(csvp,"w",newline="",encoding="utf-8") as w:
        wr=csv.DictWriter(w, fieldnames=list(rows_sorted[0].keys()))
        wr.writeheader(); wr.writerows(rows_sorted)
    md=OUT/f"sweep_{stamp}.md"
    md.write_text("# Sweep Summary\n\n"+"|exp|k|p@k|sharpe_net|sharpe|maxDD|turnover|\n|---|---:|---:|---:|---:|---:|---:|\n" +
                  "\n".join([f"|{r['exp']}|{r['k']}|{r['p_at_k']:.3f}|{r['sharpe_net']:.3f}|{r['sharpe']:.3f}|{r['maxDD']:.3f}|{r['turnover']:.3f}|"
                            for r in rows_sorted[:20]]), encoding="utf-8")
    print("[SWEEP] done ->", csvp, md)
if __name__=="__main__": main()