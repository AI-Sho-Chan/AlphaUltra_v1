from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq
from pyarrow import Table
from datetime import datetime

def ensure_dir(p: str | Path) -> Path:
    path = Path(p)
    path.mkdir(parents=True, exist_ok=True)
    return path

def write_parquet(df: pd.DataFrame, path: str | Path):
    path = Path(path)
    ensure_dir(path.parent)
    table = Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, path)

def read_parquet(path: str | Path) -> pd.DataFrame:
    return pq.read_table(path).to_pandas()

def now_utc_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
