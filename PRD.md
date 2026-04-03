# 上币评估 AI 系统 — 产品需求文档（PRD）

> 版本：v2.0 | 日期：2026-04-03
> 项目代号：Token Lens
> 参赛方向：开放命题（方向5）| 目标段位：Lv.5

---

## 一、产品概述

### 1.1 背景与问题

交易所上币是高影响力决策。现有流程：

- 分析师手动查 CoinGecko、GitHub、社区数据
- 无结构化评分标准，结论主观
- 单次调研耗时 **2-3 个工作日**
- 不同分析师结论差异大，缺乏一致性

**核心问题**：上币决策依赖人工经验，效率低、标准不统一、覆盖面有限。

### 1.2 产品定位

> 输入一个 Token 名称、符号或合约地址，3 分钟内输出结构化上币评估报告。

Token Lens 是一个 **AI 驱动的上币评估工具**，自动聚合多维度公开数据（CoinGecko + DeFiLlama + 链上 API），由 Claude 进行多轮反思分析，输出可执行的推荐结论。

### 1.3 目标用户

| 用户 | 使用场景 |
|------|----------|
| 上币运营团队 | 快速筛选待评估项目，生成初步评估报告 |
| 业务负责人 | 路演/决策前的参考依据 |
| 研究分析师 | 替代重复性数据收集工作 |

### 1.4 核心价值

| 旧方式 | Token Lens |
|--------|-----------|
| 2-3 天人工调研 | 3 分钟自动完成 |
| 主观判断 | 7 维度结构化评分 + AI 多轮反思分析 |
| 数据散落各处 | 统一报告（含 PDF 导出），一目了然 |
| 个人经验依赖 | 可复用、可交接的标准流程 + 历史基准对标 |

---

## 二、功能范围

### 2.1 核心功能

| 功能 | 描述 | 优先级 |
|------|------|--------|
| Token 搜索 | 支持名称/符号/合约地址（EVM + Solana），模糊匹配候选列表 | P0 |
| 多源数据采集 | CoinGecko（主）+ DeFiLlama（TVL）+ Etherscan/Solscan（链上持有者） | P0 |
| 7 维度评分 | 市场/社区/技术/竞争/风险/Tokenomics/链上健康 自动计分，总分 100 | P0 |
| Claude AI 多轮反思分析 | 第一轮综合分析 + 第二轮反思校验，含置信度和数据矛盾检测 | P0 |
| 评估报告展示 | 7 维度雷达图 + 评分条 + 文字分析 + 数据矛盾提示 | P0 |
| 最终推荐结论 | 强烈推荐 / 建议观望 / 不建议 | P0 |
| PDF / Markdown 导出 | 一键导出完整评估报告（支持中文字体） | P1 |
| 历史记录 | SQLite 持久化，支持查看历史评估和预测记录 | P1 |
| 基准对标 | 自动匹配历史相似项目作为参照，注入 Claude prompt | P1 |
| 多语言支持 | 中文 / English 界面切换 | P1 |
| Demo 模式 | `DEMO_MODE=true` 无需 API Key，规则自动生成分析结果 | P1 |
| 快速演示按钮 | 预置 ETH/HYPE/SEI/SUI 一键评估 | P1 |

### 2.2 非核心功能（本次不做）

- 用户登录/权限管理
- 多 Token 横向对比
- 邮件/消息通知

---

## 三、用户流程

```
用户打开系统
    ↓
搜索框输入 Token 名称/符号/合约地址（如 "SUI" 或 "0x..."）
    ↓
系统返回候选列表，用户确认选择（或点击快速演示按钮）
    ↓
系统展示分步进度条：
    ├── 📡 CoinGecko 数据采集（市场/社区/技术/交易所列表）
    ├── 📊 DeFiLlama TVL 数据丰富
    ├── 📊 Tokenomics 分析（流通比例/供应结构）
    ├── 🔗 链上数据分析（持有者分布/浓度风险）
    ├── 📊 基准对标（匹配历史相似项目）
    ├── 📊 规则评分（7 维度计算）
    └── 🤖 Claude AI 多轮反思分析
    ↓
展示完整评估报告
    ├── 基础信息卡片
    ├── 7 维度评分条 + 雷达图
    ├── Claude 分析文字（推荐理由 + 风险点）
    ├── 数据矛盾提示（如有）
    ├── BYDFi 跟进紧迫性建议
    ├── 最终推荐结论
    └── 导出按钮（PDF / Markdown）
```

