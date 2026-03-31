# 上币评估系统 - 完整需求文档

> 基于多维度数据的代币上币评估平台

---

## 目录

1. [项目概述](#1-项目概述)
2. [核心功能](#2-核心功能)
3. [数据源与API](#3-数据源与api)
4. [评分体系](#4-评分体系)
5. [技术架构](#5-技术架构)
6. [界面设计](#6-界面设计)
7. [数据采集模块](#7-数据采集模块)
8. [分析引擎](#8-分析引擎)
9. [报告生成](#9-报告生成)
10. [开发路线图](#10-开发路线图)

---

## 1. 项目概述

### 1.1 项目背景

交易所上币决策需要多维度综合评估，目前缺乏自动化工具整合链上数据、社区舆情、竞品对比等信息。本系统通过自动化数据采集收集多维度公开数据，生成结构化评估报告，辅助决策。

### 1.2 核心价值

| 价值点 | 说明 |
|--------|------|
| **效率提升** | 自动化数据收集，节省调研时间 |
| **数据全面** | 多维度综合评估，减少信息盲区 |
| **客观量化** | 结构化评分体系，辅助决策 |
| **风险预警** | 识别潜在风险信号 |

### 1.3 目标用户

- 交易所上币团队
- VC 投资尽调团队
- 研究分析师

---

## 2. 核心功能

### 2.1 代币搜索与识别

| 功能 | 说明 | 约束 |
|------|------|------|
| 代币名称搜索 | 输入代币名称（如 BTC、ETH、SOL） | 字符限制 30 位 |
| 合约地址搜索 | 输入合约地址自动识别链 | 支持 0x、0x... 格式 |
| 多链支持 | 识别主流公链地址 | 见[支持链列表](#22-支持的区块链) |
| 自动匹配 | 支持模糊搜索，返回匹配列表 | 最多返回 10 个候选 |

### 2.2 支持的区块链

| 链 | 前缀 | 示例 |
|----|------|------|
| Ethereum | 0x | 0x... |
| BSC | 0x | 0x... |
| Polygon | 0x | 0x... |
| Solana | 无 | 58f... |
| Arbitrum | 0x | 0x... |
| Optimism | 0x | 0x... |
| Avalanche | 0x | 0x... |
| Tron | 无 | TSB... |

### 2.3 多维度评估模块

```
┌─────────────────────────────────────────────────────────────┐
│                    上币评估系统                              │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐  │
│  │  1. 链上数据层                                        │  │
│  │  ├─ 市值数据 (CoinGecko/CoinMarketCap)                │  │
│  │  ├─ 交易量统计                                        │  │
│  │  ├─ 持币分布 (大户持仓比例)                            │  │
│  │  ├─ TVL 趋势 (DeFiLlama)                              │  │
│  │  └─ 合约审计报告 (Certik/Slowmist)                    │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  2. 社区与舆情层                                      │  │
│  │  ├─ Twitter/X 提及量 & 情绪分析                      │  │
│  │  ├─ Reddit 讨论热度                                  │  │
│  │  ├─ 官方文档完整性评估                                │  │
│  │  └─ 社交媒体活跃度 (Telegram/Discord 人数)           │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  3. 竞品对比层                                        │  │
│  │  ├─ 同赛道项目识别                                    │  │
│  │  ├─ 交易所上线情况 (Binance/OKX/Bybit)               │  │
│  │  ├─ 差异化优势分析                                    │  │
│  │  └─ 市场份额对比                                      │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  4. 风险评估层 (AI 分析)                             │  │
│  │  ├─ 团队背景与历史记录                                │  │
│  │  ├─ 代码开源情况 (GitHub/代码审计)                   │  │
│  │  ├─ 监管风险信号                                      │  │
│  │  └─ 合约漏洞扫描结果                                  │  │
│  └─────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    评分引擎 & 报告生成                      │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  ├─ 各维度加权评分                                    │  │
│  │  ├─ 雷达图生成                                        │  │
│ 1│  ├─ 风险警示汇总                                      │  │
│  │  └─ 推荐结论 (强烈推荐/建议观望/不建议)                │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 数据源与API

### 3.1 市场数据 API

| 数据源 | API | 数据内容 | 免费额度 |
|--------|-----|----------|----------|
| **CoinGecko** | `/coins/{id}` | 市值、24h交易量、价格 | 10-50 req/min |
| **CoinMarketCap** | `/v2/cryptocurrency/quotes/latest` | 市值、排名 | 免费版有限 |
| **DeFiLlama** | `/protocol/{slug}` | TVL、链分布 | 免费 |
| **TokenInsights** | 自研聚合 | 持币分布、大户持仓 | - |

### 3.2 审计报告 API

| 数据源 | 数据内容 | 获取方式 |
|--------|----------|----------|
| **Certik** | 审计报告、安全评分 | API / 爬取 |
| **Slowmist** | 审计报告、风险评估 | 爬取 |
| **PeckShield** | 审计报告 | 爬取 |
| **OpenZeppelin** | 标准合约库 | - |

### 3.3 社交媒体 API

| 平台 | API | 数据内容 |
|------|-----|----------|
| **Twitter/X** | Search API | 提及量、转发、点赞、情绪分析 |
| **Reddit** | Reddit API | 帖子数、评论数、热度 |
| **Telegram** | TGFun API / 爬取 | 群组人数、活跃度 |
| **Discord** | Discord API | 服务器人数、频道活跃度 |

### 3.4 代码与团队数据

| 数据源 | 获取方式 | 数据内容 |
|--------|----------|----------|
| **GitHub** | GitHub API | 代码库、贡献者、最近提交 |
| **GitLab** | GitLab API | 代码库、活跃度 |
| **Etherscan** | API / 爬取 | 合约源码、验证状态 |
| **LinkedIn** | 爬取 | 团队成员背景 |

---

## 4. 评分体系

### 4.1 维度权重分配

| 维度 | 权重 | 说明 |
|------|------|------|
| 市场规模 | 25% | 市值、交易量、流动性 |
| 社区活跃度 | 20% | 社交媒体活跃度、用户基数 |
| 技术实力 | 20% | 代码质量、审计报告、开发活跃度 |
| 团队背景 | 15% | 团队经验、过往项目 |
| 竞争优势 | 10% | 赛道地位、差异化 |
| 风险控制 | 10% | 监管风险、合约风险 |

### 4.2 各维度评分细则

#### 4.2.1 市场规模 (25分)

| 指标 | 评分规则 | 分值 |
|------|----------|------|
| 市值排名 | Top 10: 10分<br>Top 100: 8分<br>Top 500: 6分<br>其他: 4分 | 10 |
| 24h 交易量 | >$1B: 5分<br>>$100M: 4分<br>>$10M: 3分<br><$10M: 2分 | 5 |
| 流动性深度 | 做市商数量、订单薄深度 | 5 |
| 价格波动率 | 波动率 < 50%: 5分<br>波动率 50-100%: 3分<br>>100%: 1分 | 5 |

#### 4.2.2 社区活跃度 (20分)

| 指标 | 评分规则 | 分值 |
|------|----------|------|
| Twitter 关注数 | >100k: 5分<br>>50k: 4分<br>>10k: 3分 | 5 |
| 24h 提及量 | >1000: 5分<br>>500: 4分<br>>100: 3分 | 5 |
| 情绪分析 | 正面 > 60%: 5分<br>正面 40-60%: 3分<br><40%: 1分 | 5 |
| Telegram/Discord 人数 | >50k: 5分<br>>10k: 4分<br>>1k: 3分 | 5 |

#### 4.2.3 技术实力 (20分)

| 指标 | 评分规则 | 分值 |
|------|----------|------|
| 代码开源 | GitHub star >1000: 5分<br>>100: 3分<br>私有: 0分 | 5 |
| 审计报告 | Top3 审计机构: 5分<br>其他审计: 3分<br>无审计: 0分 | 5 |
| TVL 规模 | >$100M: 5分<br>>$10M: 3分<br><$10M: 1分 | 5 |
| 开发活跃度 | 近30天提交数、Issue 处理速度 | 5 |

#### 4.2.4 团队背景 (15分)

| 指标 | 评分规则 | 分值 |
|------|----------|------|
| 团队知名度 | 有知名机构背景: 5分<br>经验丰富: 3分<br>匿名: 1分 | 5 |
| 过往项目 | 成功项目经验: 5分<br>无记录: 2分<br>负面记录: 0分 | 5 |
| 团队稳定性 | 成员流失率、联合创始人数量 | 5 |

#### 4.2.5 竞争优势 (10分)

| 指标 | 评分规则 | 分值 |
|------|----------|------|
| 赛道地位 | 赛道 Top3: 5分<br>中游: 3分<br>新入局: 1分 | 5 |
| 差异化 | 有独特创新: 5分<br>同质化: 2分 | 5 |

#### 4.2.6 风险控制 (10分)

| 指标 | 评分规则 | 分值 |
|------|----------|------|
| 监管风险 | 无明显风险: 5分<br>潜在风险: 2分<br>高风险: 0分 | 5 |
| 合约风险 | 无已知漏洞: 5分<br>有历史漏洞: 2分<br>高危: 0分 | 5 |

### 4.3 综合评分计算

```
总分 = 市场规模 × 25% + 社区活跃度 × 20% + 技术实力 × 20% +
       团队背景 × 15% + 竞争优势 × 10% + 风险控制 × 10%
```

### 4.4 推荐结论判定

| 总分范围 | 推荐等级 | 说明 |
|----------|----------|------|
| ≥ 80分 | 🟢 **强烈推荐** | 各维度表现优秀，风险可控 |
| 60-79分 | 🟡 **建议观望** | 整体尚可，需关注风险点 |
| < 60分 | 🔴 **不建议** | 多维度存在明显问题 |

### 4.5 特殊情况处理

| 情况 | 处理 |
|------|------|
| 无审计报告 | 技术评分扣 5 分，并在报告中标记高风险 |
| 匿名团队 | 团队评分不超过 3 分 |
| 涉嫌拉盘 | 直接判定为"不建议" |
| 监管警告 | 直接判定为"不建议" |

---

## 5. 技术架构

### 5.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端应用                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  Search  │  │  Report  │  │ History  │  │  Radar   │       │
│  │  Input   │  │  View    │  │  Manage  │  │  Chart   │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
└───────┼─────────────┼─────────────┼─────────────┼──────────────┘
        │             │             │             │
        ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API 网关 (Next.js API)                    │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  /api/assess       - 触发评估                            │  │
│  │  /api/search       - 代币搜索                            │  │
│  │  /api/report/{id}  - 获取报告                            │  │
│  │  /api/history      - 历史记录                            │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   数据采集器     │  │   分析引擎       │  │   报告生成器     │
│  ┌────────────┐ │  │  ┌────────────┐ │  │  ┌────────────┐ │
│  │ 市场数据   │ │  │  │ 评分计算   │ │  │  │ PDF 生成   │ │
│  │ 社交舆情   │ │  │  │ AI 分析    │ │  │  │ 图表生成   │ │
│  │ 审计报告   │ │  │  │ 风险评估   │ │  │  │ 模板渲染   │ │
│  │ 代码分析   │ │  │  └────────────┘ │  │  └────────────┘ │
│  └────────────┘ │  └──────────────────┘  └──────────────────┘
└──────────────────┘
        │
        ├─────▶ CoinGecko / CoinMarketCap / DeFiLlama
        ├─────▶ Twitter / Reddit / Telegram API
        ├─────▶ Certik / Slowmist / GitHub
        ├─────▶ Claude API (AI 分析)
        └─────▶ Database (PostgreSQL + Redis)
```

### 5.2 项目结构

```
token-listing-assessment/
├── frontend/                    # Next.js 前端
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx         # 首页/搜索
│   │   │   ├── report/[id]/     # 报告详情
│   │   │   └── history/         # 历史记录
│   │   ├── components/
│   │   │   ├── SearchInput/
│   │   │   ├── RadarChart/
│   │   │   ├── ReportCard/
│   │   │   └── RiskAlert/
│   │   ├── hooks/
│   │   └── lib/
│   └── package.json
│
├── backend/                     # Python / Node.js 后端
│   ├── collectors/              # 数据采集器
│   │   ├── market_data.py       # 市场数据
│   │   ├── social_sentiment.py  # 社交舆情
│   │   ├── audit_reports.py     # 审计报告
│   │   └── code_analysis.py     # 代码分析
│   ├── analyzers/               # 分析引擎
│   │   ├── scoring_engine.py    # 评分引擎
│   │   ├── risk_assessment.py   # 风险评估
│   │   └── ai_analyzer.py       # AI 分析 (Claude)
│   ├── generators/              # 报告生成器
│   │   ├── report_builder.py    # 报告构建
│   │   ├── pdf_export.py        # PDF 导出
│   │   └── chart_generator.py   # 图表生成
│   ├── api/
│   │   └── routes/
│   ├── models/
│   ├── utils/
│   └── requirements.txt
│
├── database/                   # 数据库
│   ├── migrations/
│   ├── schema.sql
│   └── seed.sql
│
├── docs/                       # 文档
├── scripts/                    # 脚本
├── .env.example
├── docker-compose.yml
└── README.md
```

### 5.3 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | Next.js 14, TypeScript, TailwindCSS, Recharts |
| **后端** | Python / Node.js, FastAPI / Express |
| **数据库** | PostgreSQL (主), Redis (缓存) |
| **队列** | Celery / Bull (异步任务) |
| **爬虫** | Scrapy, Playwright (JS 渲染) |
| **AI 分析** | Claude API |
| **导出** | ReportLab / jsPDF |

---

## 6. 界面设计

### 6.1 搜索页

```
┌─────────────────────────────────────────────────────────────┐
│                    上币评估系统                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  🔍 输入代币名称或合约地址 (最多30字符)              │   │
│  │  ┌────────────────────────────────────────────────┐ │   │
│  │  │ [例如: Bitcoin / 0x... / SOL]               │ │   │
│  │  └────────────────────────────────────────────────┘ │   │
│  │                                                     │   │
│  │  🔍 高级搜索 (可选)                                 │   │
│  │  ┌─────────┐ ┌─────────┐                           │   │
│  │  │ 选择链   │ │ 分类筛选 │                           │   │
│  │  └─────────┘ └─────────┘                           │   │
│  │                                                     │   │
│  │  [开始评估]                                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  最近评估:                                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Bitcoin (BTC)          ━━━━━━━━ 85分  [查看报告]  │   │
│  │  评估时间: 2026-03-28 14:30                         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 报告页

```
┌─────────────────────────────────────────────────────────────┐
│  🔙 Bitcoin (BTC) 上币评估报告          📄 导出 PDF         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐  ┌────────────────────────────────┐  │
│  │  综合评分: 85    │  │  推荐结论: 🟢 强烈推荐        │  │
│  │  ┌────────────┐  │  │  理由: 市场规模大、社区活跃、  │  │
│  │  │  雷达图    │  │  │        技术成熟、风险可控      │  │
│  │  │  [图表]    │  │  └────────────────────────────────┘  │
│  │  └────────────┘  │                                    │  │
│  └──────────────────┘                                    │  │
│                                                             │
│  ───────────────────────────────────────────────────────  │
│                                                             │
│  📊 市场规模 (25/25)                                       │
│  ├─ 市值排名: #1                           ✅ 优秀        │
│  ├─ 24h 交易量: $28.5B                   ✅ 优秀        │
│  ├─ 流动性深度: 极高                      ✅ 优秀        │
│  └─ 价格波动率: 3.2%                       ✅ 稳定        │
│                                                             │
│  ───────────────────────────────────────────────────────  │
│                                                             │
│  👥 社区活跃度 (18/20)                                     │
│  ├─ Twitter: 8.2M 关注 | 24h提及: 12.5k  ✅ 优秀        │
│  ├─ 情绪分析: 正面 72%                     ✅ 优秀        │
│  ├─ Telegram: 52k 会员                     ✅ 优秀        │
│  └─ Discord: 350k 会员                    ✅ 优秀        │
│                                                             │
│  ───────────────────────────────────────────────────────  │
│                                                             │
│  ⚙️ 技术实力 (18/20)                                        │
│  ├─ 代码开源: GitHub 78k ⭐               ✅ 优秀        │
│  ├─ 审计报告: 多次审计                     ✅ 优秀        │
│  ├─ TVL: 不适用 (非 DeFi)                  ⚪ N/A        │
│  └─ 开发活跃度: 极高                      ✅ 优秀        │
│                                                             │
│  ───────────────────────────────────────────────────────  │
│                                                             │
│  👨‍💼 团队背景 (12/15)                                       │
│  ├─ 团队知名度: Satoshi Nakamoto (匿名)    ⚠️ 未知       │
│  ├─ 过往项目: 无记录                      ⚠️ 未知       │
│  └─ 团队稳定性: -                          ⚪ N/A        │
│                                                             │
│  ───────────────────────────────────────────────────────  │
│                                                             │
│  🏆 竞争优势 (10/10)                                        │
│  ├─ 赛道地位: Layer 1 创始者               ✅ 领先       │
│  └─ 差异化: 价值存储开创者                  ✅ 独特       │
│                                                             │
│  ───────────────────────────────────────────────────────  │
│                                                             │
│  ⚠️ 风险控制 (8/10)                                         │
│  ├─ 监管风险: 部分国家监管                ⚠️ 关注       │
│  └─ 合约风险: 无已知漏洞                   ✅ 低风险     │
│                                                             │
│  ───────────────────────────────────────────────────────  │
│                                                             │
│  🔴 核心风险警示                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  ⚠️ 匿名团队，背景未知                                  │   │
│  │  ⚠️ 监管政策可能变化                                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ✅ 推荐上线时机与条件                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  • 建议立即上线                                        │   │
│  │  • 上线后持续关注监管动态                               │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 6.3 历史记录页

```
┌─────────────────────────────────────────────────────────────┐
│  📜 评估历史记录                                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  筛选: [全部时间▼] [推荐等级▼] 排序: [评估时间▼]            │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Bitcoin (BTC)          ━━━━━━━━ 85分  [查看] [删除] │   │
│  │  推荐结论: 🟢 强烈推荐 | 评估时间: 2026-03-28 14:30  │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  PepeToken (PEPE)        ━━━━ 45分    [查看] [删除] │   │
│  │  推荐结论: 🔴 不建议     | 评估时间: 2026-03-28 13:15  │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Uniswap (UNI)          ━━━━━━━━ 78分  [查看] [删除] │   │
│  │  推荐结论: 🟡 建议观望   | 评估时间: 2026-03-28 12:00  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [加载更多]                                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. 数据采集模块

### 7.1 市场数据采集器

```python
# collectors/market_data.py
class MarketDataCollector:
    """采集市场数据"""

    def collect_coingecko(self, token_id: str) -> Dict:
        """从 CoinGecko 获取数据"""
        # 市值、交易量、价格、排名等

    def collect_coinsniper(self, token_id: str) -> Dict:
        """从 CoinSniper 获取社区投票数据"""

    def collect_defillama(self, token_id: str) -> Dict:
        """从 DeFiLlama 获取 TVL 数据"""

    def get_holding_distribution(self, chain: str, contract: str) -> Dict:
        """获取持币分布（大户持仓比例）"""
```

### 7.2 社交舆情采集器

```python
# collectors/social_sentiment.py
class SocialSentimentCollector:
    """采集社交舆情数据"""

    def collect_twitter(self, token_name: str) -> Dict:
        """
        从 Twitter/X 获取
        - 关注数
        - 24h 提及量
        - 搜索推文进行情绪分析
        """

    def collect_reddit(self, token_name: str) -> Dict:
        """从 Reddit 获取讨论热度"""

    def collect_telegram(self, group_url: str) -> Dict:
        """从 Telegram 获取群组人数和活跃度"""

    def analyze_sentiment(self, text: str) -> float:
        """情绪分析 (正面/负面/中性概率)"""
        # 使用 NLP 模型或调用 API
```

### 7.3 审计报告采集器

```python
# collectors/audit_reports.py
class AuditReportCollector:
    """采集审计报告数据"""

    def search_certik(self, project_name: str) -> List[Dict]:
        """搜索 Certik 审计报告"""

    def search_slowmist(self, project_name: str) -> List[Dict]:
        """搜索 Slowmist 审计报告"""

    def get_audit_summary(self, reports: List[Dict]) -> Dict:
        """汇总审计报告摘要"""
        return {
            "total_reports": len(reports),
            "top_firms": [...],
            "overall_score": 85,
            "high_risk_issues": 0,
        }
```

### 7.4 代码分析器

```python
# collectors/code_analysis.py
class CodeAnalyzer:
    """代码与项目分析"""

    def analyze_github(self, repo_url: str) -> Dict:
        """分析 GitHub 仓库"""
        # Stars、Forks、贡献者、最近提交

    def check_contract_source(self, chain: str, contract: str) -> Dict:
        """检查合约源码是否验证"""
        # Etherscan / Solscan / BscScan

    def scan_vulnerabilities(self, contract: str) -> List[Dict]:
        """扫描已知漏洞"""
        # 检查常见漏洞模式
```

---

## 8. 分析引擎

### 8.1 评分引擎

```python
# analyzers/scoring_engine.py
class ScoringEngine:
    """综合评分引擎"""

    def calculate_market_score(self, data: Dict) -> int:
        """计算市场规模得分"""
        score = 0
        score += self._score_market_cap(data["market_cap"])
        score += self._score_volume(data["volume_24h"])
        score += self._score_liquidity(data["liquidity"])
        score += self._score_volatility(data["volatility"])
        return min(score, 25)

    def calculate_social_score(self, data: Dict) -> int:
        """计算社区活跃度得分"""
        score = 0
        score += self._score_twitter(data["twitter"])
        score += self._score_telegram(data["telegram"])
        score += self._score_sentiment(data["sentiment"])
        return min(score, 20)

    def calculate_total_score(self, scores: Dict) -> int:
        """计算综合总分"""
        return (
            scores["market"] * 0.25 +
            scores["social"] * 0.20 +
            scores["tech"] * 0.20 +
            scores["team"] * 0.15 +
            scores["competitive"] * 0.10 +
            scores["risk"] * 0.10
        )
```

### 8.2 AI 分析模块

```python
# analyzers/ai_analyzer.py
class AIAnalyzer:
    """使用 Claude API 进行深度分析"""

    def analyze_team(self, project_data: Dict) -> Dict:
        """
        AI 分析团队背景
        - 搜索公开信息
        - 评估可信度
        - 识别潜在风险
        """
        prompt = f"""
        请分析以下代币项目的团队背景，并评估风险：
        项目名称: {project_data['name']}
        团队信息: {project_data['team_info']}
        ...

        请返回:
        1. 团队可信度评分 (0-10)
        2. 潜在风险点
        3. 推荐意见
        """

    def analyze_regulatory_risk(self, token_data: Dict) -> Dict:
        """分析监管风险"""
        # 识别代币类型（证券/实用型）
        # 检查合规声明
        # 评估监管风险

    def analyze_competitive_advantage(self, token_data: Dict) -> Dict:
        """分析竞争优势"""
        # 识别赛道
        # 对比竞品
        # 评估差异化
```

### 8.3 风险评估器

```python
# analyzers/risk_assessment.py
class RiskAssessment:
    """风险评估"""

    def check_red_flags(self, token_data: Dict) -> List[str]:
        """检查红色警示信号"""
        red_flags = []

        # 无审计报告
        if not token_data.get("audit_reports"):
            red_flags.append("无审计报告，合约安全风险高")

        # 匿名团队
        if token_data.get("team_anonymous"):
            red_flags.append("匿名团队，背景未知")

        # 高度中心化
        if token_data.get("whale_holding") > 0.8:
            red_flags.append("前10地址持仓超过80%，高度中心化")

        # 监管警告
        if token_data.get("regulatory_warning"):
            red_flags.append("存在监管警告")

        return red_flags
```

---

## 9. 报告生成

### 9.1 报告构建器

```python
# generators/report_builder.py
class ReportBuilder:
    """评估报告构建器"""

    def build_report(self, token_id: str) -> Dict:
        """构建完整报告"""
        # 1. 采集多维度数据
        market_data = self.collectors.market.collect(token_id)
        social_data = self.collectors.social.collect(token_id)
        audit_data = self.collectors.audit.collect(token_id)
        code_data = self.collectors.code.analyze(token_id)

        # 2. AI 深度分析
        ai_analysis = self.analyzers.ai.analyze({
            "market": market_data,
            "social": social_data,
            "audit": audit_data,
            "code": code_data,
        })

        # 3. 计算各维度评分
        scores = self.scoring_engine.calculate_all({
            "market": market_data,
            "social": social_data,
            "tech": code_data,
            "team": ai_analysis["team"],
        })

        # 4. 风险评估
        risks = self.risk_assessment.check_red_flags({...})

        # 5. 生成推荐结论
        recommendation = self._generate_recommendation(scores, risks)

        # 6. 组装报告
        return {
            "token_id": token_id,
            "scores": scores,
            "total_score": sum(scores.values()),
            "recommendation": recommendation,
            "details": {
                "market": market_data,
                "social": social_data,
                "audit": audit_data,
                "code": code_data,
                "ai_analysis": ai_analysis,
            },
            "risks": risks,
            "generated_at": datetime.utcnow(),
        }
```

### 9.2 PDF 导出

```python
# generators/pdf_export.py
class PDFExporter:
    """PDF 报告导出器"""

    def export_report(self, report: Dict) -> bytes:
        """生成 PDF 报告"""
        doc = SimpleDocTemplate("report.pdf")

        # 生成雷达图
        radar_chart = self._create_radar_chart(report["scores"])

        # 构建 PDF 内容
        elements = []
        elements.append(Paragraph(f"{report['token_id']} 上币评估报告", title_style))
        elements.append(Paragraph(f"综合评分: {report['total_score']}", heading_style))
        elements.append(radar_chart)

        # 各维度详情
        for dimension, score in report["scores"].items():
            elements.append(self._build_dimension_section(dimension, score, report["details"]))

        # 风险警示
        if report["risks"]:
            elements.append(Paragraph("核心风险警示", alert_style))
            for risk in report["risks"]:
                elements.append(Paragraph(f"⚠️ {risk}", bullet_style))

        doc.build(elements)
```

### 9.3 雷达图生成

```typescript
// frontend/components/RadarChart.tsx
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis } from 'recharts';

interface RadarChartProps {
  scores: {
    market: number;
    social: number;
    tech: number;
    team: number;
    competitive: number;
    risk: number;
  };
}

export function TokenRadarChart({ scores }: RadarChartProps) {
  const data = [
    { dimension: '市场规模', score: scores.market },
    { dimension: '社区活跃', score: scores.social },
    { dimension: '技术实力', score: scores.tech },
    { dimension: '团队背景', score: scores.team },
    { dimension: '竞争优势', score: scores.competitive },
    { dimension: '风险控制', score: scores.risk },
  ];

  return (
    <RadarChart width={400} height={400} data={data}>
      <PolarGrid />
      <PolarAngleAxis dataKey="dimension" />
      <PolarRadiusAxis angle={90} domain={[0, 100]} />
      <Radar name="评分" dataKey="score" stroke="#8884d8" fill="#8884d8" fillOpacity={0.6} />
    </RadarChart>
  );
}
```

---

## 10. 开发路线图

### Phase 1: MVP 基础功能 (4-6周)

- [ ] 后端开发
  - [ ] 项目初始化
  - [ ] 市场数据采集器
  - [ ] 社交舆情采集器
  - [ ] 评分引擎
- [ ] 前端开发
  - [ ] 搜索页面
  - [ ] 报告展示页面
  - [ ] 雷达图组件
- [ ] 数据库设计
  - [ ] Schema 设计
  - [ ] 数据模型

### Phase 2: 完善数据源 (2-3周)

- [ ] 审计报告采集
  - [ ] Certik / Slowmist 爬虫
- [ ] 代码分析
  - [ ] GitHub API 集成
  - [ ] 合约源码检查
- [ ] 更多社交数据源
  - [ ] Reddit API
  - [ ] Telegram / Discord

### Phase 3: AI 深度分析 (2-3周)

- [ ] AI 分析模块
  - [ ] 团队背景分析
  - [ ] 监管风险评估
  - [ ] 竞争优势分析
- [ ] 风险警示系统
  - [ ] 红色信号检测
  - [ ] 历史风险库

### Phase 4: 报告导出 (1-2周)

- [ ] PDF 导出
- [ ] 报告模板系统
- [ ] 批量评估功能

### Phase 5: 优化与上线 (2-3周)

- [ ] 性能优化
  - [ ] 缓存策略 (Redis)
  - [ ] 异步任务队列
- [ ] 用户体验优化
  - [ ] 加载状态
  - [ ] 错误处理
- [ ] 部署上线
  - [ ] Docker 部署
  - [ ] 监控告警

---

## 附录

### A. API 配置

```ini
# .env.example

# CoinGecko
COINGECKO_API_KEY=xxx
COINGECKO_API_URL=https://api.coingecko.com/api/v3

# CoinMarketCap
COINMARKETCAP_API_KEY=xxx

# DeFiLlama
DEFILLAMA_API_URL=https://api.llama.fi

# Twitter API (X)
TWITTER_BEARER_TOKEN=xxx

# Reddit API
REDDIT_CLIENT_ID=xxx
REDDIT_CLIENT_SECRET=xxx

# Claude AI
CLAUDE_API_KEY=xxx

# Database
DATABASE_URL=postgresql://user:pass@localhost/token_assessment
REDIS_URL=redis://localhost:6379
```

### B. 参考资源

| 类别 | 链接 |
|------|------|
| CoinGecko API | https://docs.coingecko.com |
| CoinMarketCap API | https://coinmarketcap.com/api |
| DeFiLlama API | https://defillama.com/docs |
| Twitter API | https://developer.twitter.com |
| Reddit API | https://www.reddit.com/dev/api |
| Claude API | https://docs.anthropic.com |
| Recharts | https://recharts.org |

### C. 评分权重自定义

允许用户自定义各维度权重：

```json
{
  "custom_weights": {
    "market": 0.30,
    "social": 0.25,
    "tech": 0.15,
    "team": 0.10,
    "competitive": 0.10,
    "risk": 0.10
  }
}
```

---

*文档版本: 1.0 | 最后更新: 2026-03-28*