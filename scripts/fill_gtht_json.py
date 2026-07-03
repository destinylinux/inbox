#!/usr/bin/env python3
"""
GTHT历史数据补齐脚本（2026-06-22 重写版）
- 逐日补齐 v7_data_latest.json 中 "待补齐" 行
- 每次查询GTHT获取该日候选（带行业信息）
- 在同一次查询结果中完成：V7基础筛选 → 高危排除 → 板块≥2判断 → 评分排序 → 选首推
- 腾讯K线查次日验证（不消耗GTHT配额）
- GTHT配额用尽即停，次日凌晨从断点续跑
"""
import json, os, sys, subprocess, time, re, math, urllib.request
from datetime import datetime, timedelta
from collections import Counter

WORKSPACE = os.path.expanduser('/home/sandbox/.openclaw/workspace')
SKILL_DIR = os.path.join(WORKSPACE, 'skills', 'gtht-smartstockselection-skill')
JSON_FILE = os.path.join(WORKSPACE, 'v7_web', 'final_version', 'v7_data_latest.json')

# V7 风控层参数
HIGH_RISK = {'房地产','国防军工','食品饮料','非银金融','机械设备','传媒'}
MAX_QUERIES_PER_RUN = 12  # GTHT日配额保守数
QUERY_DELAY = 3  # 每次查询间隔秒数


def gtht_query(query, retries=2):
    """调用GTHT smartstockselection进行自然语言查询"""
    cmd = ['node', 'skill-entry.js', 'mcpClient', 'call', 'financial', 'financial-search', f'query={query}']
    for attempt in range(retries + 1):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=SKILL_DIR)
            if r.returncode != 0:
                if attempt < retries: time.sleep(3); continue
                return None
            raw = r.stdout.strip()
            if not raw: return None
            obj = json.loads(raw)
            result_str = obj.get('text', '')
            if not result_str: return None
            lines = result_str.split('\n')
            header_line = None; data_lines = []; found_sep = False
            for line in lines:
                s = line.strip()
                if s.startswith('|') and s.endswith('|'):
                    if '股票代码' in s: header_line = s
                    elif '---' in s: found_sep = True
                    elif found_sep and header_line: data_lines.append(s)
            if not header_line or not data_lines: return []
            headers = [h.strip() for h in header_line.strip('|').split('|')]
            rows = []
            for dl in data_lines:
                cells = [c.strip() for c in dl.strip('|').split('|')]
                if len(cells) == len(headers): rows.append(dict(zip(headers, cells)))
                elif len(cells) > len(headers): rows.append(dict(zip(headers, cells[:len(headers)])))
            return rows
        except Exception as e:
            if attempt < retries: time.sleep(3); continue
            return None
    return None


def parse_float(v, default=None):
    """安全转float"""
    if v is None: return default
    try: return float(v)
    except: return default


def extract_row(row, prefix):
    """
    从GTHT返回的一行中提取字段。
    同花顺行业格式: "['通信', '通信设备', '通信网络设备及器件']" → 取一级"通信"
    """
    out = {'code': '', 'name': '', 'zdf': None, 'lb': None, 'hs': None, 'flow': None, 'amount': None, 'sector': ''}
    try:
        out['code'] = row.get('股票代码', '') or row.get('code', '')
        out['name'] = row.get('股票简称', '') or row.get('name', '')
        
        # 行业：所属同花顺行业是列表字符串，如 "['通信', '通信设备', '通信网络设备及器件']"
        hy = row.get('所属同花顺行业', '')
        if hy:
            # 解析 ['一级', '二级', '三级'] → 取一级
            m = re.search(r"'([^']+)'", str(hy))
            if m:
                out['sector'] = m.group(1)
        if not out['sector']:
            hy2 = row.get('所属行业', '')
            if hy2:
                sec = str(hy2).strip('[]').replace("'","").split(',')[0].strip()
                if '-' in sec: sec = sec.split('-')[0].strip()
                out['sector'] = sec
        
        # 找字段：优先匹配带日期前缀的，如 涨跌幅[20260422]
        ns = f'[{prefix}]'
        for k, v in row.items():
            if not v: continue
            if k.endswith(ns):
                if '涨跌幅' in k and '前复权' not in k: out['zdf'] = parse_float(v)
                elif '量比' in k: out['lb'] = parse_float(v)
                elif '换手率' in k: out['hs'] = parse_float(v)
                elif '主力资金流向' in k: out['flow'] = parse_float(v)
                elif '成交额' in k: out['amount'] = parse_float(v)
        
        # 如果带前缀没找到，退而求最新涨跌幅
        if out['zdf'] is None:
            lv = row.get('最新涨跌幅')
            if lv is not None: out['zdf'] = parse_float(lv)
        
        # 主力增仓占比
        zz = row.get(f'主力增仓占比{ns}', '')
        if not zz: zz = row.get('主力增仓占比', '')
        out['zzzb'] = parse_float(zz)
        
        # 排除ST
        name = out['name']
        if name and ('ST' in name or '*' in name): return None
        
        return out
    except:
        return None


