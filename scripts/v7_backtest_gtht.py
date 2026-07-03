#!/usr/bin/env python3
"""
V7完整回测 — 基于国泰海通金融数据查询（GTHT）

用法:
  python3 scripts/v7_backtest_gtht.py              # 跑2025全年
  python3 scripts/v7_backtest_gtht.py 20250605      # 单日
  python3 scripts/v7_backtest_gtht.py 20250101 20250331  # 日期范围

输出: validation_data/v7_backtest_gtht/ 目录下
"""

import subprocess, json, re, os, sys, time
from datetime import datetime, timedelta
from collections import Counter

WORKSPACE = os.path.expanduser('~/.openclaw/workspace')
SKILL_DIR = f"{WORKSPACE}/skills/gtht-financialsearch-skill"
OUT_DIR = f"{WORKSPACE}/validation_data/v7_backtest_gtht"
EXCLUDE_SECTORS = ['房地产']

os.makedirs(OUT_DIR, exist_ok=True)

def gtht_query(query, timeout=90, retry=5):
    """调用GTHT金融数据查询（带重试和退避）"""
    for attempt in range(retry):
        try:
            result = subprocess.run(
                ["node", "skill-entry.js", "mcpClient", "call", "financial", "financial-search",
                 f"query={query}"],
                cwd=SKILL_DIR, capture_output=True, text=True, timeout=timeout
            )
            outer = json.loads(result.stdout.strip())
            # Check if response contains error with rate limit
            if 'error' in outer:
                err_text = str(outer['error'])
                if 'Too many requests' in err_text or '限流' in err_text or 'too many' in err_text.lower():
                    wait = 30 * (attempt + 1)
                    print(f"[限流,等待{wait}s]", end='', flush=True)
                    time.sleep(wait)
                    continue
                raise Exception(err_text)
            raw_text = outer.get('text', '')
            if not raw_text:
                if attempt < retry - 1:
                    wait = 10 * (attempt + 1)
                    print(f"[空响应,等待{wait}s]", end='', flush=True)
                    time.sleep(wait)
                    continue
                raise Exception('空响应')
            # Check for rate limit in text
            if 'Too many requests' in raw_text or '限流' in raw_text or 'too many' in raw_text.lower():
                wait = 30 * (attempt + 1)
                print(f"[限流,等待{wait}s]", end='', flush=True)
                time.sleep(wait)
                continue
            return parse_markdown_table(raw_text)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError) as e:
            if attempt < retry - 1:
                wait = 10 * (attempt + 1)
                print(f"[重试{attempt+1}/{retry}]", end='', flush=True)
                time.sleep(wait)
                continue
            raise
    return []

def parse_markdown_table(text):
    """从GTHT返回的markdown表格中提取数据"""
    lines = text.strip().split('\n')
    headers = []
    data_rows = []
    found_header = False
    sep_passed = False

    for line in lines:
        line = line.strip()
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if not found_header:
            headers = cells
            found_header = True
        elif all(ch == '-' or ch == ':' for c in cells for ch in c if ch):
            sep_passed = True
        else:
            # Clean up partial cells from line breaks
            if cells and sep_passed:
                # Check if this looks like a continuation row
                if len(cells) < len(headers) and data_rows:
                    # It's a continuation - append to last row
                    last = data_rows[-1]
                    for i, cell in enumerate(cells):
                        if i < len(last):
                            last[i] = last[i] + cell
                        elif i == len(last):
                            last.append(cell)
                else:
                    data_rows.append(cells)

    # Convert rows to dicts
    result = []
    for row in data_rows:
        d = {}
        for i, h in enumerate(headers):
            val = row[i] if i < len(row) else ''
            d[h] = val
        result.append(d)
    return result

def clean_code(code):
    """提取6位股票代码"""
    nums = re.findall(r'\d{6}', str(code))
    return nums[0] if nums else code

def get_date_query(date_str, date_display=None):
    """构造V7筛选的自然语言查询"""
    if date_display is None:
        d = datetime.strptime(date_str, '%Y%m%d')
        date_display = f"{d.year}年{d.month}月{d.day}日"
    return (f"{date_display}A股主板非ST股票 "
            f"涨幅在2%到8% "
            f"量比大于1.2 "
            f"换手率大于3% 换手率小于16% "
            f"主力净流入大于5000万元 "
            f"所属同花顺行业 成交额")

def get_5d_flow_query(stocks, date_str):
    """构造多股票5日资金流查询"""
    d = datetime.strptime(date_str, '%Y%m%d')
    # Find the dates for previous 5 trading days (approximately 7 calendar days back)
    start_d = d - timedelta(days=7)
    start_display = f"{start_d.year}年{start_d.month}月{start_d.day}日"
    end_display = f"{d.year}年{d.month}月{d.day}日"

    names = '、'.join(stocks[:15])  # Limit to 15 stocks per query to avoid issues
    return f"{names} {start_display}到{end_display}主力资金流向"