---

## 四、数据源

### 4.1 CoinGecko API（主数据源）

#### 搜索 Token

**名称/符号搜索**：`GET /api/v3/search?query={name}`

**合约地址搜索**：`GET /api/v3/coins/{platform}/contract/{address}`
- 支持 EVM 链（ethereum/binance-smart-chain/polygon-pos/arbitrum-one/avalanche/base/optimistic-ethereum）
- 支持 Solana 链
- 自动检测地址类型并按优先级尝试匹配

#### 获取详情数据

**接口**：`GET /api/v3/coins/{id}?tickers=true&market_data=true&community_data=true&developer_data=true`

**获取字段**：

| 字段 | 用途 |
|------|------|
| `market_data.market_cap.usd` | 市值 |
| `market_data.total_volume.usd` | 24h 交易量 |
| `market_data.price_change_percentage_30d` | 30日价格波动率 |
| `market_data.market_cap_rank` | 市值排名 |
| `market_data.total_supply` | 总供应量（Tokenomics 用） |
| `market_data.circulating_supply` | 流通供应量（Tokenomics 用） |
| `market_data.max_supply` | 最大供应量（Tokenomics 用） |
| `watchlist_portfolio_users` | CoinGecko Watchlist 关注人数（替代 Twitter） |
| `sentiment_votes_up_percentage` | 社区情绪正面比例 |
| `community_data.telegram_channel_user_count` | Telegram 成员数 |
| `developer_data.stars` | GitHub Star 数 |
| `developer_data.forks` | Fork 数 |
| `developer_data.commit_count_4_weeks` | 近4周提交数 |
| `developer_data.last_4_weeks_commit_activity_series` | 每周提交趋势 |
| `tickers[].market.name` | 已上线的交易所名称 |
| `platforms` | 各链合约地址（用于链上数据查询） |

> **说明**：CoinGecko 免费版 Reddit/Twitter 数据已不可用（均返回 0 或 null），改用 `watchlist_portfolio_users` 作为社区关注度主力指标。

**tickers 裁剪规则**：

```python
MAJOR_EXCHANGES = {
    "Binance", "OKX", "Bybit", "Coinbase Exchange", "Kraken",
    "Bitget", "Gate", "BYDFi", "KuCoin", "HTX",
    "MEXC", "Bitfinex", "Gemini", "Crypto.com Exchange"
}
```

交易所分级（用于竞争位置评分）：
- **Tier1**：Binance、Coinbase Exchange、OKX、Bybit、Kraken
- **Tier2**：Bitget、KuCoin、Gate、MEXC、HTX、Bitfinex、Crypto.com Exchange、Gemini

### 4.2 DeFiLlama API（TVL 数据丰富）

通过 `coins.llama.fi/prices/coingecko/{coin_id}` 获取 TVL 相关数据，丰富 Token 信息：
- `tvl`：协议 TVL
- `tvl_change_24h`：24h TVL 变化
- `mcap_to_tvl`：市值/TVL 比率
- `fdv_to_tvl`：FDV/TVL 比率

> DeFiLlama 数据为可选丰富项，获取失败不影响主流程。

### 4.3 链上 API（持有者分布数据）

根据 CoinGecko `platforms` 字段提取合约地址，按优先级查询链上数据：

| 链 | API | 获取数据 |
|----|-----|----------|
| Ethereum | Etherscan API | Top 10 持有者占比、持有者总数 |
| BSC | BscScan API | 持有者数据 |
| Solana | Solscan API | 持有者数据 |

**降级方案**：链上 API 不可用时，基于市值排名 + 交易量启发式估算持有者浓度风险等级。

---

## 五、评分体系

### 5.1 维度说明（7 维度，总分 100）

| 维度 | 满分 | 数据来源 | 评分方式 |
|------|------|----------|----------|
| 市场规模 | 25 | CoinGecko market_data | 规则（原始满分30，等比缩放至25） |
| 社区活跃度 | 15 | CoinGecko watchlist + telegram | 规则（原始满分20，等比缩放至15） |
| 技术实力 | 15 | CoinGecko developer_data | 规则（原始满分20，等比缩放至15） |
| 竞争位置 | 15 | Claude 分析（基于 tickers 实时数据） | AI |
| 风险信号 | 10 | 规则引擎 + Claude 语义判断 + 反思调整 | 混合（原始满分15，等比缩放至10） |
| Tokenomics | 10 | CoinGecko supply 数据 | 规则（扣分制） |
| 链上健康度 | 10 | Etherscan/Solscan/估算 | 规则（扣分制） |

