#!/usr/bin/env python3
"""
15:01 第二次开工 + 自动收集（全自动：验证上日+记录今日+更新面板+推送）

被 openclaw cron 调用：
  python3 scripts/cron_kai_gong_collect.py

注意：14:40 的首次开工结果存储在 tmp/kai_gong_pre_*.json 中供对比分歧
"""
import sys, os, json, time, subprocess, base64, re
from datetime import date, datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

# ---------- trading day check ----------
HOLIDAYS_2026 = {
    date(2026,1,1),date(2026,1,2),date(2026,1,3),
    date(2026,2,17),date(2026,2,18),date(2026,2,19),date(2026,2,20),
    date(2026,2,21),date(2026,2,22),date(2026,2,23),
    date(2026,4,4),date(2026,4,5),date(2026,4,6),
    date(2026,5,1),date(2026,5,2),date(2026,5,3),date(2026,5,4),date(2026,5,5),
    date(2026,6,19),date(2026,6,20),date(2026,6,21),
    date(2026,10,1),date(2026,10,2),date(2026,10,3),date(2026,10,4),
    date(2026,10,5),date(2026,10,6),date(2026,10,7),date(2026,10,8),
}
MAKEUP_DAYS_2026 = {date(2026,4,26),date(2026,9,27)}

def is_trading_day(d=None):
    if d is None: d = date.today()
    if d in MAKEUP_DAYS_2026: return True
    if d in HOLIDAYS_2026: return False
    return d.weekday() < 5

# ====== GTHT ranklist ======
def query_gtht():
    skill_dir = BASE / 'skills' / 'gtht-ranklist-skill'
    result = subprocess.run(
        ['node', 'skill-entry.js', 'mcpClient', 'call', 'ranklist', 'ranklist',
         'code=BK101003', 'limit=500', 'offset=0', 'sorted_type=1', 'order_by=2',
         'mask={"M_64_0":35184372088831}'],
        cwd=str(skill_dir), capture_output=True, text=True, timeout=30
    )
    data = json.loads(result.stdout)
    board_items = data['items'][0]['board_items']
    candidates = []
    for bi in board_items:
        code = bi.get('code',''); name = bi.get('name','')
        if any(code.startswith(p) for p in ('SZ300','SZ301','SH688','BJ')): continue
        if '*ST' in name or '退市' in name or name.startswith('N'): continue
        zdf = bi.get('price_change_percent',0)*100
        lb = bi.get('relative_volume_ratio',0)
        hs = bi.get('turnover_ratio',0)*10000
        jlr = bi.get('capital_flow',0); cje = bi.get('total_amount',0)
        if not (2 <= zdf <= 8): continue
        if lb == 0 or lb == '--' or float(lb) < 1.2: continue
        if not (2 <= hs <= 16): continue
        if jlr < 50000000: continue
        if cje > 0 and (jlr/cje*100) < 3: continue
        candidates.append({'code':code,'name':name,'zdf':round(zdf,2),'lb':round(float(lb),2),
            'hs':round(hs,2),'jlr':round(jlr/1e8,2),'jlr_ratio':round(jlr/cje*100,2) if cje>0 else 0})
    if not candidates: return []
    return sorted(candidates, key=lambda c: c['zdf']*0.3 + c['jlr']*0.3 + c['jlr_ratio']*0.2 + min(c['lb'],5)*0.2, reverse=True)

