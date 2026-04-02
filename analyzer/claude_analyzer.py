"""
Claude 分析模块
负责后2个维度：竞争位置（15分）、风险信号最终分（含语义判断）
以及生成自然语言分析文字
"""

import json
import os
import re
import time

import anthropic

try:
    from ..utils.logger import get_logger, log_function_call
except ImportError:
    from utils.logger import get_logger, log_function_call

logger = get_logger()

MODEL = "claude-sonnet-4-6"

# 头部交易所分级（用于竞争位置评分参考）
TIER1_EXCHANGES = {"Binance", "Coinbase Exchange", "OKX", "Bybit", "Kraken"}
TIER2_EXCHANGES = {"Bitget", "KuCoin", "Gate", "MEXC", "HTX", "Bitfinex", "Crypto.com Exchange", "Gemini"}

SYSTEM_PROMPT = """你是 BYDFi 交易所的资深上币分析师。
你的职责是评估加密货币项目是否值得上线 BYDFi，需要结合数据做出客观、专业的判断。
分析时要直接、具体，避免模糊表述。所有判断必须基于提供的数据，不得依赖训练集中的历史印象。

严格遵守以下数据约束规则：
1. 所有数字必须来自「输入数据」部分，禁止引用训练集中的历史数据或记忆中的数字
2. 如果输入数据中某字段为 null 或缺失，则不得在分析中提及该指标的具体数值
3. 分析时必须解释「为什么」而非仅说「是什么」
4. 当发现数据矛盾时（如高市值但低交易量、高社区关注但低开发活跃度），必须在 data_contradictions 字段中明确指出并分析原因

特别关注以下三类风险信号：
1. 数据质量风险：关键指标缺失或异常
2. 数据矛盾风险：多个指标之间逻辑不一致
3. 供应风险：流通比例过低、无最大供应量限制等 Tokenomics 问题"""


