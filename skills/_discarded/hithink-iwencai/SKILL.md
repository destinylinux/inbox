---
name: hithink-wencai-suite
description: >
  同花顺问财金融技能套件，包含 10 个专业金融子技能：
  1. announcement-search - 金融公告搜索（定期报告、分红派息、回购增持、资产重组等）
  2. hithink-astock-selector - A股智能选股（行情指标、技术形态、财务指标、行业概念筛选）
  3. hithink-finance-query - 财务数据查询（营收、净利润、ROE、负债率、现金流等）
  4. hithink-fund-query - 基金理财查询（业绩、持仓、风险、评级、基金经理等）
  5. hithink-futures-selector - 期货期权筛选（行情、波动率、产销、会员持仓等）
  6. hithink-macro-query - 宏观数据查询（GDP、CPI、PPI、利率、汇率、社融等）
  7. hithink-market-query - 行情数据查询（股票、ETF、指数行情、资金流向、技术指标等）
  8. hithink-zhishu-query - 指数数据查询（上证指数、沪深300、创业板指、恒生指数、纳斯达克等）
  9. news-search - 财经资讯搜索（新闻、公告、政策动态、行业革新等）
  10. report-search - 研报搜索（投研机构报告、投资评级、目标价等）
  触发词：同花顺、问财、金融数据、行情查询、财务指标、选股、自选股、基金、期货、宏观数据、指数、公告、新闻、研报、财经资讯。
author: 同花顺问财团队
version: 3.0.0
required_env_vars:
  - IWENCAI_API_KEY
credentials:
  - type: api_key
    name: IWENCAI_API_KEY
    description: 从同花顺i问财SkillHub获取的 API Key，首次使用需注册获取
    setup_url: "https://www.iwencai.com/skillhub"
---

# 同花顺问财金融技能套件

本技能套件基于**同花顺问财 OpenAPI** 构建，提供一站式金融数据查询、行情分析、选股筛选、资讯搜索等十大专业金融功能。所有子技能通过统一的 `IWENCAI_API_KEY` 认证，支持自然语言交互。

## 包含的子技能

| # | 技能名称 | 功能说明 | 详细文档 |
|---|---------|---------|---------|
| 1 | **announcement-search** | 金融公告搜索：定期财务报告、分红派息、回购增持、资产重组、重大合同、业绩预告等 | `references/announcement-search.md` |
| 2 | **hithink-astock-selector** | A股智能选股：行情指标、技术形态、财务指标、行业概念等多条件组合筛选 | `references/hithink-astock-selector.md` |
| 3 | **hithink-finance-query** | 财务数据查询：营收、净利润、ROE、负债率、现金流、毛利率、净利率等 | `references/hithink-finance-query.md` |
| 4 | **hithink-fund-query** | 基金理财查询：业绩分析、持仓明细、风险评级、基金经理、基金公司等 | `references/hithink-fund-query.md` |
| 5 | **hithink-futures-selector** | 期货期权筛选：行情、波动率、产销数据、会员持仓、行权等多条件筛选 | `references/hithink-futures-selector.md` |
| 6 | **hithink-macro-query** | 宏观数据查询：GDP、CPI、PPI、利率、汇率、社融、M2、PMI等 | `references/hithink-macro-query.md` |
| 7 | **hithink-market-query** | 行情数据查询：股票/ETF/指数实时行情、资金流向、技术指标等 | `references/hithink-market-query.md` |
| 8 | **hithink-zhishu-query** | 指数数据查询：上证指数、沪深300、创业板指、恒生指数、纳斯达克等 | `references/hithink-zhishu-query.md` |
| 9 | **news-search** | 财经资讯搜索：财经新闻、政策动态、行业革新、企业业务进展等 | `references/news-search.md` |
| 10 | **report-search** | 研报搜索：投研机构报告、投资评级、目标价、分析逻辑等 | `references/report-search.md` |

## 首次使用 - 获取 API Key

**所有子技能都需要 `IWENCAI_API_KEY` 环境变量才能使用。** 如果用户尚未配置，按以下步骤引导：

### 步骤 1：获取 API Key

在浏览器内打开同花顺i问财SkillHub页面：
**https://www.iwencai.com/skillhub**

### 步骤 2：登录

### 步骤 3：获取 API Key

点击具体的Skill，打开弹窗查看详情，在"安装方式-Agent用户"找到 `IWENCAI_API_KEY` 这一段，复制

### 步骤 4：配置环境变量