# ====== 问财 ======
def query_wencai():
    token = None
    with open(BASE.parent / '.xiaoyienv') as f:
        for line in f:
            if line.startswith('117862897_login_token='):
                token = line.strip().split('=',1)[1]; break
    script = BASE / 'skills' / 'hithink-iwencai' / 'scripts' / 'astock_selector.py'
    env = os.environ.copy(); env['IWENCAI_API_KEY'] = token
    result = subprocess.run(
        ['python3',str(script),'--query','今日涨幅2%到8% 资金净流入大于5000万 量比大于1.2 换手率2%到16%','--limit','100'],
        capture_output=True, text=True, timeout=30, env=env)
    data = json.loads(result.stdout); datas = data.get('datas',[])
    candidates = []
    for item in datas:
        code = item.get('股票代码',''); name = item.get('股票简称','')
        if code.startswith('300') or code.startswith('301') or code.startswith('688'): continue
        if '*ST' in name or name.startswith('ST'): continue
        if code.startswith('8'): continue
        zdf = float(item.get('最新涨跌幅',0)); lb = float(item.get('量比',0))
        hs = float(item.get('换手率[20260626]',0))
        jlr = float(item.get('资金流向[20260626]',0))
        cje = float(item.get('成交额[20260626]',0))
        if not (2 <= zdf <= 8): continue
        if lb < 1.2: continue; 
        if not (2 <= hs <= 16): continue
        if jlr < 50000000: continue
        if cje > 0 and (jlr/cje*100) < 3: continue
        candidates.append({'code':code,'name':name,'zdf':round(zdf,2),'lb':round(lb,2),
            'hs':round(hs,2),'jlr':round(jlr/1e8,2),'jlr_ratio':round(jlr/cje*100,2) if cje>0 else 0})
    if not candidates: return []
    return sorted(candidates, key=lambda c: c['zdf']*0.3 + c['jlr']*0.3 + c['jlr_ratio']*0.2 + min(c['lb'],5)*0.2, reverse=True)

# ====== Sina close data ======
def fetch_sina(code):
    """Fetch stock close data from Sina. Returns {open,high,close,low} or None"""
    prefix = 'sz' if code.startswith('00') or code.startswith('30') else 'sh'
    url = f'https://hq.sinajs.cn/list={prefix}{code}'
    try:
        req = urllib.request.Request(url, headers={'Referer':'https://finance.sina.com.cn'})
        resp = urllib.request.urlopen(req, timeout=10)
        raw = resp.read().decode('gbk')
        match = re.search(r'"[^"]+"', raw)
        if not match: return None
        parts = match.group().strip('"').split(',')
        # name=parts[0], open=parts[1], pre_close=parts[2], close=parts[3],
        # high=parts[4], low=parts[5]
        pre_close = float(parts[2])
        return {
            'open': (float(parts[1]) - pre_close) / pre_close * 100,
            'close': (float(parts[3]) - pre_close) / pre_close * 100,
            'high': (float(parts[4]) - pre_close) / pre_close * 100,
            'low': (float(parts[5]) - pre_close) / pre_close * 100,
        }
    except: return None

# ====== API push to GitHub ======
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
REPO = 'destinylinux/inbox'
BRANCH = 'master'

def push_to_github(panel_path):
    with open(panel_path) as f: content = f.read()
    b64 = base64.b64encode(content.encode()).decode()
    import urllib.request
    # Get SHA
    req = urllib.request.Request(f'https://api.github.com/repos/{REPO}/contents/index.html',
        headers={'Authorization': f'token {GITHUB_TOKEN}','User-Agent':'python'})
    resp = urllib.request.urlopen(req)
    sha = json.loads(resp.read()).get('sha')
    # Upload
    payload = json.dumps({'message':f'auto collect {date.today().isoformat()}','content':b64,'sha':sha,'branch':BRANCH}).encode()
    req2 = urllib.request.Request(f'https://api.github.com/repos/{REPO}/contents/index.html',
        data=payload, headers={'Authorization':f'token {GITHUB_TOKEN}','Content-Type':'application/json','User-Agent':'python'},
        method='PUT')
    resp2 = urllib.request.urlopen(req2)
    result = json.loads(resp2.read())
    return result.get('content',{}).get('size',0)

