#!/usr/bin/env python3
"""
rebuild_panel.py — 收集后重建 index.html (GitHub Pages)

从两个 JSON（v7_data_latest.json / v7_wencai_latest.json）重新生成
面板内 #pageGtht / #pageWencai / #pageCompare 的内容，就地替换。
输出直接写入 index.html (git跟踪，推送到 GitHub Pages)。
"""
import json, re, os, sys
from datetime import datetime

_self_dir = os.path.dirname(__file__)
_base = os.path.normpath(os.path.join(_self_dir, '..'))
_final = os.path.join(_base, 'v7_web', 'final_version')

def fmt(v, suf=''):
    if v is None: return '—'
    return f'{v:.2f}{suf}'

def gen_gtht_wencai_body(data, title):
    """生成 GTHT/问财 页面 body HTML（不含 <div id="pageX"> 标签）"""
    v7 = data['v7_rows']
    stats = data['stats']
    v7_cum = stats['v7_cum']
    W = {'一':'周一','二':'周二','三':'周三','四':'周四','五':'周五','六':'周六','日':'周日'}
    suf_map = {'zdf':'%','lb':'','hs':'%','flow':'亿'}
    H = [('首推','股票（评分）'),('行业','所属板块'),('涨幅','当日±%'),('量比','资金关注'),
         ('换手','活跃度%'),('净流入','主力亿'),('评分','V7总分'),('次开%','次日开盘'),('次高%','次日最高'),
         ('次收%','次日收盘'),('判定','✅/❌'),('累计%','V7累加')]
    parts = []
    def w(s): parts.append(s)

    ok_count = sum(1 for r in v7 if r.get('status')=='OK')
    nn_count = sum(1 for r in v7 if r.get('_show_no_candidate') and r.get('status')!='待补齐')
    dq_count = sum(1 for r in v7 if r.get('status')=='待补齐')
    wins = stats['wins']; verified = stats['verified']
    close_wins = sum(1 for r in v7 if r.get('code') and r.get('next_close') is not None and r.get('next_close') >= 2.0)

    up_class = 'up' if v7_cum > 0 else 'dn'
    is_wc = '问财' in title
    real_pnl = '0.00' if is_wc else '-849.00'
    close_rate = round(close_wins / verified * 100) if verified else 0

    w('<div class="sm">')
    w(f'<div class="sc {up_class}"><div class="l">V7 模拟累计</div><div class="v">{"+" if v7_cum>0 else ""}{v7_cum:.2f}%</div><div class="s">已验证 {verified} 天</div></div>')
    w(f'<div class="sc ne"><div class="l">实盘累计</div><div class="v">{real_pnl}</div></div>')
    w(f'<div class="sc blue"><div class="l">交易日 / 有候选</div><div class="v">{len(v7)}</div><div class="s">候选 {ok_count} | 待验 {stats["pd"]} | 无 {nn_count} | 待补 {dq_count}</div></div>')
    w(f'<div class="sc neu"><div class="l">V7 已验证</div><div class="s" style="font-size:13px;line-height:1.8;color:#333">盘中 {wins}/{verified} = {stats["rate"]}%<br>收盘 {close_wins}/{verified} = {close_rate}%</div></div>')
    w('</div>')

    w('<div class="w"><table><thead><tr>')
    w('<th style="min-width:62px;background:#e8ecf3;border-right:2px solid #dee2e6">日期</th>')
    for h,sub in H:
        w(f'<th>{h}<span class="sh">{sub}</span></th>')
    w('</tr></thead><tbody>')

    for row in v7:
        m = int(row['date'][5:7])
        d_int = int(row['date'][8:10])
        wd = row['weekday']
        fri = (wd == '五')
        pend = (row['date'] == '2026-06-23')
        pend2 = ('问财' in title and row['date'] == '2026-06-25')
        fricls = ' fri' if fri else ''
        pend_marker = '<span class="pend-marker">⚠两线分歧</span>' if pend else ''
        if pend2:
            sty = 'color:#e67e22;border-color:#e67e22'
            pm = f'<span class="pend-marker" style="{sty}">⏱盘中vs盘后</span>'
            pend_marker = pend_marker + pm
        w(f'<tr><td class="dc{fricls}">{m}月{d_int}日<span class="dw">{W[wd]}</span>{pend_marker}</td>')

        s = row.get('status','')
        j = row.get('judge','')
        nc_bool = row.get('_show_no_candidate', False) or s == '待补齐'

        # 首推
        if s == '待补齐':
            w('<td class="c-zz">待补齐</td>')
        elif nc_bool:
            w('<td class="c-zz">无候选</td>')
        else:
            n = row.get('name') or chr(8212)
            sc = row.get('score')
            if j in ('✅达标','🟡盘中达标'):
                cls = 'c-ok'
            elif j == '❌失败':
                cls = 'c-fl'
            else:
                cls = 'c-pd'
            dsp = chr(8212) if n == chr(8212) else (f'{n}<br><span style="font-size:10px;color:#999">{int(sc)}分</span>' if sc else n)
            w(f'<td class="{cls}">{dsp}</td>')

        # 行业
        if s == '待补齐' or nc_bool:
            w('<td class="c-zz">—</td>')
        else:
            sec = row.get('sector','') or ''
            w(f'<td style="font-size:11px">{sec}</td>' if sec else '<td class="c-pd">?</td>')

        # 核心数据
        for k in ['zdf','lb','hs','flow']:
            v = row.get(k)
            suf = suf_map[k]
            if s == '待补齐' or nc_bool:
                w('<td class="c-zz">—</td>')
            elif v is not None:
                w(f'<td>{v}{suf}</td>')
            else:
                w('<td class="c-pd">?</td>')

        # 评分
        sc = row.get('score')
        if sc and s not in ('待补齐','') and not nc_bool:
            w(f'<td>{int(sc)}</td>')
        else:
            w('<td class="c-zz">—</td>')

        # 次日数据
        for k in ['next_open','next_high','next_close']:
            v = row.get(k)
            if j in ('✅达标','🟡盘中达标','❌失败') and v is not None:
                w(f'<td>{fmt(v, "%")}</td>')
            elif s == '待补齐' or nc_bool:
                w('<td class="c-zz">—</td>')
            else:
                w('<td class="c-pd">?</td>')

        # 判定
        if j in ('✅达标','🟡盘中达标','❌失败'):
            ok_cls = 'c-ok' if '达标' in j else 'c-fl'
            ok_mark = '✅' if '达标' in j else '❌'
            w(f'<td class="{ok_cls}">{ok_mark}</td>')
        elif s == '待补齐' or nc_bool:
            w('<td class="c-zz">—</td>')
        else:
            w('<td class="c-pd">⌛</td>')

        # 累计
        rc = row.get('running_cum')
        if rc is not None:
            rc_cls = 'c-ok' if rc > 0 else ('c-fl' if rc < 0 else '')
            w(f'<td class="{rc_cls}">{fmt(rc, "%")}</td>')
        else:
            w('<td class="c-zz">—</td>')

        w('</tr>')

    w('</tbody></table></div>')
    return ''.join(parts)


