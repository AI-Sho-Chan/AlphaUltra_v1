from pathlib import Path
f = Path("scripts/model_lightgbm_v2.py")
src = f.read_text(encoding="utf-8")

anchor = "    # === end key normalization ==="
patch = r"""
    # === pre-merge reduction to avoid many-to-many ===
    # 1) key types
    df["ticker"] = df["ticker"].astype(str)
    px["ticker"] = px["ticker"].astype(str)
    df["eff_date"] = pd.to_datetime(df["eff_date"]).dt.normalize()
    px["eff_date"] = pd.to_datetime(px["eff_date"]).dt.normalize()

    # 2) unique keys on both sides
    df_keys = df.loc[:, ["ticker","eff_date"]].dropna().drop_duplicates()
    px = px.loc[:, ["ticker","eff_date","adj_close","volume","addv_3m"]].dropna(subset=["ticker","eff_date"]).drop_duplicates()

    # 3) semi-join: keep only keys present in df
    px = px.merge(df_keys, on=["ticker","eff_date"], how="inner")

    # 4) downcast to save memory
    px["adj_close"] = pd.to_numeric(px["adj_close"], errors="coerce").astype("float32")
    px["volume"]    = pd.to_numeric(px["volume"],    errors="coerce").fillna(0).astype("int32")
    if "addv_3m" in px.columns:
        px["addv_3m"] = pd.to_numeric(px["addv_3m"], errors="coerce").astype("float32")
    # === end pre-merge reduction ===
"""
if anchor not in src:
    raise SystemExit({"error":"anchor not found"})
out = src.replace(anchor, anchor + patch)
bak = f.with_suffix(".py.bak_mm")
bak.write_text(src, encoding="utf-8")
f.write_text(out, encoding="utf-8")
print({"patched": True, "backup": str(bak)})