def _build_prompt(token_data: dict, rule_scores: dict) -> str:
    """构建传给 Claude 的结构化 prompt"""
    listed_major = token_data.get("listed_on_major", [])
    listed_other_count = token_data.get("listed_on_other_count", 0)
    listed_on_bydfi = token_data.get("listed_on_bydfi", False)

    # 计算 Tier1/Tier2 覆盖数，作为评分参考
    tier1_count = len(set(listed_major) & TIER1_EXCHANGES)
    tier2_count = len(set(listed_major) & TIER2_EXCHANGES)

    input_data = {
        "token": {
            "name": token_data.get("name"),
            "symbol": token_data.get("symbol"),
            "description": token_data.get("description", "")[:400],
            "market_cap_rank": token_data.get("market_cap_rank"),
            "market_cap_usd": token_data.get("market_cap_usd"),
            "volume_24h_usd": token_data.get("volume_24h_usd"),
            "price_change_30d": token_data.get("price_change_30d"),
            "watchlist_users": token_data.get("watchlist_users"),
            "sentiment_up_pct": token_data.get("sentiment_up_pct"),
            "github_stars": token_data.get("github_stars"),
            "commit_count_4_weeks": token_data.get("commit_count_4_weeks"),
        },
        "rule_scores": {
            "market_score": rule_scores["market"]["score"],
            "community_score": rule_scores["community"]["score"],
            "technical_score": rule_scores["technical"]["score"],
            "rule_risk_score": rule_scores["risk_rules"]["score"],
            "rule_risk_deductions": rule_scores["risk_rules"]["deductions"],
        },
        "exchange_listing": {
            "major_exchanges": listed_major,
            "tier1_count": tier1_count,
            "tier2_count": tier2_count,
            "other_exchange_count": listed_other_count,
            "already_on_bydfi": listed_on_bydfi,
        },
    }

    # 构建 Tokenomics 数据区块（如有）
    tokenomics_section = ""
    total_supply = token_data.get("total_supply")
    circulating_supply = token_data.get("circulating_supply")
    max_supply = token_data.get("max_supply")
    if total_supply is not None or circulating_supply is not None or max_supply is not None:
        tokenomics_lines = ["\n## Tokenomics 数据"]
        if total_supply is not None:
            tokenomics_lines.append(f"- 总供应量: {total_supply:,.0f}")
        if circulating_supply is not None:
            tokenomics_lines.append(f"- 流通供应量: {circulating_supply:,.0f}")
        if max_supply is not None:
            tokenomics_lines.append(f"- 最大供应量: {max_supply:,.0f}")
            has_max_supply = True
        else:
            has_max_supply = False
            tokenomics_lines.append("- 是否有最大供应量限制: 否")
        if total_supply and circulating_supply:
            circulation_ratio = circulating_supply / total_supply
            tokenomics_lines.append(f"- 流通比例: {circulation_ratio:.1%}")
        if max_supply is not None:
            tokenomics_lines.append(f"- 是否有最大供应量限制: 是")
        tokenomics_section = "\n".join(tokenomics_lines)

    # 构建链上数据区块（如有）
    onchain_section = ""
    concentration_risk = token_data.get("concentration_risk")
    top_10_holder_pct = token_data.get("top_10_holder_pct")
    total_holders = token_data.get("total_holders")
    if concentration_risk is not None or top_10_holder_pct is not None or total_holders is not None:
        onchain_lines = ["\n## 链上数据"]
        if concentration_risk is not None:
            onchain_lines.append(f"- 持有者浓度风险: {concentration_risk}")
        if top_10_holder_pct is not None:
            onchain_lines.append(f"- Top 10 持有者占比: {top_10_holder_pct:.1%}")
        if total_holders is not None:
            onchain_lines.append(f"- 持有者总数: {total_holders:,}")
        onchain_section = "\n".join(onchain_lines)

    # 构建基准对标区块（如有）
    benchmark_section = ""
    benchmark_info = token_data.get("benchmark_info")
    if benchmark_info:
        benchmark_section = f"\n## 基准对标\n{benchmark_info}"

    # 拼接可选数据区块
    optional_sections = tokenomics_section + onchain_section + benchmark_section

    competitive_rubric = """
竞争位置评分标准（0-15分）：
- 13-15分：覆盖 4+ 家 Tier1 交易所（Binance/Coinbase/OKX/Bybit/Kraken）
- 10-12分：覆盖 2-3 家 Tier1 交易所
-  7-9分：覆盖 1 家 Tier1 + 多家 Tier2，或 3+ 家 Tier2
-  4-6分：仅上线 1-2 家 Tier2 交易所
-  1-3分：极少主流交易所，市场认知度低
-    0分：未在任何已知主流交易所上线

⚠️ 重要：exchange_listing.major_exchanges 是实时抓取的数据，必须以此为准，不得用训练记忆替代。"""

    bydfi_urgency_rubric = """
BYDFi 跟进紧迫性判断标准：
- 高：已上 Binance/OKX/Coinbase 等头部所，但 BYDFi 尚未上线 → 竞争压力大，需尽快跟进
- 中：主要在 Tier2 所流通，BYDFi 还有先机，但需评估用户需求
- 低：满足以下任一 → (1) BYDFi 已上线 (2) 项目风险过高 (3) 市场关注度不足"""

    return f"""请基于以下数据，完成 Token 上币评估分析。

## 输入数据
{json.dumps(input_data, ensure_ascii=False, indent=2)}{optional_sections}

## 评分任务

### 任务1：竞争位置评分
{competitive_rubric}

### 任务2：语义风险补充判断
规则引擎已处理客观风险（见 rule_risk_deductions）。
你需要识别规则无法捕捉的语义层风险，例如：
- 赛道严重过饱和（同类项目 5+ 家已上主流所）
- 项目描述模糊，无法明确用例
- 市值排名与交易量严重倒挂（可能存在刷量）
最多额外扣 2 分，无明显额外风险则为 0。

### 任务3：推荐理由与风险点
基于全部数据给出 3 条核心推荐/反对理由，2 条最需关注的风险。
要求：具体、有数据支撑，避免"发展潜力大"这类空话。
⚠️ 严格限制：所有数字（价格、涨跌幅、交易量、市值等）必须来自上方"输入数据"，
   禁止引用训练集中的历史数据或个人记忆中的数字。如输入数据中某字段为 null，
   则不得在分析中提及该数据点的具体数值。

### 任务4：BYDFi 跟进紧迫性
{bydfi_urgency_rubric}

### 任务5：一句话总结
面向 BYDFi 决策者，直接说结论，包含关键数据支撑。

## 输出格式
严格输出 JSON，不加任何额外文字，直接从 {{ 开始：

{{
  "competitive_score": <0-15的整数>,
  "competitive_reason": "<基于实际交易所数据的1-2句说明>",
  "risk_extra_deduction": <0或1或2>,
  "risk_extra_reason": "<额外风险说明，无则为空字符串>",
  "top_reasons": ["<含数据的具体理由1>", "<含数据的具体理由2>", "<含数据的具体理由3>"],
  "top_risks": ["<具体风险1>", "<具体风险2>"],
  "bydfi_urgency": "<高|中|低>",
  "bydfi_urgency_reason": "<1句具体理由>",
  "summary": "<面向决策者的一句话结论，含关键数据>",
  "confidence_level": <0-1的浮点数，对最终评分的置信度>,
  "data_contradictions": ["<数据矛盾1>", "<数据矛盾2>"]  // 可为空数组
}}"""


