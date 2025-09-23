from pathlib import Path, re
f = Path("scripts/model_lightgbm_v2.py")
src = f.read_text(encoding="utf-8")

old = "return df.merge(aug, on=['ticker','eff_date'], how='left')"

new = r"""
    # === safe join to avoid many-to-many explosion ===
    # 0) keys normalize
    df["ticker"] = df["ticker"].astype(str)
    df["eff_date"] = pd.to_datetime(df["eff_date"]).dt.normalize()
    px["ticker"] = px["ticker"].astype(str)
    px["eff_date"] = pd.to_datetime(px["eff_date"]).dt.normalize()

    # 1) build unique key frame from df only
    df_keys = df.loc[:, ["ticker","eff_date"]].dropna().drop_duplicates()

    # 2) make px unique on key and keep only needed cols
    pxu = px.loc[:, ["ticker","eff_date","adj_close","volume","addv_3m"]].dropna(subset=["ticker","eff_date"])
    pxu = pxu.drop_duplicates(["ticker","eff_date"])

    # 3) inner join on unique keys (at most 1 row per key)
    aug = df_keys.merge(pxu, on=["ticker","eff_date"], how="left")

    # 4) many-to-one: map back to original df
    df = df.merge(aug, on=["ticker","eff_date"], how="left", validate="m:1")

    # 5) type downcast
    if "adj_close" in df.columns:
        df["adj_close"] = pd.to_numeric(df["adj_close"], errors="coerce").astype("float32")
    if "volume" in df.columns:
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype("int32")
    if "addv_3m" in df.columns:
        df["addv_3m"] = pd.to_numeric(df["addv_3m"], errors="coerce").astype("float32")

    return df
"""

if old not in src:
    raise SystemExit({"error":"merge return anchor not found"})
bak = f.with_suffix(".py.bak_safejoin")
bak.write_text(src, encoding="utf-8")
f.write_text(src.replace(old, new), encoding="utf-8")
print({"patched": True, "backup": str(bak)})
