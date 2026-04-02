"""
多语言支持模块
"""

# 语言配置
LANGUAGES = {
    "zh": {  # 中文
        # 标题
        "app_title": "🔍 Token Lens",
        "app_subtitle": "BYDFi 上币评估 AI 系统 · 实时数据 · Claude 驱动",
        "sidebar_title": "🔍 Token Lens",
        "sidebar_subtitle": "BYDFi 上币评估系统",
        
        # 搜索
        "search_placeholder": "输入 Token 名称，如 ETH、HYPE、SUI...",
        "search_button": "🔍 搜索",
        "search_hint": "输入任意 Token 名称，3 分钟内输出结构化上币评估报告。",
        "search_results": "找到 {count} 个结果",
        "search_not_found": "未找到「{query}」，请检查拼写或尝试英文名称",
        "search_failed": "搜索失败：{error}",
        
        # 按钮
        "start_evaluation": "🚀 开始评估",
        "refresh": "🔄 刷新",
        "download_md": "📥 MD 报告",
        "download_pdf": "📄 PDF 报告",
        "download_md_only": "📥 下载 MD 报告",
        
        # 快速演示
        "quick_demo": "快速演示",
        "quick_start": "🚀 快速开始",
        "batch_eval": "📦 批量评估",
        "compare": "📊 对比 ({count}个)",
        
        # 系统信息
        "system_info": "系统信息",
        "ai_model": "AI: claude-sonnet-4-6",
        "data_source": "数据: CoinGecko 实时",
        "demo_mode": "⚠️ Demo 模式",
        "api_status": "API: {status}",
        
        # 评分说明
        "score_help": "评分说明",
        "dimension_market": "市场规模",
        "dimension_community": "社区活跃",
        "dimension_technical": "技术实力",
        "dimension_competitive": "竞争位置",
        "dimension_risk": "风险信号",
        "dimension_tokenomics": "Tokenomics",
        "dimension_onchain": "链上健康度",
        "threshold": "阈值: 🟢≥75 / 🟡55-74 / 🔴<55",
        
        # 评估记录
        "history_title": "评估记录",
        "add_to_compare": "添加到对比",
        "added": "已添加!",
        
        # 首页
        "welcome": "### 👋 欢迎使用 Token Lens",
        "welcome_desc": "输入任意 Token 名称，**3 分钟内**输出结构化上币评估报告。",
        "feature_realtime": "实时数据",
        "feature_realtime_desc": "CoinGecko 实时抓取",
        "feature_ai": "AI 分析",
        "feature_ai_desc": "Claude 驱动评估",
        "feature_bydfi": "BYDFi 视角",
        "feature_bydfi_desc": "跟进紧迫性建议",
        "try_hint": "💡 点击左侧 **快速演示** 按钮立即体验，或在上方搜索框输入 Token 名称",
        
        # 报告
        "verdict_strong": "🟢 <strong>强烈推荐上币</strong>",
        "verdict_watch": "🟡 <strong>建议观望</strong>",
        "verdict_not_recommend": "🔴 <strong>不建议上币</strong>",
        "analysis_time": "⏱️ 分析耗时 {time:.1f} 秒",
        
        # Tabs
        "tab_overview": "📊 概览",
        "tab_scores": "📈 评分详情",
        "tab_exchanges": "🏦 交易所覆盖",
        "tab_ai": "🤖 AI 分析",
        
        # 指标
        "metric_rank": "市值排名",
        "metric_cap": "市值",
        "metric_volume": "24h 交易量",
        "metric_price": "当前价格",
        "metric_watchlist": "CoinGecko 关注",
        "metric_sentiment": "看涨情绪",
        
        # 评分维度
        "score_market": "市场规模",
        "score_community": "社区活跃度",
        "score_technical": "技术实力",
        "score_competitive": "竞争位置",
        "score_risk": "风险信号",
        "total_score": "综合总分",
        
        # AI 分析
        "ai_reasons": "### ✅ 推荐理由",
        "ai_risks": "### ⚠️ 风险点",
        "bydfi_suggestion": "### BYDFi 跟进建议",
        "urgency": "紧迫性：{icon} {urgency}",
        "listed_exchanges": "已上线主流交易所：{exchanges}",
        "bydfi_listed": "✅ 已上线 BYDFi",
        "bydfi_not_listed": "❌ 未上线 BYDFi",
        
        # 进度
        "progress_preparing": "准备开始...",
        "progress_fetching": "数据采集中...",
        "progress_defi": "获取 DeFi 数据...",
        "progress_scoring": "规则评分中...",
        "progress_ai": "AI 分析中...",
        "progress_done": "✅ 分析完成！",
        
        # 批量评估
        "batch_title": "📦 批量评估",
        "batch_back": "← 返回",
        "batch_desc": "输入多个 Token 名称（每行一个），系统将依次评估",
        "batch_placeholder": "ethereum\nbitcoin\nsui\nnear\n...",
        "batch_start": "🚀 开始批量评估",
        "batch_evaluating": "正在评估第 {current}/{total} 个 Token: **{name}**",
        "batch_done": "✅ 批量评估完成！共评估 {count} 个 Token",
        
        # 对比
        "compare_title": "📊 Token 对比",
        "compare_warning": "请至少选择 2 个 Token 进行对比",
        "compare_score": "评分对比",
        "compare_dimension": "维度",
        "compare_total": "总分",
        "compare_clear": "清空对比列表",
        
        # 其他
        "na": "N/A",
        
        # 诊断面板
        "diagnostics_title": "📊 系统诊断",
        "diag_total_predictions": "预测总数",
        "diag_verified": "已验证",
        "diag_accuracy": "准确率",
        "diag_data_coverage": "数据覆盖",
        "diag_accuracy_by_verdict": "各结论准确率",
        "diag_no_verified_data": "暂无已验证的预测数据，评估记录满30天后将自动验证",
        "diag_weight_suggestions": "权重优化建议",
        "diag_insufficient_data": "数据不足，需要更多已验证的评估记录",
        "diag_error": "诊断异常",
        "diag_run_backtest": "🔄 运行回测",
        "diag_backtest_running": "正在回测...",
        "diag_backtest_complete": "回测完成",
        "progress_tokenomics": "Tokenomics 分析...",
        "progress_onchain": "链上数据分析...",
        "progress_benchmark": "基准对标...",
        "new_search": "重置搜索",
        
        "demo_tokens": [
            {"label": "⭐ ETH", "id": "ethereum", "name": "Ethereum", "symbol": "ETH"},
            {"label": "🔴 HYPE", "id": "hyperliquid", "name": "Hyperliquid", "symbol": "HYPE"},
            {"label": "🟡 SEI", "id": "sei-network", "name": "Sei", "symbol": "SEI"},
            {"label": "🔵 SUI", "id": "sui", "name": "Sui", "symbol": "SUI"},
        ],
    },
    "en": {  # English
        # Title
        "app_title": "🔍 Token Lens",
        "app_subtitle": "BYDFi Token Assessment AI System · Real-time Data · Claude Powered",
        "sidebar_title": "🔍 Token Lens",
        "sidebar_subtitle": "BYDFi Token Assessment System",
        
        # Search
        "search_placeholder": "Enter token name, e.g. ETH, HYPE, SUI...",
        "search_button": "🔍 Search",
        "search_hint": "Enter any token name to get a structured assessment report in 3 minutes.",
        "search_results": "Found {count} results",
        "search_not_found": "Token「{query}」not found, please check spelling",
        "search_failed": "Search failed: {error}",
        
        # Buttons
        "start_evaluation": "🚀 Start Assessment",
        "refresh": "🔄 Refresh",
        "download_md": "📥 MD Report",
        "download_pdf": "📄 PDF Report",
        "download_md_only": "📥 Download MD Report",
        
        # Quick Demo
        "quick_demo": "Quick Demo",
        "quick_start": "🚀 Quick Start",
        "batch_eval": "📦 Batch Assessment",
        "compare": "📊 Compare ({count} items)",
        
        # System Info
        "system_info": "System Info",
        "ai_model": "AI: claude-sonnet-4-6",
        "data_source": "Data: CoinGecko Real-time",
        "demo_mode": "⚠️ Demo Mode",
        "api_status": "API: {status}",
        
        # Score Help
        "score_help": "Scoring Guide",
        "dimension_market": "Market Cap",
        "dimension_community": "Community",
        "dimension_technical": "Technology",
        "dimension_competitive": "Competition",
        "dimension_risk": "Risk",
        "dimension_tokenomics": "Tokenomics",
        "dimension_onchain": "On-chain Health",
        "threshold": "Threshold: 🟢≥75 / 🟡55-74 / 🔴<55",
        
        # History
        "history_title": "Assessment History",
        "add_to_compare": "Add to compare",
        "added": "Added!",
        
        # Homepage
        "welcome": "### 👋 Welcome to Token Lens",
        "welcome_desc": "Enter any token name to get a **structured assessment report in 3 minutes**.",
        "feature_realtime": "Real-time Data",
        "feature_realtime_desc": "CoinGecko Live Fetch",
        "feature_ai": "AI Analysis",
        "feature_ai_desc": "Claude Powered",
        "feature_bydfi": "BYDFi Perspective",
        "feature_bydfi_desc": "Urgency Suggestions",
        "try_hint": "💡 Click **Quick Demo** on the left to try, or enter a token name above",
        
        # Report
        "verdict_strong": "🟢 <strong>Strongly Recommend</strong>",
        "verdict_watch": "🟡 <strong>Watch</strong>",
        "verdict_not_recommend": "🔴 <strong>Not Recommended</strong>",
        "analysis_time": "⏱️ Analysis time: {time:.1f}s",
        
        # Tabs
        "tab_overview": "📊 Overview",
        "tab_scores": "📈 Score Details",
        "tab_exchanges": "🏦 Exchange Coverage",
        "tab_ai": "🤖 AI Analysis",
        
        # Metrics
        "metric_rank": "Market Cap Rank",
        "metric_cap": "Market Cap",
        "metric_volume": "24h Volume",
        "metric_price": "Current Price",
        "metric_watchlist": "CoinGecko Watchers",
        "metric_sentiment": "Bullish Sentiment",
        
        # Score Dimensions
        "score_market": "Market Cap",
        "score_community": "Community Activity",
        "score_technical": "Technology",
        "score_competitive": "Competitive Position",
        "score_risk": "Risk Signals",
        "total_score": "Total Score",
        
        # AI Analysis
        "ai_reasons": "### ✅ Reasons to Recommend",
        "ai_risks": "### ⚠️ Risk Factors",
        "bydfi_suggestion": "### BYDFi Listing Suggestion",
        "urgency": "Urgency: {icon} {urgency}",
        "listed_exchanges": "Listed on major exchanges: {exchanges}",
        "bydfi_listed": "✅ Listed on BYDFi",
        "bydfi_not_listed": "❌ Not listed on BYDFi",
        
        # Progress
        "progress_preparing": "Preparing...",
        "progress_fetching": "Fetching data...",
        "progress_defi": "Fetching DeFi data...",
        "progress_scoring": "Calculating scores...",
        "progress_ai": "AI analyzing...",
        "progress_done": "✅ Analysis complete!",
        
        # Batch Assessment
        "batch_title": "📦 Batch Assessment",
        "batch_back": "← Back",
        "batch_desc": "Enter multiple token names (one per line)",
        "batch_placeholder": "ethereum\nbitcoin\nsui\nnear\n...",
        "batch_start": "🚀 Start Batch Assessment",
        "batch_evaluating": "Assessing {current}/{total}: **{name}**",
        "batch_done": "✅ Batch assessment complete! {count} tokens assessed",
        
        # Compare
        "compare_title": "📊 Token Comparison",
        "compare_warning": "Please select at least 2 tokens to compare",
        "compare_score": "Score Comparison",
        "compare_dimension": "Dimension",
        "compare_total": "Total",
        "compare_clear": "Clear comparison list",
        
        # Other
        "na": "N/A",
        
        # Diagnostics Panel
        "diagnostics_title": "📊 System Diagnostics",
        "diag_total_predictions": "Total Predictions",
        "diag_verified": "Verified",
        "diag_accuracy": "Accuracy",
        "diag_data_coverage": "Data Coverage",
        "diag_accuracy_by_verdict": "Accuracy by Verdict",
        "diag_no_verified_data": "No verified prediction data yet. Records will be auto-verified after 30 days.",
        "diag_weight_suggestions": "Weight Optimization Suggestions",
        "diag_insufficient_data": "Insufficient data, need more verified assessment records",
        "diag_error": "Diagnostics Error",
        "diag_run_backtest": "🔄 Run Backtest",
        "diag_backtest_running": "Running backtest...",
        "diag_backtest_complete": "Backtest completed",
        "progress_tokenomics": "Tokenomics analysis...",
        "progress_onchain": "On-chain data analysis...",
        "progress_benchmark": "Benchmark comparison...",
        "new_search": "Reset Search",
        
        "demo_tokens": [
            {"label": "⭐ ETH", "id": "ethereum", "name": "Ethereum", "symbol": "ETH"},
            {"label": "🔴 HYPE", "id": "hyperliquid", "name": "Hyperliquid", "symbol": "HYPE"},
            {"label": "🟡 SEI", "id": "sei-network", "name": "Sei", "symbol": "SEI"},
            {"label": "🔵 SUI", "id": "sui", "name": "Sui", "symbol": "SUI"},
        ],
    }
}


def get_text(key: str, lang: str = "zh", **kwargs) -> str:
    """
    获取文本
    
    Args:
        key: 文本键
        lang: 语言代码 (zh/en)
        **kwargs: 格式化参数
        
    Returns:
        文本内容
    """
    lang_dict = LANGUAGES.get(lang, LANGUAGES["zh"])
    text = lang_dict.get(key, LANGUAGES["zh"].get(key, key))
    
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    
    return text


def get_demo_tokens(lang: str = "zh") -> list:
    """获取演示 Token 列表"""
    lang_dict = LANGUAGES.get(lang, LANGUAGES["zh"])
    return lang_dict.get("demo_tokens", LANGUAGES["zh"]["demo_tokens"])
