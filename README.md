# Token Lens — 上币评估 AI 系统

> BYDFi AI Reforge Hackathon 参赛项目 · 开放命题（方向5）

**输入 Token 名称或合约地址，3 分钟内输出结构化上币评估报告。**

---

## 解决什么问题

传统上币调研需要 2-3 天：分析师手动查市值、看 GitHub、比对各交易所上线情况、评估风险信号。

Token Lens 把这个流程压缩到 **3 分钟**：

```
用户输入 Token 名称/符号/合约地址
  → 实时拉取 CoinGecko 数据（市场/社区/技术/交易所）
  → 规则引擎计算前3个维度评分
  → Claude claude-sonnet-4-6 分析竞争位置 + 识别语义风险
  → 输出结构化报告 + 雷达图 + BYDFi 跟进建议
```

---

## 核心亮点

### 1. BYDFi 视角的紧迫性判断
不只是"这个 Token 好不好"，而是"**BYDFi 现在要不要上**"。

基于实时交易所列表判断：
- 已上 Coinbase/Binance/OKX 但 BYDFi 没有 → **🔴 高紧迫性**
- 已在 BYDFi 上线 → **🟢 低紧迫性**（转为运营建议）

### 2. Claude 做真正的分析，不是装饰
- 竞争位置评分（0-15分）：基于实时交易所数据，有明确评分标准，非训练记忆
- 语义风险识别：赛道过饱和、定位模糊等规则无法捕捉的风险
- 生成数据驱动的理由，禁止引用输入数据以外的数字

### 3. 数据全部实时，无缓存
每次评估现场调用 CoinGecko API，交易所上线情况实时获取。

### 4. 多语言支持
支持中英文切换，右上角一键切换语言。

### 5. 智能搜索
- 支持 Token 名称、符号、合约地址搜索
- 支持 EVM 链（Ethereum/BSC/Polygon/Arbitrum 等）和 Solana 链
- 自动检测钱包地址并给出提示

---

## 评分维度

| 维度 | 权重 | 数据来源 | 评分方式 |
|------|------|----------|----------|
| 市场规模 | 25% | CoinGecko market_data | 规则 |
| 社区活跃度 | 15% | CoinGecko watchlist_users | 规则 |
| 技术实力 | 15% | CoinGecko developer_data | 规则 |
| 竞争位置 | 15% | Claude 分析（基于实时 tickers） | AI |
| 风险信号 | 10% | 规则 + Claude 语义判断 | 规则+AI |
| Tokenomics | 10% | 供应量/流通比例分析 | 规则 |
| 链上数据 | 10% | 活跃地址/交易量等 | 规则 |

**推荐阈值**：🟢 ≥75 强烈推荐 / 🟡 55-74 建议观望 / 🔴 <55 不建议

---

## 路演演示 Token（实测数据）

| Token | 总分 | 结论 | 演示场景 |
|-------|------|------|----------|
| **ETH** | 91/100 | 🟢 强烈推荐 | 高分案例，基本面全面 |
| **HYPE**（Hyperliquid） | 60/100 | 🟡 建议观望 | **最强场景**：未上BYDFi，4家Tier1已有，紧迫性高 |
| **SEI** | 51/100 | 🔴 不建议 | 风险识别：零提交+下跌+高竞争 |

---

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 ANTHROPIC_API_KEY

# 3. 启动
python3 -m streamlit run app.py
```

浏览器访问 `http://localhost:8501`

### 环境变量

```bash
ANTHROPIC_API_KEY=sk-ant-...     # 必填
COINGECKO_API_KEY=CG-...         # 可选，提升 API 限额
DEMO_MODE=true                    # 可选，跳过 Claude API（路演备用）
```

---

## 技术架构

```
app.py                          # Streamlit 主入口 + UI 渲染
i18n.py                         # 多语言支持（中/英）
collectors/
  coingecko.py                  # CoinGecko 数据采集（名称/符号/合约地址搜索）
  defillama.py                  # DeFiLlama TVL 数据
  tokenomics.py                 # Tokenomics 分析
  onchain.py                    # 链上数据获取
analyzer/
  scorer.py                     # 规则评分引擎（市场/社区/技术/风险）
  claude_analyzer.py            # Claude API 调用（竞争位置 + 语义风险）
  benchmark.py                  # 基准对标分析
report/
  chart.py                      # Plotly 雷达图生成
  pdf_export.py                 # PDF 报告导出
database/
  database.py                   # SQLite 数据持久化
```

**技术选型**：Python · Streamlit · Claude API · CoinGecko API · DeFiLlama API · Plotly

---

## 项目结构设计决策

- **只用 CoinGecko**：一个 API 覆盖市场/社区/技术/交易所全量数据，避免多源依赖
- **watchlist_portfolio_users 作社区指标**：CoinGecko 免费版 Reddit/Twitter 数据已不可用，改用关注人数（ETH 230万/DOGE 86万/SUI 36万）
- **Demo 模式**：路演时 API 不可用的零风险备用方案

---

*BYDFi AI Reforge Hackathon · 2026*