def v7_flow_ratio(flow_yi, amount_yi):
    """净流入占比（%）"""
    if amount_yi and amount_yi > 0:
        return flow_yi / amount_yi * 100
    return 0


def v7_score(zdf, lb, hs, flow_yi, ratio):
    """
    V7正式评分规则（0-75分）
    参考: v7_model/README.md
    板块≥2已是硬条件，评分不重复加分
    """
    score = 40  # 基础分
    
    # 1. 净流入占比（>12% +25, >8% +20, >5% +18, >3% +10）
    if ratio > 12: score += 25
    elif ratio > 8: score += 20
    elif ratio > 5: score += 18
    elif ratio > 3: score += 10
    
    # 2. 净流入规模（>1.5亿 +8, >1亿 +5, >0.5亿 +3）
    if flow_yi > 1.5: score += 8
    elif flow_yi > 1: score += 5
    elif flow_yi > 0.5: score += 3
    
    # 3. 涨幅区间（2.5-5% +8, ≤6.5% +5）
    if 2.5 <= zdf <= 5: score += 8
    elif zdf <= 6.5: score += 5
    
    # 4. 资金效率 = 净流入占比 / 换手（>0.5 +8, >0.2 +5）
    if hs > 0:
        eff = ratio / hs if hs > 0 else 0
        if eff > 0.5: score += 8
        elif eff > 0.2: score += 5
    
    # 5. 量比（1.5-4 +5）
    if 1.5 <= lb <= 4: score += 5
    
    # 降分：高量比高换手 -5
    if lb > 3 and hs > 12: score -= 5
    # 降分：低换手高占比 -8（换手<5但占比>20%→脉冲）
    if hs < 5 and ratio > 20: score -= 8
    
    return max(0, min(75, score))


def sector_meets_criteria(candidates_dict):
    """
    板块≥2判断 + 热度警戒（≥10只排除整个板块）
    返回通过板块过滤的候选列表
    """
    # 先统计板块分布
    sector_count = Counter()
    for code, c in candidates_dict.items():
        sec = c.get('sector', '')
        if sec: sector_count[sec] += 1
    
    # 排除高危板块+板块<2+板块热度≥10
    valid = []
    excluded_reasons = []
    for code, c in candidates_dict.items():
        sec = c.get('sector', '')
        cnt = sector_count.get(sec, 0)
        
        if not sec:
            excluded_reasons.append(f"  ❌ {c['name']}({code}) — 无行业信息")
            continue
        if sec in HIGH_RISK:
            excluded_reasons.append(f"  ❌ {c['name']}({code}) {sec} — 高危板块")
            continue
        if cnt < 2:
            excluded_reasons.append(f"  ❌ {c['name']}({code}) {sec} — 板块仅{cnt}只(<2)")
            continue
        if cnt >= 10:
            excluded_reasons.append(f"  ❌ {c['name']}({code}) {sec} — 板块热度{cnt}只(≥10警戒)")
            continue
        valid.append(c)
    
    return valid, excluded_reasons