def _validate_scores(result: dict) -> dict:
    """校验并修正分数范围"""
    result["competitive_score"] = max(0, min(15, int(result.get("competitive_score", 8))))
    result["risk_extra_deduction"] = max(0, min(2, int(result.get("risk_extra_deduction", 0))))

    # 确保列表字段存在
    if not isinstance(result.get("top_reasons"), list):
        result["top_reasons"] = [str(result.get("top_reasons", ""))]
    if not isinstance(result.get("top_risks"), list):
        result["top_risks"] = [str(result.get("top_risks", ""))]

    # 截取到合理数量
    result["top_reasons"] = result["top_reasons"][:3]
    result["top_risks"] = result["top_risks"][:2]

    # 紧迫性只允许特定值
    if result.get("bydfi_urgency") not in ("高", "中", "低"):
        result["bydfi_urgency"] = "中"

    # 解析新增字段：置信度和数据矛盾
    confidence = result.get("confidence_level", 0.8)
    try:
        result["confidence_level"] = max(0.0, min(1.0, float(confidence)))
    except (ValueError, TypeError):
        result["confidence_level"] = 0.8

    if not isinstance(result.get("data_contradictions"), list):
        result["data_contradictions"] = []

    return result


def _parse_response(text: str) -> dict:
    """解析 Claude 输出，带容错处理"""
    if not text:
        return _fallback_result()

    # 剥掉可能存在的 markdown 代码块
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    raw = match.group(1) if match else text.strip()

    # 文本不以 { 开始时，尝试提取 JSON 部分
    if not raw.startswith("{"):
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            raw = json_match.group(0)

    try:
        result = json.loads(raw)
        return _validate_scores(result)
    except (json.JSONDecodeError, ValueError):
        return _fallback_result()


def _fallback_result() -> dict:
    """Claude 解析失败时的降级返回"""
    return {
        "competitive_score": 8,
        "competitive_reason": "AI 分析异常，以规则评分为准",
        "risk_extra_deduction": 0,
        "risk_extra_reason": "",
        "top_reasons": ["AI 分析模块异常，当前展示规则评分结果"],
        "top_risks": ["建议人工核查"],
        "bydfi_urgency": "中",
        "bydfi_urgency_reason": "AI 分析异常，建议人工核查",
        "summary": "AI 分析模块异常，请参考规则评分结果。",
        "parse_error": True,
        "confidence_level": 0.8,
        "data_contradictions": [],
    }


