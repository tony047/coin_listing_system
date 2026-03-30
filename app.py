"""
Token Lens — 上币评估 AI 系统
Streamlit 主入口
"""

import os
import time
import streamlit as st
from dotenv import load_dotenv

from collectors.coingecko import search_token, get_token_data
from analyzer.scorer import compute_rule_scores
from analyzer.claude_analyzer import analyze
from report.chart import build_radar_chart

# 本地开发读 .env，Streamlit Cloud 读 st.secrets
load_dotenv()
try:
    for key in ["ANTHROPIC_API_KEY", "COINGECKO_API_KEY", "DEMO_MODE"]:
        if key in st.secrets and not os.getenv(key):
            os.environ[key] = st.secrets[key]
except Exception:
    pass  # 本地无 secrets.toml 时跳过

# 路演演示 Token（coin_id 固定，点击直接触发评估，无需搜索选择）
DEMO_TOKENS = [
    {"label": "⭐ ETH — 强烈推荐（91分）",    "id": "ethereum",    "name": "Ethereum",    "symbol": "ETH"},
    {"label": "🔴 HYPE — 高紧迫性（未上BYDFi）","id": "hyperliquid", "name": "Hyperliquid", "symbol": "HYPE"},
    {"label": "🟡 SEI — 不建议（零提交风险）",  "id": "sei-network", "name": "Sei",         "symbol": "SEI"},
    {"label": "🔵 SUI — 建议观望",             "id": "sui",         "name": "Sui",         "symbol": "SUI"},
]

# ── 全局样式 ──────────────────────────────────────────────

def _inject_css():
    st.markdown("""
<style>
/* 标题区域 */
h1 { letter-spacing: -0.5px; }

/* Metric 数值加粗 */
[data-testid="stMetricValue"] {
    font-size: 1.25rem !important;
    font-weight: 700 !important;
}

/* 进度条加高 */
[data-testid="stProgress"] > div > div {
    height: 8px !important;
    border-radius: 4px !important;
}

/* Tab 字体稍大 */
[data-testid="stTabs"] button {
    font-size: 0.9rem !important;
}

/* 侧边栏按钮左对齐 */
section[data-testid="stSidebar"] button {
    text-align: left !important;
    justify-content: flex-start !important;
}

/* 首页特性卡片 */
.feature-card {
    padding: 1rem 1.2rem;
    border-radius: 8px;
    border: 1px solid rgba(128,128,128,0.2);
    margin-bottom: 0.5rem;
}

/* 数据来源标注 */
.data-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    background: rgba(99,132,255,0.15);
    color: #6384ff;
    margin-left: 4px;
}
</style>
""", unsafe_allow_html=True)


# ── 工具函数 ──────────────────────────────────────────────

def _fmt_usd(value) -> str:
    """格式化美元金额"""
    if value is None:
        return "N/A"
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    return f"${value:,.0f}"


def _score_color(pct: float) -> str:
    """根据得分百分比返回颜色标签"""
    if pct >= 0.75:
        return "🟢"
    if pct >= 0.50:
        return "🟡"
    return "🔴"


def _data_quality_warnings(token_data: dict) -> list[str]:
    """检查数据完整性，返回警告列表"""
    warnings = []
    # github_stars 为 None 或 0 均视为无 GitHub 数据（0 star 的已上交易所项目不正常）
    no_github = not token_data.get("github_stars") and token_data.get("commit_count_4_weeks") == 0
    if no_github:
        warnings.append("GitHub 数据缺失或异常：CoinGecko 未关联有效仓库，技术实力评分仅供参考")
    if not token_data.get("watchlist_users"):
        warnings.append("社区关注数据缺失，社区活跃度评分可能偏低")
    return warnings