### 5.2 各维度评分规则

#### 市场规模（原始满分 30，缩放至 25）

| 指标 | 规则 | 原始分值 |
|------|------|----------|
| 市值排名 | Top 20: 15分 / Top 100: 10分 / Top 500: 6分 / 其他: 3分 | 15 |
| 24h 交易量 | >$500M: 10分 / >$100M: 7分 / >$10M: 5分 / <$10M: 2分 | 10 |
| 30日波动率 | <30%: 5分 / 30-60%: 3分 / >60%: 1分 | 5 |

#### 社区活跃度（原始满分 20，缩放至 15）

| 指标 | 规则 | 原始分值 | 异常检测 |
|------|------|----------|---------|
| Watchlist 用户数 | ≥1M: 14分 / ≥500k: 11分 / ≥100k: 8分 / ≥10k: 5分 / >0: 2分 / 无: 0分 | 14 | Watchlist ≥100k 且 24h 交易量 <$1M，标记"高社区关注/低流动性异常" |
| Telegram 成员数 | ≥100k: 6分 / ≥10k: 4分 / ≥1k: 2分 / <1k: 1分 / 无: 0分 | 6 | — |

> 说明：CoinGecko 免费版 Twitter 数据已不可用（均返回 0），改用 `watchlist_portfolio_users` 作为主力社区指标。

#### 技术实力（原始满分 20，缩放至 15）

> **数据来源**：全部从 CoinGecko developer_data 获取，无需单独调用 GitHub API。

| 指标 | 规则 | 原始分值 |
|------|------|----------|
| GitHub Star 数 | ≥10k: 10分 / ≥1k: 7分 / ≥100: 4分 / <100或无: 1分 / null: 0分 | 10 |
| 近4周提交活跃度 | ≥50次: 10分 / ≥10次: 7分 / >0次: 3分 / 0次: 0分 / null: 0分 | 10 |

#### 竞争位置（满分 15，由 Claude 评定）

**Claude 评分标准**：

| 分数区间 | 条件 |
|----------|------|
| 13-15 | 覆盖 4+ 家 Tier1 交易所 |
| 10-12 | 覆盖 2-3 家 Tier1 交易所 |
| 7-9 | 覆盖 1 家 Tier1 + 多家 Tier2，或 3+ 家 Tier2 |
| 4-6 | 仅上线 1-2 家 Tier2 交易所 |
| 1-3 | 极少主流交易所，市场认知度低 |
| 0 | 未在任何已知主流交易所上线 |

**输出**：0-15 的整数分，附 1-2 句说明

#### 风险信号（原始基础分 15，缩放至满分 10，扣分制）

**规则引擎扣分**（scorer.py，不依赖 Claude）：

| 风险类型 | 扣分 | 判断依据 |
|----------|------|---------|
| 代码长期停止更新 | -5 | `commit_count_4_weeks == 0` 且有 GitHub 数据 |
| 无 GitHub 开源代码 | -3 | `github_stars` 为 null |
| 近期价格剧烈下跌 | -3 | `price_change_30d < -50%` |
| 高市值/低社区不匹配 | -2 | 市值排名 Top 100 但 Twitter 粉丝 <10k |

**Claude 语义判断扣分**（最多额外扣 2 分）：
- 赛道严重过饱和（同类项目 5+ 家已上主流所）
- 项目描述模糊，无法明确用例
- 市值排名与交易量严重倒挂（可能存在刷量）

**反思轮次调整**（最多 ±2 分）：第二轮反思可进一步调整风险分。

#### Tokenomics 健康度（满分 10，扣分制）

| 风险类型 | 扣分 | 判断依据 |
|----------|------|---------|
| 流通比例 < 20% | -3 | 砸盘风险高 |
| 流通比例 20%-30% | -2 | 存在一定砸盘风险 |
| 无最大供应量限制 | -1 | 可能存在无限通胀风险 |

