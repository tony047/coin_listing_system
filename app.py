"""
Token Lens — 上币评估 AI 系统
Streamlit 主入口
"""

import os
import time
import streamlit as st
from dotenv import load_dotenv

from collectors.coingecko import search_token, get_token_data
from collectors.defillama import enrich_token_data
from collectors.tokenomics import analyze_tokenomics
from collectors.onchain import get_onchain_data
from analyzer.scorer import compute_rule_scores
from analyzer.claude_analyzer import analyze, analyze_with_reflection
from analyzer.benchmark import find_benchmarks
from report.chart import build_radar_chart
from report.pdf_export import export_pdf
from database import init_db, get_db
from i18n import get_text, get_demo_tokens
from utils.logger import get_logger

logger = get_logger()

# 本地开发读 .env，Streamlit Cloud 读 st.secrets
load_dotenv()
try:
    for key in ["ANTHROPIC_API_KEY", "COINGECKO_API_KEY", "DEMO_MODE"]:
        if key in st.secrets and not os.getenv(key):
            os.environ[key] = st.secrets[key]
except Exception:
    pass  # 本地无 secrets.toml 时跳过

# 初始化数据库
init_db()

# 辅助函数：获取当前语言
def t(key: str, **kwargs) -> str:
    """获取当前语言的文本"""
    lang = st.session_state.get("lang", "zh")
    return get_text(key, lang, **kwargs)

# 路演演示 Token（coin_id 固定，点击直接触发评估，无需搜索选择）
DEMO_TOKENS = [
    {"label": "⭐ ETH",  "id": "ethereum",    "name": "Ethereum",    "symbol": "ETH"},
    {"label": "🔴 HYPE", "id": "hyperliquid", "name": "Hyperliquid", "symbol": "HYPE"},
    {"label": "🟡 SEI",  "id": "sei-network", "name": "Sei",         "symbol": "SEI"},
    {"label": "🔵 SUI",  "id": "sui",         "name": "Sui",         "symbol": "SUI"},
]

# ── 全局样式 ──────────────────────────────────────────────

def _inject_css():
    # 只使用暗色主题
    bg_color = "#0a0a0b"
    text_color = "#fafafa"
    text_muted = "#a1a1aa"
    card_bg = "#141415"
    card_border = "#27272a"
    accent_color = "#6366f1"
    success_color = "#22c55e"
    warning_color = "#eab308"
    danger_color = "#ef4444"
    
    st.markdown(f"""
<style>
/* ===== 隐藏侧边栏 ===== */
section[data-testid="stSidebar"] {{
    display: none !important;
}}
.stApp > div:first-child {{
    margin-left: 0 !important;
}}

/* ===== 全局样式 ===== */
.stApp {{
    background-color: {bg_color};
}}

/* 减少顶部区域空白 */
.main .block-container {{
    padding-top: 1rem;
}}

/* 标题样式 */
h1 {{
    letter-spacing: -0.5px;
    color: {text_color};
    font-weight: 700 !important;
    margin-bottom: 0.25rem !important;
}}

h2, h3, h4 {{
    color: {text_color};
    font-weight: 600 !important;
}}

p, span, div {{
    color: {text_color};
}}

/* ===== 输入框样式 ===== */
[data-testid="stTextInput"] {{
    max-width: 500px !important;
}}

[data-testid="stTextInput"] input {{
    background-color: {card_bg} !important;
    border: 1px solid {card_border} !important;
    color: {text_color} !important;
    border-radius: 8px !important;
    padding: 0.5rem 0.75rem !important;
}}

[data-testid="stTextInput"] input::placeholder {{
    color: {text_muted} !important;
}}

[data-testid="stTextInput"] input:focus {{
    border-color: {accent_color} !important;
    box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
}}

/* ===== 按钮样式 ===== */
.stButton > button {{
    border-radius: 6px !important;
    padding: 0.4rem 0.75rem !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}}

.stButton > button:hover {{
    transform: translateY(-1px) !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
}}

/* 主要按钮 hover 微光效果 */
button[kind="primary"]:hover, .stButton > button[kind="primaryFormSubmit"]:hover {{
    box-shadow: 0 0 20px rgba(99, 102, 241, 0.3) !important;
}}

/* 主要按钮 */
.stButton > button[kind="primary"] {{
    background-color: {accent_color} !important;
    border-color: {accent_color} !important;
}}

/* 侧边栏按钮 */
section[data-testid="stSidebar"] .stButton > button {{
    width: 100% !important;
    text-align: left !important;
    justify-content: flex-start !important;
    font-size: 0.875rem !important;
}}

/* ===== Metric 样式 ===== */
[data-testid="stMetric"] {{
    background-color: {card_bg};
    border: 1px solid {card_border};
    border-radius: 8px;
    padding: 0.75rem !important;
}}

[data-testid="stMetricValue"] {{
    font-size: 1.25rem !important;
    font-weight: 700 !important;
    color: {text_color} !important;
}}

[data-testid="stMetricLabel"] {{
    font-size: 0.75rem !important;
    color: {text_muted} !important;
}}

/* ===== 进度条样式 ===== */
[data-testid="stProgress"] > div > div {{
    height: 10px !important;
    border-radius: 5px !important;
    background-color: {card_border} !important;
}}

[data-testid="stProgress"] > div > div > div {{
    background-color: {accent_color} !important;
}}

/* ===== Tab 样式 ===== */
.stTabs [data-baseweb="tab"] {{
    transition: all 0.2s ease;
    border-radius: 8px 8px 0 0;
    padding: 0.5rem 1rem;
    font-size: 0.875rem !important;
    color: {text_muted} !important;
}}

.stTabs [data-baseweb="tab"]:hover {{
    background: rgba(99, 102, 241, 0.05);
}}

/* Tab 选中态 - 增加底部粗线和背景 */
.stTabs [data-baseweb="tab"][aria-selected="true"] {{
    background: rgba(99, 102, 241, 0.1);
    border-bottom: 3px solid {accent_color};
    color: {text_color} !important;
    font-weight: 600;
}}

/* ===== 侧边栏样式 ===== */
section[data-testid="stSidebar"] {{
    background-color: {card_bg} !important;
    border-right: 1px solid {card_border} !important;
}}

section[data-testid="stSidebar"] .element-container {{
    margin-bottom: 0.5rem !important;
}}

/* ===== 卡片样式 ===== */
.feature-card {{
    padding: 1rem;
    border-radius: 8px;
    border: 1px solid {card_border};
    background: {card_bg};
    color: {text_color};
    margin-bottom: 0.75rem;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}}

.feature-card:hover {{
    transform: translateY(-4px);
    box-shadow: 0 8px 25px rgba(99, 102, 241, 0.15);
    border-color: {accent_color};
}}

.history-card {{
    padding: 0.75rem 1rem;
    border-radius: 6px;
    border: 1px solid {card_border};
    background: {card_bg};
    margin-bottom: 0.5rem;
}}

/* ===== 数据来源标注 ===== */
.data-badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.7rem;
    background: rgba(99, 102, 241, 0.15);
    color: {accent_color};
    margin-left: 4px;
}}

/* ===== 表格样式 ===== */
.stTable {{
    border-radius: 8px !important;
    overflow: hidden !important;
}}

.stTable table {{
    border-collapse: collapse !important;
}}

.stTable th {{
    background-color: {card_bg} !important;
    color: {text_color} !important;
    border-bottom: 2px solid {accent_color} !important;
}}

.stTable td {{
    border-bottom: 1px solid {card_border} !important;
}}

/* 表格行 hover 高亮 */
table tbody tr:hover {{
    background: rgba(99, 102, 241, 0.08) !important;
}}

/* ===== Selectbox 样式 ===== */
[data-testid="stSelectbox"] {{
    max-width: 400px !important;
}}

[data-testid="stSelectbox"] > div > div {{
    background-color: {card_bg} !important;
    border: 1px solid {card_border} !important;
    border-radius: 6px !important;
}}

/* ===== 下载按钮 ===== */
.stDownloadButton > button {{
    font-size: 0.8rem !important;
    padding: 0.35rem 0.6rem !important;
}}

/* ===== 分隔线 ===== */
hr {{
    border-color: {card_border} !important;
}}

[data-testid="stDivider"] {{
    border-color: {card_border} !important;
}}

/* ===== Alert 样式 ===== */
[data-testid="stAlert"] {{
    border-radius: 6px !important;
}}

/* ===== Expander 样式 ===== */
[data-testid="stExpander"] {{
    background-color: {card_bg} !important;
    border: 1px solid {card_border} !important;
    border-radius: 6px !important;
}}

.streamlit-expanderHeader {{
    border-left: 3px solid {accent_color};
    padding-left: 1rem;
}}

/* ===== 文字不换行优化 ===== */
[data-testid="stMetricValue"],
[data-testid="stMetricLabel"] {{
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}}

/* ===== 对比表格 ===== */
.compare-table {{
    width: 100%;
    border-collapse: collapse;
}}
.compare-table th, .compare-table td {{
    padding: 0.5rem;
    text-align: center;
    border-bottom: 1px solid {card_border};
}}
.compare-table th {{
    background: rgba(99, 102, 241, 0.1);
}}

/* ===== 滚动条样式 ===== */
::-webkit-scrollbar {{
    width: 6px;
    height: 6px;
}}
::-webkit-scrollbar-track {{
    background: {card_bg};
}}
::-webkit-scrollbar-thumb {{
    background: {card_border};
    border-radius: 3px;
}}
::-webkit-scrollbar-thumb:hover {{
    background: {text_muted};
}}
</style>
""", unsafe_allow_html=True)


