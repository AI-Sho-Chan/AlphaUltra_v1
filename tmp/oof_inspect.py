import pandas as pd
o = pd.read_parquet(r"reports/checks/tdnet_model_y_2x_oof.parquet")
print({"rows":len(o),
       "pos":int((o["y"]==1).sum()),
       "score_min":float(o["score"].min()),
       "score_max":float(o["score"].max())})
