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

# 路演演示 Token
DEMO_TOKENS = [
    {"label": "⭐ ETH — 以太坊（高分案例）", "query": "ethereum"},
    {"label": "🔵 SUI — Sui（中高分）", "query": "sui"},
    {"label": "🟡 OP — Optimism（建议观望）", "query": "optimism"},
    {"label": "🐕 DOGE — 狗狗币（风险案例）", "query": "dogecoin"},
]


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


# ── 侧边栏 ────────────────────────────────────────────────

def _render_sidebar():
    """渲染侧边栏：演示快捷键 + 系统信息"""
    with st.sidebar:
        st.header("Token Lens")
        st.caption("BYDFi AI Reforge Hackathon")
        st.divider()

        # 演示快捷入口
        st.subheader("快速演示")
        for item in DEMO_TOKENS:
            if st.button(item["label"], use_container_width=True, key=f"demo_{item['query']}"):
                st.session_state["demo_query"] = item["query"]
                st.rerun()

        st.divider()

        # 系统信息
        st.subheader("系统信息")
        demo_mode = os.getenv("DEMO_MODE", "").lower() == "true"
        st.markdown(f"**AI 模型**：claude-sonnet-4-6")
        st.markdown(f"**数据源**：CoinGecko API")
        if demo_mode:
            st.warning("Demo 模式：AI 分析由规则生成")
        else:
            has_key = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
            st.markdown(f"**Claude API**：{'✅ 已配置' if has_key else '❌ 未配置'}")

        st.divider()

        # 评分说明
        with st.expander("评分维度说明"):
            st.markdown("""
| 维度 | 权重 | 评分方式 |
|------|------|----------|
| 市场规模 | 30% | 规则 |
| 社区活跃度 | 20% | 规则 |
| 技术实力 | 20% | 规则 |
| 竞争位置 | 15% | AI |
| 风险信号 | 15% | 规则+AI |

**推荐阈值**
- 🟢 ≥75 强烈推荐
- 🟡 55-74 建议观望
- 🔴 <55 不建议
""")

        # 历史记录
        history = [k.replace("result_", "") for k in st.session_state if k.startswith("result_")]
        if history:
            st.divider()
            st.subheader("本次会话记录")
            for coin_id in history:
                cached = st.session_state.get(f"result_{coin_id}", {})
                name = cached.get("token_data", {}).get("name", coin_id)
                score = cached.get("total_score", "?")
                if st.button(f"{name} — {score}分", key=f"hist_{coin_id}", use_container_width=True):
                    st.session_state["jump_to"] = coin_id
                    st.rerun()


# ── 报告渲染 ─────────────────────────────────────────────

def _render_report(result: dict):
    """渲染完整评估报告"""
    token = result["token_data"]
    scores = result["final_scores"]
    ai = result["ai_result"]
    total = result["total_score"]
    elapsed = result.get("elapsed_seconds")

    st.divider()

    # ── 顶部：结论横幅 ───────────────────────────────────
    if total >= 75:
        st.success(f"🟢 **强烈推荐上币**　{total} / 100 分　　{ai.get('summary', '')}")
    elif total >= 55:
        st.warning(f"🟡 **建议观望**　{total} / 100 分　　{ai.get('summary', '')}")
    else:
        st.error(f"🔴 **不建议上币**　{total} / 100 分　　{ai.get('summary', '')}")

    if elapsed:
        st.caption(f"分析耗时 {elapsed:.1f} 秒")

    # ── Tab 布局 ─────────────────────────────────────────
    tab_overview, tab_scores, tab_exchange, tab_ai = st.tabs(
        ["📊 概览", "📈 评分详情", "🏦 交易所覆盖", "🤖 AI 分析"]
    )

    # Tab1: 概览
    with tab_overview:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader(f"{token['name']} ({token['symbol']})")
            rank = token.get("market_cap_rank")
            price = token.get("price_usd")
            change_30d = token.get("price_change_30d")

            # 指标网格
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

        # BYDFi 跟进建议（概览里也显示）
        urgency = ai.get("bydfi_urgency", "中")
        urgency_icon = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(urgency, "⚪")
        if token.get("listed_on_bydfi"):
            st.success("✅ 已在 BYDFi 上线")
        else:
            st.info(f"{urgency_icon} **BYDFi 跟进紧迫性：{urgency}**　{ai.get('bydfi_urgency_reason', '')}")

    # Tab2: 评分详情
    with tab_scores:
        dim_labels = {
            "market":      ("市场规模",    30),
            "community":   ("社区活跃度",  20),
            "technical":   ("技术实力",    20),
            "competitive": ("竞争位置",    15),
            "risk":        ("风险信号",    15),
        }
        st.markdown("### 各维度评分")
        for key, (label, max_score) in dim_labels.items():
            s = scores[key]
            pct = s["score"] / s["max"]
            icon = _score_color(pct)
            col_icon, col_label, col_bar, col_score = st.columns([0.3, 2, 5, 1])
            col_icon.write(icon)
            col_label.write(f"**{label}**")
            col_bar.progress(pct)
            col_score.write(f"**{s['score']}**/{s['max']}")

        st.divider()
        st.metric("综合总分", f"{total} / 100", delta=None)

        # 风险扣分明细
        deductions = result["rule_scores"]["risk_rules"].get("deductions", [])
        if deductions:
            st.markdown("### 风险扣分明细")
            for d in deductions:
                st.warning(f"**{d['risk']}**（扣 {d['deduction']} 分）　{d['detail']}")
        extra = ai.get("risk_extra_deduction", 0)
        if extra:
            st.warning(f"**AI 识别额外风险**（扣 {extra} 分）　{ai.get('risk_extra_reason', '')}")

        # 社区/技术原始数据
        with st.expander("原始数据明细"):
            raw_cols = {
                "市值排名": token.get("market_cap_rank"),
                "市值 (USD)": _fmt_usd(token.get("market_cap_usd")),
                "24h 交易量": _fmt_usd(token.get("volume_24h_usd")),
                "30日涨跌幅": f"{token.get('price_change_30d', 0):.1f}%" if token.get("price_change_30d") else "N/A",
                "CoinGecko 关注人数": f"{token.get('watchlist_users', 0):,}" if token.get("watchlist_users") else "N/A",
                "Telegram 成员": token.get("telegram_members") or "N/A",
                "GitHub Stars": token.get("github_stars") or "N/A",
                "近4周 Commits": token.get("commit_count_4_weeks") or "N/A",
            }
            for k, v in raw_cols.items():
                c1, c2 = st.columns([2, 3])
                c1.caption(k)
                c2.write(str(v))

    # Tab3: 交易所覆盖
    with tab_exchange:
        listed = token.get("listed_on_major", [])
        other_count = token.get("listed_on_other_count", 0)

        if listed:
            st.markdown(f"### 已上线主流交易所（{len(listed)} 家）")
            # 每行4个展示
            for i in range(0, len(listed), 4):
                cols = st.columns(4)
                for j, ex in enumerate(listed[i:i+4]):
                    is_bydfi = ex == "BYDFi"
                    cols[j].success(f"✅ {ex}") if is_bydfi else cols[j].info(f"📌 {ex}")
            if other_count:
                st.caption(f"另有 {other_count} 家其他交易所")
        else:
            st.warning("未获取到交易所上线信息")

        st.divider()
        st.markdown(f"**竞争位置评分**：{scores['competitive']['score']}/15")
        st.caption(ai.get("competitive_reason", ""))

    # Tab4: AI 分析
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

    # 异常警告（所有 Tab 共享）
    for w in result["rule_scores"].get("warnings", []):
        st.warning(f"⚠️ {w}")


