#!/usr/bin/env python3
"""
V7 每日选股流水线（通过 hithink CLI 封装）

此脚本用 hithink CLI 调用替代原 v7_daily_pipeline.py 中的裸 HTTP API 调用。
所有 V7 筛选逻辑、评分、输出格式保持不变。

用法:
  python3 v7_daily_pipeline_hithink.py screen    # 14:40 盘中筛选
  python3 v7_daily_pipeline_hithink.py verify    # 15:05 收盘验证
"""

import json
import os
import subprocess
import sys
import time

WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_ROOT = os.path.join(WORKSPACE, 'daily_data')
CLI_PATH = os.path.join(os.path.dirname(WORKSPACE), 'skills', 'hithink-astock-selector', 'scripts', 'cli.py')


def cli_query(query, page=1, limit=100):
    """通过 hithink CLI 调用问财 API，返回 parsed JSON 或 {'error': ...}"""
    cmd = [
        'python3', CLI_PATH,
        '--query', query,
        '--page', str(page),
        '--limit', str(limit),
        '--timeout', '60'
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90, env={**os.environ})
        if result.returncode != 0:
            stderr = result.stderr.strip()
            if '次数已用完' in stderr:
                return {'error': 'quota_exhausted'}
            return {'error': f'CLI exit {result.returncode}', 'detail': stderr[:200]}
        raw = result.stdout.strip()
        if not raw:
            return {'error': 'empty_response'}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {'error': 'json_parse_failed'}
    except subprocess.TimeoutExpired:
        return {'error': 'timeout'}
    except Exception as e:
        return {'error': str(e)}


def fetch_all_pages(query):
    """翻页获取全量数据 (via hithink CLI)"""
    all_datas = []
    page = 1
    max_pages = 30

    while page <= max_pages:
        result = cli_query(query, page=page)

        if 'error' in result:
            # 重试一次
            time.sleep(iat2)
            result = cli_query(query, page=page)
            if 'error' in result:
                return None, result['error']

        datas = result.get('datas', result.get('data', []))
        if not datas:
            break

        all_datas.extend(datas)

        total_pages = result.get('total_pages', result.get('totalPage', 0))
        if page >= total_pages:
            break

        page += 1
        time.sleep(0.3)

    return all_datas, None


# ============================================================
# Monkey-patch the original v7_daily_pipeline module
# Replace its read_token / api_call / fetch_all_pages
# ============================================================

if __name__ == '__main__':
    import v7_daily_pipeline as pipe

    # Replace the API functions
    pipe.read_token = lambda: None  # no token needed
    pipe.api_call = lambda *args, **kwargs: cli_query(kwargs.get('query', args[0] if args else ''))
    pipe.fetch_all_pages = fetch_all_pages

    # Extract mode and date from CLI args
    if len(sys.argv) < 2:
        print("用法: python3 v7_daily_pipeline_hithink.py [screen|verify] [YYYYMMDD]")
        sys.exit(1)

    mode = sys.argv[1]
    date_str = sys.argv[2] if len(sys.argv) > 2 else None

    if mode == 'screen':
        pipe.run_screen(date_str)
    elif mode == 'verify':
        pipe.run_verify(date_str)
    else:
        print(f"未知模式: {mode}")