# ====== Main ======
def main():
    if not is_trading_day():
        print("非交易日，跳过"); sys.exit(0)
    
    today_str = date.today().isoformat()
    wd = '一二三四五六日'[date.today().weekday()]
    final = BASE / 'v7_web' / 'final_version'
    panel = BASE / 'index_个人专属.html'
    panel_copy = BASE / 'index.html'
    report_lines = []
    
    def log(s):
        print(s); report_lines.append(s)
    
    log(f"🕐 {today_str} 15:01 自动开工+收集...")
    
    # ===== ① 读14:40预存数据做分歧对比 =====
    pre_data = None
    pre_files = sorted(Path(BASE/'tmp').glob('kai_gong_pre_*.json'))
    if pre_files:
        with open(pre_files[-1]) as f:
            pre_data = json.load(f)
    
    # ===== ② 开工：拉收盘数据 =====
    gtht_cands = query_gtht()
    wencai_cands = query_wencai()
    gtht_top = gtht_cands[0] if gtht_cands else None
    wencai_top = wencai_cands[0] if wencai_cands else None
    
    log(f"GTHT首推: {gtht_top['name']}({gtht_top['code']}) +{gtht_top['zdf']}% 量比{gtht_top['lb']} 净流入{gtht_top['jlr']}亿" if gtht_top else "GTHT: 无候选")
    log(f"问财首推: {wencai_top['name']}({wencai_top['code']}) +{wencai_top['zdf']}% 量比{wencai_top['lb']} 净流入{wencai_top['jlr']}亿" if wencai_top else "问财: 无候选")
    
    # ===== ③ 分歧对比 =====
    divergence = None
    if pre_data:
        pre_g = pre_data.get('gtht_top'); pre_w = pre_data.get('wencai_top')
        g_diff = pre_g and gtht_top and pre_g['code'] != gtht_top['code']
        w_diff = pre_w and wencai_top and pre_w['code'] != wencai_top['code']
        if g_diff or w_diff:
            divergence = {
                'date': today_str, 'reason': '盘中(14:40) vs 收盘(15:01) 首推变化',
                'GTHT': {'1440_top': pre_g, '1501_top': gtht_top, 'changed': g_diff},
                '问财': {'1440_top': pre_w, '1501_top': wencai_top, 'changed': w_diff}
            }
            log("⚠️ 存在分歧！14:40与15:01首推不一致")
            if g_diff: log(f"  GTHT: 14:40→{pre_g['name']} | 15:01→{gtht_top['name']}")
            if w_diff: log(f"  问财: 14:40→{pre_w['name']} | 15:01→{wencai_top['name']}")
    
    # 默认使用15:01收盘数据，除非没有（兜底用14:40）
    if not gtht_top and pre_data and pre_data.get('gtht_top'):
        log("GTHT收盘无候选，回退使用14:40结果")
        gtht_top = pre_data['gtht_top']
    if not wencai_top and pre_data and pre_data.get('wencai_top'):
        log("问财收盘无候选，回退使用14:40结果")
        wencai_top = pre_data['wencai_top']
    
    # ===== ④ 验证上日首推 =====
    def verify_prev_day(json_path, pipeline_name):
        with open(json_path) as f:
            data = json.load(f)
        rows = data['v7_rows']
        # Find the last 待验证 row before today
        prev = None
        for r in reversed(rows):
            if r['judge'] == '待验证' and r.get('next_close') is None:
                prev = r; break
        if not prev: return data, False
        
        info = fetch_sina(prev['code'][:6] if prev['code'].endswith('.SZ') or prev['code'].endswith('.SH') else prev['code'])
        if not info:
            log(f"⚠️ {pipeline_name}: 无法获取{prev['name']}的收盘数据")
            return data, False
        
        prev['judge'] = '✅达标' if info['close'] >= 2 or info['high'] >= 2 else ('🟡盘中达标' if info['high'] >= 2 else '❌失败')
        prev['next_open'] = round(info['open'], 2)
        prev['next_high'] = round(info['high'], 2)
        prev['next_close'] = round(info['close'], 2)
        prev['day_pnl'] = round(info['close'], 2)
        
        # Update running_cum
        # Find previous verified row's cum
        prev_cum = 0
        for r in rows:
            if r.get('running_cum') is not None and r['judge'] not in ('待验证',) and r.get('day_pnl') is not None:
                prev_cum = r['running_cum']
        prev['running_cum'] = round(prev_cum + info['close'], 2)
        
        # Judge
        if prev['judge'] == '✅达标':
            j = '✅'
            log(f"✅ {pipeline_name} {prev['name']}: 收{info['close']:.2f}% ✅达标")
        elif prev['judge'] == '🟡盘中达标':
            j = '🟡盘中'
            log(f"{pipeline_name} {prev['name']}: 收{info['close']:.2f}%(最高{info['high']:.2f}%) 🟡盘中达标")
        else:
            j = '❌'
            log(f"❌ {pipeline_name} {prev['name']}: 收{info['close']:.2f}% (最高{info['high']:.2f}%) ❌失败")
        
        # Also check for divergence in meta
        meta = data.get('meta', {})
        div_key = f'divergence_{date.today().isoformat()}'
        # Wait, no - divergence is for the day the divergence was identified
        # Actually, we need to check if the PREVIOUS day had divergence
        # prev['date'] is the screening date
        # We need to find the last market day - find its divergence
        prev_date_str = prev['date']
        # Extract the day number for divergence_YYYYMMDD key
        div_key_to_check = f'divergence_{prev_date_str.replace("-","")}'
        prev_div = meta.get(div_key_to_check) or meta.get(f'divergence_detail_{prev_date_str.replace("-","")}')
        
        if prev_div:
            log(f"  ⚠️ 前一日存在分歧，已记录")
        
        with open(json_path, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Update stats
        verified = [r for r in data['v7_rows'] if r['judge'] not in ('待验证',)]
        wins = sum(1 for r in verified if r['judge'] in ('✅达标','🟡盘中达标'))
        last_v = verified[-1] if verified else None
        data['stats']['wins'] = wins
        data['stats']['verified'] = len(verified)
        data['stats']['pd'] = sum(1 for r in data['v7_rows'] if r['judge'] == '待验证')
        data['stats']['rate'] = round(wins/len(verified)*100) if verified else 0
        if last_v:
            data['stats']['v7_cum'] = last_v.get('running_cum', data['stats'].get('v7_cum', 0))
        
        with open(json_path, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return data, True
    
    # Verify GTHT prev day
    verify_prev_day(final / 'v7_data_latest.json', 'GTHT')
    # Verify 问财 prev day
    verify_prev_day(final / 'v7_wencai_latest.json', '问财')
    
    # ===== ⑤ 分歧票验证（如有） =====
    def verify_divergence(json_path, pipeline_name):
        with open(json_path) as f:
            data = json.load(f)
        meta = data.get('meta', {})
        # Find the divergence for the relevant day
        yesterday = date.today()
        # Go back to find the last trading day
        for offset in [1, 2, 3, 4]:
            d = date.today()
            from datetime import timedelta
            d = d - timedelta(days=offset)
            if is_trading_day(d):
                yesterday = d; break
        
        div_key = f'divergence_detail_{yesterday.isoformat().replace("-","")}'
        div_data = meta.get(div_key)
        if not div_data:
            return data, False
        
        log(f"\n📋 验证分歧票({yesterday})：")
        changed = False
        for source, info in div_data.items():
            if source == 'date' or source == 'summary':
                continue
            code = info.get('code', '')
            name = info.get('name', '')
            if info.get('judge') and info.get('judge') != '待验证':
                continue  # already verified
            if not code:
                continue
            
            sina = fetch_sina(code[:6])
            if not sina:
                log(f"  ⚠️ 分歧票{name}({code})无法获取数据")
                continue
            judge = '✅达标' if sina['close'] >= 2 or sina['high'] >= 2 else ('🟡盘中达标' if sina['high'] >= 2 else '❌失败')
            info['judge'] = judge
            info['next_open'] = round(sina['open'], 2)
            info['next_high'] = round(sina['high'], 2)
            info['next_close'] = round(sina['close'], 2)
            mark = '✅' if '达标' in judge else ('🟡' if '盘中' in judge else '❌')
            log(f"  {source} {name}({code}): 收{sina['close']:.2f}% {mark}")
            changed = True
        
        if changed:
            meta[div_key] = div_data
            data['meta'] = meta
            with open(json_path, 'w') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        return data, changed
    
    verify_divergence(final / 'v7_data_latest.json', 'GTHT')
    verify_divergence(final / 'v7_wencai_latest.json', '问财')
    
    # ===== ⑥ 记录今日首推 =====
    def record_today(json_path, pipeline_name, top_pick):
        if not top_pick:
            log(f"⚠️ {pipeline_name}: 无首推，跳过记录")
            return
        with open(json_path) as f:
            data = json.load(f)
        rows = data['v7_rows']
        # Compute running_cum from last row
        last_cum = rows[-1].get('running_cum', 0) if rows else 0
        
        new_row = {
            'date': today_str, 'weekday': wd, 'status': 'OK',
            'code': f"{top_pick['code']}" if '.' in top_pick['code'] else top_pick['code'],
            'name': top_pick['name'],
            'sector': '?',  # would need industry query
            'zdf': top_pick['zdf'], 'lb': top_pick['lb'], 'hs': top_pick['hs'],
            'flow': top_pick['jlr'], 'ratio': top_pick['jlr_ratio'],
            'score': int(top_pick['zdf']*0.3 + top_pick['jlr']*0.3 + top_pick['jlr_ratio']*0.2 + min(top_pick['lb'],5)*0.2),
            'judge': '待验证',
            'next_open': None, 'next_high': None, 'next_close': None,
            'day_pnl': 0, 'running_cum': round(last_cum, 2)
        }
        rows.append(new_row)
        with open(json_path, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log(f"📝 {pipeline_name}: 记录首推{top_pick['name']}")
    
    record_today(final / 'v7_data_latest.json', 'GTHT', gtht_top)
    record_today(final / 'v7_wencai_latest.json', '问财', wencai_top)
    
    # ===== ⑦ 分歧写入meta =====
    if divergence:
        div_key = f'divergence_detail_{today_str.replace("-","")}'
        for json_path in [final / 'v7_data_latest.json', final / 'v7_wencai_latest.json']:
            with open(json_path) as f:
                data = json.load(f)
            if 'meta' not in data: data['meta'] = {}
            data['meta'][f'divergence_{today_str.replace("-","")}'] = f"{today_str} 盘中vs盘后分歧：{'GTHT变化' if divergence['GTHT']['changed'] else ''}{' / ' if divergence['GTHT']['changed'] and divergence['问财']['changed'] else ''}{'问财变化' if divergence['问财']['changed'] else ''}"
            data['meta'][div_key] = divergence
            with open(json_path, 'w') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        log(f"📋 分歧信息已写入meta")
    
    # ===== ⑧ 重建面板 + 推送 =====
    from scripts.rebuild_panel import rebuild_panel, gen_gtht_wencai_body, gen_compare_body, gen_fenqi_body
    with open(final / 'v7_data_latest.json') as f:
        gtht_data = json.load(f)
    with open(final / 'v7_wencai_latest.json') as f:
        wencai_data = json.load(f)
    
    gtht_body = gen_gtht_wencai_body(gtht_data, 'V7 选股日报(GTHT)')
    wencai_body = gen_gtht_wencai_body(wencai_data, 'V7 选股日报(问财)')
    compare_body = gen_compare_body(gtht_data, wencai_data)
    fenqi_body = gen_fenqi_body(gtht_data, wencai_data)
    rebuild_panel(str(panel), gtht_body, wencai_body, compare_body, fenqi_body)
    
    panel_size = panel.stat().st_size
    import shutil; shutil.copy2(panel, panel_copy)
    
    # Push
    size = push_to_github(str(panel))
    log(f"📤 面板已推送: {size} bytes")
    
    # ===== 写memory =====
    mem_file = BASE / 'memory' / f'{today_str}.md'
    with open(mem_file, 'a') as f:
        f.write(f"\n### {today_str} 自动收集(15:01 cron)\n")
        if gtht_top: f.write(f"- GTHT首推: {gtht_top['name']}(+{gtht_top['zdf']}%)\n")
        else: f.write("- GTHT: 无候选\n")
        if wencai_top: f.write(f"- 问财首推: {wencai_top['name']}(+{wencai_top['zdf']}%)\n")
        else: f.write("- 问财: 无候选\n")
        if divergence: f.write(f"- ⚠️ 存在分歧\n")
        f.write(f"- 面板已更新({panel_size} bytes)\n")
    
    log(f"\n✅ {today_str} 开工+收集 全部完成！")
    return '\n'.join(report_lines)

if __name__ == '__main__':
    import urllib.request  # needed for fetch_sina
    result = main()
    print("\n=== 报告 ===")
    print(result)
