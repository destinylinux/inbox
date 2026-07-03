# 同花顺问财金融技能套件

> 基于[同花顺问财 OpenAPI](https://openapi.iwencai.com) 构建的一站式金融技能套件，为 AI 助手提供专业的金融数据查询、行情分析、选股筛选、资讯搜索等十大专业金融功能。

## 功能概览

| 技能 | 功能 | 典型用法 |
|------|------|---------|
| **announcement-search** | 金融公告搜索 | "搜索贵州茅台最近的公告"、"查询宁德时代的业绩预告" |
| **hithink-astock-selector** | A股智能选股 | "帮我选市盈率低于20的股票"、"今天涨停的股票有哪些" |
| **hithink-finance-query** | 财务数据查询 | "查询东方财富的营业收入"、"ROE最高的股票" |
| **hithink-fund-query** | 基金理财查询 | "业绩最好的基金有哪些"、"基金经理是谁" |
| **hithink-futures-selector** | 期货期权筛选 | "黄金期货有哪些"、"原油期货行情" |
| **hithink-macro-query** | 宏观数据查询 | "最近CPI数据"、"LPR利率是多少" |
| **hithink-market-query** | 行情数据查询 | "东方财富最新价格"、"主力资金流向" |
| **hithink-zhishu-query** | 指数数据查询 | "上证指数今天多少点"、"沪深300涨跌幅" |
| **news-search** | 财经资讯搜索 | "人工智能行业有什么新闻"、"新能源政策动态" |
| **report-search** | 研报搜索 | "找一下芯片行业的研报"、"特斯拉的投资评级" |

## 快速开始

### 1. 获取 API Key

首次使用需要注册同花顺i问财平台并获取 API Key：

**点击下方链接获取 API Key：**

👉 **[https://www.iwencai.com/skillhub](https://www.iwencai.com/skillhub)**

流程：
1. 打开链接，登录同花顺账号
2. 点击具体的Skill，查看详情
3. 在"安装方式-Agent用户"中找到 `IWENCAI_API_KEY`，复制

### 2. 配置环境变量

获取到 API Key 后，设置环境变量 `IWENCAI_API_KEY`：

```bash
# Linux / macOS
export IWENCAI_API_KEY=你的API_KEY

# Windows PowerShell
$env:IWENCAI_API_KEY = "你的API_KEY"

# Windows CMD
set IWENCAI_API_KEY=你的API_KEY
```

> 建议将环境变量写入 shell 配置文件（`~/.bashrc`、`~/.zshrc` 等）或系统环境变量中，避免每次重启后需要重新设置。

### 3. 使用 AI 助手调用

配置完成后，直接通过 AI 助手自然语言交互即可使用所有10个技能：

- "查询上证指数今天的表现"
- "帮我找一下贵州茅台最近的分红公告"
- "选出现在市盈率低于15的银行股"
- "最近有哪些利好医药行业的政策新闻"

## 安装到 AI 助手

将 `hithink-wencai-suite` 文件夹复制到以下路径：

```
~/.workbuddy/skills/hithink-wencai-suite/
```

完整路径示例：
- Windows: `C:\Users\你的用户名\.workbuddy\skills\hithink-wencai-suite\`
- macOS/Linux: `~/.workbuddy/skills/hithink-wencai-suite/`

## 目录结构

```
hithink-wencai-suite/
├── SKILL.md                          # 主技能配置文件
├── README.md                         # 本文档
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

## 使用脚本（独立于 AI 助手）

### 简单技能(7个) - 直接使用 scripts/ 目录下的脚本

以下7个技能的脚本可以直接在套件根目录调用：

### A股选股
```bash
python scripts/astock_selector.py "今日涨跌幅大于5%"
python scripts/astock_selector.py "市盈率小于15的银行股"
```

### 财务数据查询
```bash
python scripts/finance_query.py "东方财富营业收入"
python scripts/finance_query.py "ROE最高的股票"
```

### 基金查询
```bash
python scripts/fund_query.py "业绩最好的基金"
python scripts/fund_query.py "基金经理是谁"
```

### 期货筛选
```bash
python scripts/futures_selector.py "黄金期货"
python scripts/futures_selector.py "原油期货行情"
```

### 宏观数据查询
```bash
python scripts/macro_query.py "2024年中国GDP"
python scripts/macro_query.py "最近一期CPI"
```

### 行情查询
```bash
python scripts/market_query.py "东方财富最新价格"
python scripts/market_query.py "主力资金流向"
```

### 指数查询
```bash
python scripts/zhishu_query.py "上证指数涨跌幅"
python scripts/zhishu_query.py "沪深300最新点位"
```

### 复杂技能(3个) - 进入子目录使用

以下3个技能采用模块化设计，需要进入对应的子目录使用：

### 公告搜索
```bash
cd announcement
python __main__.py "贵州茅台 公告"
python __main__.py "业绩预告" --limit 20
```

### 新闻搜索
```bash
cd news
python __main__.py -q "人工智能最新动态"
python __main__.py -q "新能源政策"
```

### 研报搜索
```bash
cd report
python __main__.py -q "芯片行业研究报告"
python __main__.py -q "特斯拉投资评级"
```

## API 信息

| 项目 | 值 |
|------|---|
| API 域名 | `https://openapi.iwencai.com` |
| 认证方式 | Bearer Token，环境变量 `IWENCAI_API_KEY` |
| 请求方法 | POST |
| Content-Type | application/json |

## 常见问题

### Q: 如何获取 API Key？
A: 访问 https://www.iwencai.com/skillhub，登录后点击具体Skill查看详情即可获取。

### Q: 所有技能都使用同一个 API Key 吗？
A: 是的，所有10个子技能共享同一个 `IWENCAI_API_KEY`。

### Q: 查询没有结果怎么办？
A: 可以尝试：
1. 放宽查询条件
2. 使用更通用的关键词
3. 访问同花顺问财 web端查询：https://www.iwencai.com/unifiedwap/chat

### Q: API 调用失败怎么解决？
A: 检查：
1. API Key 是否正确配置
2. 网络连接是否正常
3. 请求频率是否过高

## 数据来源标注

**重要提示**：
- 引用同花顺数据时，必须强调**数据来源于同花顺问财**（https://www.iwencai.com/unifiedwap/chat）
- 如果没有查询到数据，提示用户可以到**同花顺问财 web端**查询

## 安全说明

- 所有数据仅发送至同花顺官方域名 `openapi.iwencai.com`
- API Key 通过环境变量传递，不会在任何文件中明文存储
- 必须遵守同花顺问财 API 服务条款

## 更新日志

### v3.0.0 (2026-05-11)
- 整合10个独立技能为一个统一套件
- 保留所有子技能的完整功能和文档
- 统一 API Key 认证方式
- 提供清晰的索引和使用指引
- **重要更新**: 将10个skill整合为一个套件
  - 7个简单skill保留为独立脚本(在scripts/目录)
  - 3个复杂skill保持模块化结构(announcement/, news/, report/子目录)
  - references/目录包含所有13个文档(10个SKILL.md + 3个api.md)
  - 更新SKILL.md和README.md,清晰说明子目录使用方式

## 致谢

本套件基于同花顺问财团队提供的原始技能包整合打包，保留了所有原始功能和文档。

## 许可

本技能套件仅供学习和个人使用。同花顺问财 API 的使用需遵守同花顺平台的相关服务条款。
