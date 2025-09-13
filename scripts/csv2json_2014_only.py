#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2014年の Kabutan CSV を対象に、日別 JSON を再生成する専用スクリプト。

入力: data/raw/kabutan/2014-**/**/tdnet.csv
出力: data/raw/tdnet/2014/MM/DD/*.json

注意: re.Match と Path の結合不具合を回避（正規表現は str に適用し、
      m.groups() で (y, m_, d) を得て文字列でパス構築）。
"""

from pathlib import Path
import json
import re
import sys
import pandas as pd


ROOT = Path('.').resolve()
CSV_ROOT = ROOT / 'data/raw/kabutan'
OUT_ROOT = ROOT / 'data/raw/tdnet'


def to_jst_iso(date_str: str, hm: str) -> str:
    hm = (hm or '').strip()
    if not re.match(r'^\d{1,2}:\d{2}$', hm):
        hm = '00:00'
    return f"{date_str}T{hm}:00+09:00"


def extract_code4(val: str) -> str | None:
    # NFKC normalize then extract first 4-digit run anywhere
    try:
        import unicodedata as ud
        s = ud.normalize('NFKC', str(val) or '').strip()
    except Exception:
        s = (str(val) or '').strip()
    # Accept patterns like "7203", "7203 トヨタ", "7203-トヨタ"
    m = re.search(r'(\d{4})', s)
    if not m:
        return None
    return m.group(1)


def process_csv(csv_path: Path) -> int:
    s = str(csv_path)
    m = re.search(r'(20\d{2})-(\d{2})-(\d{2})', s)
    if not m:
        return 0
    y, m_, d = m.groups()
    if y != '2014':
        return 0

    try:
        try:
            df = pd.read_csv(csv_path, dtype=str, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(csv_path, dtype=str, encoding='utf-8-sig')
    except Exception:
        return 0

    col_code = None
    for c in df.columns:
        x = (str(c) or '').strip()
        if x in ('コード', 'code', 'ｺｰﾄﾞ', 'Code', 'コード・銘柄名', 'コード '):
            col_code = c
            break
    # ヒューリスティック: 4桁に合致率が高い列をコード列とみなす
    if not col_code:
        best = None; best_rate = 0.0
        for c in df.columns:
            s = df[c].astype(str).str.strip()
            m = s.str.match(r'^\d{4}$', na=False)
            rate = m.mean() if len(s) else 0.0
            if rate > best_rate:
                best, best_rate = c, rate
        if best_rate >= 0.2:  # 2割以上が4桁
            col_code = best
    col_title = None
    for c in df.columns:
        x = c.strip()
        if x in ('タイトル', 'title'):
            col_title = c
            break
    col_time = None
    for c in df.columns:
        x = c.strip()
        if x in ('掲載時刻', '時刻', 'time'):
            col_time = c
            break
    col_url = None
    for c in df.columns:
        x = c.strip()
        if x in ('URL', 'url'):
            col_url = c
            break

    if not col_code:
        return 0

    out_dir = OUT_ROOT / y / m_ / d
    out_dir.mkdir(parents=True, exist_ok=True)

    ymd = f"{y}-{m_}-{d}"
    n = 0
    for i, row in df.iterrows():
        code4 = extract_code4(row.get(col_code, ''))
        if not code4:
            continue
        try:
            if int(code4) < 1300:
                continue
        except Exception:
            continue
        title = str(row.get(col_title, '')).strip() if col_title else ''
        hm    = str(row.get(col_time,  '')).strip() if col_time  else ''
        url   = str(row.get(col_url,   '')).strip() if col_url   else ''

        data = {
            'ticker': f'{code4}.T',
            'code4': code4,
            'title': title,
            'published_at_jst': to_jst_iso(ymd, hm),
            'date': ymd,
            'event_type': 'other',
            'url_detail': url,
            'url_pdf': ''
        }
        out = out_dir / f"{code4}_{i:03d}.json"
        out.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        n += 1
    return n


def main():
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    total = 0
    # 2014年の CSV のみ対象
    for csv_path in sorted(CSV_ROOT.glob('2014-*/tdnet.csv')):
        try:
            total += process_csv(csv_path)
        except Exception as e:
            sys.stderr.write(f"[csv2json_2014] error {csv_path}: {e}\n")
            continue
    print({'year': 2014, 'wrote_events': int(total)})


if __name__ == '__main__':
    main()
