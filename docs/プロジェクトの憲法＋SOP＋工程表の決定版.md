結論：**TDNETファーストのゼロベース設計に全面ピボット。二系統ユニバースで「発見」と「運用」を分離。T+1寄り整合・リーケージ禁止・Purged/Embargo＋クラスタPurge・WF＋DSR・校正PPV≥80%**を憲法に固定する。以下が**完全版の方針＋SOP＋工程表**。

---

## 1. 開発の考え方／方針／内容（ゼロベース＋PIVOT版）

### 1.1 目的と到達基準

* 目的：定性（**TDNET**／EDINET／EDGAR／ニュース）×定量（価格／ファンダ）で
  ① **1年2倍**候補、② **3–5年10倍**候補、③ **S\&P500超過**候補（1M/3M/12M）を高精度に発見。
* 最終運用目標：**アラートPPV≥80%**（校正後）。
* 当面の合格ライン（OOS/Walk‑Forward）：

  * y\_2x：Precision\@K(1%) ≥ 0.20、ネットSharpe>0、**DSR>0**。
  * 相対超過：Hit-Rate 1M/3M/12M > 55/60/65%、ネットSharpe>0、DSR>0。
  * すべて**コスト控除**（US往復10bps、JP往復15bps）後。

### 1.2 守ること（憲法）

* **リーケージ禁止**：発表時刻以降のみ定性特徴使用。TDNETは**JST**をソース・オブ・トゥルース。
* **時間整合**：日足運用は**T+1寄り以降**に効果発現。`merge_asof(direction="forward", tolerance=1D, by=ticker)`。
* **検証規範**：Purged/Embargo 時系列CV＋**クラスタPurge**（GICS または相関クラスタ）。
* **過学習検知**：**Deflated Sharpe Ratio**。
* **流動性ガード**：ADDV、価格下限、スプレッド（中央値）でフィルタ。
* **データ**：TDNET公式APIは不使用。**株探由来データ**等の提供データを前提。

---

## 2. 設計の要点（TDNETゼロベース）

### 2.1 データ仕様

* TDNET（株探由来）：`code` 4桁、`title`、`published_at_jst`、`url_pdf`、`url_detail`、`body`（可能範囲）、**推定 event\_type**。
* 格納：`data/raw/tdnet/YYYY/MM/DD/<code>.json`。JPティッカーは `{code}.T` に正規化。
* EDINET/EDGAR：中期の文脈差分に使用（`acceptanceDateTime`/`submitDateTime`、不明時は提出日EOD）。
* ニュース：`published_at`、TDNETと重複除外。
* 価格・指数：日次OHLCV、企業アクション調整、ベンチは SPY 等。営業日整合は JPX/NYSE/Nasdaq カレンダー。

### 2.2 TDNETイベント → 特徴（学術的期待値の高い項目を選択）

* **イベント分類（例）**：
  決算短信、業績予想修正（上方／下方）、配当（増配／減配）、**自社株買い**、**増資／CB（希薄化）**、M\&A／子会社、**大型受注／契約**、設備投資、提携／共同開発、**新製品／承認**、人事（CEO/CFO）、不祥事／訴訟。
* **主要特徴**：

  * 種別ワンホット。
  * **極性**フラグ（上方・増配・買い等）／**希薄化**フラグ。
  * **強度**：金額・規模の**比率化**（買付総額/時価総額、投資額/売上、配当増額率 等）。
  * **新規性**：自社過去1年の同種イベント群に対する **KL/JS/コサイン差分**、新規語率。
  * **時刻ゲート**：`gate = clip(1 + α·event_strength + β·novelty, 0.5, 2.0)` を発表当日〜N営業日（初期N=3、探索最大N=5）に適用。ネガや希薄化は抑制ゲート（重み<1）。
* **定量融合**：12‑1/6‑1/3‑1モメンタム、5D反転、20/60Dボラ、β、IdioVol、**残差モメンタム**。
* **結合規範**：`ticker,date`で asof forward（**T+1寄り**）→ `dataset_final.parquet`。

### 2.3 検証設計

