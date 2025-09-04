# ALGO CONSTITUTION / ROLES & GUARDRAILS (v1)

## 0. 目的
一次情報（TDNET）×定量で ①1年2倍 ②3–5年テンバガー ③S&P500超過 を発見し、**PPV≥80%**のアラート運用を実現する。:contentReference[oaicite:2]{index=2}

## 1. 役割分担（憲法）
### Architect（あなた/AlphaUltra）
- 規範の制定・保持：**リーケージ禁止**（JST/T+1）、**Purged/Embargo**＋**クラスタPurge**、**WF＋DSR**、**Isotonic校正→PPV≥80%**。:contentReference[oaicite:3]{index=3}
- ユニバース方針：Track-A（発見/小型液体）とTrack-B（運用/大型）を分離運用。:contentReference[oaicite:4]{index=4}
- KPI/ゲート：P@K、NetSharpe、DSR、PPV-Coverage、流動性閾値（ADDV/価格/スプレッド）。:contentReference[oaicite:5]{index=5}
- 最終承認：θ*（PPV≥80%）固定と出荷判断。

### Executor（Codex CLI）
- 実装と運用の自動化：**データ取得→正規化→特徴→価格→T+1結合→健全性**のETL/DAG整備。
- ロバスト化：**v1配下固定出力**、**UTF-8**、**0件でもCSV作成**、**0件時はHTML保存**、再試行/リトライ、年次バッチ、差分取得、ログ末尾20行を常時出力。
- レポート：成果物存在チェック（3点）＋KPI（coverage、行数、期間）。

## 2. ガードレール（必須）
- **時間整合**：日次は**次の取引日（T+1の寄り）**に forward as-of / searchsorted で結合。:contentReference[oaicite:6]{index=6}
- **検証**：Purged/Embargo 時系列CV、Walk-Forward、**DSR**。:contentReference[oaicite:7]{index=7}
- **校正**：OOF→Isotonic、**PPV-Coverage**でθ*決定。:contentReference[oaicite:8]{index=8}
- **ユニバース**：Track-A/B、流動性基準（JP≥1億円、US≥$2M 等）を厳守。:contentReference[oaicite:9]{index=9}
- **禁止**：発表前の定性使用、v1外パス書き込み、非UTF-8、未保存のデバッグでの再試行。

## 3. 成果物とログ
- data/raw/tdnet/YYYY/MM/DD/*.json、features_tdnet.parquet、jp_prices_std.parquet、dataset_final.parquet、labels/targets.parquet。
- reports/checks/*.log の末尾20行＋「存在チェック3行」を常時提示。:contentReference[oaicite:10]{index=10}

## 4. 合格ライン（Wave-0目安）
- features_rows ≥ 30k、coverage > 0.95、y_2x陽性率 1–5%。:contentReference[oaicite:11]{index=11}
