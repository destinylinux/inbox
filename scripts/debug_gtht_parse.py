#!/usr/bin/env python3
"""Debug: check raw GTHT table structure for historical date"""
import json, subprocess, sys, os

WORKSPACE = os.path.expanduser('~/.openclaw/workspace')
GTHT_SKILL = os.path.join(WORKSPACE, 'skills/gtht-financialsearch-skill')

date_str = sys.argv[1] if len(sys.argv) > 1 else '2026-01-28'
query = f'{date_str} 涨幅2%到8% 量比大于1.2 换手率2%到16% 资金净流入大于0.5亿 所属行业'

cmd = ['node', 'skill-entry.js', 'mcpClient', 'call', 'financial', 'financial-search', f'query={query}']
r = subprocess.run(cmd, cwd=GTHT_SKILL, capture_output=True, text=True, timeout=30)

text = r.stdout
depth = start = end = 0; d = 0
for i, c in enumerate(text):
    if c == '{':
        if d == 0: start = i
        d += 1
    elif c == '}':
        d -= 1
        if d == 0 and start >= 0:
            outer = json.loads(text[start:i+1])
            body = outer.get('text', '').replace('\\n', '\n').replace('\\"', '"')
            break

lines = body.strip().split('\n')
header_idx = next(i for i, l in enumerate(lines) if l.startswith('| 股票代码'))
headers = [h.strip() for h in lines[header_idx].strip('|').split('|') if h.strip()]

print("Headers:", headers)
print()

# Show first 3 data rows raw
data_lines = [l for l in lines[header_idx+2:] if l.startswith('|') and '---' not in l]
print(f"Total data rows: {len(data_lines)}")
print()

# Show 3 specific stocks that had good 最新涨跌幅
for l in data_lines[:3]:
    parts = [c.strip() for c in l.strip('|').split('|') if c.strip()]
    print(f"Row cols: {len(parts)}")
    for h, p in zip(headers, parts):
        print(f"  {h}: {p[:60]}")
    print()

# Now check: are the [20260128] suffixed columns actually populated?
for l in data_lines:
    parts = [c.strip() for c in l.strip('|').split('|') if c.strip()]
    if len(parts) == len(headers):
        row = dict(zip(headers, parts))
        code = row.get('股票代码','')
        hzdf = row.get(f'涨跌幅[{date_str}]', '')
        hlb = row.get(f'量比[{date_str}]', '')
        hhs = row.get(f'换手率[{date_str}]', '')
        hflow = row.get(f'资金流向[{date_str}]', '')
        # Only show rows where at least one historical field is non-empty
        if hzdf or hlb or hhs or hflow:
            print(f"  {code}: 涨跌幅[{date_str}]={hzdf[:15]} 量比={hlb[:15]} 换手={hhs[:15]} 资金流向={hflow[:15]}")

print(f"\nChecked {len(data_lines)} rows")