# ── 工具函数 ──────────────────────────────────────────────

def _fmt_usd(value) -> str:
    """格式化美元金额，支持 T/B/M/K 单位"""
    if value is None:
        return "N/A"
    if isinstance(value, str):
        try:
            value = float(value.replace(",", ""))
        except (ValueError, AttributeError):
            return str(value)
    if value >= 1e12:
        return f"${value / 1e12:.2f}T"
    if value >= 1e9:
        return f"${value / 1e9:.2f}B"
    if value >= 1e6:
        return f"${value / 1e6:.2f}M"
    if value >= 1e3:
        return f"${value / 1e3:.1f}K"
    return f"${value:.2f}"


def _score_bar_color(pct: float) -> str:
    """根据得分百分比返回颜色"""
    if pct >= 0.8:
        return "#22c55e"  # 绿色 - 优秀
    elif pct >= 0.6:
        return "#6366f1"  # 蓝色 - 良好
    elif pct >= 0.4:
        return "#eab308"  # 黄色 - 一般
    else:
        return "#ef4444"  # 红色 - 较差


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
        f"| 市场规模 | {scores['market']['score']} | 25 |",
        f"| 社区活跃度 | {scores['community']['score']} | 15 |",
        f"| 技术实力 | {scores['technical']['score']} | 15 |",
        f"| 竞争位置 | {scores['competitive']['score']} | 15 |",
        f"| 风险信号 | {scores['risk']['score']} | 10 |",
        f"| Tokenomics | {scores.get('tokenomics', {}).get('score', 10)} | 10 |",
        f"| 链上健康度 | {scores.get('onchain', {}).get('score', 10)} | 10 |",
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


# ── 诊断面板 ──────────────────────────────────────────────

