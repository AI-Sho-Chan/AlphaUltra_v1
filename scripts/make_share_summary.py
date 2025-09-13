import pathlib, json
from datetime import datetime
import pyarrow.parquet as pq
import pandas as pd
out_dir = pathlib.Path(r'reports/share'); out_dir.mkdir(parents=True, exist_ok=True)
summary = {'generated_at': datetime.utcnow().isoformat()+'Z', 'adj_files': []}
adj = pathlib.Path(r'data/proc/adj_prices')
if adj.exists():
    for p in sorted(adj.glob('*.parquet')):
        try:
            rows = pq.ParquetFile(p).metadata.num_rows
        except Exception:
            rows = None
        summary['adj_files'].append({'file': p.name, 'rows': rows})
pd.DataFrame(summary['adj_files']).to_csv(out_dir/'adj_rows.csv', index=False)
(out_dir/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
