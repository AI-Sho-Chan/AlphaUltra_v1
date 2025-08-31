# UNIVERSE_POLICY（二系統運用）

## 目的
- Track‑A（発見）：2x/10xの取りこぼし回避（Growth/小型の**高流動性**ゾーン）。
- Track‑B（運用）：相対超過でSharpeとキャパシティを両立（大型）。

## 対象範囲
- JP：Growth/Standard/Prime を銘柄マスタで管理。JPはティッカー `{code}.T` に正規化。
- US：NASDAQ、Russell 2000 Growth、S&P500、Russell1000。

## 高流動性（暫定しきい値）
- ADDV(3M)：JP≥1億円 / US≥$2M
- 価格下限：JP≥200円 / US≥$2
- クォート・スプレッド中央値：≤50bps
- 補助：売買回転率、約定率。

## 除外
- 仕手/超低流動、連続SUSP、極端な価格帯外（逆日歩常態等）。

## Wave展開
- Wave‑0：A=JP100/US100、B=代表100（配管確認）
- Wave‑1：A=Growth＋Standard(液体)＋R2G/NASDAQ(液体)、B=S&P500＋JP Prime
- Wave‑2：AへJP小型(液体)追加、BへRussell1000＋JP Standard拡張
- Wave‑3：研究枠（超小型）、運用は参考のみ

## メンテ
- 月次で流動性再計算。ADDV/価格/スプレッドの**どれか不適合**で除外。
- 銘柄入替は**月次ローテーション日**に一括反映。