> 数据不可用时返回满分 10（不扣分），标注 `data_available: false`。

#### 链上健康度（满分 10，扣分制）

| 风险类型 | 扣分 | 判断依据 |
|----------|------|---------|
| Top 10 持有者占比 > 60% | -4 | 极端集中，CRITICAL |
| Top 10 持有者占比 40%-60% | -2 | 较高集中度，HIGH |
| 持有者总数 < 1000 | -3 | 极少人持有，流动性差 |
| 持有者总数 1000-5000 | -1 | 流动性一般 |

> 数据不可用时返回满分 10（不扣分），标注 `data_available: false`。

### 5.3 推荐结论

| 总分 | 结论 | 颜色 |
|------|------|------|
| ≥ 75 | 强烈推荐上币 | 绿色 |
| 55-74 | 建议观望，重点关注风险点 | 黄色 |
| < 55 | 不建议上币 | 红色 |

---

## 六、Claude 分析模块

### 6.1 模型配置

- **模型**：`claude-sonnet-4-6`
- **System Prompt 角色**：BYDFi 交易所资深上币分析师
- **核心约束**：
  - 所有数字必须来自输入数据，禁止引用训练集历史数据
  - 缺失字段不得在分析中提及具体数值
  - 必须解释「为什么」而非仅说「是什么」
  - 发现数据矛盾时必须在 `data_contradictions` 中明确指出

### 6.2 输入给 Claude 的内容

```
结构化数据摘要（JSON）：
- Token 基础信息（名称、符号、描述、市值、交易量、市值排名、30日价格变化）
- Watchlist 用户数、社区情绪
- 开发者数据（Stars、近4周提交数）
- 规则评分结果（前3个维度分数 + 规则引擎已识别的风险及扣分）
- 已上线交易所列表（Tier1/Tier2 覆盖数 + 主流所名称列表）
- 是否已在 BYDFi 上线（布尔值）
- Tokenomics 数据（供应量、流通比例，如有）
- 链上数据（持有者浓度、Top 10 占比，如有）
- 基准对标信息（历史相似项目，如有）
```

### 6.3 多轮反思分析流程

```
第一轮：analyze()
  → 竞争位置评分 + 语义风险判断 + 推荐理由 + 风险点 + BYDFi 紧迫性 + 总结
  → 输出置信度 + 数据矛盾列表

第二轮：analyze_with_reflection()（非 Demo 模式）
  → 将第一轮结果作为输入，反思：
    1. 是否存在未被充分关注的矛盾信号？
    2. Tokenomics 数据对风险判断的影响？
    3. 竞争位置评分的置信度？
    4. 建议对风险评分做 -2 到 +2 的调整？
  → 合并结果：更新置信度、追加遗漏信号、调整风险分
```

### 6.4 Claude 输出格式（结构化 JSON）

```json
{
  "competitive_score": 12,
  "competitive_reason": "已在 Binance、OKX、Bybit 上线，头部所均有覆盖，流动性充足",
  "risk_extra_deduction": 2,
  "risk_extra_reason": "项目定位与同赛道多个头部项目高度重叠，差异化不明显",
  "top_reasons": [
    "市值排名 Top 50，交易量充足，流动性风险低",
    "CoinGecko 关注人数超 80 万，社区基础扎实",
    "已在3家头部交易所上线，市场认可度高"
  ],
  "top_risks": [
    "近期开发活跃度下降，需关注团队是否仍在积极维护",
    "赛道竞争激烈，差异化优势需进一步验证"
  ],
  "bydfi_urgency": "高",
  "bydfi_urgency_reason": "竞品已全面覆盖，BYDFi 尚未上线，存在用户流失风险",
  "summary": "综合评估建议上币，流动性和社区基础良好，需关注开发活跃度。",
  "confidence_level": 0.85,
  "data_contradictions": ["高市值但开发活跃度偏低，需关注团队投入"]
}
```

### 6.5 Claude 输出解析容错

```python
def _parse_response(text: str) -> dict:
    # 1. 剥掉可能存在的 markdown 代码块
    # 2. 文本不以 { 开始时，尝试提取 JSON 部分
    # 3. json.loads 解析
    # 4. _validate_scores 校验分数范围（competitive_score 0-15，risk_extra_deduction 0-2）
    # 5. 解析失败时返回 _fallback_result()（中位分 + parse_error 标记）
```

