#!/usr/bin/env python3
"""
产出V11网页展示数据：
对每个交易日，V11算法选Top3，按：
  - t+1日开盘价买入
  - t+2日开盘价卖出
计算每只盈亏 + 三支平均
输出JSON供页面使用
"""
import sqlite3, json, sys
from collections import defaultdict, OrderedDict
from pathlib import Path

DB = Path.home() / '.openclaw/workspace/data/h1_full.db'
OUT = Path.home() / '.openclaw/workspace/data/v11_web_data.json'

HIGH_RISK = {'房地产', '国防军工', '食品饮料', '非银金融', '机械设备', '传媒'}


def score_v11(r, scnt):
    s = 0
    lb = float(r.get('volume_ratio') or 0)
    if 1.2 <= lb < 2.0:   s += 18
    elif 2.0 <= lb < 3.0: s += 12
    elif 3.0 <= lb < 5.0: s += 6
    elif 0.8 <= lb < 1.0: s += 3

    hs = float(r.get('turnover_rate') or 0)
    if 5 <= hs < 10:     s += 15
    elif 10 <= hs < 15:   s += 10
    elif 3 <= hs < 5:     s += 8

    fl = float(r.get('net_inflow') or 0) / 1e8
    if fl > 0:           s += 15
    elif fl > -0.2:      s += 5

    if r.get('macd_red') == 1:   s += 12
    if r.get('above_ma60') == 1: s += 10

    sec = (r.get('sector') or '').strip()
    sc = scnt.get(sec, 0)
    if 5 <= sc < 10:     s += 10
    elif 3 <= sc < 5:   s += 5

    zf = float(r.get('change_pct') or 0)
    if 3 <= zf < 5:      s += 10
    elif 1 <= zf < 3:    s += 8
    elif 5 <= zf < 7:    s += 5

    amp = float(r.get('amplitude_pct') or 0)
    if amp >= 5:         s += 10
    elif amp >= 4:       s += 5
    return s


def run():
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 获取所有交易日，仅2026年
    cur.execute("SELECT DISTINCT trade_date FROM daily WHERE trade_date >= '2026-01-01' ORDER BY trade_date")
    all_dates = [r[0] for r in cur.fetchall()]
    
    # 建立日期->下个交易日和下下交易日映射
    date_idx = {d: i for i, d in enumerate(all_dates)}

    # 建立日期索引
    results = []

    for i, td in enumerate(all_dates):
        # 需要至少还有2个交易日才能做买入卖出
        if i + 2 >= len(all_dates):
            break
        
        buy_date = all_dates[i + 1]
        sell_date = all_dates[i + 2]

        # V11筛选
        cur.execute("""
            SELECT stock_code, stock_name, sector,
                   change_pct, volume_ratio, turnover_rate,
                   net_inflow, macd_red, above_ma60,
                   amplitude_pct, above_ma5
            FROM daily
            WHERE trade_date = ?
              AND amplitude_pct >= 3.0
              AND change_pct <= 3.0
              AND turnover_rate >= 3.0
              AND above_ma5 = 1
              AND stock_name NOT LIKE '%ST%'
              AND macd IS NOT NULL
              AND volume_ratio IS NOT NULL
        """, (td,))

        raw = [dict(r) for r in cur.fetchall()]
        raw = [s for s in raw if (s.get('sector') or '').strip() not in HIGH_RISK]

        if len(raw) < 3:
            continue

        scnt = defaultdict(int)
        for s in raw:
            sec = (s.get('sector') or '').strip()
            if sec:
                scnt[sec] += 1

        for s in raw:
            s['score'] = score_v11(s, scnt)
        raw.sort(key=lambda x: x['score'], reverse=True)

        top3 = raw[:3]
        
        picks = []
        daily_chgs = []
        
        for pk in top3:
            name = pk['stock_name']
            code = pk['stock_code']
            score_val = pk['score']
            
            # 买入价: buy_date的开盘价
            cur.execute("SELECT open,close FROM daily WHERE stock_code=? AND trade_date=?",
                       (code, buy_date))
            r1 = cur.fetchone()
            buy_p = r1['open'] if r1 else None
            
            # 卖出价: sell_date的开盘价
            cur.execute("SELECT open FROM daily WHERE stock_code=? AND trade_date=?",
                       (code, sell_date))
            r2 = cur.fetchone()
            sell_p = r2['open'] if r2 else None
            
            if buy_p and sell_p and buy_p > 0:
                chg = round((sell_p - buy_p) / buy_p * 100, 2)
            else:
                chg = None
            
            picks.append({
                'name': name,
                'code': code,
                'score': score_val,
                'buy_price': buy_p or 0,
                'sell_price': sell_p or 0,
                'chg': chg
            })
            if chg is not None:
                daily_chgs.append(chg)
        
        if len(daily_chgs) < 3:
            continue
        
        avg_chg = round(sum(daily_chgs) / 3, 2)
        
        results.append({
            'pick_date': td,
            'buy_date': buy_date,
            'sell_date': sell_date,
            'picks': picks,
            'avg_chg': avg_chg
        })

    conn.close()
    
    # 计算累计收益
    cumulative = 100.0
    for r in results:
        cumulative *= (1 + r['avg_chg'] / 100)
        r['cumulative'] = round(cumulative, 2)
    
    return results


if __name__ == '__main__':
    data = run()
    with open(OUT, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 统计
    hits = sum(1 for d in data if d['avg_chg'] > 0)
    miss = sum(1 for d in data if d['avg_chg'] <= 0)
    avg_all = round(sum(d['avg_chg'] for d in data) / len(data), 2)
    
    print(f"📊 V11 逐日数据 (开盘→开盘)")
    print(f"  总交易日(有候选≥3): {len(data)}")
    print(f"  盈利天数: {hits} ({round(hits/len(data)*100,1)}%)")
    print(f"  亏损天数: {miss}")
    print(f"  日均涨幅: {avg_all:+.2f}%")
    print(f"  累计收益: {round(data[-1]['cumulative']-100, 2)}%")
    print(f"\n  数据已写入: {OUT}")
    
    # 打印前10行和后10行
    print(f"\n  前5行:")
    for d in data[:5]:
        pnames = ' | '.join([f"{p['name']}({p['code']}) {p['chg']:+.2f}%" for p in d['picks']])
        print(f"    {d['pick_date']} 买入{d['buy_date']} 卖出{d['sell_date']} | {pnames} | 均{d['avg_chg']:+.2f}% 累{d['cumulative']}")
    
    print(f"\n  后5行:")
    for d in data[-5:]:
        pnames = ' | '.join([f"{p['name']}({p['code']}) {p['chg']:+.2f}%" for p in d['picks']])
        print(f"    {d['pick_date']} 买入{d['buy_date']} 卖出{d['sell_date']} | {pnames} | 均{d['avg_chg']:+.2f}% 累{d['cumulative']}")
