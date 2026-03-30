"""
Claude 分析模块
负责后2个维度：竞争位置（15分）、风险信号最终分（含语义判断）
以及生成自然语言分析文字
"""

import json
import os
import re

import anthropic

MODEL = "claude-sonnet-4-6"

# 头部交易所分级（用于竞争位置评分参考）
TIER1_EXCHANGES = {"Binance", "Coinbase Exchange", "OKX", "Bybit", "Kraken"}
TIER2_EXCHANGES = {"Bitget", "KuCoin", "Gate.io", "MEXC", "Huobi", "Bitfinex", "Crypto.com Exchange", "Gemini"}

SYSTEM_PROMPT = """你是 BYDFi 交易所的资深上币分析师。
你的职责是评估加密货币项目是否值得上线 BYDFi，需要结合数据做出客观、专业的判断。
分析时要直接、具体，避免模糊表述。所有判断必须基于提供的数据，不得依赖训练集中的历史印象。"""


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
{json.dumps(input_data, ensure_ascii=False, indent=2)}

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
  "summary": "<面向决策者的一句话结论，含关键数据>"
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
    }


def analyze(token_data: dict, rule_scores: dict) -> dict:
    """
    调用 Claude 完成竞争位置分析 + 语义风险判断 + 文字生成
    返回 Claude 分析结果字典
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key or api_key.startswith("sk-ant-api03-xxx"):
        raise RuntimeError("未配置有效的 ANTHROPIC_API_KEY，请在 .env 中填入真实 Key")

    client = anthropic.Anthropic(api_key=api_key)
    prompt = _build_prompt(token_data, rule_scores)

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = message.content[0].text
        return _parse_response(response_text)
    except anthropic.APITimeoutError:
        return _fallback_result()
    except anthropic.AuthenticationError:
        raise RuntimeError("ANTHROPIC_API_KEY 无效，请检查 .env 配置")
    except anthropic.RateLimitError:
        raise RuntimeError("Claude API 请求频率过高，请稍后重试")
    except anthropic.APIError as e:
        raise RuntimeError(f"Claude API 错误：{e}")