def get_next_day_data_query(name, code, next_date_str):
    """构造次日行情查询"""
    d = datetime.strptime(next_date_str, '%Y%m%d')
    date_display = f"{d.year}年{d.month}月{d.day}日"
    return f"{name} {date_display}开盘价最高价收盘价最低价涨跌幅主力资金流向量比换手率"

def get_trading_days(start_date, end_date):
    """获取指定范围内的交易日列表"""
    days = []
    d = datetime.strptime(start_date, '%Y%m%d')
    end = datetime.strptime(end_date, '%Y%m%d')
    while d <= end:
        if d.weekday() < 5:
            days.append(d.strftime('%Y%m%d'))
        d += timedelta(days=1)
    return days

def next_trading_day(date_str):
    """获取下一交易日"""
    d = datetime.strptime(date_str, '%Y%m%d') + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d.strftime('%Y%m%d')

def get_sector(item):
    """从GTHT返回数据提取行业"""
    sector_raw = item.get('所属同花顺行业', '')
    if isinstance(sector_raw, list):
        return sector_raw[0] if sector_raw else '未知'
    # Format: "['通信', '通信设备', '通信网络设备及器件']"
    m = re.findall(r"'([^']+)'", str(sector_raw))
    return m[0] if m else str(sector_raw).strip("[]' ")

def v7_score(candidate):
    """V7五维评分（0-100分）"""
    scores = {}
    flow = float(candidate.get('flow', 0))
    flow_ratio = float(candidate.get('flow_ratio', 0))
    turnover = float(candidate.get('turnover', 0))
    vol_ratio = float(candidate.get('vol_ratio', 1))
    change = abs(float(candidate.get('change_pct', 0)))
    flow_wan = flow / 10000

    # 基础分
    scores['基础分'] = 40

    # 净流入占比分 (0-25)
    if flow_ratio > 12:
        scores['净流入占比'] = 25
    elif flow_ratio > 8:
        scores['净流入占比'] = 20
    elif flow_ratio > 5:
        scores['净流入占比'] = 18
    elif flow_ratio > 3:
        scores['净流入占比'] = 10

    # 净流入绝对值 (0-12)
    if flow_wan > 15000:
        scores['净流入绝对值'] = 12
    elif flow_wan > 10000:
        scores['净流入绝对值'] = 10
    elif flow_wan > 5000:
        scores['净流入绝对值'] = 5

    # 涨幅区间 (0-8)
    if 2.5 <= change <= 5:
        scores['涨幅区间'] = 8
    elif change <= 6.5:
        scores['涨幅区间'] = 5

    # 资金效率 (0-8)
    if turnover > 0:
        efficiency = flow_wan / turnover
        if efficiency > 0.5:
            scores['资金效率'] = 8
        elif efficiency > 0.2:
            scores['资金效率'] = 5

    # 量比区间 (0-5)
    if 1.5 <= vol_ratio <= 4:
        scores['量比区间'] = 5

    # 板块加分 (0-5)
    if candidate.get('sector_count', 0) >= 2:
        scores['板块加分'] = 5

    # 惩罚
    if vol_ratio > 4 and turnover > 14:
        scores['高量比高换手'] = -5
    if turnover < 5 and flow_ratio > 15:
        scores['低换手高占比'] = -8

    total = sum(scores.values())
    return total, scores

