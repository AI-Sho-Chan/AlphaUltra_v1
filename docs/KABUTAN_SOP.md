# KABUTAN_SOP（TDNETファースト連携）

## 目的
Kabutanのエクスポート機能（有料プラン）で取得した適時開示を、本プロジェクトの標準スキーマに正規化し、特徴抽出・学習に接続する。

## データ配置
- 置き場：`data/raw/tdnet/inbox/`
- 受入拡張子：`.csv`, `.tsv`, `.json`
- 受入列名（いずれかの同義語で可）
  - コード：`code` / `銘柄コード` / `証券コード` / `コード`
  - 見出し：`title` / `表題` / `件名` / `タイトル` / `見出し`
  - 公開時刻：`published_at` / `開示日時` / `公開日時` / `日時` / `date` / `time`
  - PDF：`url_pdf` / `PDF` / `PDFリンク` / `pdf` / `PDFURL`
  - 詳細URL：`url_detail` / `URL` / `リンク` / `詳細URL`
  - 本文：`body` / `本文` / `内容` / `text`

## 実行手順（手動）
1. Kabutanから期間指定でエクスポート → `data/raw/tdnet/inbox/` に保存
2. 実行：`$env:PYTHONPATH=(Get-Location).Path; .\scripts	dnet_on_new.ps1`
3. 成果物：`data/proc/features_tdnet/tdnet_event_features.parquet`

## 監視（半自動）
- 起動：`.\scripts	dnet_watch_folder.ps1`
- 新規ファイル作成を検知し、インジェスト→特徴化を自動実行。
- （任意）`register_tdnet_watcher_task.ps1` でWindowsログオン時に自動起動。

## 重要事項
- Kabutanの利用規約・許諾範囲を遵守。自動化は規約の許す範囲でのみ実施。
- 時刻はJST（tz付き）で保持。学習結合は**T+1寄り**に限定（リーケージ禁止）。