def _demo_analyze(token_data: dict, rule_scores: dict) -> dict:
    """
    Demo 模式：基于规则评分自动生成合理的 AI 分析结果
    用于 API 不可用时的路演备用，保证报告完整可展示
    """
    listed_major = token_data.get("listed_on_major", [])
    tier1_count = len(set(listed_major) & TIER1_EXCHANGES)
    tier2_count = len(set(listed_major) & TIER2_EXCHANGES)

    # 竞争位置评分（基于交易所覆盖的简化规则）
    if tier1_count >= 4:
        competitive_score = 14
        competitive_reason = f"已覆盖 {tier1_count} 家 Tier1 交易所，头部市场认可度极高。"
    elif tier1_count >= 2:
        competitive_score = 11
        competitive_reason = f"覆盖 {tier1_count} 家 Tier1 交易所，主流市场认可度良好。"
    elif tier1_count == 1:
        competitive_score = 8
        competitive_reason = f"仅覆盖 1 家 Tier1 交易所，另有 {tier2_count} 家 Tier2，市场覆盖偏窄。"
    elif tier2_count >= 3:
        competitive_score = 6
        competitive_reason = f"覆盖 {tier2_count} 家 Tier2 交易所，尚未进入头部所。"
    else:
        competitive_score = 3
        competitive_reason = "主流交易所覆盖极少，市场认知度有限。"

    # BYDFi 紧迫性
    on_bydfi = token_data.get("listed_on_bydfi", False)
    if on_bydfi:
        urgency, urgency_reason = "低", "该 Token 已在 BYDFi 上线，无需新增上币决策。"
    elif tier1_count >= 3:
        urgency, urgency_reason = "高", f"已上 {tier1_count} 家头部交易所，BYDFi 尚未跟进，竞争压力大。"
    elif tier1_count >= 1:
        urgency, urgency_reason = "中", "已上部分头部所，BYDFi 可评估用户需求后决策。"
    else:
        urgency, urgency_reason = "低", "主流交易所覆盖有限，市场需求待验证。"

    # 自动生成理由（基于数据）
    name = token_data.get("name", "该 Token")
    rank = token_data.get("market_cap_rank")
    volume = token_data.get("volume_24h_usd") or 0
    commits = token_data.get("commit_count_4_weeks")
    watchlist = token_data.get("watchlist_users")
    deductions = rule_scores["risk_rules"]["deductions"]

    reasons = []
    if rank and rank <= 50:
        reasons.append(f"市值排名 #{rank}，属于市场头部项目，用户认知度高")
    elif rank and rank <= 200:
        reasons.append(f"市值排名 #{rank}，中型项目，有一定市场基础")
    if volume >= 100_000_000:
        reasons.append(f"24h 交易量 ${volume/1e6:.0f}M，流动性充裕，上币风险低")
    if commits and commits >= 10:
        reasons.append(f"近4周 GitHub 提交 {commits} 次，项目开发持续活跃")
    if watchlist and watchlist >= 100_000:
        reasons.append(f"CoinGecko 关注人数 {watchlist:,}，社区关注度高")
    if len(reasons) < 3:
        reasons.append(f"已上线 {len(listed_major)} 家主流交易所，市场流通性有保障")
    reasons = reasons[:3]

    risks = []
    for d in deductions[:2]:
        risks.append(d["risk"] + "：" + d["detail"])
    if not risks:
        risks.append("市场波动风险：加密市场整体波动可能影响短期价格")
    if len(risks) < 2:
        risks.append("赛道竞争风险：同类项目众多，需持续关注竞争格局变化")
    risks = risks[:2]

    # 总结
    total_rule = (rule_scores["market"]["score"] + rule_scores["community"]["score"] +
                  rule_scores["technical"]["score"] + rule_scores["risk_rules"]["score"] +
                  competitive_score)
    if total_rule >= 75:
        conclusion = f"{name} 综合评分强劲，市值排名 #{rank}，建议优先上线。"
    elif total_rule >= 55:
        conclusion = f"{name} 综合评分中等，建议观望并跟踪后续数据变化。"
    else:
        conclusion = f"{name} 综合评分偏低，当前不建议上线，建议持续观察。"

    return {
        "competitive_score": competitive_score,
        "competitive_reason": competitive_reason,
        "risk_extra_deduction": 0,
        "risk_extra_reason": "",
        "top_reasons": reasons,
        "top_risks": risks,
        "bydfi_urgency": urgency,
        "bydfi_urgency_reason": urgency_reason,
        "summary": conclusion,
        "demo_mode": True,
        "confidence_level": 0.75,
        "data_contradictions": [],
    }


