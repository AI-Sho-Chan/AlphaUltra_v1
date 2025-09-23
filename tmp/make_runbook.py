import os, json, datetime
EXP=os.environ["EXP_DIR"]
evt=json.loads(open(os.path.join(EXP,"pick_evt.json"),encoding="utf-8").read())
meta=json.loads(open(os.path.join(EXP,"pick_meta.json"),encoding="utf-8").read())
fnd=json.loads(open(os.path.join(EXP,"fnd_best.json"),encoding="utf-8").read())

lines=[]
lines+=["# 運用提案 ({} )".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M")),""]
lines+=["## EVT（短期・イベント）",
         f"- 採択: H={evt.get('N') and 60 or '60'} / N={evt.get('N')} / コスト(bps)={evt.get('bps')}  ",
         f"- 年率超過(推定): {evt.get('ann'):.2f}  95%CI: [{evt.get('ci_lo'):.2f}, {evt.get('ci_hi'):.2f}]",
         "- ルール: しきい値0.205、日次で上位N銘柄、均等重み、保有H日"]
lines+=["","## FND（中期・ファンダ最小）",
         f"- 採択: α={fnd.get('alpha')}  k={fnd.get('k')}  PPV≈{fnd.get('ppv'):.2f}  coverage={fnd.get('coverage')}",
         "- ルール: 当日上位αを候補提示（J-Quants財務as-of導入後に再最適化）"]
lines+=["","## META（統合）",
         f"- 採択: {meta.get('rule')}  n={meta.get('n')}  年率≈{meta.get('ann')}  95%CI={meta.get('ci',['-','-'])}",
         "- ルール: EVT×FNDの統合スコア。月次CIの下限>0を目標にTOP-K/閾値を調整"]
lines+=["","## 次アクション",
         "1) J-Quants as-of 財務を追加してFND再最適化（EPS/売上/営益YoY, PBR, 配当, FCF）",
         "2) METAのTOP-Kと重み（等金額/1/vol）を並走評価して月次CI下限>0を達成",
         "3) EVTは採択パラメタで日次レポートを`reports/daily/`へ自動出力（候補・エントリー日・H日後EXIT日）"]
open(os.path.join(EXP,"RUNBOOK.md"),"w",encoding="utf-8").write("\n".join(lines))
print({"runbook":os.path.join(EXP,"RUNBOOK.md")})