### 6.6 Demo 模式

`DEMO_MODE=true` 时跳过 Claude API 调用，基于规则自动生成分析结果：
- 竞争位置评分：基于 Tier1/Tier2 覆盖数的简化规则
- BYDFi 紧迫性：基于交易所覆盖和是否已上线 BYDFi
- 推荐理由/风险点：基于市值排名、交易量、提交数等数据自动生成

---

## 七、界面设计

### 7.1 页面结构

```
┌─────────────────────────────────────────────────────────┐
│  🔍  Token Lens — BYDFi 上币评估 AI 系统                 │
│  [中文/EN 切换]                                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [ 输入 Token 名称或合约地址... ]  [🔍 搜索]             │
│                                                         │
│  快速演示：[⭐ ETH] [🔴 HYPE] [🟡 SEI] [🔵 SUI]        │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  ── 评估结果 ──────────────────────────────────────────  │
│                                                         │
│  ┌──────────────────────┐  ┌────────────────────────┐  │
│  │  基础信息             │  │  雷达图                 │  │
│  │  名称: SUI            │  │  （7维度可视化）        │  │
│  │  市值: $8.2B          │  │                        │  │
│  │  24h 量: $450M        │  │                        │  │
│  │  市值排名: #28        │  │                        │  │
│  └──────────────────────┘  └────────────────────────┘  │
│                                                         │
│  ── 各维度评分 ─────────────────────────────────────── │
│  市场规模     ████████░░  20/25                         │
│  社区活跃度   ██████░░░░  11/15                         │
│  技术实力     ███████░░░  12/15                         │
│  竞争位置     ████████░░  12/15                         │
│  风险信号     ████████░░   8/10                         │
│  Tokenomics   █████████░   9/10                         │
│  链上健康度   ████████░░   8/10                         │
│                           总分: 80/100                  │
│                                                         │
│  ── Claude 分析 ────────────────────────────────────── │
│  ✅ 推荐理由                                            │
│  • ...                                                  │
│  ⚠️ 风险点                                              │
│  • ...                                                  │
│  📊 数据矛盾（如有）                                    │
│  • ...                                                  │
│                                                         │
│  ── BYDFi 跟进建议 ──────────────────────────────────  │
│  🔴 紧迫性：高                                          │
│  竞品已全面覆盖，BYDFi 尚未上线，存在用户流失风险        │
│                                                         │
│  ┌─────────────────────────────────────────────────┐  │
│  │  🟢 强烈推荐  总分 80 — ...                       │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
│  [📄 PDF 报告] [📥 MD 报告]                              │
└─────────────────────────────────────────────────────────┘
```

### 7.2 状态说明

| 状态 | 展示方式 |
|------|----------|
| 数据加载中 | Streamlit progress bar + 分步进度文字 |
| CoinGecko 请求失败 | 对应维度显示"数据不可用"，不影响其他维度 |
| DeFiLlama/链上 API 失败 | 静默降级，不影响主流程 |
| Token 未找到 | 提示"未搜索到代币信息，请检查名称或合约地址" |
| 合约地址为钱包地址 | 提示"检测到可能是钱包地址，请使用代币合约地址" |
| Claude 分析中 | 进度条显示"AI 分析中..." |
| Claude API 余额不足 | 提示可设置 `DEMO_MODE=true` 跳过 |

---

## 八、技术架构

### 8.1 项目结构

```
token-lens/
├── app.py                      # Streamlit 主入口，UI 渲染 + 评估流程编排
├── i18n.py                     # 多语言支持（中文/English）
├── collectors/
│   ├── __init__.py
│   ├── coingecko.py            # CoinGecko 数据采集（搜索 + 详情 + 合约地址）
│   ├── defillama.py            # DeFiLlama TVL 数据丰富
│   ├── tokenomics.py           # Tokenomics 分析（从 CoinGecko 数据提取）
│   └── onchain.py              # 链上数据采集（Etherscan/Solscan + 降级估算）
├── analyzer/
│   ├── __init__.py
│   ├── scorer.py               # 规则评分引擎（7 维度 + 风险扣分）
│   ├── claude_analyzer.py      # Claude API 调用（多轮反思分析）
│   ├── benchmark.py            # 基准对标分析（匹配历史相似项目）
│   └── backtest.py             # 回测引擎（验证历史预测准确性）
├── report/
│   ├── __init__.py
│   ├── chart.py                # Plotly 7 维度雷达图
│   └── pdf_export.py           # PDF 导出（ReportLab，支持中文字体）
├── database/
│   ├── __init__.py
│   └── database.py             # SQLite 数据库（历史记录 + 预测记录）
├── utils/
│   ├── __init__.py
│   ├── cache.py                # 内存缓存（TTL 机制）
│   └── logger.py               # 日志模块（控制台 + 文件）
├── .env                        # 环境变量（不提交）
├── .env.example                # 示例配置文件
└── requirements.txt
```