@log_function_call
def analyze(token_data: dict, rule_scores: dict) -> dict:
    """
    调用 Claude 完成竞争位置分析 + 语义风险判断 + 文字生成
    返回 Claude 分析结果字典
    DEMO_MODE=true 时跳过 Claude，用规则自动生成分析结果
    """
    token_name = token_data.get("name", "Unknown")

    # Demo 模式：无需 API Key，路演备用
    if os.getenv("DEMO_MODE", "").lower() == "true":
        logger.info(f"Using demo mode for {token_name}")
        return _demo_analyze(token_data, rule_scores)

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key or api_key.startswith("sk-ant-api03-xxx"):
        error_msg = "未配置有效的 ANTHROPIC_API_KEY，请在 .env 中填入真实 Key"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    start_time = time.time()
    client = anthropic.Anthropic(api_key=api_key)
    prompt = _build_prompt(token_data, rule_scores)

    try:
        logger.api_call("Claude", f"analyze({token_name})", {"model": MODEL})
        logger.info(f"Starting Claude analysis for {token_name}")

        message = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = message.content[0].text

        duration = time.time() - start_time
        logger.api_success("Claude.analyze", duration)
        logger.info(f"Claude analysis completed for {token_name} in {duration:.2f}s")

        return _parse_response(response_text)

    except anthropic.APITimeoutError as e:
        duration = time.time() - start_time
        logger.error(f"Claude API timeout for {token_name}: {e}")
        logger.warning("Using fallback result due to timeout")
        return _fallback_result()

    except anthropic.AuthenticationError as e:
        duration = time.time() - start_time
        error_msg = "ANTHROPIC_API_KEY 无效，请检查 .env 配置"
        logger.error(f"{error_msg}: {e}")
        raise RuntimeError(error_msg)

    except anthropic.RateLimitError as e:
        duration = time.time() - start_time
        error_msg = "Claude API 请求频率过高，请稍后重试"
        logger.error(f"{error_msg}: {e}")
        raise RuntimeError(error_msg)

    except anthropic.BadRequestError as e:
        duration = time.time() - start_time
        # 余额不足也会报 400 BadRequest
        msg = str(e)
        if "credit balance" in msg or "too low" in msg:
            error_msg = "Anthropic 账户余额不足，请前往 console.anthropic.com 充值"
            logger.error(f"{error_msg}: {e}")
            raise RuntimeError(error_msg)
        error_msg = f"Claude API 请求错误：{e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    except anthropic.APIError as e:
        duration = time.time() - start_time
        error_msg = f"Claude API 错误：{e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    except Exception as e:
        duration = time.time() - start_time
        error_msg = f"Claude 分析过程中发生未知错误：{e}"
        logger.error(error_msg)
        logger.warning("Using fallback result due to unexpected error")
        return _fallback_result()


def _parse_reflection_response(text: str) -> dict:
    """
    解析反思轮次的 Claude 输出
    
    Args:
        text: Claude 返回的原始文本
        
    Returns:
        包含反思结果的字典，失败时返回默认值
    """
    default_result = {
        "risk_adjustment": 0,
        "adjustment_reason": "",
        "missed_signals": [],
        "final_confidence": 0.8,
    }
    
    if not text:
        return default_result
    
    # 剥掉可能存在的 markdown 代码块
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    raw = match.group(1) if match else text.strip()
    
    # 文本不以 { 开始时，尝试提取 JSON 部分
    if not raw.startswith("{"):
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            raw = json_match.group(0)
    
    try:
        result = json.loads(raw)
        # 校验并限制调整范围
        adjustment = result.get("risk_adjustment", 0)
        try:
            result["risk_adjustment"] = max(-2, min(2, int(adjustment)))
        except (ValueError, TypeError):
            result["risk_adjustment"] = 0
        
        confidence = result.get("final_confidence", 0.8)
        try:
            result["final_confidence"] = max(0.0, min(1.0, float(confidence)))
        except (ValueError, TypeError):
            result["final_confidence"] = 0.8
        
        if not isinstance(result.get("missed_signals"), list):
            result["missed_signals"] = []
        
        if not isinstance(result.get("adjustment_reason"), str):
            result["adjustment_reason"] = str(result.get("adjustment_reason", ""))
        
        return result
    except (json.JSONDecodeError, ValueError):
        return default_result