获取到 API Key 后，直接复制指引文字发送给AI助手，或手动设置环境变量：

**macOS / Linux (bash/zsh):**
```bash
export IWENCAI_API_KEY="your_api_key_here"
```

**Windows (PowerShell):**
```powershell
$env:IWENCAI_API_KEY="your_api_key_here"
```

**Windows (CMD):**
```cmd
set IWENCAI_API_KEY=your_api_key_here
```

### 验证配置

配置完成后，尝试调用任意子技能接口验证 Key 是否有效。

## 使用方式

根据用户请求自动匹配对应子技能，按需加载 `references/` 下的详细文档：

- **查公告/公告搜索** → 加载 `references/announcement-search.md`，调用公告搜索接口
- **A股选股/筛选股票** → 加载 `references/hithink-astock-selector.md`，调用选股接口
- **财务数据/营收利润** → 加载 `references/hithink-finance-query.md`，调用财务数据接口
- **基金查询/基金经理** → 加载 `references/hithink-fund-query.md`，调用基金查询接口
- **期货期权/期货筛选** → 加载 `references/hithink-futures-selector.md`，调用期货筛选接口
- **宏观数据/GDP CPI** → 加载 `references/hithink-macro-query.md`，调用宏观数据接口
- **行情查询/资金流向** → 加载 `references/hithink-market-query.md`，调用行情数据接口
- **指数查询/上证指数** → 加载 `references/hithink-zhishu-query.md`，调用指数数据接口
- **新闻搜索/资讯查询** → 加载 `references/news-search.md`，调用资讯搜索接口
- **研报搜索/投资评级** → 加载 `references/report-search.md`，调用研报搜索接口

## API 基础信息

### 通用接口信息

- **Base URL**: `https://openapi.iwencai.com`
- **认证方式**: Bearer Token，从环境变量 `IWENCAI_API_KEY` 读取
- **请求方法**: POST
- **Content-Type**: `application/json`

### 通用请求头（Claw Headers）

所有发往问财 OpenAPI 网关的请求必须包含以下 Header：

| Header | 取值说明 |
|--------|----------|
| `Authorization` | `Bearer <API Key>`，API Key 仅从环境变量 `IWENCAI_API_KEY` 读取 |
| `Content-Type` | `application/json` |
| `X-Claw-Call-Type` | `normal`（正常请求）或 `retry`（失败后的重试） |
| `X-Claw-Skill-Id` | 技能标识（根据调用的子技能而定） |
| `X-Claw-Skill-Version` | 当前技能版本号（根据调用的子技能而定） |
| `X-Claw-Plugin-Id` | `none` |
| `X-Claw-Plugin-Version` | `none` |
| `X-Claw-Trace-Id` | **每次请求必须新生成的 64 字符全局唯一追踪 ID** |

### 通用错误处理

- **密钥缺失**：提示用户配置 `IWENCAI_API_KEY` 环境变量
- **无数据返回**：引导用户访问同花顺问财 web端（https://www.iwencai.com/unifiedwap/chat）
- **最多重试 2 次**：逐步放宽条件（重试时 `X-Claw-Call-Type` 改为 `retry`）

## 数据来源标注

**重要提示**：
- 引用同花顺数据时，必须强调**数据来源于同花顺问财**（https://www.iwencai.com/unifiedwap/chat）
- 如果没有查询到数据，提示用户可以到**同花顺问财 web端**查询

## 典型使用场景

| 用户问题 | 应调用的子技能 |
|---------|--------------|
| "搜索贵州茅台最近的公告" | announcement-search |
| "帮我选市盈率低于20的A股" | hithink-astock-selector |
| "查询宁德时代的财务数据" | hithink-finance-query |
| "哪只基金业绩最好" | hithink-fund-query |
| "黄金期货有哪些" | hithink-futures-selector |
| "最近CPI数据怎么样" | hithink-macro-query |
| "东方财富最新价格" | hithink-market-query |
| "上证指数今天多少点" | hithink-zhishu-query |
| "人工智能行业有什么新闻" | news-search |
| "找一下芯片行业的研报" | report-search |

## CLI 使用方式

### 简单技能(7个) - 直接使用 scripts/ 目录下的脚本

以下7个技能的脚本可以直接在套件根目录调用：

