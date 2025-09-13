import pathlib,re

def strip_triple_quotes(p: pathlib.Path):
    if not p.exists():
        print(f"skip: {p}"); return
    b = p.read_bytes()
    try:
        s = b.decode("cp932")
    except Exception:
        try:
            s = b.decode("utf-8")
        except Exception:
            s = b.decode("utf-8","ignore")
    # 連続する """...""" と '''...''' を安全に除去（未終端でも終端まで削除）
    def _strip(text, q):
        out=[]; i=0; n=len(text)
        q3=q*3
        while i<n:
            j=text.find(q3,i)
            if j<0:
                out.append(text[i:]); break
            out.append(text[i:j])
            k=text.find(q3,j+3)
            if k<0:
                # 未終端 → 末尾まで捨てて終了
                return "".join(out)
            i=k+3
        return "".join(out)
    s=_strip(s,'"')
    s=_strip(s,"'")
    # 制御文字除去
    s=re.sub(r'[\x00-\x08\x0b-\x1f]',' ',s)
    p.write_text(s,encoding="utf-8")
    print(f"fixed: {p}")

for rel in [
    "tools/tdnet_kabutan_crawl_range.py",
    "tools/tdnet_kabutan_fetch_html.py",
    "tools/tdnet_kabutan_enrich_day.py",
]:
    strip_triple_quotes(pathlib.Path(rel))
print("done")