def gen_compare_body(gtht_data, wencai_data):
    """生成对比页 body HTML"""
    gtht_map = {}
    for r in gtht_data['v7_rows']:
        gtht_map[r['date']] = r
    wencai_map = {}
    for r in wencai_data['v7_rows']:
        wencai_map[r['date']] = r

    all_dates = sorted(set(gtht_map.keys()) | set(wencai_map.keys()),
                       key=lambda d: d)
    total = len(all_dates)
    gtht_ok = sum(1 for r in gtht_data['v7_rows'] if r.get('judge') in ('✅达标','🟡盘中达标'))
    wencai_ok = sum(1 for r in wencai_data['v7_rows'] if r.get('judge') in ('✅达标','🟡盘中达标'))
    both_ok = sum(1 for d in all_dates
                  if gtht_map.get(d,{}).get('judge') in ('✅达标','🟡盘中达标')
                  and wencai_map.get(d,{}).get('judge') in ('✅达标','🟡盘中达标'))

    rows = []
    for date in all_dates:
        g = gtht_map.get(date, {})
        w = wencai_map.get(date, {})
        g_j = '✅' if g.get('judge') in ('✅达标','🟡盘中达标') else ('❌' if g.get('judge')=='❌失败' else '⏳')
        w_j = '✅' if w.get('judge') in ('✅达标','🟡盘中达标') else ('❌' if w.get('judge')=='❌失败' else '⏳')
        g_cls = 'c-ok' if g_j == '✅' else 'c-fl'
        w_cls = 'c-ok' if w_j == '✅' else 'c-fl'
        m = int(date[5:7]); d_int = int(date[8:10])
        rows.append(f'''<tr>
      <td class="dc">{m}月{d_int}日</td>
      <td class="stk {g_cls}">{g.get('name','—')}</td>
      <td class="tag {g_cls} gr">{g_j}</td>
      <td class="stk {w_cls}">{w.get('name','—')}</td>
      <td class="tag {w_cls}">{w_j}</td>
    </tr>''')

    table_html = '\n'.join(rows)
    return f'''<div class="sm">
  <div class="sc up"><div class="l">GTHT 达标</div><div class="v">{gtht_ok}/{total}</div><div class="s">{gtht_ok*100//max(total,1)}%</div></div>
  <div class="sc blue"><div class="l">问财 达标</div><div class="v">{wencai_ok}/{total}</div><div class="s">{wencai_ok*100//max(total,1)}%</div></div>
  <div class="sc green"><div class="l">同日双✅</div><div class="v">{both_ok}</div><div class="s">共{total}天</div></div>
</div>
<div class="w">
<table>
<thead>
<tr><th rowspan="2" style="min-width:58px">日期</th>
  <th class="grp-gtht" colspan="2">📈 国泰海通</th>
  <th class="grp-wc" colspan="2">📊 问财</th></tr>
<tr><th class="sub">首推</th><th class="sub gr" style="width:26px">判定</th><th class="sub">首推</th><th class="sub" style="width:26px">判定</th></tr>
</thead>
<tbody>
{table_html}
</tbody>
</table>
</div>'''


