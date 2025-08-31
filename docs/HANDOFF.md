# HANDOFF（TDNETファースト / ゼロベースPIVOT 決定版）

## 目的と指標
- 目的：定性（**TDNET**/EDINET/EDGAR/ニュース）×定量（価格/ファンダ）で
  ① 1年2倍（y_2x）、② 3–5年10倍（y_10x）、③ S&P500超過（1M/3M/12M）を高精度検知。
- 最終運用目標：**アラートPPV≥80%**（校正後）。
- 合格ライン（OOS/WF）：y_2x P@K(1%)≥0.20、相対超過Hit-Rate>55/60/65%、ネットSharpe>0、**DSR>0**。

## 憲法（守ること）
- **リーケージ禁止**：発表時刻以降のみ定性使用。TDNETは**JST**を真実の時刻とする。
- **時間整合**：日足は**T+1寄り**以降に影響。`merge_asof(direction="forward", tolerance=1D, by=ticker)`。
- **検証**：Purged/Embargo付き時系列CV＋**クラスタPurge**（GICS/相関クラスタ）。
- **過学習検知**：**Deflated Sharpe Ratio**。
- **コスト**：US往復10bps/JP往復15bps控除。**流動性フィルタ**必須。
- **データ**：TDNET公式APIは不使用。**株探由来データ**等の提供データを前提。

## ユニバース（二系統）
- **Track‑A（発見）**：JP Growth＋JP Standard（高流動性サブセット）、US Russell 2000 Growth＋NASDAQ（高流動性サブセット）。
- **Track‑B（運用）**：S&P500＋JP Prime。

### 高流動性の暫定基準
- ADDV(3M)：JP≥1億円 / US≥$2M、価格：JP≥200円 / US≥$2、クォート・スプレッド中央値≤50bps。

### Wave展開
- Wave‑0：Aの液体サンプル200（JP100/US100）＋B代表100。
- Wave‑1：A=上記フル、B=S&P500＋JP Prime。
- Wave‑2：AにJP小型（液体）追加、BにRussell1000＋JP Standard拡張。
- Wave‑3：研究枠として超小型（運用は参考のみ）。

## 特徴量
- **TDNETイベント**：種別（決算/ガイダンス↑↓/配当↑↓/自社株買い/増資CB/大型受注/設備投資/提携/新製品承認/人事/不祥事訴訟 等）、極性、
  **強度**（比率化）、**新規性**（過去1年 KL/JS/コサイン・新規語率）、
  **時刻ゲート** `gate=clip(1+α·strength+β·novelty,0.5,2.0)`（当日〜N営業日）。
- **定量**：モメンタム12‑1/6‑1/3‑1、5D反転、20/60Dボラ、β、IdioVol、残差モメンタム。
- **文書差分**：EDINET/EDGARのMD&A/事業/リスクで前年差分。

## ラベル
- y_2x：`max(P_adj[t+1..t+252])/P_adj[t] ≥ 2`、y_10x：`max(...t+1260)/... ≥ 10`（12–24M早期兆候併用）。
- 相対：`R_rel(k)=R_stock(k)-R_bench(k)`（k=21/63/252）。フラグ＋連続値。

## 検証・校正
- Purged/Embargo＋クラスタPurge → Walk‑Forward（Train5y→Valid6m）。
- 指標：AUC‑ROC/PR、P@K、ネットSharpe、**DSR**、到達日数分布。
- 校正：**Isotonic**→**PPV‑Coverage**から θ*（PPV≥80%）を決定。

## 失敗時切り捨て
- WFで**DSR≤0が2期連続**、又はPPV≥80%帯のカバレッジ極小、又はTDNET寄与がAblationで有意でない。

## 次アクション（T0–T7抜粋）
- T0：`UNIVERSE_POLICY.md`/`EVENT_TAXONOMY.md`/`NEXT_STEPS_TDNET.md` を整備。
- T1：株探エクスポート→`data/raw/tdnet/` に正規化保存。
- T2：分類・極性・強度・新規性→`features_tdnet/tdnet_event_features.parquet`。
- T3：定量→`features_quant.parquet`、T4：ラベル→`labels/targets.parquet`、T5：結合→`dataset_final.parquet`。
- T6：CV/WF/DSR、T7：Isotonic→θ*固定。

本書は「ハンドオフ仕様」。更新はPRで。