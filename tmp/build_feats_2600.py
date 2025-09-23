FE="tmp/features_tdnet_q4_work.parquet"   # ← 2600
PX="data/proc/prices/jp_prices_std_compat_q4p.parquet"
NEED=["ret_5","ret_20","z20","mom20","v_z20"]
# 以下は build_feats_safe2_fix.py と同等ロジック（FEのみ差替）
# ※ファイル名: tmp/build_feats_2600.py