def gen_fenqi_body(gtht_data, wencai_data):
    """生成分歧页 body HTML — 从两JSON的meta中读取分歧记录自动生成"""
    gtht_map = {r['date']: r for r in gtht_data['v7_rows']}
    wencai_map = {r['date']: r for r in wencai_data['v7_rows']}

    # 收集所有分歧日期（排除 _detail_ 等子记录）
    div_keys = set()
    for meta in [gtht_data.get('meta',{}), wencai_data.get('meta',{})]:
        for k in meta:
            # 只取 divergence_20260629 格式，不要 divergence_detail_
            parts = k.split('_', 1)
            if parts[0] == 'divergence' and len(parts) > 1 and parts[1].isdigit():
                div_keys.add(k)
    div_dates = sorted([k.replace('divergence_','') for k in div_keys])

    if not div_dates:
        return '<div style="padding:20px;text-align:center;color:#999">暂无分歧记录</div>'

    W = ['','一','二','三','四','五','六','日']
    buttons = []
    pages = []

    for idx, date_str in enumerate(div_dates):
        m = int(date_str[4:6]); d = int(date_str[6:8])
        from datetime import date
        wd = date(int(date_str[:4]), m, d).weekday()
        label = f'{m}/{d} 周{W[wd]}'
        active = 'active' if idx == 0 else ''

        # 分别取两线数据
        g_r = gtht_map.get(f'{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}', {})
        w_r = wencai_map.get(f'{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}', {})

        # 判定状态
        def judge_status(r):
            j = r.get('judge','')
            if j in ('✅达标','🟡盘中达标'):
                return ('win', 'good', '✅', '#27ae60')
            elif j == '❌失败':
                return ('lose', 'bad', '❌', '#e74c3c')
            else:
                return ('pend', 'pend', '⏳', '#f39c12')

        g_st, g_cls, g_mark, g_col = judge_status(g_r)
        w_st, w_cls, w_mark, w_col = judge_status(w_r)

        # 整体状态
        if g_st == 'win' and w_st == 'win':
            overall_badge = '<span class="fq-badge ok-badge">✅ 双达标</span>'
            diff_color, diff_bg = '#27ae60', '#e8f5e9'
        elif g_st == 'lose' and w_st == 'lose':
            overall_badge = '<span class="fq-badge fail-badge">❌ 双败</span>'
            diff_color, diff_bg = '#e74c3c', '#ffebee'
        elif g_st == 'pend' or w_st == 'pend':
            overall_badge = '<span class="fq-badge pend-badge">⏳ 待验证</span>'
            diff_color, diff_bg = '#f39c12', '#fff8e1'
        else:
            overall_badge = '<span class="fq-badge warn-badge">⚠ 有分歧</span>'
            diff_color, diff_bg = '#e67e22', '#fff3e0'

        # 获取分歧备注
        meta_info = '—'
        for meta in [gtht_data.get('meta',{}), wencai_data.get('meta',{})]:
            dv = meta.get(f'divergence_{date_str}', {})
            if isinstance(dv, dict) and dv.get('note'):
                meta_info = dv['note']
                break

        # OHLC数据
        def ohlc_str(r):
            o = r.get('next_open'); h = r.get('next_high'); c = r.get('next_close')
            if o is not None and h is not None and c is not None:
                return f'开{fmt(o,"%")} · 高{fmt(h,"%")} · 收{fmt(c,"%")}'
            return '次日数据待补齐'

        g_name = g_r.get('name','—') or '—'
        w_name = w_r.get('name','—') or '—'
        g_code = g_r.get('code','') or ''
        w_code = w_r.get('code','') or ''
        g_score = int(g_r['score']) if g_r.get('score') else '?'
        w_score = int(w_r['score']) if w_r.get('score') else '?'
        g_flow = (f'{g_r["flow"]}亿') if g_r.get('flow') is not None else '—'
        w_flow = (f'{w_r["flow"]}亿') if w_r.get('flow') is not None else '—'
        g_zdf = (f'{fmt(g_r["zdf"],"%")}') if g_r.get('zdf') is not None else '—'
        w_zdf = (f'{fmt(w_r["zdf"],"%")}') if w_r.get('zdf') is not None else '—'
        g_sector = g_r.get('sector','') or '—'
        w_sector = w_r.get('sector','') or '—'

        buttons.append(f'''  <button class="fq-btn {active}" onclick="switchFenqi({idx})" id="fqBtn{idx}">
    <span style="display:block;font-size:16px;margin-bottom:1px">📅</span>
    {label}
  </button>''')

        pages.append(f'''<div class="fq-page{" active" if idx==0 else ""}" id="fqPage{idx}" style="padding:0 12px 20px">

<div class="fq-card">
  <div class="fq-card-hdr warn">
    <span>📌 {m}/{d}（周{W[wd]}）双管线分歧</span>
    {overall_badge}
  </div>
  <div class="fq-card-body">

    <div class="fq-duel">
      <div class="fq-side {g_st}">
        <div class="fq-side-top">
          <div class="fq-pipe">📈 GTHT</div>
          <div class="fq-code">{g_code}</div>
        </div>
        <div class="fq-stock-name">{g_name}</div>
        <div class="fq-tag-row"><span class="fq-tag {g_cls}" style="background:{g_col}20;color:{g_col}">{g_mark} {g_sector}</span></div>
        <div class="fq-stats">
          <div>评分 <b>{g_score}</b></div>
          <div>净流入 <b>{g_flow}</b></div>
          <div>涨幅 <b>{g_zdf}</b></div>
        </div>
        <div class="fq-ohlc">{ohlc_str(g_r)}</div>
      </div>
      <div class="fq-vs-badge">VS</div>
      <div class="fq-side {w_st}">
        <div class="fq-side-top">
          <div class="fq-pipe">📊 问财</div>
          <div class="fq-code">{w_code}</div>
        </div>
        <div class="fq-stock-name">{w_name}</div>
        <div class="fq-tag-row"><span class="fq-tag {w_cls}" style="background:{w_col}20;color:{w_col}">{w_mark} {w_sector}</span></div>
        <div class="fq-stats">
          <div>评分 <b>{w_score}</b></div>
          <div>净流入 <b>{w_flow}</b></div>
          <div>涨幅 <b>{w_zdf}</b></div>
        </div>
        <div class="fq-ohlc">{ohlc_str(w_r)}</div>
      </div>
    </div>

    <div class="fq-diff-bar" style="background:{diff_bg};color:{diff_color}">
      {meta_info}
    </div>

  </div>
</div>

</div>''')

    buttons_html = '\n'.join(buttons)
    pages_html = '\n'.join(pages)

    return f'''<div style="background:linear-gradient(135deg,#e67e22,#d35400);color:#fff;text-align:center;padding:14px 12px;font-size:16px;font-weight:700;letter-spacing:1px">
  ⚠ 双管线分歧档案
  <div style="font-size:11px;font-weight:400;margin-top:4px;opacity:.8">每次分歧都是迭代模型的机会</div>
</div>

<div style="display:flex;gap:8px;padding:12px;background:#f0f0ec">
{buttons_html}
</div>

{pages_html}

<div style="font-size:10px;color:#aaa;text-align:center;padding:10px;border-top:1px dashed #ddd;margin-top:12px">
分歧数据自动记录于meta · 收集时同步更新
</div>'''


