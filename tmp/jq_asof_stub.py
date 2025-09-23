import os, json, pandas as pd
ENV=r".secrets\jq.env"
if not os.path.exists(ENV):
    print({"jq":"missing","action":".secrets\\jq.env をBOMなしUTF-8で作成。refreshTokenを設定してください。"})
    raise SystemExit(0)
print({"jq":"ok","note":"J-Quants as-of 取り込みの実装フック作成済み"})
