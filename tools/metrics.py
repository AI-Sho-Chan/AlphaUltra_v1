import pandas as pd
import numpy as np


def precision_at_k(df_scored: pd.DataFrame, k: int = 50, label_col: str = "target_5d", score_col: str = "pred_score") -> float:
    """
    df_scored: columns [date, ticker, pred_score, target_5d]
    1日ごとに pred_score 上位K銘柄の label>0 比率を求め、日次平均を返す
    """
    if df_scored is None or len(df_scored) == 0:
        return 0.0
    daily = []
    for _, g in df_scored.groupby("date"):
        g = g.sort_values(score_col, ascending=False).head(k)
        if len(g) == 0:
            continue
        hit = (g[label_col] > 0).mean()
        daily.append(float(hit))
    return float(np.mean(daily)) if daily else 0.0


def portfolio_5d_returns(df_scored: pd.DataFrame, k: int = 50, label_col: str = "target_5d", score_col: str = "pred_score") -> pd.Series:
    """
    1日ごとに pred_score 上位Kの target_5d の平均を、その日の“5日保有リターン”とみなす簡易シリーズを返す。
    """
    if df_scored is None or len(df_scored) == 0:
        return pd.Series(dtype=float)
    rets = []
    for d, g in df_scored.groupby("date"):
        g = g.sort_values(score_col, ascending=False).head(k)
        if len(g) == 0:
            continue
        rets.append((d, float(g[label_col].mean())))
    if not rets:
        return pd.Series(dtype=float)
    s = pd.Series([r for _, r in rets], index=[d for d, _ in rets]).sort_index()
    s.name = "ret_5d"
    return s


def sharpe_from_5d(ret5: pd.Series, periods_per_year: int = 252 // 5) -> float:
    """
    5日リターン系列から年率Sharpeを概算。平均/標準偏差 * sqrt(年換算頻度)
    """
    if ret5 is None or len(ret5) < 2:
        return 0.0
    mu = float(ret5.mean())
    sd = float(ret5.std(ddof=1))
    if sd == 0.0:
        return 0.0
    return float(mu / sd * np.sqrt(periods_per_year))


def max_drawdown_from_5d(ret5: pd.Series) -> float:
    """
    5日ステップの累積曲線の最大ドローダウン（簡易）。
    """
    if ret5 is None or len(ret5) == 0:
        return 0.0
    curve = (1.0 + ret5).cumprod()
    peak = curve.cummax()
    dd = (curve / peak) - 1.0
    return float(dd.min())