def rebuild_panel(panel_path, gtht_body, wencai_body, compare_body, fenqi_body):
    """读取面板 HTML，替换全部四个页面内容"""
    with open(panel_path) as f:
        html = f.read()

    # 替换 GTHT 页
    html = re.sub(
        r'(<div class="page" id="pageGtht">).*?(</div>\s*<div class="page" id="pageWencai")',
        lambda m: m.group(1) + gtht_body + m.group(2),
        html, count=1, flags=re.DOTALL
    )

    # 替换 问财 页
    html = re.sub(
        r'(<div class="page" id="pageWencai">).*?(</div>\s*<div class="page" id="pageCompare")',
        lambda m: m.group(1) + wencai_body + m.group(2),
        html, count=1, flags=re.DOTALL
    )

    # 替换 对比 页
    html = re.sub(
        r'(<div class="page" id="pageCompare">).*?(</div>\s*<div class="page" id="pageFenqi")',
        lambda m: m.group(1) + compare_body + m.group(2),
        html, count=1, flags=re.DOTALL
    )

    # 替换 分歧 页
    html = re.sub(
        r'(<div class="page" id="pageFenqi">).*?(</div>\s*<div class="page" id="pageCheckin"|</div>\s*</div>\s*</div>\s*<script)',
        lambda m: m.group(1) + fenqi_body + m.group(2),
        html, count=1, flags=re.DOTALL
    )

    with open(panel_path, 'w') as f:
        f.write(html)
    return True