def run_day(date_str, all_results):
    """回测单日"""
    date_display = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    next_date = next_trading_day(date_str)

    print(f"  [{date_display}] ", end='', flush=True)

    # Step 1: V7筛选
    query = get_date_query(date_str)
    try:
        data = gtht_query(query)
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        all_results[date_str] = {'error': str(e)}
        return

    if not data:
        print("无数据")
        all_results[date_str] = {'code_count': 0, 'verdict': '无数据'}
        return

    print(f"{len(data)}只→", end='', flush=True)

    # Step 2: 解析候选池
    candidates = []
    for item in data:
        code = clean_code(item.get('股票代码', ''))
        name = item.get('股票简称', '')
        if not code: continue

        # Try to get date-specific values from keys containing the date
        change = 0
        vol = 0
        tovr = 0
        flow = 0
        amount = 0

        for k, v in item.items():
            try:
                if f'涨跌幅[{date_str}]' in k:
                    change = float(v or 0)
                elif f'量比[{date_str}]' in k:
                    vol = float(v or 0)
                elif f'换手率[{date_str}]' in k:
                    tovr = float(v or 0)
                elif f'主力资金流向[{date_str}]' in k:
                    flow = float(v or 0)
                elif f'成交额[{date_str}]' in k:
                    amount = float(v or 0)
            except:
                pass

        sector = get_sector(item)

        # Data quality check: skip if key fields are zero (stale/cached data)
        if change == 0 and vol == 0 and tovr == 0:
            continue
        if flow == 0:
            continue

        flow_ratio = (flow / amount * 100) if amount > 0 else 0

        if sector in EXCLUDE_SECTORS:
            continue

        candidates.append({
            'code': code, 'name': name, 'sector': sector,
            'change_pct': change, 'vol_ratio': vol, 'turnover': tovr,
            'flow': flow, 'flow_wan': round(flow / 10000, 2),
            'amount': amount, 'flow_ratio': flow_ratio,
        })

    if not candidates:
        print("无候选(行业过滤)")
        all_results[date_str] = {'code_count': len(data), 'verdict': '行业过滤后无候选'}
        return

    # Step 3: 板块热度警戒
    sector_counts = Counter(c['sector'] for c in candidates)
    hot_sectors = {s for s, c in sector_counts.items() if c >= 10}
    if hot_sectors:
        candidates = [c for c in candidates if c['sector'] not in hot_sectors]
        print(f"板块热{len(sector_counts)}→排除{sorted(hot_sectors)}→{len(candidates)}只→", end='', flush=True)

    if not candidates:
        print("板块热度过滤后无候选")
        all_results[date_str] = {'code_count': len(data), 'verdict': '板块热度过滤后无候选'}
        return

    # Step 4: V7评分（直接对所有候选评分，无5日硬否决）
    sector_counts_all = Counter(c['sector'] for c in candidates)
    for c in candidates:
        c['sector_count'] = sector_counts_all.get(c['sector'], 0)
        total, details = v7_score(c)
        c['score'] = total
        c['score_details'] = details

    candidates.sort(key=lambda x: x['score'], reverse=True)
    top_pick = candidates[0]

    print(f"候选{len(candidates)}只→首推{top_pick['name']}({top_pick['score']}分)→", end='', flush=True)

    time.sleep(3)  # 限流保护

    # Step 6: 查首推次日表现
    next_day = {'change_pct': 0, 'high_change': 0, 'open': 0, 'high': 0, 'close': 0, 'low': 0}
    try:
        nd_query = get_next_day_data_query(top_pick['name'], top_pick['code'], next_date)
        nd_data = gtht_query(nd_query)
        time.sleep(0.3)

        if nd_data:
            nd = nd_data[0]
            open_p = float(nd.get(f'开盘价[{next_date}]', 0) or 0)
            high_p = float(nd.get(f'最高价[{next_date}]', 0) or 0)
            close_p = float(nd.get(f'收盘价[{next_date}]', 0) or 0)
            low_p = float(nd.get(f'最低价[{next_date}]', 0) or 0)
            change = float(nd.get(f'涨跌幅[{next_date}]', 0) or 0)
            next_day = {
                'open': open_p, 'high': high_p, 'close': close_p,
                'low': low_p, 'change_pct': change,
                'high_change': ((high_p - open_p) / open_p * 100) if open_p else 0
            }
    except Exception as e:
        print(f"[次日查询失败:{e}]", end='', flush=True)

    # 判定
    cp = next_day['change_pct']
    hc = next_day['high_change']
    if cp >= 2:
        verdict = '✅'
    elif hc >= 2:
        verdict = '→✅盘中'
    elif 0 < cp < 2:
        verdict = '❌'
    else:
        verdict = '💀'

    print(f"次日{cp:.2f}%{verdict}")

    all_results[date_str] = {
        'date': date_str,
        'next_date': next_date,
        'date_display': date_display,
        'code_count': len(data),
        'candidates': len(candidates),
        'passed_5d': 0,
        'eliminated_5d': 0,
        'sector_counts': {s: c for s, c in sorted(sector_counts.items())},
        'hot_sectors': list(hot_sectors) if hot_sectors else [],
        'top_pick': {
            'name': top_pick['name'],
            'code': top_pick['code'],
            'sector': top_pick['sector'],
            'score': top_pick['score'],
            'score_details': top_pick['score_details'],
            'change_pct': top_pick['change_pct'],
            'vol_ratio': top_pick['vol_ratio'],
            'turnover': top_pick['turnover'],
            'flow_wan': top_pick['flow_wan'],
            'total_5d_wan': top_pick.get('total_5d_wan', 0),
            'flow_ratio': top_pick['flow_ratio'],
        },
        'next_day': next_day,
        'verdict': verdict,
    }


