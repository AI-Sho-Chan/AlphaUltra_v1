import os, re, json
from pathlib import Path
import pandas as pd

SRC=Path('tmp/kabutan_exports')
DST=Path('data/raw/tdnet')
DST.mkdir(parents=True, exist_ok=True)

def norm_cols(df):
    m = {c.lower().strip(): c for c in df.columns}
    def pick(keys):
        for k in keys:
            if k in m: return m[k]
        return None
    return {
        'code': pick(['コード','code','銘柄コード']),
        'published_at': pick(['掲載日時','published_at','date','日時']),
        'title': pick(['タイトル','title']),
        'body': pick(['本文','body','テキスト','内容']),
        'url_pdf': pick(['pdf','pdf_url','url_pdf']),
        'url_detail': pick(['url','url_detail','詳細','link'])
    }

def guess_event(title):
    t = str(title)
    t2 = t.lower()
    k = [
        ('buyback', r'自社株買|自己株式取得|share repurchase'),
        ('offering', r'公募|増資|第三者割当|cb|convertible|希薄'),
        ('guidance_up', r'上方修正|上方|上方見通し'),
        ('guidance_down', r'下方修正|下方|下方見通し'),
        ('div_up', r'増配'),
        ('div_down', r'減配'),
        ('ma', r'm&a|買収|売却|子会社|吸収合併|会社分割|スピンオフ'),
        ('product', r'承認|許可|販売開始|発売|臨床|clinical|approval'),
        ('personnel', r'社長|ceo|cfo|役員人事|取締役'),
        ('lawsuit', r'訴訟|係争|調査|investigation'),
        ('capex', r'設備投資|建設計画|増設'),
        ('order', r'大型受注|受注|契約|コンソーシアム')
    ]
    for name,pat in k:
        if re.search(pat, t) or re.search(pat, t2): return name
    return 'other'

rows=0
for p in list(SRC.glob('*.csv'))+list(SRC.glob('*.CSV')):
    try:
        try:
            df = pd.read_csv(p, encoding='utf-8-sig')
        except UnicodeDecodeError:
            df = pd.read_csv(p, encoding='cp932')
        cols = norm_cols(df)
        if not cols['code'] or not cols['published_at'] or not cols['title']:
            print(f'skip {p} (missing required cols)'); continue
        df['_code'] = df[cols['code']].astype(str).str.extract(r'(\d{4})')[0]
        df = df[df['_code'].notna()]
        df['_ticker'] = df['_code'] + '.T'
        ts = pd.to_datetime(df[cols['published_at']], errors='coerce')
        df = df.assign(_dt=ts)
        df = df[df['_dt'].notna()]
        for _,r in df.iterrows():
            d = r['_dt'].strftime('%Y-%m-%d')
            y,m,dd = d.split('-')
            out_dir = DST/ y / m / dd
            out_dir.mkdir(parents=True, exist_ok=True)
            rec = {
                'ticker': r['_ticker'],
                'code4': r['_code'],
                'title': str(r[cols['title']]),
                'published_at_jst': r['_dt'].strftime('%Y-%m-%d %H:%M:%S'),
                'url_pdf': None if not cols['url_pdf'] else (None if pd.isna(r[cols['url_pdf']]) else str(r[cols['url_pdf']])),
                'url_detail': None if not cols['url_detail'] else (None if pd.isna(r[cols['url_detail']]) else str(r[cols['url_detail']])),
                'body': None if not cols['body'] else (None if pd.isna(r[cols['body']]) else str(r[cols['body']])),
                'event_type': guess_event(r[cols['title']]),
                'source': 'kabutan'
            }
            # 1イベント=1ファイル（重複回避のためハッシュ代替）
            fname = f"{r['_ticker']}_{r['_dt'].strftime('%H%M%S')}_{abs(hash(rec['title']))%1000000}.json"
            with open(out_dir/fname, 'w', encoding='utf-8') as f:
                json.dump(rec, f, ensure_ascii=False)
            rows += 1
        print(f'loaded {p} -> {out_dir} (+{len(df)})')
    except Exception as e:
        print(f'error {p}: {e}')

print({'files': rows})