| 技能 | 脚本路径 | 使用示例 |
|------|---------|---------|
| A股选股 | `scripts/astock_selector.py` | `python3 scripts/astock_selector.py -q "市盈率低于10的股票"` |
| 财务数据 | `scripts/finance_query.py` | `python3 scripts/finance_query.py -q "东方财富营业收入"` |
| 基金查询 | `scripts/fund_query.py` | `python3 scripts/fund_query.py -q "业绩最好的基金"` |
| 期货筛选 | `scripts/futures_selector.py` | `python3 scripts/futures_selector.py -q "黄金期货"` |
| 宏观数据 | `scripts/macro_query.py` | `python3 scripts/macro_query.py -q "最近CPI数据"` |
| 行情查询 | `scripts/market_query.py` | `python3 scripts/market_query.py -q "东方财富最新价格"` |
| 指数查询 | `scripts/zhishu_query.py` | `python3 scripts/zhishu_query.py -q "上证指数涨跌幅"` |

### 复杂技能(3个) - 进入子目录使用

以下3个技能采用模块化设计,需要进入对应的子目录使用:

| 技能 | 子目录 | 使用示例 |
|------|--------|---------|
| 公告搜索 | `announcement/` | `cd announcement && python3 __main__.py "贵州茅台 公告"` |
| 新闻搜索 | `news/` | `cd news && python3 __main__.py -q "人工智能"` |
| 研报搜索 | `report/` | `cd report && python3 __main__.py -q "芯片行业研报"` |

### 环境变量配置

无论使用哪个技能,都需要先配置环境变量:

```bash
# Linux / macOS
export IWENCAI_API_KEY="your-api-key"

# Windows PowerShell
$env:IWENCAI_API_KEY = "your-api-key"
```

## 目录结构

```
hithink-wencai-suite/
├── SKILL.md                          # 主技能配置文件（本文档）
├── README.md                         # 使用说明文档
├── LICENSE.txt                       # 许可证文件
├── _meta.json                        # 元数据文件
│
├── scripts/                          # 7个简单技能的独立脚本
│   ├── astock_selector.py            # A股选股
│   ├── finance_query.py              # 财务数据
│   ├── fund_query.py                 # 基金查询
│   ├── futures_selector.py           # 期货筛选
│   ├── macro_query.py                # 宏观数据
│   ├── market_query.py               # 行情查询
│   └── zhishu_query.py               # 指数查询
│
├── announcement/                      # 公告搜索技能(完整模块化结构)
│   ├── __main__.py                   # CLI入口点
│   ├── announcement_search.py        # 主程序
│   ├── config.py                     # 配置模块
│   ├── utils.py                      # 工具模块
│   ├── SKILL.md                      # 技能配置(完整文档)
│   ├── README.md                     # 使用说明
│   └── ... (其他依赖文件)
│
├── news/                              # 新闻搜索技能(完整模块化结构)
│   ├── __main__.py                   # CLI入口点
│   ├── news_search.py                # 主程序(30KB+)
│   ├── config.py                     # 配置模块
│   ├── SKILL.md                      # 技能配置(完整文档)
│   ├── README.md                     # 使用说明
│   └── ... (其他依赖文件)
│
├── report/                            # 研报搜索技能(完整模块化结构)
│   ├── __main__.py                   # CLI入口点
│   ├── cli.py                        # CLI模块
│   ├── api_client.py                 # API客户端
│   ├── data_processor.py             # 数据处理
│   ├── config.py                     # 配置模块
│   ├── SKILL.md                      # 技能配置(完整文档)
│   ├── README.md                     # 使用说明
│   └── ... (其他依赖文件)
│
└── references/                        # 子技能详细参考文档(13个)
    ├── announcement-search.md         # 公告搜索完整文档
    ├── announcement-api.md            # 公告API接口文档
    ├── hithink-astock-selector.md     # A股选股完整文档
    ├── hithink-finance-query.md       # 财务数据完整文档
    ├── hithink-fund-query.md          # 基金查询完整文档
    ├── hithink-futures-selector.md    # 期货筛选完整文档
    ├── hithink-macro-query.md         # 宏观数据完整文档
    ├── hithink-market-query.md        # 行情查询完整文档
    ├── hithink-zhishu-query.md        # 指数查询完整文档
    ├── news-search.md                 # 新闻搜索完整文档
    ├── news-api.md                    # 新闻API接口文档
    ├── report-search.md               # 研报搜索完整文档
    └── report-api.md                  # 研报API接口文档
```

## 安全说明

- 所有数据仅发送至同花顺官方域名 `openapi.iwencai.com`
- API Key 通过环境变量传递,不会在任何文件中明文存储
- 必须遵守同花顺问财 API 服务条款
