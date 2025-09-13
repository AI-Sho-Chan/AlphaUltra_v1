import json, os, pathlib as P
rec={
 "ticker":"7203.T","code4":"7203",
 "title":"決算短信を公表","published_at_jst":"2025-07-01 15:00:00",
 "date":"2025-07-01","event_type":"earnings","source":"kabutan"
}
out=P.Path("data/raw/tdnet/2025/07/01/7203.T_0001.json")
out.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
print(str(out))