if __name__ == '__main__':
    gtht_json = os.path.join(_final, 'v7_data_latest.json')
    wencai_json = os.path.join(_final, 'v7_wencai_latest.json')
    panel = os.path.join(_base, 'index.html')

    if not os.path.exists(panel):
        print(f'❌ 面板文件不存在: {panel}')
        sys.exit(1)

    with open(gtht_json) as f:
        gtht_data = json.load(f)
    with open(wencai_json) as f:
        wencai_data = json.load(f)

    print(f'GTHT: {len(gtht_data["v7_rows"])} rows, {gtht_data["stats"]["v7_cum"]:.2f}%')
    print(f'问财: {len(wencai_data["v7_rows"])} rows, {wencai_data["stats"]["v7_cum"]:.2f}%')

    gtht_body = gen_gtht_wencai_body(gtht_data, 'V7 选股日报(GTHT)')
    wencai_body = gen_gtht_wencai_body(wencai_data, 'V7 选股日报(问财)')
    compare_body = gen_compare_body(gtht_data, wencai_data)
    fenqi_body = gen_fenqi_body(gtht_data, wencai_data)

    print(f'GTHT body: {len(gtht_body)} bytes')
    print(f'问财 body: {len(wencai_body)} bytes')
    print(f'对比 body: {len(compare_body)} bytes')
    print(f'分歧 body: {len(fenqi_body)} bytes')

    rebuild_panel(panel, gtht_body, wencai_body, compare_body, fenqi_body)

    final_size = os.path.getsize(panel)
    print(f'✅ 面板已更新: {final_size} bytes → {panel}')