@log_function_call
def analyze_with_reflection(token_data: dict, rule_scores: dict) -> dict:
    """
    多轮反思分析（仅在非 Demo 模式下使用）
    
    通过两轮 Claude 调用实现深度分析：
    - 第一轮：调用现有 analyze() 获取初步结果
    - 第二轮：发送反思 prompt，检查数据矛盾和不确定区域
    - 合并结果：基于反思调整风险扣分（最多额外 +-2 分）
    
    Args:
        token_data: Token 的原始数据字典
        rule_scores: 规则评分结果字典
        
    Returns:
        与 analyze() 相同格式的 dict，额外包含：
        - reflection_adjustment: int  # 反思调整的分数 (-2 到 +2)
        - analysis_depth: 'DEEP'  # 标记为深度分析
    """
    token_name = token_data.get("name", "Unknown")
    
    # Demo 模式：直接返回 analyze() 结果，不做反思
    if os.getenv("DEMO_MODE", "").lower() == "true":
        logger.info(f"Demo mode: skipping reflection for {token_name}")
        result = analyze(token_data, rule_scores)
        result["reflection_adjustment"] = 0
        result["analysis_depth"] = "STANDARD"
        return result
    
    # 检查 API key 是否可用
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key or api_key.startswith("sk-ant-api03-xxx"):
        logger.warning(f"API key not available, skipping reflection for {token_name}")
        result = analyze(token_data, rule_scores)
        result["reflection_adjustment"] = 0
        result["analysis_depth"] = "STANDARD"
        return result
    
    # 第一轮：获取初步分析结果
    logger.info(f"Starting reflection analysis for {token_name} - Round 1")
    initial_result = analyze(token_data, rule_scores)
    
    # 如果初步分析失败，直接返回
    if initial_result.get("parse_error") or initial_result.get("demo_mode"):
        logger.warning(f"Initial analysis failed or in demo mode, skipping reflection for {token_name}")
        initial_result["reflection_adjustment"] = 0
        initial_result["analysis_depth"] = "STANDARD"
        return initial_result
    
    # 构建反思 prompt
    reflection_prompt = f"""基于以下初步评估结果，请反思以下几点：

## 初步评估结果
{json.dumps(initial_result, ensure_ascii=False, indent=2)}

## 反思要求
1. 数据中是否存在未被充分关注的矛盾信号？
2. 如果有 Tokenomics 数据，流通比例和供应结构是否对风险判断有影响？
3. 你对竞争位置评分的置信度如何？有哪些不确定因素？
4. 综合考虑所有因素，你建议对风险评分做 -2 到 +2 的调整吗？

请以 JSON 格式回答：
{{
  "risk_adjustment": 0,  // -2到+2，正数表示增加风险扣分
  "adjustment_reason": "说明调整原因",
  "missed_signals": ["可能遗漏的信号1"],
  "final_confidence": 0.85  // 调整后的置信度
}}"""
    
    # 第二轮：反思分析
    try:
        logger.info(f"Starting reflection analysis for {token_name} - Round 2")
        client = anthropic.Anthropic(api_key=api_key)
        
        start_time = time.time()
        logger.api_call("Claude", f"reflection({token_name})", {"model": MODEL})
        
        message = client.messages.create(
            model=MODEL,
            max_tokens=512,
            system="你是一位严谨的风险分析师，负责审核初步评估结果并提出调整建议。",
            messages=[{"role": "user", "content": reflection_prompt}],
        )
        response_text = message.content[0].text
        
        duration = time.time() - start_time
        logger.api_success("Claude.reflection", duration)
        logger.info(f"Reflection analysis completed for {token_name} in {duration:.2f}s")
        
        # 解析反思结果
        reflection_result = _parse_reflection_response(response_text)
        
        # 合并结果
        final_result = initial_result.copy()
        final_result["reflection_adjustment"] = reflection_result["risk_adjustment"]
        final_result["analysis_depth"] = "DEEP"
        
        # 更新置信度（使用反思后的置信度）
        final_result["confidence_level"] = reflection_result["final_confidence"]
        
        # 如果反思发现了遗漏的信号，追加到 data_contradictions
        if reflection_result["missed_signals"]:
            existing_contradictions = final_result.get("data_contradictions", [])
            final_result["data_contradictions"] = existing_contradictions + reflection_result["missed_signals"]
        
        # 添加反思原因（如果有调整）
        if reflection_result["risk_adjustment"] != 0:
            final_result["reflection_reason"] = reflection_result["adjustment_reason"]
        
        logger.info(f"Reflection for {token_name}: adjustment={reflection_result['risk_adjustment']}, confidence={reflection_result['final_confidence']}")
        
        return final_result
        
    except Exception as e:
        logger.error(f"Reflection analysis failed for {token_name}: {e}")
        logger.warning("Returning initial result without reflection")
        # 反思失败时，返回初步结果并标记
        initial_result["reflection_adjustment"] = 0
        initial_result["analysis_depth"] = "STANDARD"
        initial_result["reflection_error"] = str(e)
        return initial_result