* **ターゲット**：

  * y\_2x：`max(P_adj[t+1..t+252]/P_adj[t]) ≥ 2`。
  * y\_10x：`max(P_adj[t+1..t+1260]/P_adj[t]) ≥ 10`（12–24M 早期兆候も追跡）。
  * 相対：`R_rel(k)=R_stock(k)-R_bench(k)`（k=21/63/252）、閾値到達フラグ＋連続値。
* **CV**：Purged/Embargo（y\_2x: 20–30D、y\_10x: 長め）。**クラスタPurge**。
* **Walk‑Forward**：Train 5y → Valid 6m → スライド。
* **指標**：AUC‑ROC/PR、P\@K（1%/5%）、トップKロングの**ネットSharpe**、**DSR**、到達日数分布。
* **校正**：OOF予測→**Isotonic**。**PPV‑Coverage曲線**で θ\*（PPV≥80%）決定。
* **切り捨て基準**：WFでDSR≤0が**連続2期**／PPV80%帯の**カバレッジ極小**。

---

## 3. ユニバース拡大の考え方と計画

### 3.1 回答（懸念への対応）

* 2x/10xは**Growth/小型**に多い。見落とし防止のため**Track‑A**を独立運用。
* Sharpeとキャパシティは**大型**が有利。相対超過は**Track‑B**で安定運用。
* よって**二系統同時運転**が合理的。

### 3.2 実装計画（段階展開）

* **Track‑A（発見）**：JP Growth＋JP Standard（**高流動性サブセット**）、US Russell 2000 Growth＋NASDAQ（**高流動性サブセット**）。

  * 流動性（暫定）：ADDV 3M **JP≥1億円／US≥\$2M**、価格 **JP≥200円／US≥\$2**、スプレッド中央値≤50bps。
* **Track‑B（運用）**：S\&P500＋JP Prime。
* **Wave**：

  * Wave‑0：Aのサンプル200銘柄（JP100/US100）＋Bの代表100（配管確認）。
  * Wave‑1：A=上記フル、B=S\&P500＋JP Prime。
  * Wave‑2：AにJP小型（高流動性ゾーン）追加、BにRussell1000＋JP Standard拡張。
  * Wave‑3：研究枠として超小型。運用シグナルは参考のみ。

---

## 4. 新チャット初動SOP（TDNET版 DayT0–T7）

* **T0 準備**：`docs/UNIVERSE_POLICY.md`（二系統と流動性閾値）、`docs/EVENT_TAXONOMY.md`（分類・極性規則）を作成。
* **T1 取込**：株探エクスポートを `data/raw/tdnet/YYYY/MM/DD/*.json` に正規化。キーは `{code}.T`。
* **T2 特徴化**：`tdnet_event_features.parquet` を作成（種別／極性／強度／新規性／ゲート）。
* **T3 定量**：`features_quant.parquet`（モメンタム、ボラ、β、IdioVol、残差モメンタム）。
* **T4 ラベル**：`targets.parquet`（y\_2x／y\_10x／相対）。
* **T5 結合**：asof forward（**T+1寄り**）で `dataset_final.parquet`。
* **T6 検証**：Purged/Embargo CV＋Walk‑Forward＋**DSR**、A/B別に評価。
* **T7 校正**：Isotonic→PPV‑Coverage→θ\*保存（`configs/thresholds.yaml`）。A/B別々に実施。

---

## 5. 引き継ぎドキュメント差し替え

* `docs/HANDOFF.md`（本方針に刷新）、`docs/UNIVERSE_POLICY.md`、`docs/EVENT_TAXONOMY.md`、`docs/NEXT_STEPS_TDNET.md`。
* `reports/checks/handoff_status.json` に現状メトリクスと「TDNETファースト」を明記。
* 運用ルール：\*\*「コミットSHA＋ログ末尾20行＋成果物存在チェック3行」\*\*のみ共有。

---

## 6. まとめ（意思決定）

* **今すぐゼロベースに切替**。一次情報は**TDNET**。
* \*\*Track‑A（発見）**と**Track‑B（運用）\*\*の二系統。
* 検証は**WF＋DSR**、運用は\*\*校正PPV≥80%\*\*で閾値設定。
* 段階的にユニバース拡大。**小型Growthの取りこぼし回避**と**大型の安定Sharpe**を両立。