def _generate_report_md(result: dict) -> str:
    """生成可下载的 Markdown 格式报告"""
    token = result["token_data"]
    scores = result["final_scores"]
    ai = result["ai_result"]
    total = result["total_score"]
    elapsed = result.get("elapsed_seconds", 0)

    if total >= 75:
        verdict = "🟢 强烈推荐上币"
    elif total >= 55:
        verdict = "🟡 建议观望"
    else:
        verdict = "🔴 不建议上币"

    lines = [
        f"# Token Lens 上币评估报告",
        f"",
        f"**Token**：{token['name']} ({token['symbol']})",
        f"**评估结论**：{verdict}　**总分**：{total} / 100",
        f"**分析耗时**：{elapsed:.1f} 秒",
        f"",
        f"---",
        f"",
        f"## 基础数据",
        f"",
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| 市值排名 | #{token.get('market_cap_rank', 'N/A')} |",
        f"| 市值 | {_fmt_usd(token.get('market_cap_usd'))} |",
        f"| 24h 交易量 | {_fmt_usd(token.get('volume_24h_usd'))} |",
        f"| 30日涨跌 | {token.get('price_change_30d', 0):.1f}% |" if token.get('price_change_30d') is not None else "| 30日涨跌 | N/A |",
        f"| CoinGecko 关注人数 | {token.get('watchlist_users', 'N/A'):,} |" if token.get('watchlist_users') else "| CoinGecko 关注人数 | N/A |",
        f"| GitHub Stars | {token.get('github_stars', 'N/A')} |",
        f"| 近4周提交数 | {token.get('commit_count_4_weeks', 'N/A')} |",
        f"",
        f"---",
        f"",
        f"## 各维度评分",
        f"",
        f"| 维度 | 得分 | 满分 |",
        f"|------|------|------|",
        f"| 市场规模 | {scores['market']['score']} | 30 |",
        f"| 社区活跃度 | {scores['community']['score']} | 20 |",
        f"| 技术实力 | {scores['technical']['score']} | 20 |",
        f"| 竞争位置 | {scores['competitive']['score']} | 15 |",
        f"| 风险信号 | {scores['risk']['score']} | 15 |",
        f"| **总分** | **{total}** | **100** |",
        f"",
        f"---",
        f"",
        f"## AI 分析",
        f"",
        f"### 推荐理由",
        f"",
    ]
    for r in ai.get("top_reasons", []):
        lines.append(f"- {r}")
    lines += [
        f"",
        f"### 风险点",
        f"",
    ]
    for r in ai.get("top_risks", []):
        lines.append(f"- {r}")

    urgency = ai.get("bydfi_urgency", "中")
    listed = token.get("listed_on_major", [])
    lines += [
        f"",
        f"---",
        f"",
        f"## BYDFi 跟进建议",
        f"",
        f"**紧迫性**：{urgency}　{ai.get('bydfi_urgency_reason', '')}",
        f"",
        f"**已上线主流交易所**：{', '.join(listed) if listed else '无数据'}",
        f"**BYDFi 上线状态**：{'✅ 已上线' if token.get('listed_on_bydfi') else '❌ 未上线'}",
        f"",
        f"---",
        f"",
        f"*由 Token Lens 自动生成 · BYDFi AI Reforge Hackathon*",
    ]
    return "\n".join(lines)


# ── 侧边栏 ────────────────────────────────────────────────

def _render_sidebar():
    with st.sidebar:
        st.header("Token Lens")
        st.caption("BYDFi AI Reforge Hackathon")
        st.divider()

        st.subheader("快速演示")
        for item in DEMO_TOKENS:
            if st.button(item["label"], use_container_width=True, key=f"demo_{item['id']}"):
                # 直接存 coin dict，主流程跳过搜索直接评估
                st.session_state["auto_coin"] = {"id": item["id"], "name": item["name"], "symbol": item["symbol"]}
                st.rerun()

        st.divider()

        st.subheader("系统信息")
        demo_mode = os.getenv("DEMO_MODE", "").lower() == "true"
        st.markdown("**AI 模型**：claude-sonnet-4-6")
        st.markdown("**数据源**：CoinGecko API（实时）")
        if demo_mode:
            st.warning("Demo 模式：AI 分析由规则生成")
        else:
            has_key = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
            st.markdown(f"**Claude API**：{'✅ 已配置' if has_key else '❌ 未配置'}")

        st.divider()
        with st.expander("评分维度说明"):
            st.markdown("""
| 维度 | 权重 | 方式 |
|------|------|------|
| 市场规模 | 30% | 规则 |
| 社区活跃度 | 20% | 规则 |
| 技术实力 | 20% | 规则 |
| 竞争位置 | 15% | AI |
| 风险信号 | 15% | 规则+AI |

**结论阈值**：🟢≥75 / 🟡55-74 / 🔴<55
""")

        history = [k.replace("result_", "") for k in st.session_state if k.startswith("result_")]
        if history:
            st.divider()
            st.subheader("本次会话记录")
            for coin_id in history:
                cached = st.session_state.get(f"result_{coin_id}", {})
                name = cached.get("token_data", {}).get("name", coin_id)
                score = cached.get("total_score", "?")
                icon = "🟢" if score != "?" and score >= 75 else ("🟡" if score != "?" and score >= 55 else "🔴")
                if st.button(f"{icon} {name} — {score}分", key=f"hist_{coin_id}", use_container_width=True):
                    st.session_state["auto_coin"] = {
                        "id": coin_id,
                        "name": name,
                        "symbol": cached.get("token_data", {}).get("symbol", ""),
                    }
                    st.rerun()