def _render_diagnostics_panel():
    """渲染系统诊断面板"""
    import json
    db = get_db()
    
    # 第一行：核心指标（4列）
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        try:
            stats = db.get_prediction_stats()
            st.metric(t("diag_total_predictions"), stats.get("total_predictions", 0))
        except Exception:
            st.metric(t("diag_total_predictions"), 0)
    
    with col2:
        try:
            stats = db.get_prediction_stats()
            st.metric(t("diag_verified"), stats.get("verified_count", 0))
        except Exception:
            st.metric(t("diag_verified"), 0)
    
    with col3:
        try:
            stats = db.get_prediction_stats()
            accuracy = stats.get("accuracy_rate")  # Note: get_prediction_stats uses 'accuracy_rate'
            st.metric(t("diag_accuracy"), f"{accuracy:.1%}" if accuracy is not None else "N/A")
        except Exception:
            st.metric(t("diag_accuracy"), "N/A")
    
    with col4:
        # 数据覆盖率：从最近10条评估中统计 tokenomics/onchain 数据可用比例
        try:
            history = db.get_history(limit=10)
            tokenomics_available = 0
            onchain_available = 0
            total_checked = 0
            for record in history:
                try:
                    # get_history returns records without result_json, need to fetch full record
                    full_record = db.get_assessment_by_id(record.get("id"))
                    if not full_record:
                        continue
                    result = full_record.get("result_json", {})
                    if isinstance(result, str):
                        result = json.loads(result)
                    final_scores = result.get("final_scores", {})
                    if final_scores.get("tokenomics", {}).get("data_available", False):
                        tokenomics_available += 1
                    if final_scores.get("onchain", {}).get("data_available", False):
                        onchain_available += 1
                    total_checked += 1
                except Exception:
                    pass
            coverage = f"{tokenomics_available + onchain_available}/{total_checked * 2}" if total_checked > 0 else "N/A"
            st.metric(t("diag_data_coverage"), coverage)
        except Exception:
            st.metric(t("diag_data_coverage"), "N/A")
    
    st.markdown("---")
    
    # 第二行：按结论分类的准确率
    try:
        accuracy_data = db.calculate_accuracy()
        if accuracy_data and accuracy_data.get("verified_predictions", 0) > 0:
            st.subheader(t("diag_accuracy_by_verdict"))
            precision = accuracy_data.get("precision_by_verdict", {})
            
            verdict_cols = st.columns(3)
            for i, (verdict, data) in enumerate(precision.items()):
                with verdict_cols[i % 3]:
                    total = data.get("total", 0)
                    correct = data.get("correct", 0)
                    prec = data.get("precision", 0)
                    st.metric(verdict, f"{prec:.0%}" if total > 0 else "N/A", 
                             delta=f"{correct}/{total}")
        else:
            st.info(t("diag_no_verified_data"))
    except Exception:
        st.info(t("diag_no_verified_data"))
    
    st.markdown("---")
    
    # 第三行：权重优化建议
    st.subheader(t("diag_weight_suggestions"))
    try:
        from analyzer.backtest import BacktestEngine
        engine = BacktestEngine()
        suggestions = engine.suggest_weight_adjustments()
        
        if suggestions and suggestions.get("failure_patterns"):
            for pattern in suggestions["failure_patterns"]:
                st.caption(f"**{pattern.get('dimension', '')}**: {pattern.get('suggestion', '')}")
            
            # 显示建议权重
            suggested = suggestions.get("suggested_weights", {})
            if suggested:
                weight_cols = st.columns(len(suggested))
                for i, (dim, weight) in enumerate(suggested.items()):
                    with weight_cols[i]:
                        st.metric(dim, f"{weight}")
        else:
            st.caption(t("diag_insufficient_data"))
    except Exception as e:
        st.caption(f"⚠️ {t('diag_error')}: {e}")
    
    st.markdown("---")
    
    # 第四行：运行回测按钮
    if st.button(t("diag_run_backtest"), use_container_width=True):
        with st.spinner(t("diag_backtest_running")):
            try:
                from analyzer.backtest import BacktestEngine
                engine = BacktestEngine()
                result = engine.run_backtest(max_records=20)
                st.success(f"✅ {t('diag_backtest_complete')}")
                st.json(result)
            except Exception as e:
                st.error(f"❌ {e}")


# ── 首页引导 ──────────────────────────────────────────────