---

## 7. 次にやるべきこと（人間=管理者の作業）

1. **リポのdocs更新**：上記4ファイルを作成しコミット。
2. **株探エクスポート**：まず**直近90日分**を `data/raw/tdnet/` へ投入（日付フォルダで保存）。
3. **最小動作確認**：T1→T3までのログ末尾と成果物存在チェックを提示。以後は私がSOPに沿って誘導。

---

## 8. 日毎の詳細工程表（ゼロベースPIVOT版）

> 期間の目安：**28日**。二系統の同時実装と校正まで含む。各日の**達成・合格基準**を明記。
> すべてのチェックは**存在判定（ファイル）＋ログ末尾20行**で報告。

### Day 0：方針確定とドキュメント刷新

* 作業：`HANDOFF.md`、`UNIVERSE_POLICY.md`、`EVENT_TAXONOMY.md`、`NEXT_STEPS_TDNET.md` 作成。
* 合格：4ファイルが `docs/` に存在。コミット完了。

### Day 1：TDNET取込パイプライン雛形

* 作業：`scripts/tdnet_ingest.py`（株探エクスポート→正規化保存）。90日分で試走。
* 合格：`data/raw/tdnet/YYYY/MM/DD/*.json` が**各日10件以上**。ログで失敗0件。

### Day 2：イベント分類・極性ルール実装

* 作業：`EVENT_TAXONOMY.md`に従いマッピング。上方修正／増配／希薄化等の正規表現・辞書。
* 合格：90日分で**分類成功率≥95%**（未分類は要ラベル）。

### Day 3：強度・新規性スコア

* 作業：金額比率計算、過去1年比較の KL/JS/コサイン、新規語率。
* 合格：`features_tdnet/tdnet_event_features.parquet` 出力。**行数＝原イベント数±5%以内**。

### Day 4：時刻ゲート実装

* 作業：`gate = clip(1 + α·strength + β·novelty, 0.5, 2.0)`、適用窓 N=3 初期。
* 合格：ゲート有／無で特徴列が増分。**NaNなし**。分布サマリOK。

### Day 5：定量特徴

* 作業：12‑1/6‑1/3‑1、5D反転、20/60Dボラ、β、IdioVol、残差モメンタム。
* 合格：`features_quant.parquet` 出力。**欠損率<2%**。

### Day 6：ラベル生成

* 作業：y\_2x／y\_10x／相対（1M/3M/12M）。企業アクション調整と T+1基準で定義。
* 合格：`labels/targets.parquet` 出力。**y\_2x陽性率 1–5% 圏内**（ユニバースによる）。

### Day 7：結合

* 作業：asof forward（**T+1寄り**）、`dataset_final.parquet`。
* 合格：**行数>3万**（Wave‑0規模で目安）。`ticker,date` 重複なし。ラベル欠損率<1%。

### Day 8：Ablation準備とベースライン学習（Track‑A y\_2x）

* 作業：LightGBMでCV=5。TDNETのみ／定量のみ／融合の3パターン。
* 合格：融合が**P\@K(1%)で最良**。AUC‑PRがTDNETのみより\*\*+2pp\*\*以上。

### Day 9：Track‑B 相対超過ベースライン

* 作業：同上。
* 合格：Hit-Rate 1M/3M/12M > 55/60/65%（CV平均）。Sharpe>0。

### Day 10：Purged/Embargo 実装

* 作業：ラベル窓とイベント窓に合わせた purge。embargo 初期20D。
* 合格：**CVリーケージ検査OK**。スコアの異常上振れなし。

### Day 11：クラスタPurge

* 作業：GICS or 相関クラスタ。検証窓の同クラスタ近接を学習から除外。
* 合格：AUC変化が±2pp以内で安定。**過学習所見が減少**。

### Day 12：Walk‑Forward実装

* 作業：Train 5y → Valid 6m → スライド。トップKロングの**ネットSharpe**算出。
* 合格：Track‑A/B ともネットSharpe>0。

### Day 13：DSR計算

