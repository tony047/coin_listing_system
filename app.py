"""
Token Lens — 上币评估 AI 系统
Streamlit 主入口
"""

import os
import streamlit as st
from dotenv import load_dotenv

from collectors.coingecko import search_token, get_token_data
from analyzer.scorer import compute_rule_scores
from analyzer.claude_analyzer import analyze
from report.chart import build_radar_chart

# 本地开发读 .env，Streamlit Cloud 读 st.secrets
load_dotenv()
for key in ["ANTHROPIC_API_KEY", "COINGECKO_API_KEY"]:
    if key in st.secrets and not os.getenv(key):
        os.environ[key] = st.secrets[key]

st.set_page_config(
    page_title="Token Lens — 上币评估系统",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 Token Lens — 上币评估系统")
st.caption("输入 Token 名称，3 分钟内输出结构化上币评估报告")

# ── 搜索区域 ──────────────────────────────────────────────

query = st.text_input(
    "Token 名称",
    placeholder="输入 Token 名称，如 SUI、NEAR、OP...",
    label_visibility="collapsed",
)

if not query:
    st.stop()

# 搜索候选列表
with st.spinner("搜索中..."):
    try:
        candidates = search_token(query)
    except RuntimeError as e:
        st.error(str(e))
        st.stop()

if not candidates:
    st.warning(f"未找到「{query}」，请检查拼写或尝试英文名称")
    st.stop()

# 候选选择
options = [f"{c['name']} ({c['symbol']})" for c in candidates]
selected_idx = st.selectbox("选择 Token", range(len(options)), format_func=lambda i: options[i])
coin = candidates[selected_idx]

if st.button("开始评估", type="primary"):
    _run_evaluation(coin)


def _run_evaluation(coin: dict):
    """执行完整评估流程"""
    coin_id = coin["id"]

    # 使用 session_state 缓存，避免重复调用
    cache_key = f"result_{coin_id}"
    if cache_key in st.session_state:
        _render_report(st.session_state[cache_key])
        return

    # ── 数据采集 ─────────────────────────────────
    with st.spinner(f"正在采集 {coin['name']} 数据..."):
        try:
            token_data = get_token_data(coin_id)
        except RuntimeError as e:
            st.error(str(e))
            return

    # ── 规则评分 ─────────────────────────────────
    with st.spinner("规则评分计算中..."):
        rule_scores = compute_rule_scores(token_data)

    # ── Claude 分析 ──────────────────────────────
    with st.spinner("AI 分析中..."):
        try:
            ai_result = analyze(token_data, rule_scores)
        except RuntimeError as e:
            st.error(str(e))
            return

    # 合并最终评分
    risk_final_score = max(
        0,
        rule_scores["risk_rules"]["score"] - ai_result.get("risk_extra_deduction", 0)
    )

    result = {
        "token_data": token_data,
        "rule_scores": rule_scores,
        "ai_result": ai_result,
        "final_scores": {
            "market": {"score": rule_scores["market"]["score"], "max": 30},
            "community": {"score": rule_scores["community"]["score"], "max": 20},
            "technical": {"score": rule_scores["technical"]["score"], "max": 20},
            "competitive": {"score": ai_result.get("competitive_score", 8), "max": 15},
            "risk": {"score": risk_final_score, "max": 15},
        },
    }
    result["total_score"] = sum(v["score"] for v in result["final_scores"].values())

    # 缓存结果
    st.session_state[cache_key] = result
    _render_report(result)


def _render_report(result: dict):
    """渲染评估报告"""
    token = result["token_data"]
    scores = result["final_scores"]
    ai = result["ai_result"]
    total = result["total_score"]

    st.divider()

    # ── 基础信息 + 雷达图 ─────────────────────────
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader(f"{token['name']} ({token['symbol']})")
        market_cap = token.get("market_cap_usd")
        volume = token.get("volume_24h_usd")
        rank = token.get("market_cap_rank")
        price = token.get("price_usd")

        st.metric("市值排名", f"#{rank}" if rank else "N/A")
        st.metric("市值", _fmt_usd(market_cap))
        st.metric("24h 交易量", _fmt_usd(volume))
        if price:
            st.metric("当前价格", f"${price:,.4f}" if price < 1 else f"${price:,.2f}")

    with col2:
        fig = build_radar_chart(scores)
        st.plotly_chart(fig, use_container_width=True)

    # ── 各维度评分条 ──────────────────────────────
    st.subheader("各维度评分")
    dim_labels = {
        "market": "市场规模",
        "community": "社区活跃度",
        "technical": "技术实力",
        "competitive": "竞争位置",
        "risk": "风险信号",
    }
    for key, label in dim_labels.items():
        s = scores[key]
        pct = s["score"] / s["max"]
        st.write(f"**{label}**　{s['score']}/{s['max']}")
        st.progress(pct)

    st.metric("**总分**", f"{total} / 100")

    # 异常警告
    warnings = result["rule_scores"].get("warnings", [])
    if warnings:
        for w in warnings:
            st.warning(f"⚠️ {w}")

    # ── Claude 分析文字 ───────────────────────────
    st.subheader("AI 分析")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**✅ 推荐理由**")
        for reason in ai.get("top_reasons", []):
            st.markdown(f"• {reason}")

    with col_b:
        st.markdown("**⚠️ 风险点**")
        for risk in ai.get("top_risks", []):
            st.markdown(f"• {risk}")

    # ── BYDFi 跟进建议 ────────────────────────────
    st.subheader("BYDFi 跟进建议")
    urgency = ai.get("bydfi_urgency", "中")
    urgency_color = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(urgency, "⚪")
    st.markdown(f"{urgency_color} **紧迫性：{urgency}**")
    st.markdown(ai.get("bydfi_urgency_reason", ""))

    listed = token.get("listed_on_major", [])
    if listed:
        st.caption(f"已上线主流交易所：{', '.join(listed)}")
    if token.get("listed_on_bydfi"):
        st.success("✅ 已在 BYDFi 上线")
    else:
        st.info("ℹ️ 尚未在 BYDFi 上线")

    # ── 最终结论 ──────────────────────────────────
    st.divider()
    if total >= 75:
        st.success(f"🟢 **强烈推荐上币**　总分 {total} — {ai.get('summary', '')}")
    elif total >= 55:
        st.warning(f"🟡 **建议观望**　总分 {total} — {ai.get('summary', '')}")
    else:
        st.error(f"🔴 **不建议上币**　总分 {total} — {ai.get('summary', '')}")


def _fmt_usd(value) -> str:
    """格式化美元金额"""
    if value is None:
        return "N/A"
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    return f"${value:,.0f}"