# ── 评估流程 ─────────────────────────────────────────────

def _run_evaluation(coin: dict):
    """执行完整评估流程，带分阶段进度"""
    coin_id = coin["id"]
    cache_key = f"result_{coin_id}"

    if cache_key in st.session_state:
        _render_report(st.session_state[cache_key])
        return

    start_time = time.time()

    # 分阶段进度展示
    progress = st.progress(0, text="准备开始...")
    status = st.empty()

    # 阶段1：数据采集
    status.info(f"📡 正在从 CoinGecko 采集 **{coin['name']}** 数据...")
    progress.progress(10, text="数据采集中...")
    try:
        token_data = get_token_data(coin_id)
    except RuntimeError as e:
        progress.empty()
        status.empty()
        st.error(str(e))
        return
    progress.progress(35, text="数据采集完成 ✓")

    # 阶段2：规则评分
    status.info("📊 规则评分计算中...")
    progress.progress(40, text="规则评分中...")
    rule_scores = compute_rule_scores(token_data)
    progress.progress(55, text="规则评分完成 ✓")

    # 阶段3：Claude 分析
    status.info("🤖 AI 深度分析中（约 10-20 秒）...")
    progress.progress(60, text="AI 分析中...")
    try:
        ai_result = analyze(token_data, rule_scores)
    except RuntimeError as e:
        progress.empty()
        status.empty()
        st.error(str(e))
        return
    progress.progress(90, text="AI 分析完成 ✓")

    # 合并最终评分
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
            "market":      {"score": rule_scores["market"]["score"],           "max": 30},
            "community":   {"score": rule_scores["community"]["score"],        "max": 20},
            "technical":   {"score": rule_scores["technical"]["score"],        "max": 20},
            "competitive": {"score": ai_result.get("competitive_score", 8),   "max": 15},
            "risk":        {"score": risk_final_score,                         "max": 15},
        },
    }
    result["total_score"] = sum(v["score"] for v in result["final_scores"].values())

    progress.progress(100, text="分析完成！")
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

_render_sidebar()

st.title("🔍 Token Lens")
st.caption("BYDFi 上币评估 AI 系统 · 输入 Token 名称，3 分钟内输出结构化报告")

# 侧边栏 demo 快捷键触发后，把 query 预填进输入框
default_query = st.session_state.pop("demo_query", "")

query = st.text_input(
    "Token 名称",
    value=default_query,
    placeholder="输入 Token 名称，如 ETH、SUI、NEAR...",
    label_visibility="collapsed",
)

if not query:
    st.info("👆 输入 Token 名称开始评估，或点击左侧快捷演示按钮")
    st.stop()

with st.spinner("搜索中..."):
    try:
        candidates = search_token(query)
    except RuntimeError as e:
        st.error(str(e))
        st.stop()

if not candidates:
    st.warning(f"未找到「{query}」，请检查拼写或尝试英文名称")
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
