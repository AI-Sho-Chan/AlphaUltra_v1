# EVENT_TAXONOMY（TDNET分類規則・極性）

## 目的
TDNET見出し/本文をイベント種別に正規化し、**極性**（ポジ/ネガ/希薄化）、**強度**（規模比）、**新規性**（差分）を生成。

## 種別（例）とキーワード（抜粋）
- Earnings（決算短信）：`決算短信`、`連結業績`、`四半期決算`
- GuidanceUp/Down（業績予想修正）：`上方修正`、`下方修正`、`通期予想`、`業績予想修正`
- DividendUp/Down（配当）：`増配`、`減配`、`配当予想`
- Buyback（自社株買い）：`自己株式取得`、`自己株式の取得状況`
- EquityOffering/CB（希薄化）：`公募増資`、`第三者割当`、`転換社債`
- M&A/Subsidiary：`子会社設立`、`株式取得`、`事業譲受`、`合併`、`分割`
- LargeOrder/Contract：`大型受注`、`包括契約`、`基本合意`、`受注のお知らせ`
- Investment/Capex：`設備投資`、`生産能力増強`、`新工場`
- Partnership/Alliance：`業務提携`、`共同開発`
- Product/Approval：`発売開始`、`認可`、`承認`、`上市`
- ExecutiveChange：`社長交代`、`代表取締役の異動`
- Litigation/Scandal：`訴訟`、`お詫び`、`不適切`、`不祥事`

## 極性ルール（例）
- GuidanceUp/DividendUp/Buyback/LargeOrder/Product/Approval：**Positive**
- EquityOffering/CB/GuidanceDown/DividendDown/Litigation/Scandal：**Negative**
- ExecutiveChange/Investment/Partnership：**Neutral→文脈で補正**

## 強度の算出（例）
- Buyback：`買付総額 / 時価総額`
- DividendUp：`増額幅 / 時価総額` または `増配率`
- Investment：`投資額 / 売上高`
- GuidanceUp/Down：`新ガイダンス - 旧ガイダンス` の相対変化（取得可なら）

## 新規性
- 自社過去1年の同種イベント集合に対する **KL/JS/コサイン差分**、新規語率。

## 時刻ゲート
- `gate = clip(1 + α·strength + β·novelty, 0.5, 2.0)` を **発表当日〜N営業日** に適用。
- ネガ/希薄化は抑制ゲート（重み < 1）。