def _render_homepage():
    """无搜索时展示引导界面"""
    st.markdown(t("welcome_desc"))
    
    # 功能特点 - 卡片布局
    st.markdown("<div style=\"height:1.5rem;\"></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3, gap="small")
    with col1:
        st.markdown(f'''<div class="feature-card" style="text-align:center; padding:1.5rem 1rem;">
        <div style="font-size:2.5rem; margin-bottom:0.75rem;">📡</div>
        <div style="font-weight:700; font-size:1rem; margin-bottom:0.5rem; color:#fafafa;">{t('feature_realtime')}</div>
        <div style="color:#a1a1aa; font-size:0.85rem; line-height:1.5;">{t('feature_realtime_desc')}</div>
        </div>''', unsafe_allow_html=True)
    with col2:
        st.markdown(f'''<div class="feature-card" style="text-align:center; padding:1.5rem 1rem;">
        <div style="font-size:2.5rem; margin-bottom:0.75rem;">🤖</div>
        <div style="font-weight:700; font-size:1rem; margin-bottom:0.5rem; color:#fafafa;">{t('feature_ai')}</div>
        <div style="color:#a1a1aa; font-size:0.85rem; line-height:1.5;">{t('feature_ai_desc')}</div>
        </div>''', unsafe_allow_html=True)
    with col3:
        st.markdown(f'''<div class="feature-card" style="text-align:center; padding:1.5rem 1rem;">
        <div style="font-size:2.5rem; margin-bottom:0.75rem;">🏦</div>
        <div style="font-weight:700; font-size:1rem; margin-bottom:0.5rem; color:#fafafa;">{t('feature_bydfi')}</div>
        <div style="color:#a1a1aa; font-size:0.85rem; line-height:1.5;">{t('feature_bydfi_desc')}</div>
        </div>''', unsafe_allow_html=True)

    # 快速开始区域
    st.markdown(f"<div style='margin-top:1.5rem; margin-bottom:0.5rem; font-size:0.85rem; color:#a1a1aa;'>{t('quick_start')}</div>", unsafe_allow_html=True)
    lang = st.session_state.get("lang", "zh")
    demo_tokens = get_demo_tokens(lang)
    demo_cols = st.columns(len(demo_tokens), gap="small")
    for i, item in enumerate(demo_tokens):
        with demo_cols[i]:
            if st.button(item["label"], use_container_width=True, key=f"home_demo_{item['id']}"):
                st.session_state["auto_coin"] = {"id": item["id"], "name": item["name"], "symbol": item["symbol"]}
                st.rerun()
    
    
    # 评估历史
    history = [k.replace("result_", "") for k in st.session_state if k.startswith("result_")]
    db_history = get_db().get_history(limit=5)
    
    if history or db_history:
        st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:0.85rem; color:#a1a1aa; margin-bottom:0.5rem;'>📝 {t('history_title')}</div>", unsafe_allow_html=True)
        
        seen_ids = set()
        display_records = []
        
        for coin_id in history:
            if coin_id not in seen_ids:
                cached = st.session_state.get(f"result_{coin_id}", {})
                name = cached.get("token_data", {}).get("name", coin_id)
                score = cached.get("total_score", "?")
                display_records.append({"id": coin_id, "name": name, "score": score, "source": "session", "data": cached})
                seen_ids.add(coin_id)
        
        
        for record in db_history:
            if record["coin_id"] not in seen_ids:
                display_records.append({"id": record["coin_id"], "name": record["coin_name"], "score": record["total_score"], "source": "database", "record_id": record["id"], "data": record})
                seen_ids.add(record["coin_id"])
        
        
        # 显示最近5条记录
        hist_cols = st.columns(min(5, len(display_records)), gap="small")
        for i, record in enumerate(display_records[:5]):
            with hist_cols[i]:
                score = record["score"]
                icon = "🟢" if score != "?" and score >= 75 else ("🟡" if score != "?" and score >= 55 else "🔴")
                if st.button(f"{icon} {record['name'][:10]}", key=f"hist_{record['source']}_{record['id']}", use_container_width=True):
                    if record["source"] == "session":
                        cached = record["data"]
                        st.session_state["auto_coin"] = {"id": record["id"], "name": record["name"], "symbol": cached.get("token_data", {}).get("symbol", "")}
                    else:
                        db_result = get_db().get_assessment_by_id(record["record_id"])
                        if db_result:
                            st.session_state[f"result_{record['id']}"] = db_result["result_json"]
                            st.session_state["auto_coin"] = {"id": record["id"], "name": record["name"], "symbol": record["data"]["coin_symbol"]}
                    st.rerun()
    
    # 评分说明
    st.markdown("<div style=\"height:1rem;\"></div>", unsafe_allow_html=True)
    with st.expander(t("score_help")):
        st.markdown(f"""
        | {t('dimension_market')} | 25% |
        |---|---|
        | {t('dimension_community')} | 15% |
        | {t('dimension_technical')} | 15% |
        | {t('dimension_competitive')} | 15% |
        | {t('dimension_risk')} | 10% |
        | {t('dimension_tokenomics')} | 10% |
        | {t('dimension_onchain')} | 10% |
        
        {t('threshold')}
        """)
    
    # 诊断面板（默认折叠）
    with st.expander(t("diagnostics_title"), expanded=False):
        _render_diagnostics_panel()


# ── 报告渲染 ─────────────────────────────────────────────

def _render_report(result: dict):
    token = result["token_data"]
    scores = result["final_scores"]
    ai = result["ai_result"]
    total = result["total_score"]
    elapsed = result.get("elapsed_seconds")
    
    st.divider()
    
    # 结论横幅 - 突出显示
    if total >= 75:
        verdict_class = "success"
        verdict_text = t("verdict_strong")
        color = "#22c55e"
        rgb = "34,197,94"
    elif total >= 55:
        verdict_class = "warning"
        verdict_text = t("verdict_watch")
        color = "#eab308"
        rgb = "234,179,8"
    else:
        verdict_class = "error"
        verdict_text = t("verdict_not_recommend")
        color = "#ef4444"
        rgb = "239,68,68"
    
    lang = st.session_state.get("lang", "zh")
    score_suffix = "分" if lang == "zh" else ""
    st.markdown(f'''
    <div style="padding:1.25rem 1.5rem; border-radius:10px; margin-bottom:0.75rem; background:rgba({rgb},0.15); border-left:4px solid {color}; display:flex; align-items:center; justify-content:space-between;">
        <span style="font-size:1.2rem; color:#fafafa;">{verdict_text}</span>
        <span style="font-size:1.5rem; font-weight:800; color:{color};">{total}/100 {score_suffix}</span>
    </div>
    ''', unsafe_allow_html=True)
    
    # 耗时和下载按钮 - 同一行
    col_time, col_dl = st.columns([2, 1])
    with col_time:
        if elapsed:
            st.caption(t("analysis_time", time=elapsed))
    with col_dl:
        # 下载按钮
        report_md = _generate_report_md(result)
        pdf_bytes = None
        try:
            pdf_bytes = export_pdf(result)
        except Exception:
            pass
            
        # 下载按钮 - 等宽并排
        st.markdown('<div style="display:flex; gap:0.5rem; margin-top:0.25rem;">', unsafe_allow_html=True)
        dl_col1, dl_col2 = st.columns(2, gap="small")
        with dl_col1:
            st.download_button(
                label=f"📄 {t('download_md')}",
                data=report_md,
                file_name=f"token_lens_{token.get('symbol', 'report').lower()}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with dl_col2:
            if pdf_bytes:
                st.download_button(
                    label=f"📑 {t('download_pdf')}",
                    data=pdf_bytes,
                    file_name=f"token_lens_{token.get('symbol', 'report').lower()}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            else:
                st.download_button(
                    label=f"📑 {t('download_pdf')}",
                    data="",
                    file_name="unavailable.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    disabled=True,
                )
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 数据完整性警告
    for w in _data_quality_warnings(token):
        st.warning(f"⚠️ {w}")
    
    # Tab 布局
    tab_overview, tab_scores, tab_exchange, tab_ai = st.tabs(
        [t("tab_overview"), t("tab_scores"), t("tab_exchanges"), t("tab_ai")]
    )
    
    with tab_overview:
        # Token 信息头部
        col1, col2 = st.columns([1.2, 1])
        with col1:
            # Token 名称和基本信息 - 美化样式
            st.markdown(f'''
            <div style="margin-bottom:1rem; border-bottom: 1px solid #27272a; padding-bottom: 0.75rem;">
                <span style="font-size:1.8rem;font-weight:700;color:#fafafa;">{token['name']}</span>
                <span style="background: rgba(99,102,241,0.15); padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.9rem; color:#a1a1aa; margin-left:0.5rem;">{token['symbol']}</span>
            </div>
            ''', unsafe_allow_html=True)
                
            rank = token.get("market_cap_rank")
            price = token.get("price_usd")
            change_30d = token.get("price_change_30d")
                
            # 指标网格
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric(t("metric_rank"), f"#{rank}" if rank else t("na"))
            with m2:
                st.metric(t("metric_cap"), _fmt_usd(token.get("market_cap_usd")))
            with m3:
                st.metric(t("metric_volume"), _fmt_usd(token.get("volume_24h_usd")))
                
            m4, m5, m6 = st.columns(3)
            with m4:
                if price:
                    st.metric(
                        t("metric_price"),
                        f"${price:,.4f}" if price < 1 else f"${price:,.2f}",
                        delta=f"{change_30d:.1f}% (30d)" if change_30d is not None else None,
                    )
            with m5:
                watchlist = token.get("watchlist_users")
                if watchlist:
                    st.metric(t("metric_watchlist"), f"{watchlist:,}")
            with m6:
                sentiment = token.get("sentiment_up_pct")
                if sentiment is not None:
                    st.metric(t("metric_sentiment"), f"{sentiment:.0f}%")
        
        with col2:
            lang = st.session_state.get("lang", "zh")
            fig = build_radar_chart(scores, lang)
            st.plotly_chart(fig, use_container_width=True)
        
        # BYDFi 建议
        st.markdown("<div style=\"height:0.5rem;\"></div>", unsafe_allow_html=True)
        urgency = ai.get("bydfi_urgency", "中")
        urgency_icon = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(urgency, "⚪")
        if token.get("listed_on_bydfi"):
            st.success(t("bydfi_listed"))
        else:
            st.info(f"{urgency_icon} **BYDFi {t('bydfi_suggestion')}**: {urgency}\u3000{ai.get('bydfi_urgency_reason', '')}")
    
    with tab_scores:
        dim_labels = {
            "market":      t("score_market"),
            "community":   t("score_community"),
            "technical":   t("score_technical"),
            "competitive": t("score_competitive"),
            "risk":        t("score_risk"),
            "tokenomics":  t("dimension_tokenomics"),
            "onchain":     t("dimension_onchain"),
        }
        for key, label in dim_labels.items():
            s = scores.get(key, {"score": 0, "max": 1})
            pct = s["score"] / s["max"] if s["max"] > 0 else 0
            icon = _score_color(pct)
            col_icon, col_label, col_bar, col_score = st.columns([0.3, 2, 5, 1])
            col_icon.write(icon)
            col_label.write(f"**{label}**")
            # 自定义 HTML 进度条，根据得分动态配色
            bar_color = _score_bar_color(pct)
            with col_bar:
                bar_html = f'''
                <div style="background:#27272a; border-radius:5px; height:10px; width:100%; overflow:hidden; margin-top:8px;">
                    <div style="background:{bar_color}; width:{pct*100:.1f}%; height:100%; border-radius:5px; transition: width 0.5s ease;"></div>
                </div>
                '''
                st.markdown(bar_html, unsafe_allow_html=True)
            col_score.write(f"**{s['score']}**/{s['max']}")
            
            # 为新维度显示数据可用性和扣分详情
            if key == "tokenomics":
                if not s.get('data_available', True):
                    st.caption("⚠️ Tokenomics 数据暂不可用，使用默认满分")
                elif s.get('deductions'):
                    for d in s['deductions']:
                        reason = d.get('reason', d) if isinstance(d, dict) else str(d)
                        points = d.get('points', 0) if isinstance(d, dict) else 0
                        st.caption(f"  ⚠️ {reason}：-{points} 分")
            elif key == "onchain":
                if not s.get('data_available', True):
                    st.caption("⚠️ 链上数据暂不可用，使用默认满分")
                elif s.get('deductions'):
                    for d in s['deductions']:
                        reason = d.get('reason', d) if isinstance(d, dict) else str(d)
                        points = d.get('points', 0) if isinstance(d, dict) else 0
                        st.caption(f"  ⚠️ {reason}：-{points} 分")

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
                        # BYDFi 卡片 - 发光突出效果
                        cols[j].markdown(f'''
                        <div style="padding:0.75rem 1rem; border-radius:8px; text-align:center;
                                    background:rgba(34,197,94,0.15); border:1px solid #22c55e;
                                    box-shadow: 0 0 15px rgba(34,197,94,0.2);
                                    color:#22c55e; font-weight:600;">
                            ✅ {ex}
                        </div>
                        ''', unsafe_allow_html=True)
                    else:
                        cols[j].markdown(f'''
                        <div style="padding:0.75rem 1rem; border-radius:8px; text-align:center;
                                    background:rgba(99,102,241,0.08); border:1px solid #3f3f46;
                                    color:#a1a1aa;">
                            📌 {ex}
                        </div>
                        ''', unsafe_allow_html=True)
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
            st.markdown(t("ai_reasons"))
            for reason in ai.get("top_reasons", []):
                st.markdown(f'''
                <div style="padding:0.6rem 1rem; margin-bottom:0.5rem; border-radius:8px; 
                            background:rgba(34,197,94,0.08); border-left:3px solid #22c55e;
                            color:#e4e4e7; font-size:0.9rem; line-height:1.6;">
                    ✅ {reason}
                </div>
                ''', unsafe_allow_html=True)
        with col_b:
            st.markdown(t("ai_risks"))
            for risk in ai.get("top_risks", []):
                st.markdown(f'''
                <div style="padding:0.6rem 1rem; margin-bottom:0.5rem; border-radius:8px; 
                            background:rgba(234,179,8,0.08); border-left:3px solid #eab308;
                            color:#e4e4e7; font-size:0.9rem; line-height:1.6;">
                    ⚠️ {risk}
                </div>
                ''', unsafe_allow_html=True)
    
        st.divider()
        st.markdown(t("bydfi_suggestion"))
        urgency = ai.get("bydfi_urgency", "中")
        urgency_icon = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(urgency, "⚪")
        st.markdown(f"{urgency_icon} **{t('urgency', icon=urgency_icon, urgency=urgency)}**: {ai.get('bydfi_urgency_reason', '')}")
    
        if ai.get("demo_mode"):
            st.caption("ℹ️ Demo mode: AI analysis generated by rules")
        if ai.get("parse_error"):
            st.caption("⚠️ AI analysis error, using default scores")
    
    # 规则引擎社区警告
    for w in result["rule_scores"].get("warnings", []):
        st.warning(f"⚠️ {w}")


# ── 评估流程 ─────────────────────────────────────────────

def _run_evaluation(coin: dict, force_refresh: bool = False):
    coin_id = coin["id"]
    cache_key = f"result_{coin_id}"

    if not force_refresh and cache_key in st.session_state:
        _render_report(st.session_state[cache_key])
        return

    start_time = time.time()
    progress = st.progress(0, text=t("progress_preparing"))
    status = st.empty()

    # 阶段1：数据采集
    status.info(f"📡 CoinGecko: **{coin['name']}**...")
    progress.progress(5, text=t("progress_fetching"))
    try:
        token_data = get_token_data(coin_id)
    except RuntimeError as e:
        progress.empty()
        status.empty()
        st.error(f"{t('search_failed', error=str(e))}")
        st.button(t("refresh"), on_click=st.rerun)
        return
    
    # 阶1.5：DeFiLlama 数据丰富
    progress.progress(25, text=t("progress_defi"))
    status.info(f"📊 {t('progress_defi')}")
    try:
        token_data = enrich_token_data(coin_id, token_data)
    except Exception:
        pass  # DeFiLlama 数据失败不影响主流程
    progress.progress(30, text=t("progress_done"))
    
    # 阶2：Tokenomics 分析（新增）
    progress.progress(35, text="Tokenomics 分析...")
    status.info("📊 Tokenomics 分析...")
    try:
        tokenomics_data = analyze_tokenomics(token_data)
        logger.info(f"Tokenomics 分析完成: data_available={tokenomics_data.get('data_available')}")
    except Exception as e:
        logger.warning(f"Tokenomics 分析失败: {e}")
        tokenomics_data = None
    
    # 阶2.5：链上数据（新增）
    progress.progress(40, text="链上数据分析...")
    status.info("🔗 链上数据...")
    try:
        onchain_data = get_onchain_data(token_data)
        logger.info(f"链上数据获取完成: data_available={onchain_data.get('data_available')}")
    except Exception as e:
        logger.warning(f"链上数据获取失败: {e}")
        onchain_data = None
    
    # 阶2.8：基准对标（新增）
    progress.progress(45, text="基准对标...")
    status.info("📊 基准对标...")
    benchmark_projects = []
    try:
        benchmark_projects, benchmark_text = find_benchmarks(token_data, limit=5)
        # 将基准对标信息注入 token_data 供 Claude 使用
        token_data["benchmark_info"] = benchmark_text
        logger.info(f"基准对标完成: 找到 {len(benchmark_projects)} 个相似项目")
    except Exception as e:
        logger.warning(f"基准对标分析失败: {e}")
        token_data["benchmark_info"] = ""
    
    # 阶3：规则评分（更新：传入新数据）
    status.info(f"📊 {t('progress_scoring')}")
    progress.progress(50, text=t("progress_scoring"))
    rule_scores = compute_rule_scores(token_data, tokenomics_data=tokenomics_data, onchain_data=onchain_data)
    progress.progress(55, text=t("progress_done"))

    # 阶4：Claude 分析（增强：使用多轮反思）
    status.info(f"🤖 {t('progress_ai')}")
    progress.progress(60, text=t("progress_ai"))
        
    # 将 tokenomics 和 onchain 数据也传入 token_data 供 Claude 使用
    if tokenomics_data:
        token_data["tokenomics_analysis"] = tokenomics_data
    if onchain_data:
        token_data["onchain_analysis"] = onchain_data
        
    try:
        # 使用增强分析（非 Demo 模式下启用多轮反思）
        ai_result = analyze_with_reflection(token_data, rule_scores)
    except Exception as e:
        logger.warning(f"多轮反思分析失败，降级到普通分析: {e}")
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
    
    # 计算风险最终分（基于规则评分 + AI 补充扣分 + 反思调整）
    reflection_adjustment = ai_result.get("reflection_adjustment", 0)
    risk_final_score = max(
        0,
        rule_scores["risk_rules"]["score"] - ai_result.get("risk_extra_deduction", 0) - reflection_adjustment
    )
        
    # 竞争位置评分（需缩放到新满分15，与旧保持一致）
    competitive_score = ai_result.get("competitive_score", 8)
    
    result = {
        "token_data": token_data,
        "rule_scores": rule_scores,
        "ai_result": ai_result,
        "elapsed_seconds": time.time() - start_time,
        "final_scores": {
            "market":      {"score": rule_scores["market"]["score"],         "max": 25},
            "community":   {"score": rule_scores["community"]["score"],      "max": 15},
            "technical":   {"score": rule_scores["technical"]["score"],      "max": 15},
            "competitive": {"score": competitive_score,                       "max": 15},
            "risk":        {"score": risk_final_score,                        "max": 10},
            "tokenomics":  rule_scores.get("tokenomics", {"score": 10, "max": 10}),
            "onchain":     rule_scores.get("onchain", {"score": 10, "max": 10}),
        },
        # 新增字段
        "tokenomics_data": tokenomics_data,
        "onchain_data": onchain_data,
        "benchmark_projects": benchmark_projects,
        "confidence_level": ai_result.get("confidence_level", 0.8),
        "data_contradictions": ai_result.get("data_contradictions", []),
    }
    result["total_score"] = sum(v["score"] for v in result["final_scores"].values())

    progress.progress(100, text="✅ 分析完成！")
    time.sleep(0.3)
    progress.empty()
    status.empty()

    st.session_state[cache_key] = result
    
    # 保存到数据库
    assessment_id = None
    try:
        verdict = "强烈推荐" if result["total_score"] >= 75 else ("建议观望" if result["total_score"] >= 55 else "不建议")
        assessment_id = get_db().save_assessment(
            coin_id=coin_id,
            coin_name=token_data["name"],
            coin_symbol=token_data["symbol"],
            total_score=result["total_score"],
            verdict=verdict,
            result=result,
        )
    except Exception as e:
        logger.warning(f"数据库保存失败: {e}")
    
    # 保存预测记录（在 save_assessment 之后）
    try:
        if assessment_id:
            db = get_db()
            db.save_prediction(
                assessment_id=assessment_id,
                coin_id=coin_id,
                coin_name=token_data.get("name", ""),
                predicted_score=result["total_score"],
                predicted_verdict=verdict
            )
            logger.info(f"预测记录已保存: assessment_id={assessment_id}")
    except Exception as e:
        logger.warning(f"保存预测记录失败: {e}")
    
    _render_report(result)


# ── 页面主体 ─────────────────────────────────────────────

st.set_page_config(
    page_title="BYDFi - Token Assessment System",
    page_icon="📊",
    layout="wide",
)

_inject_css()

# 顶部导航栏 - BYDFi Logo + 语言切换同行
col_title, col_lang = st.columns([5, 1])
with col_title:
    st.markdown('''
    <div style="padding-top:0.5rem; display:flex; align-items:center; gap:0.75rem;">
        <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAAAV1BMVEVHcEz4uzcSFiL6xTj4uzf4uzf4uzf4uzf6vjf5vDcICiASFiL4uzf7vTcRFSISFiIPEhwOEyESFiL4uzf4uzcIDSEOFCISFiL4uzcSFiL4uzcSFiL4uzcbZniUAAAAG3RSTlMAcewG9orQwRZCE9PpKIK7BjtlWdsmTKSrMppy/mljAAABCklEQVQ4jXWS27aDIBBDRxABFa+1tS3//52HI04sqHmaJVmbMJG+uxZKpXwUseE1JOemzA3fKTEUng2CDc0NYQKiI6t3VQUjWqobIGpTMfhh9lkRjUC8yLLBr3GuTLiuh2MhDYfb5vk/zxs5+8G1bNAyzDom7oB4Yj++nMNso2EAQpAEoiWp+NEHYjo25AuSbBiQUywSOVt37O15vYufzfZI+cEV9nf1o9j7QAe+SuvfcoqRVjzTpoZaxF0D8Ml+oK3Vmh4AmNwQWu1oRkKVn4ecTe0AqE6AoPdRRGzxJIdzfXl+1JA/kYUmLxKmiKuEEaH3nm9lTy3mWvMWT4gyb/GU8+6JLKNk+uEPSjAvNsI1XKcAAAAASUVORK5CYII=" alt="BYDFi" style="width:32px; height:32px;">
        <span style="font-size:1.5rem; font-weight:800; background: linear-gradient(135deg, #fbbf24, #f59e0b); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">BYDFi</span>
    </div>
    <div style="color:#71717a; font-size:0.75rem; margin-top:0.1rem;">Token Assessment System</div>
    ''', unsafe_allow_html=True)
with col_lang:
    current_lang = st.session_state.get("lang", "zh")
    lang_options = {"zh": "🇨🇳 中文", "en": "🇺🇸 EN"}
    selected_lang = st.selectbox(
        "Language",
        options=list(lang_options.keys()),
        format_func=lambda x: lang_options[x],
        index=0 if current_lang == "zh" else 1,
        label_visibility="collapsed",
        key="lang_selector_main",
    )
    if selected_lang != current_lang:
        st.session_state["lang"] = selected_lang
        st.rerun()

# 搜索框 - 注入CSS让搜索框和按钮紧贴
st.markdown("""
<style>
    /* 搜索区域 - 消除列间距 */
    div[data-testid="stColumns"]:has(div[data-testid="stTextInput"]) {
        gap: 0 !important;
    }
    div[data-testid="stColumns"]:has(div[data-testid="stTextInput"]) > div {
        padding-left: 0 !important;
        padding-right: 0 !important;
    }
    /* 搜索按钮列只保留最小左内距 */
    div[data-testid="stColumns"]:has(div[data-testid="stTextInput"]) > div:last-child {
        padding-left: 0.25rem !important;
    }
    /* 重置/新搜索按钮样式 - 深色背景 */
    div[data-testid="stButton"] > button[kind="secondary"] {
        background-color: #27272a !important;
        border: 1px solid #3f3f46 !important;
        color: #a1a1aa !important;
    }
    div[data-testid="stButton"] > button[kind="secondary"]:hover {
        background-color: #3f3f46 !important;
        border-color: #52525b !important;
        color: #e4e4e7 !important;
    }
</style>
""", unsafe_allow_html=True)
col_search, col_btn, col_spacer = st.columns([3, 1, 4], gap="small")
with col_search:
    query = st.text_input(
        "Token",
        placeholder=t("search_placeholder"),
        label_visibility="collapsed",
    )
with col_btn:
    search_clicked = st.button(t("search_button"), type="primary", use_container_width=True)

# 搜索提示文字 - 小字号置灰
st.markdown(f'<div style="color:#71717a; font-size:0.75rem; margin-top:-0.5rem; margin-bottom:0.5rem;">{t("search_hint")}</div>', unsafe_allow_html=True)

# ── 快速演示：直接触发评估，跳过搜索和选择 ──────────────
auto_coin = st.session_state.pop("auto_coin", None)
if auto_coin:
    cache_key = f"result_{auto_coin['id']}"
    force_refresh = auto_coin.pop("force_refresh", False)
    st.markdown(f"**{auto_coin['name']} ({auto_coin['symbol']})**")
    if cache_key in st.session_state and not force_refresh:
        if st.button(t("refresh"), key="refresh_auto"):
            del st.session_state[cache_key]
            st.session_state["auto_coin"] = auto_coin
            st.rerun()
    _run_evaluation(auto_coin, force_refresh=force_refresh)
    st.stop()

# ── 手动搜索流程 ──────────────────────────────────────────
# 保存搜索结果到 session_state
if search_clicked and query:
    with st.spinner(t("search_button")):
        try:
            candidates = search_token(query)
            st.session_state["search_candidates"] = candidates
            st.session_state["search_query"] = query
        except RuntimeError as e:
            st.error(f"搜索失败：{e}")
            st.stop()

# 获取保存的搜索结果
candidates = st.session_state.get("search_candidates", [])
saved_query = st.session_state.get("search_query", "")

# 如果没有搜索词或搜索结果，显示首页
if not query and not candidates:
    _render_homepage()
    st.stop()

if not candidates:
    _render_homepage()
    st.stop()

if candidates and saved_query:
    # 显示搜索结果
    if not candidates:
        st.warning(t("search_not_found", query=saved_query))
        st.stop()

    # 选择 Token - 紧凑布局
    st.markdown(f"**{t('search_results', count=len(candidates))}**")
    options = [f"{c['name']} ({c['symbol']})" for c in candidates]
    selected_idx = st.selectbox("Token", range(len(options)), 
                               format_func=lambda i: options[i], 
                               label_visibility="collapsed")
    coin = candidates[selected_idx]

    cache_key = f"result_{coin['id']}"
    col_btn, col_refresh, col_spacer = st.columns([1, 1, 4])
    with col_btn:
        run = st.button(t("start_evaluation"), type="primary", use_container_width=True)
    with col_refresh:
        # 重置按钮 - 使用 secondary 类型（深灰色背景）
        if st.button(t("new_search"), type="secondary", use_container_width=True):
            # 清除搜索状态
            st.session_state.pop("search_candidates", None)
            st.session_state.pop("search_query", None)
            st.rerun()

    if run:
        if cache_key in st.session_state:
            del st.session_state[cache_key]
        _run_evaluation(coin, force_refresh=True)
    elif cache_key in st.session_state:
        _render_report(st.session_state[cache_key])


# ── 批量评估页面 ──────────────────────────────────────────
if st.session_state.get("show_batch"):
    st.divider()
    st.header(t("batch_title"))
    
    # 清除标记
    if st.button("← 返回"):
        st.session_state["show_batch"] = False
        st.rerun()
    
    st.markdown("输入多个 Token 名称（每行一个），系统将依次评估")
    
    batch_input = st.text_area(
        "Token 列表",
        placeholder="ethereum\nbitcoin\nsui\nnear\n...",
        height=150,
    )
    
    if st.button("🚀 开始批量评估", type="primary"):
        tokens = [t.strip() for t in batch_input.split("\n") if t.strip()]
        if tokens:
            st.session_state["batch_tokens"] = tokens
            st.session_state["batch_index"] = 0
            st.session_state["batch_results"] = []
            st.rerun()
    
    # 显示批量评估进度
    if st.session_state.get("batch_tokens"):
        tokens = st.session_state["batch_tokens"]
        idx = st.session_state.get("batch_index", 0)
        results = st.session_state.get("batch_results", [])
        
        if idx < len(tokens):
            st.info(f"正在评估第 {idx + 1}/{len(tokens)} 个 Token: **{tokens[idx]}**")
            st.progress(idx / len(tokens))
            
            # 自动继续下一个
            if st.button("继续", key="batch_continue"):
                st.session_state["batch_index"] = idx + 1
                st.rerun()
        else:
            st.success(f"✅ 批量评估完成！共评估 {len(results)} 个 Token")
            
            # 显示结果摘要
            for r in results:
                score = r.get("total_score", "?")
                icon = "🟢" if isinstance(score, int) and score >= 75 else ("🟡" if isinstance(score, int) and score >= 55 else "🔴")
                st.markdown(f"{icon} **{r.get('name', '?')}**: {score} 分")
    
    st.stop()


# ── 对比页面 ──────────────────────────────────────────────
if st.session_state.get("show_compare"):
    st.divider()
    st.header("📊 Token 对比")
    
    if st.button("← 返回"):
        st.session_state["show_compare"] = False
        st.rerun()
    
    compare_list = st.session_state.get("compare_list", [])
    
    if len(compare_list) < 2:
        st.warning("请至少选择 2 个 Token 进行对比")
    else:
        # 对比表格
        st.subheader("评分对比")
        
        # 表头
        headers = ["维度"] + [f"{c['name']} ({c['symbol']})" for c in compare_list]
        
        # 表格数据
        rows = []
        dim_labels = {
            "market": "市场规模",
            "community": "社区活跃度",
            "technical": "技术实力",
            "competitive": "竞争位置",
            "risk": "风险信号",
            "tokenomics": "Tokenomics",
            "onchain": "链上健康度",
        }
        
        for key, label in dim_labels.items():
            row = [label]
            for c in compare_list:
                result = st.session_state.get(f"result_{c['id']}", {})
                scores = result.get("final_scores", {})
                score = scores.get(key, {}).get("score", "?")
                max_score = scores.get(key, {}).get("max", "?")
                row.append(f"{score}/{max_score}")
            rows.append(row)
        
        
        # 总分行
        total_row = ["总分"]
        for c in compare_list:
            result = st.session_state.get(f"result_{c['id']}", {})
            total_row.append(str(result.get("total_score", "?")))
        rows.append(total_row)
        
        # 显示表格
        import pandas as pd
        df = pd.DataFrame(rows, columns=headers)
        st.table(df)
        
        # 清空对比列表
        if st.button("清空对比列表"):
            st.session_state["compare_list"] = []
            st.rerun()
    
    st.stop()

