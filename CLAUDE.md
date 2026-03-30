# Token Lens — CLAUDE.md

## 项目简介

BYDFi AI Reforge Hackathon 参赛项目。
**上币评估 AI 系统**：输入 Token 名称，3 分钟内输出结构化上币评估报告。

参赛方向：开放命题（方向5）| 目标段位：Lv.5（+35%）
提交截止：2026-04-06 | 路演：2026-04-07~12

---

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 ANTHROPIC_API_KEY（必填）

# 3. 启动
streamlit run app.py
```

浏览器访问 `http://localhost:8501`

---

## 环境变量

```bash
# .env 文件
ANTHROPIC_API_KEY=sk-ant-...       # 必填
GITHUB_TOKEN=ghp_...               # 可选，提升 GitHub API 额度
COINGECKO_API_KEY=CG-...           # 可选，提升 CoinGecko API 额度
```

---

## 项目结构

```
token-lens/
├── app.py                      # Streamlit 主入口，UI 渲染逻辑
├── collectors/
│   └── coingecko.py            # CoinGecko API：市场/社区/技术/交易所列表（唯一数据源）
├── analyzer/
│   ├── scorer.py               # 规则评分引擎（市场/社区/技术 3个维度）
│   └── claude_analyzer.py      # Claude API：竞争位置 + 风险信号 + BYDFi紧迫性 + 文字分析
├── report/
│   └── chart.py                # Plotly 雷达图生成
├── PRD.md                      # 完整产品需求文档（含评分规则、界面设计）
├── REQUIREMENTS_MVP.md         # MVP 精简需求说明
├── .env.example                # 环境变量示例
└── requirements.txt
```

---

## 核心逻辑说明

### 数据流

```
用户输入 Token 名
  → collectors/ 并发拉取3个数据源
  → analyzer/scorer.py 计算前3个维度（规则评分）
  → analyzer/claude_analyzer.py 调用 Claude 分析后2个维度 + 生成文字
  → report/chart.py 生成雷达图
  → app.py 渲染完整报告
```

### 评分维度（总分100）

| 维度 | 权重 | 数据来源 | 评分方式 |
|------|------|----------|----------|
| 市场规模 | 30% | CoinGecko | 规则 |
| 社区活跃度 | 20% | CoinGecko | 规则 |
| 技术实力 | 20% | GitHub + DeFiLlama | 规则 |
| 竞争位置 | 15% | Claude 分析 | AI |
| 风险信号 | 15% | Claude 分析 | AI（从15分扣减）|

推荐结论：≥75 强烈推荐 / 55-74 建议观望 / <55 不建议

### Claude 调用说明

- 模型：`claude-sonnet-4-6`
- 输入：结构化 JSON（原始数据 + 规则评分结果）
- 输出：结构化 JSON（竞争分 + 风险分 + 推荐理由 + 风险点 + 总结）
- 详细 prompt 设计见 `analyzer/claude_analyzer.py`

---

## 数据源 API

| API | 文档 | 免费额度 | 是否需要 Key |
|-----|------|----------|-------------|
| CoinGecko | https://docs.coingecko.com | 10-30 req/min | 否（有 Key 更高） |
| DeFiLlama | https://defillama.com/docs/api | 无限制 | 否 |
| GitHub | https://docs.github.com/rest | 60/h（无Key）/ 5000/h（有Key） | 可选 |

---

## 开发规范

- 语言：Python 3.10+
- 界面：Streamlit（不引入其他前端框架）
- 异步：暂不引入 asyncio，保持简单同步调用
- 错误处理：每个 collector 独立 try/except，单个 API 失败不影响其他模块
- 代码注释：中文

---

## 当前开发状态

> 更新此区域，保持最新进度

- [x] Day1：项目框架 + CoinGecko 数据拉取
- [x] Day2：规则评分完成（CoinGecko-only 方案）+ 修复社区评分（改用 watchlist_portfolio_users）
- [x] Day3：Claude API 接入，端到端跑通
- [x] Day4：Streamlit 界面 + 雷达图
- [x] Day5：真实 Claude API 端到端测试 + prompt 防幻觉约束
- [x] Day6：边角打磨 + 路演排练
- [x] Day7：README + 推送 GitHub + 提交

---

## 路演演示 Token（实测确认）

| Token | 实测总分 | 结论 | 演示用途 |
|-------|----------|------|----------|
| ETH | 91/100 | 🟢强烈推荐 | 展示高分案例 |
| HYPE (Hyperliquid) | 60/100 | 🟡建议观望 | ❗BYDFi 未上线，紧迫性「高」，最强演示场景 |
| SEI | 51/100 | 🔴不建议 | 展示风险识别（零提交 + 下跌）|
