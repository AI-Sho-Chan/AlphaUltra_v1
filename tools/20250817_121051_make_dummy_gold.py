import pandas as pd, numpy as np, pathlib
base = pathlib.Path("C:/AI/AlphaUltra/data/gold")
base.mkdir(parents=True, exist_ok=True)
dates = pd.date_range("2024-01-01", periods=30, freq="B")
tickers = [f"JP{i:04d}" for i in range(1,101)]
idx = pd.MultiIndex.from_product([dates, tickers], names=["date","ticker"])
rng = np.random.default_rng(0)
features = pd.DataFrame({
    "date": idx.get_level_values("date"),
    "ticker": idx.get_level_values("ticker"),
    "scs": rng.normal(0,1,size=len(idx)),
    "sent": rng.normal(0,1,size=len(idx)),
    "vol": rng.lognormal(mean=0, sigma=1, size=len(idx))
})
labels = pd.DataFrame({
    "date": idx.get_level_values("date"),
    "ticker": idx.get_level_values("ticker"),
    "target_5d": rng.normal(0,0.02,size=len(idx)),
    "target_20d": rng.normal(0,0.05,size=len(idx))
})
features.to_parquet(base/"features_sample.parquet", index=False)
labels.to_parquet(base/"labels_sample.parquet", index=False)
print("dummy gold written")

