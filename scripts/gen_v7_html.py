#!/usr/bin/env python3
"""Generate V7 HTML from JSON data"""
import json, shutil, sys, os

# 预检：生成前先重算累计统计
_self_dir = os.path.dirname(__file__)
_recalc_path = os.path.join(_self_dir, 'recalc_v7_stats.py')
if os.path.exists(_rec_path := _recalc_path):
    with open(_rec_path) as _f:
        exec(compile(_f.read(), _rec_path, 'exec'))
    _data_dir = os.path.join(os.path.dirname(_self_dir), 'v7_web', 'final_version')
    for _fn in ['v7_data_latest.json', 'v7_wencai_latest.json']:
        _fp = os.path.join(_data_dir, _fn)
        if os.path.exists(_fp):
            _changed, _data, _stats, _checks = recalc(_fp)
            if _changed:
                with open(_fp, 'w') as _fw:
                    json.dump(_data, _fw, ensure_ascii=False, indent=2)


def fmt(v, suf=''):
    """格式化数字：保留2位小数 + 后缀"""
    if v is None:
        return '—'
    return f'{v:.2f}{suf}'


def gen_html(fp, title):
    with open(fp) as f:
        data = json.load(f)
    v7 = data['v7_rows']
    stats = data['stats']
    # 动态读取分歧日期
    is_wencai = '问财' in title
    div_dates = set()
    for k in data.get('meta', {}):
        if k.startswith('divergence_') and not k.startswith('divergence_detail_'):
            date_str = k.replace('divergence_', '')
            if len(date_str) == 8:
                div_dates.add(date_str)
    v7_cum = stats['v7_cum']
    W = {'一':'周一','二':'周二','三':'周三','四':'周四','五':'周五','六':'周六','日':'周日'}
    suf_map = {'zdf':'%','lb':'','hs':'%','flow':'亿'}
    H = [('首推','股票（评分）'),('行业','所属板块'),('涨幅','当日±%'),('量比','资金关注'),
         ('换手','活跃度%'),('净流入','主力亿'),('评分','V7总分'),('次开%','次日开盘'),('次高%','次日最高'),
         ('次收%','次日收盘'),('判定','✅/❌'),('累计%','V7累加')]
    parts = []
    def w(s): parts.append(s)

    w('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">')
    w(f'<title>{title} · 阿策 🧮</title><style>')
    w('*{box-sizing:border-box;margin:0;padding:0}')
    w('body{font-family:-apple-system,PingFang SC,Microsoft YaHei,sans-serif;background:#f5f6fa;padding:16px;color:#333}')
    w('.sm{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px}')
    w('.sc{background:#fff;border-radius:12px;padding:14px 18px;flex:1;min-width:120px;box-shadow:0 1px 4px rgba(0,0,0,.08);text-align:center}')
    w('.sc .l{font-size:11px;color:#888;margin-bottom:3px}')
    w('.sc .v{font-size:24px;font-weight:700}')
    w('.sc.up .v{color:#e74c3c}.sc.dn .v{color:#27ae60}.sc.neu .v{color:#333}.sc.blue .v{color:#2980b9}')
    w('.sc .s{font-size:10px;color:#999;margin-top:2px}')
    w('.divbox{background:#fff;border-radius:12px;box-shadow:0 1px 4px rgba(0,0,0,.08);margin-bottom:16px;overflow:hidden}')
    w('.divbox .hdr{background:#ffebee;padding:9px 14px;font-size:13px;font-weight:600;border-bottom:1px solid #ffcdd2}')
    w('.divbox .body{display:flex;gap:8px;padding:10px 12px;font-size:11px;align-items:stretch}')
    w('.divbox .col{flex:1;background:#f8f9fc;border-radius:8px;padding:8px 10px}')
    w('.divbox .col .nm{font-weight:600;margin-bottom:4px}')
    w('.divbox .vs{display:flex;align-items:center;color:#999;font-weight:700;font-size:13px;padding:0 4px}')
    w('.divbox .ft{background:#fafafa;border-top:1px solid #eef0f4;padding:6px 14px 10px;font-size:11px;color:#666}')
    w('.w{overflow-x:auto;background:#fff;border-radius:12px;box-shadow:0 1px 4px rgba(0,0,0,.08);max-height:82vh;overflow-y:auto}')
    w('table{border-collapse:collapse;font-size:12px;width:100%;min-width:700px}')
    w('th{background:#f8f9fc;border-bottom:2px solid #dee2e6;border-right:1px solid #eef0f4;padding:7px 6px;text-align:center;font-weight:600;position:sticky;top:0;z-index:2}')
    w('th .sh{font-size:10px;color:#888;font-weight:400;display:block;margin-top:2px}')
    w('td{border:1px solid #eef0f4;padding:5px 6px;text-align:center;vertical-align:middle;white-space:nowrap}')
    w('td.dc{font-weight:600;background:#f8f9fc;position:sticky;left:0;z-index:1;text-align:center;min-width:62px;font-size:12px;border-right:2px solid #dee2e6}')
    w('td.dc .dw{font-size:10px;font-weight:400;color:#666;display:block}')
    w('td.dc.fri{background:#ffecec}td.dc.fri .dw{color:#e74c3c}')
    w('.c-ok{background:#e8f5e9}.c-fl{background:#ffebee}.c-pd{background:#fff8e1}.c-zz{background:#fafafa;color:#bbb}')
    w('.dc .pend-marker{display:block;font-size:9px;color:#e74c3c;border-top:1px dashed #e74c3c;margin-top:2px;padding-top:2px}')
    w('.p-p{color:#e74c3c;font-size:11px}.p-n{color:#27ae60;font-size:11px}')
    w('.badge{display:inline-block;padding:2px 6px;border-radius:4px;margin:4px 0}')
    w('@media(max-width:600px){.sc .v{font-size:18px}body{padding:8px}td,th{padding:4px;font-size:11px}td.dc{min-width:52px;font-size:11px}}')
    w('</style></head><body>')

    ok_count = sum(1 for r in v7 if r.get('status')=='OK')
    nn_count = sum(1 for r in v7 if r.get('_show_no_candidate') and r.get('status')!='待补齐')
    dq_count = sum(1 for r in v7 if r.get('status')=='待补齐')
    wins = stats['wins']; verified = stats['verified']
    close_wins = sum(1 for r in v7 if r.get('code') and r.get('next_close') is not None and r.get('next_close') >= 2.0)

    w('<div class="sm">')
    up_class = 'up' if v7_cum > 0 else 'dn'
    w(f'<div class="sc {up_class}"><div class="l">V7 模拟累计</div><div class="v">{"+" if v7_cum>0 else ""}{v7_cum:.2f}%</div><div class="s">已验证 {verified} 天</div></div>')
    is_wc = '问财' in title
    real_pnl = '0.00' if is_wc else '-849.00'
    w(f'<div class="sc ne"><div class="l">实盘累计</div><div class="v">{real_pnl}</div></div>')
    w(f'<div class="sc blue"><div class="l">交易日 / 有候选</div><div class="v">{len(v7)}</div><div class="s">候选 {ok_count} | 待验 {stats["pd"]} | 无 {nn_count} | 待补 {dq_count}</div></div>')
    close_rate = round(close_wins / verified * 100) if verified else 0
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
        fricls = ' fri' if fri else ''
        pend_markers = ''
        # 分歧标记
        if row['date'] in div_dates:
            pend_markers += '<span class="pend-marker">⚠两线分歧</span>'
        # 问财盘中vs盘后特殊标记
        if is_wencai and row['date'] == '2026-06-25':
            sty = 'color:#e67e22;border-color:#e67e22'
            pend_markers += '<span class="pend-marker" style="'+sty+'">⏱盘中vs盘后</span>'
        w(f'<tr><td class="dc{fricls}">{m}月{d_int}日<span class="dw">{W[wd]}</span>{pend_markers}</td>')

        s = row.get('status','')
        j = row.get('judge','')
        nc_bool = row.get('_show_no_candidate', False) or s == '待补齐'

        # 首推列
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
            if n == chr(8212):
                dsp = chr(8212)
            elif sc:
                dsp = f'{n}<br><span style="font-size:10px;color:#999">{int(sc)}分</span>'
            else:
                dsp = n
            w(f'<td class="{cls}">{dsp}</td>')

        # 行业列
        if s == '待补齐' or nc_bool:
            w('<td class="c-zz">—</td>')
        else:
            sec = row.get('sector','') or ''
            if sec:
                w(f'<td style="font-size:11px">{sec}</td>')
            else:
                w('<td class="c-pd">?</td>')

        # 核心数据列（保持原样显示，不格式化精度）
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

        # 次日数据（2位小数）
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

        # 累计（2位小数）
        rc = row.get('running_cum')
        if rc is not None:
            rc_cls = 'c-ok' if rc > 0 else ('c-fl' if rc < 0 else '')
            w(f'<td class="{rc_cls}">{fmt(rc, "%")}</td>')
        else:
            w('<td class="c-zz">—</td>')

        w('</tr>')

    w('</tbody></table></div></body></html>')
    return ''.join(parts)

if __name__ == '__main__':
    # 不再生成独立HTML，直接重建面板
    _panel_script = os.path.join(os.path.dirname(__file__), 'rebuild_panel.py')
    exec(compile(open(_panel_script).read(), _panel_script, 'exec'))