# ── 首页引导 ──────────────────────────────────────────────

def _render_homepage():
    """无搜索时展示引导界面"""
    st.markdown("### 这是什么？")
    st.markdown(
        "输入任意 Token 名称，**3 分钟内**输出结构化上币评估报告。"
        "覆盖市场规模、社区活跃度、技术实力、竞争位置、风险信号五个维度，"
        "并给出 BYDFi 跟进紧迫性建议。"
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""<div class="feature-card">
<b>📡 实时数据</b><br/>
CoinGecko 现场拉取市场、社区、GitHub 数据，无缓存
</div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("""<div class="feature-card">
<b>🤖 AI 分析</b><br/>
Claude claude-sonnet-4-6 判断竞争位置与语义风险，非规则硬编码
</div>""", unsafe_allow_html=True)
    with col3:
        st.markdown("""<div class="feature-card">
<b>🏦 BYDFi 视角</b><br/>
结合实时交易所上线情况，给出「高/中/低」跟进紧迫性
</div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**快速试试** → 点击左侧「快速演示」按钮，或在上方输入框搜索 Token")


# ── 报告渲染 ─────────────────────────────────────────────

def _render_report(result: dict):
    token = result["token_data"]
    scores = result["final_scores"]
    ai = result["ai_result"]
    total = result["total_score"]
    elapsed = result.get("elapsed_seconds")

    st.divider()

    # 结论横幅
    if total >= 75:
        st.success(f"🟢 **强烈推荐上币**　{total} / 100 分　　{ai.get('summary', '')}")
    elif total >= 55:
        st.warning(f"🟡 **建议观望**　{total} / 100 分　　{ai.get('summary', '')}")
    else:
        st.error(f"🔴 **不建议上币**　{total} / 100 分　　{ai.get('summary', '')}")

    # 耗时 + 下载按钮同行
    col_time, col_dl = st.columns([3, 1])
    if elapsed:
        col_time.caption(f"数据实时拉取 · 分析耗时 {elapsed:.1f} 秒")
    with col_dl:
        report_md = _generate_report_md(result)
        st.download_button(
            label="📥 下载报告",
            data=report_md,
            file_name=f"token_lens_{token.get('symbol', 'report').lower()}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    # 数据完整性警告
    for w in _data_quality_warnings(token):
        st.warning(f"⚠️ {w}")

    # Tab 布局
    tab_overview, tab_scores, tab_exchange, tab_ai = st.tabs(
        ["📊 概览", "📈 评分详情", "🏦 交易所覆盖", "🤖 AI 分析"]
    )

    with tab_overview:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader(f"{token['name']} ({token['symbol']})")
            rank = token.get("market_cap_rank")
            price = token.get("price_usd")
            change_30d = token.get("price_change_30d")
            m1, m2 = st.columns(2)
            m1.metric("市值排名", f"#{rank}" if rank else "N/A")
            m2.metric("市值", _fmt_usd(token.get("market_cap_usd")))
            m3, m4 = st.columns(2)
            m3.metric("24h 交易量", _fmt_usd(token.get("volume_24h_usd")))
            if price:
                m4.metric(
                    "当前价格",
                    f"${price:,.4f}" if price < 1 else f"${price:,.2f}",
                    delta=f"{change_30d:.1f}% (30d)" if change_30d is not None else None,
                )
            m5, m6 = st.columns(2)
            watchlist = token.get("watchlist_users")
            sentiment = token.get("sentiment_up_pct")
            if watchlist:
                m5.metric("CoinGecko 关注", f"{watchlist:,}")
            if sentiment is not None:
                m6.metric("看涨情绪", f"{sentiment:.0f}%")

        with col2:
            fig = build_radar_chart(scores)
            st.plotly_chart(fig, use_container_width=True)

        urgency = ai.get("bydfi_urgency", "中")
        urgency_icon = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(urgency, "⚪")
        if token.get("listed_on_bydfi"):
            st.success("✅ 已在 BYDFi 上线")
        else:
            st.info(f"{urgency_icon} **BYDFi 跟进紧迫性：{urgency}**　{ai.get('bydfi_urgency_reason', '')}")

    with tab_scores:
        dim_labels = {
            "market":      "市场规模",
            "community":   "社区活跃度",
            "technical":   "技术实力",
            "competitive": "竞争位置",
            "risk":        "风险信号",
        }
        for key, label in dim_labels.items():
            s = scores[key]
            pct = s["score"] / s["max"]
            icon = _score_color(pct)
            col_icon, col_label, col_bar, col_score = st.columns([0.3, 2, 5, 1])
            col_icon.write(icon)
            col_label.write(f"**{label}**")
            col_bar.progress(pct)
            col_score.write(f"**{s['score']}**/{s['max']}")

        st.divider()
        st.metric("综合总分", f"{total} / 100")

        deductions = result["rule_scores"]["risk_rules"].get("deductions", [])
        if deductions:
            st.markdown("**风险扣分明细**")
            for d in deductions:
                st.warning(f"**{d['risk']}**（扣 {d['deduction']} 分）　{d['detail']}")
        extra = ai.get("risk_extra_deduction", 0)
        if extra:
            st.warning(f"**AI 识别额外风险**（扣 {extra} 分）　{ai.get('risk_extra_reason', '')}")

        with st.expander("原始数据明细"):
            raw_cols = {
                "市值排名": token.get("market_cap_rank"),
                "市值 (USD)": _fmt_usd(token.get("market_cap_usd")),
                "24h 交易量": _fmt_usd(token.get("volume_24h_usd")),
                "30日涨跌幅": f"{token.get('price_change_30d', 0):.1f}%" if token.get("price_change_30d") is not None else "N/A",
                "CoinGecko 关注人数": f"{token.get('watchlist_users', 0):,}" if token.get("watchlist_users") else "N/A",
                "Telegram 成员": token.get("telegram_members") or "N/A",
                "GitHub Stars": token.get("github_stars") or "N/A",
                "近4周 Commits": token.get("commit_count_4_weeks") if token.get("commit_count_4_weeks") is not None else "N/A",
            }
            for k, v in raw_cols.items():
                c1, c2 = st.columns([2, 3])
                c1.caption(k)
                c2.write(str(v))

    with tab_exchange:
        listed = token.get("listed_on_major", [])
        other_count = token.get("listed_on_other_count", 0)
        if listed:
            st.markdown(f"**已上线主流交易所（{len(listed)} 家）**")
            for i in range(0, len(listed), 4):
                cols = st.columns(4)
                for j, ex in enumerate(listed[i:i+4]):
                    if ex == "BYDFi":
                        cols[j].success(f"✅ {ex}")
                    else:
                        cols[j].info(f"📌 {ex}")
            if other_count:
                st.caption(f"另有 {other_count} 家其他交易所")
        else:
            st.warning("未获取到交易所上线信息")

        st.divider()
        st.markdown(f"**竞争位置评分**：{scores['competitive']['score']}/15")
        st.caption(ai.get("competitive_reason", ""))

    with tab_ai:
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("### ✅ 推荐理由")
            for reason in ai.get("top_reasons", []):
                st.markdown(f"> {reason}")
        with col_b:
            st.markdown("### ⚠️ 风险点")
            for risk in ai.get("top_risks", []):
                st.markdown(f"> {risk}")

        st.divider()
        st.markdown("### BYDFi 跟进建议")
        urgency = ai.get("bydfi_urgency", "中")
        urgency_icon = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(urgency, "⚪")
        st.markdown(f"{urgency_icon} **紧迫性：{urgency}**　{ai.get('bydfi_urgency_reason', '')}")

        if ai.get("demo_mode"):
            st.caption("ℹ️ Demo 模式：AI 分析由规则自动生成")
        if ai.get("parse_error"):
            st.caption("⚠️ AI 分析模块异常，竞争位置和风险分使用默认中位分")

    # 规则引擎社区警告
    for w in result["rule_scores"].get("warnings", []):
        st.warning(f"⚠️ {w}")


# ── 评估流程 ─────────────────────────────────────────────

def _run_evaluation(coin: dict):
    coin_id = coin["id"]
    cache_key = f"result_{coin_id}"

    if cache_key in st.session_state:
        _render_report(st.session_state[cache_key])
        return

    start_time = time.time()
    progress = st.progress(0, text="准备开始...")
    status = st.empty()

    # 阶段1：数据采集
    status.info(f"📡 正在从 CoinGecko 采集 **{coin['name']}** 实时数据...")
    progress.progress(10, text="数据采集中...")
    try:
        token_data = get_token_data(coin_id)
    except RuntimeError as e:
        progress.empty()
        status.empty()
        st.error(f"数据采集失败：{e}")
        st.button("重试", on_click=st.rerun)
        return
    progress.progress(35, text="✓ 数据采集完成")

    # 阶段2：规则评分
    status.info("📊 规则评分计算中...")
    progress.progress(40, text="规则评分中...")
    rule_scores = compute_rule_scores(token_data)
    progress.progress(55, text="✓ 规则评分完成")

    # 阶段3：Claude 分析
    status.info("🤖 Claude AI 深度分析中（约 15-20 秒）...")
    progress.progress(60, text="AI 分析中...")
    try:
        ai_result = analyze(token_data, rule_scores)
    except RuntimeError as e:
        progress.empty()
        status.empty()
        st.error(f"AI 分析失败：{e}")
        if "余额不足" in str(e):
            st.info("💡 提示：可在 .env 中设置 `DEMO_MODE=true` 跳过 Claude API，用规则自动生成分析")
        st.button("重试", on_click=st.rerun)
        return
    progress.progress(90, text="✓ AI 分析完成")

    risk_final_score = max(
        0,
        rule_scores["risk_rules"]["score"] - ai_result.get("risk_extra_deduction", 0)
    )

    result = {
        "token_data": token_data,
        "rule_scores": rule_scores,
        "ai_result": ai_result,
        "elapsed_seconds": time.time() - start_time,
        "final_scores": {
            "market":      {"score": rule_scores["market"]["score"],         "max": 30},
            "community":   {"score": rule_scores["community"]["score"],      "max": 20},
            "technical":   {"score": rule_scores["technical"]["score"],      "max": 20},
            "competitive": {"score": ai_result.get("competitive_score", 8), "max": 15},
            "risk":        {"score": risk_final_score,                       "max": 15},
        },
    }
    result["total_score"] = sum(v["score"] for v in result["final_scores"].values())

    progress.progress(100, text="✅ 分析完成！")
    time.sleep(0.3)
    progress.empty()
    status.empty()

    st.session_state[cache_key] = result
    _render_report(result)


# ── 页面主体 ─────────────────────────────────────────────

st.set_page_config(
    page_title="Token Lens — 上币评估系统",
    page_icon="🔍",
    layout="wide",
)

_inject_css()
_render_sidebar()

st.title("🔍 Token Lens")
st.caption("BYDFi 上币评估 AI 系统 · 数据实时拉取 · claude-sonnet-4-6 驱动")

query = st.text_input(
    "Token 名称",
    placeholder="输入 Token 名称，如 ETH、HYPE、SUI...",
    label_visibility="collapsed",
)

# ── 快速演示：直接触发评估，跳过搜索和选择 ──────────────
auto_coin = st.session_state.pop("auto_coin", None)
if auto_coin:
    cache_key = f"result_{auto_coin['id']}"
    col_title, col_clear = st.columns([3, 1])
    col_title.markdown(f"**{auto_coin['name']} ({auto_coin['symbol']})**")
    with col_clear:
        if cache_key in st.session_state:
            if st.button("🔄 刷新分析", use_container_width=True):
                del st.session_state[cache_key]
                st.session_state["auto_coin"] = auto_coin
                st.rerun()
    _run_evaluation(auto_coin)
    st.stop()

# ── 手动搜索流程 ──────────────────────────────────────────
if not query:
    _render_homepage()
    st.stop()

with st.spinner("搜索中..."):
    try:
        candidates = search_token(query)
    except RuntimeError as e:
        st.error(f"搜索失败：{e}")
        st.stop()

if not candidates:
    st.warning(f"未找到「{query}」，请检查拼写或尝试英文名称（如 ethereum、sui）")
    st.stop()

options = [f"{c['name']} ({c['symbol']})" for c in candidates]
selected_idx = st.selectbox("选择 Token", range(len(options)), format_func=lambda i: options[i])
coin = candidates[selected_idx]

cache_key = f"result_{coin['id']}"
col_btn, col_clear = st.columns([3, 1])
with col_btn:
    run = st.button("🚀 开始评估", type="primary", use_container_width=True)
with col_clear:
    if cache_key in st.session_state:
        if st.button("🔄 刷新分析", use_container_width=True):
            del st.session_state[cache_key]
            st.rerun()

if run:
    _run_evaluation(coin)
elif cache_key in st.session_state:
    _render_report(st.session_state[cache_key])