def process_date(date_str):
    """
    对某一天做完整V7筛选。
    一次GTHT查询拿到全量候选（含行业），同步完成所有筛选。
    返回: (top_candidate, next_day_data, success_flag)
    """
    prefix = date_str.replace('-', '')
    query = f'{date_str} 涨幅大于2%小于8% 量比大于1.2 换手率大于2%小于16% 主力资金净流入大于5000万 非科创板 非创业板 所属行业'
    
    rows = gtht_query(query)
    if not rows:
        return None, None, 0  # 失败（可能是限流/超时）
    if rows == []:
        return None, None, 1  # 查询成功但无结果→无候选
    
    # 解析所有行
    candidates_dict = {}
    for row in rows:
        s = extract_row(row, prefix)
        if not s: continue
        
        zdf = s['zdf']
        lb = s['lb']
        hs = s['hs']
        flow = s['flow']
        amount = s['amount']
        
        # V7基础层筛选
        if zdf is None or zdf < 2 or zdf > 8: continue
        if lb is None or lb < 1.2: continue
        if hs is None or hs < 2 or hs > 16: continue
        if flow is None or flow < 5e7: continue
        
        flow_yi = flow / 1e8
        amount_yi = (amount / 1e8) if amount else 0
        ratio = v7_flow_ratio(flow_yi, amount_yi)
        
        if ratio < 3: continue
        
        s['flow_yi'] = flow_yi
        s['ratio'] = ratio
        
        # V7风控层⑤ 量比确认（2026-06-13新增）
        # lb<1.5→硬否决（白名单豁免：净流入>5亿且市值>500亿）
        # 1.5≤lb<2.0→条件通过（流入占比>10%或涨幅<4%或净流入>3亿）
        # lb≥2.0→直接通过
        if lb is not None and lb < 1.5:
            # 白名单豁免：净流入>5亿且金额推算市值>500亿（成交额/换手率≈市值）
            flow_yi_local = flow / 1e8
            mkt_cap_yi = (amount / hs * 100) if (amount and hs and hs > 0) else 0
            if flow_yi_local > 5 and mkt_cap_yi > 500:
                pass  # 白名单豁免
            else:
                continue  # lb<1.5 硬否决
        elif lb is not None and lb < 2.0:
            # 条件通过：需满足任一
            ratio_local = v7_flow_ratio(flow / 1e8, (amount / 1e8) if amount else 0)
            if not (ratio_local > 10 or zdf < 4 or (flow / 1e8) > 3):
                continue  # 不满足条件→排除
        # lb≥2.0 直接通过
        
        # V7风控层② 低量比+高涨幅：lb<1.5且zdf>6%→排除（层⑤已处理，此处保留作为冗余）
        # V7风控层③ 高涨幅+低量确认：zdf>7%且lb<1.3→排除
        if zdf > 7 and (lb is not None and lb < 1.3): continue
        # V7风控层④ 极端换手：hs>13%→排除
        if hs > 13: continue
        
        candidates_dict[s['code']] = s
    
    if not candidates_dict:
        return None, None, 1  # 有数据但全被筛掉→算无候选
    
    # 板块过滤（一步到位：高危排除+板块≥2+热度警戒）
    valid_candidates, reasons = sector_meets_criteria(candidates_dict)
    if not valid_candidates:
        return None, None, 1  # 板块过滤后无候选
    
    # 评分
    for c in valid_candidates:
        c['score'] = v7_score(c['zdf'], c['lb'], c['hs'], c['flow_yi'], c['ratio'])
    
    # 排序取首推
    valid_candidates.sort(key=lambda x: x['score'], reverse=True)
    top = valid_candidates[0]
    
    # 腾讯K线查次日验证
    next_day = tencent_kline(top['code'], date_str)
    
    return top, next_day, 1


def tencent_kline(code, date_str):
    """
    腾讯K线API查T+1日验证数据（前复权）。
    不消耗GTHT配额。
    返回: {'next_open':%, 'next_high':%, 'next_close':%, 'next_date':str} 或 None
    """
    d = datetime.strptime(date_str, '%Y-%m-%d')
    nd = d + timedelta(days=1)
    # 跳周末
    for _ in range(5):
        if nd.weekday() < 5: break
        nd += timedelta(days=1)
    t1_date = nd.strftime('%Y-%m-%d')
    
    prefix = 'sh' if code.startswith('6') else 'sz'
    raw_code = code.split('.')[0]
    url = f'http://ifzq.gtimg.cn/appstock/app/fqkline/get?param={prefix}{raw_code},day,,,365,qfq'
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode('utf-8'))
        
        d = data.get('data', {}).get(prefix + raw_code, {})
        klines = d.get('qfqday', []) or d.get('day', []) or []
        if not klines:
            for k in d:
                if isinstance(d[k], list):
                    klines = d[k]
                    break
        
        # 找T日收盘价（作为次日涨跌幅基准）
        t_close = None
        for k in klines:
            if len(k) >= 6 and k[0] == date_str:
                t_close = float(k[2])
                break
        
        # 找T+1日数据
        for k in klines:
            if len(k) >= 6 and k[0] == t1_date:
                open_p = float(k[1]); close_p = float(k[2]); high_p = float(k[3])
                if t_close and t_close > 0:
                    n_open = round((open_p - t_close) / t_close * 100, 2)
                    n_high = round((high_p - t_close) / t_close * 100, 2)
                    n_close = round((close_p - t_close) / t_close * 100, 2)
                    return {'next_open': n_open, 'next_high': n_high, 'next_close': n_close, 'next_date': t1_date}
        
        # T+1可能还没到（比如刚收盘），跳过验证
        return None
    except:
        return None


def get_weekday(ds):
    w = datetime.strptime(ds, '%Y-%m-%d').weekday()
    return ['一','二','三','四','五','六','日'][w]