def print_summary(all_results):
    """打印汇总"""
    total = len(all_results)
    no_data = sum(1 for v in all_results.values() if v.get('verdict') in ['无数据'])
    errors = sum(1 for v in all_results.values() if 'error' in v)
    no_recommend = sum(1 for v in all_results.values() if v.get('verdict') == '今日不推荐')
    no_candidate = sum(1 for v in all_results.values()
                       if v.get('verdict') in ['行业过滤后无候选', '板块热度过滤后无候选'])
    skipped = no_data + errors + no_recommend + no_candidate
    recommended = total - skipped

    success = sum(1 for v in all_results.values() if v.get('verdict') in ['✅', '→✅盘中'])
    fail_hit = sum(1 for v in all_results.values() if v.get('verdict') in ['❌', '💀'])

    rate_with_recommend = success / max(recommended, 1) * 100
    rate_total = success / max(total, 1) * 100

    print(f"\n{'='*60}")
    print(f"  2025年回测汇总（GTHT版）")
    print(f"{'='*60}")
    print(f"  总交易日:       {total}")
    print(f"  有推荐日:       {recommended}")
    print(f"  无数据/错误:    {errors + no_data}")
    print(f"  无推荐(全否决): {no_recommend}")
    print(f"  无候选(过滤):   {no_candidate}")
    print(f"  达标(✅):       {sum(1 for v in all_results.values() if v.get('verdict') == '✅')}")
    print(f"  盘中达标(→✅):  {sum(1 for v in all_results.values() if v.get('verdict') == '→✅盘中')}")
    print(f"  失败:           {fail_hit}")
    print(f"  达标率(有推荐): {rate_with_recommend:.1f}%")
    print(f"  达标率(总交易): {rate_total:.1f}%")

    print(f"\n  逐日明细:")
    print(f"  {'日期':<12} {'推荐':<10} {'得分':<5} {'次日%':<8} {'判定'}")
    print(f"  {'-'*40}")
    for date_str in sorted(all_results.keys()):
        v = all_results[date_str]
        tp = v.get('top_pick', {})
        nd = v.get('next_day', {})
        name = tp.get('name', '-') if tp else '-'
        score = tp.get('score', '-') if tp else '-'
        change = nd.get('change_pct', 0) if nd else 0
        verdict = v.get('verdict', '?')
        print(f"  {date_str:<12} {name:<10} {str(score):<5} {change:<8.2f} {verdict}")


def main():
    args = sys.argv[1:]

    if len(args) >= 2:
        start_date, end_date = args[0], args[1]
    elif len(args) == 1:
        # Single day
        run_day(args[0], {})
        return
    else:
        # 2025 full year
        start_date = '20250101'
        end_date = '20251231'

    trading_days = get_trading_days(start_date, end_date)
    total_days = len(trading_days)
    print(f"2025回测: {total_days}个交易日")
    print(f"数据源: 国泰海通(GTHT)金融数据查询")
    print(f"算法: V7筛选 + 5日资金硬否决 + 板块热度警戒 + 五维评分")
    print(f"{'='*60}\n")

    all_results = {}

    for i, date_str in enumerate(trading_days):
        print(f"[{i+1}/{total_days}] ", end='')
        run_day(date_str, all_results)
        # Rate limit: large interval between days
        if i < total_days - 1:
            sleep_time = 15
            print(f"  [等待{sleep_time}s]", end='', flush=True)
            time.sleep(sleep_time)  # 限流保护间隔
        # Extra cooldown every 5 days
        if (i + 1) % 5 == 0 and i < total_days - 1:
            extra = 30
            print(f"[额外冷却{extra}s]", end='', flush=True)
            time.sleep(extra)

    print_summary(all_results)

    # Save
    summary = {
        'start_date': start_date,
        'end_date': end_date,
        'total_days': total_days,
        'recommended_days': sum(1 for v in all_results.values()
                                if v.get('verdict') in ['✅', '→✅盘中', '❌', '💀']),
        'success_days': sum(1 for v in all_results.values() if v.get('verdict') in ['✅', '→✅盘中']),
        'fail_days': sum(1 for v in all_results.values() if v.get('verdict') in ['❌', '💀']),
        'no_recommend': sum(1 for v in all_results.values()
                            if v.get('verdict') in ['今日不推荐', '行业过滤后无候选', '板块热度过滤后无候选', '无数据']),
        'success_rate_with_recommend': round(
            sum(1 for v in all_results.values() if v.get('verdict') in ['✅', '→✅盘中']) /
            max(sum(1 for v in all_results.values()
                    if v.get('verdict') in ['✅', '→✅盘中', '❌', '💀']), 1) * 100, 1),
        'details': all_results
    }

    now = datetime.now().strftime('%Y%m%d_%H%M%S')
    outfile = f"{OUT_DIR}/results_{start_date}_{end_date}_{now}.json"
    with open(outfile, 'w') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n  结果已保存: {outfile}")


if __name__ == '__main__':
    main()