* 作業：WF Sharpe を DSR で評価。
* 合格：**DSR>0**。不合格なら特徴かゲートを見直し。

### Day 14：OOF予測収集

* 作業：CV/OOFスコアを集約。
* 合格：`oof_{task}.csv` 出力。分布・キャリブレーションカーブの前検。

### Day 15：Isotonic校正

* 作業：タスク別にIsotonic。
* 合格：信頼度曲線の**対角線への接近**。Brier改善。

### Day 16：PPV‑Coverage 曲線と閾値 θ\*

* 作業：PPV vs Coverage を作成。\*\*PPV≥80%\*\*満たす最小θ\*を決定。
* 合格：`configs/thresholds.yaml` に θ\* 固定。日次平均カバレッジ≥**0.5件/日**。

### Day 17：ゲート α/β 探索

* 作業：Purged CV で小レンジグリッド。
* 合格：P\@KとSharpeが**同時改善**。過振幅なし（clip範囲内）。

### Day 18：Ablation（決定版）

* 作業：TDNETのみ／定量のみ／融合／ゲート有無。
* 合格：融合＋ゲートが**統計的優位**（P\@K差≥+1pp）。

### Day 19：ユニバース Wave‑1 拡大

* 作業：Track‑A/Bを本番規模へ。増分学習と再検証。
* 合格：合格ライン維持。処理時間・メモリがSLA内。

### Day 20：y\_10x 早期兆候評価

* 作業：12–24Mでの3–5倍達成率を代用指標に。サバイバル補助も検討。
* 合格：早期兆候の**Precision改善**が確認できる。

### Day 21：相対超過の実運用プロト

* 作業：θ\*運用で日次アラート候補を生成。
* 合格：**偽陽性抑制**と**実効カバレッジ**の両立。

### Day 22：監視・ドリフト検知

* 作業：重要度安定性、Shapley drift、データ欠損監視。
* 合格：逸脱時のフェイルセーフ手順を定義。

### Day 23：フォールトトレランス

* 作業：再試行、ネットワーク失敗時の保守動作、ログ収集ZIP自動化。
* 合格：**無停止処理**の実地テスト通過。

### Day 24：リスク管理・コスト精緻化

* 作業：ボラ・スプレッド・体制化コストの更新。
* 合格：ネットSharpeが過去日付で安定。

### Day 25：閾値とアラートUX

* 作業：θ\*でアラート生成。根拠（イベント種別・強度・新規性）を添付。
* 合格：日次通知テストで**誤報0件**（定義に基づく）。

### Day 26：ドキュメント最終化

* 作業：仕様、SOP、運用Runbook、しきい値更新手順。
* 合格：第三者が本書のみで再現可能。

### Day 27：最終WF＋DSRの再実行

* 作業：Wave‑1ユニバースで再評価。
* 合格：合格ライン再満足。PPV≥80%閾値の妥当性維持。

### Day 28：出荷判定

* 作業：①②③の各タスクで**校正済みθ**\*を用いたアラート生成が稼働。
* 合格：Go。NoGoなら**原因切り分け→巻き戻し点を特定**。

---

## 9. 引き継ぎに必要な最小物（新チャットに貼る／置く）

* **初期化プロンプト v3.1**（前回提示の最新版）。
* `docs/UNIVERSE_POLICY.md`（二系統と流動性閾値）、`docs/EVENT_TAXONOMY.md`（分類・極性）、`docs/NEXT_STEPS_TDNET.md`（T0–T7 SOP）。
* `reports/checks/handoff_status.json`（現状数値と「TDNETファースト」明記）。

---

## 10. すぐやる最小操作（人間=管理者がおこなうこと）

* **Docs反映**：上記4ファイルを `docs` に追加してコミット。
* **TDNETサンプル投入**：直近90日分を `data/raw/tdnet/` 階層で保存。
* **ログ共有**：T1〜T3まで実行し、**コミットSHA＋対象ログ末尾20行＋成果物存在3行**を送る。

以上。これが本プロジェクトの**憲法＋SOP＋工程表**の決定版。これに従えば、新チャットでも作業を連続的に継承できる。