def main():
    with open(JSON_FILE) as f:
        data = json.load(f)
    rows = data['v7_rows']
    
    # 找所有"待补齐"行（且日期≥4/22）
    need = [(i, r) for i, r in enumerate(rows)
            if r.get('status') in ('待补齐', '') and r['date'] >= '2026-04-22']
    
    print(f"📊 GTHT版需补齐: {len(need)} 天 (4/22→6/2)")
    print(f"   日配额: ~{MAX_QUERIES_PER_RUN} 次")
    print(f"   预计本批可补: ~{MAX_QUERIES_PER_RUN} 天\n")
    
    queries_used = 0
    done = 0
    results_summary = []
    
    for idx, (ridx, row) in enumerate(need):
        if queries_used >= MAX_QUERIES_PER_RUN:
            print(f"\n⏸️ 已达日配额 ~{queries_used} 次，剩余 {len(need)-done} 天明天继续")
            break
        
        ds = row['date']
        print(f"\n[{done+1}/{len(need)}] {ds} ", end='', flush=True)
        
        top, next_day, success = process_date(ds)
        queries_used += 1
        
        if not success:
            print(f"❌ GTHT查询失败", flush=True)
            time.sleep(QUERY_DELAY)
            continue
        
        if not top:
            print(f"无候选", flush=True)
            rows[ridx]['status'] = '无候选'
            results_summary.append((ds, '无候选', None, None))
            done += 1
            time.sleep(QUERY_DELAY)
            continue
        
        # 有候选
        n_close = next_day.get('next_close') if next_day else None
        n_high = next_day.get('next_high', 0) or 0 if next_day else 0
        
        if n_close is not None:
            if n_close >= 2: judge = '✅达标'
            elif n_high >= 2: judge = '🟡盘中达标'
            else: judge = '❌失败'
            tag = f"→ 次收{n_close}%"
        else:
            judge = '待验证'
            tag = "→ 待验证"
        
        print(f"🏆 {top['name']}({top['code']}) {top['sector']} 评分{top['score']} {tag}", flush=True)
        
        rows[ridx].update({
            'status': 'OK',
            'code': top['code'],
            'name': top['name'],
            'sector': top['sector'],
            'zdf': round(top['zdf'], 2) if top['zdf'] else None,
            'lb': round(top['lb'], 2) if top['lb'] else None,
            'hs': round(top['hs'], 2) if top['hs'] else None,
            'flow': round(top['flow_yi'], 2),
            'ratio': round(top['ratio'], 1),
            'score': top['score'],
            'judge': judge,
            'weekday': get_weekday(ds),
            'next_open': next_day.get('next_open') if next_day else None,
            'next_high': next_day.get('next_high') if next_day else None,
            'next_close': n_close,
            'day_pnl': n_close if n_close is not None else 0,
            '_show_no_candidate': False,
        })
        
        results_summary.append((ds, top['name'], top['sector'], top['score']))
        done += 1
        time.sleep(QUERY_DELAY)
    
    # 重算累计
    cum = 0.0
    verified = 0
    wins = 0
    for r in rows:
        j = r.get('judge', '')
        nc = r.get('next_close')
        if j in ('✅达标', '❌失败', '🟡盘中达标') and nc is not None:
            cum += nc
            r['running_cum'] = round(cum, 2)
            verified += 1
            if '达标' in j:
                wins += 1
        elif j == '无候选':
            r['running_cum'] = round(cum, 2)
        elif j == '待验证':
            r['running_cum'] = round(cum, 2)
        else:
            r['running_cum'] = round(cum, 2)
    
    ok = sum(1 for r in rows if r['status'] == 'OK')
    nn = sum(1 for r in rows if r['status'] in ('无候选', ''))
    pd_ = sum(1 for r in rows if r.get('judge') in ('待验证', '?', '') and r['status'] == 'OK')
    
    data['stats']['ok'] = ok
    data['stats']['nn'] = nn
    data['stats']['pd'] = pd_
    data['stats']['verified'] = verified
    data['stats']['wins'] = wins
    data['stats']['rate'] = round(wins / verified * 100) if verified else 0
    data['stats']['v7_cum'] = round(cum, 2)
    data['stats']['total_days'] = len(rows)
    data['stats']['dq'] = 0
    
    with open(JSON_FILE, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 生成HTML
    gen_script = os.path.join(WORKSPACE, 'scripts', 'gen_v7_html.py')
    subprocess.run(['python3', gen_script], capture_output=True)
    
    # 今日小结
    print(f"\n{'='*50}")
    print(f"✅ 本批完成: {done}/{len(need)} 天, 使用 {queries_used} 次GTHT查询")
    print(f"   V7累计: {cum:.2f}% | 胜率: {wins}/{verified}={data['stats']['rate']}%")
    print(f"   OK: {ok} | 无候选: {nn} | 待验: {pd_}")
    
    if results_summary:
        print(f"\n   今日首推:")
        for ds, name, sec, sc in results_summary:
            n_str = f"{name}({sec}) 评分{sc}" if name else "无候选"
            print(f"     {ds}: {n_str}")
    
    print(f"\n   次日凌晨继续: openclaw cron会于00:05自动运行")


if __name__ == '__main__':
    main()