### 8.2 依赖清单

```
streamlit>=1.32.0
anthropic>=0.20.0
requests>=2.31.0
plotly>=5.18.0
python-dotenv>=1.0.0
reportlab>=4.0.0
```

### 8.3 环境变量

```bash
ANTHROPIC_API_KEY=sk-ant-...   # 必填（DEMO_MODE=true 时可不填）
COINGECKO_API_KEY=CG-...       # 可选，不填走免费额度（10-30 req/min）
ETHERSCAN_API_KEY=...           # 可选，用于链上持有者数据
DEMO_MODE=true                  # 可选，跳过 Claude API，用规则自动生成分析
```

---

## 九、异常处理规范

| 场景 | 处理方式 |
|------|----------|
| CoinGecko 返回 404 | 提示 Token 名称错误 |
| CoinGecko 限流（429） | 立即提示"请求频率过高，请稍后重试" |
| DeFiLlama 请求失败 | 静默跳过，不影响主流程 |
| 链上 API 不可用 | 降级为启发式估算（基于市值排名 + 交易量） |
| Tokenomics 数据缺失 | 返回满分 10，标注数据不可用 |
| 链上数据缺失 | 返回满分 10，标注数据不可用 |
| developer_data 为 null | 技术评分计 0 分，标注"无开源数据" |
| Claude API 超时 | 返回 fallback 中位分结果 |
| Claude API 余额不足 | 提示充值或使用 DEMO_MODE |
| Claude API 限流 | 提示"请稍后重试" |
| 多轮反思分析失败 | 降级到单轮 analyze()，再失败则 fallback |
| 数据库保存失败 | 静默跳过，不影响报告展示 |
| 网络完全断开 | 全局错误提示 |

---

## 十、验收标准

### 路演前必须满足

- [x] 输入任意主流 Token 名称，能在 3 分钟内出完整报告
- [x] 7 个维度均有评分，总分正常计算
- [x] 7 维度雷达图正常渲染
- [x] Claude 分析文字有实质内容，不是模板废话
- [x] 最终推荐结论与数据逻辑一致
- [x] 换一个 Token 还能跑（不硬编码数据）
- [x] 有明确的加载状态（分步进度条），不会白屏卡死
- [x] PDF / Markdown 导出正常
- [x] 支持合约地址搜索
- [x] Demo 模式可用

### 路演演示 Token（实测确认）

| Token | 实测总分 | 结论 | 演示用途 |
|-------|----------|------|----------|
| ETH | 91/100 | 🟢强烈推荐 | 展示高分案例 |
| HYPE (Hyperliquid) | 60/100 | 🟡建议观望 | BYDFi 未上线，紧迫性「高」，最强演示场景 |
| SEI | 51/100 | 🔴不建议 | 展示风险识别（零提交 + 下跌）|
| SUI | — | — | 备选演示 |

---

## 十一、项目时间线

| 日期 | 里程碑 |
|------|--------|
| 3/30 | 搭框架，跑通 CoinGecko 数据拉取（含 tickers 字段） |
| 3/31 | 完成规则评分（市场/社区/技术3维度），修复社区评分（改用 watchlist_portfolio_users） |
| 4/1 | Claude API 接入，调通竞争分析 prompt，跑通端到端流程 |
| 4/2 | Streamlit 界面 + 雷达图 |
| 4/3 | 扩展至 7 维度（+Tokenomics/链上健康度），多轮反思分析，PDF 导出，历史记录，多语言 |
| 4/4 | 真实数据测试，优化 prompt 准确率 |
| 4/5 | 界面打磨，错误处理，README |
| 4/6 | 提交截止，准备路演演示数据 |
