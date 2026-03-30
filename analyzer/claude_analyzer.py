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


def _build_prompt(token_data: dict, rule_scores: dict) -> str:
    """构建传给 Claude 的结构化 prompt"""
    listed_major = token_data.get("listed_on_major", [])
    listed_other_count = token_data.get("listed_on_other_count", 0)
    listed_on_bydfi = token_data.get("listed_on_bydfi", False)

    exchange_info = {
        "major": listed_major,
        "other_count": listed_other_count,
        "on_bydfi": listed_on_bydfi,
    }

    input_data = {
        "token": {
            "name": token_data.get("name"),
            "symbol": token_data.get("symbol"),
            "description": token_data.get("description", "")[:300],
            "market_cap_rank": token_data.get("market_cap_rank"),
            "market_cap_usd": token_data.get("market_cap_usd"),
            "volume_24h_usd": token_data.get("volume_24h_usd"),
            "price_change_30d": token_data.get("price_change_30d"),
            "telegram_members": token_data.get("telegram_members"),
            "reddit_subscribers": token_data.get("reddit_subscribers"),
            "github_stars": token_data.get("github_stars"),
            "commit_count_4_weeks": token_data.get("commit_count_4_weeks"),
        },
        "rule_scores": {
            "market": rule_scores["market"]["score"],
            "community": rule_scores["community"]["score"],
            "technical": rule_scores["technical"]["score"],
            "risk_rule_deductions": rule_scores["risk_rules"]["deductions"],
            "risk_rule_score": rule_scores["risk_rules"]["score"],
        },
        "exchange_listing": exchange_info,
    }

    return f"""你是一个专业的加密货币上币评估分析师。请基于以下结构化数据，完成评估分析任务。

## 输入数据
{json.dumps(input_data, ensure_ascii=False, indent=2)}

## 评估任务

1. **竞争位置评分（0-15分）**：基于 exchange_listing.major 中的实际交易所列表（这是实时数据，不是你的训练记忆），判断该项目在头部交易所的覆盖情况和市场地位。

2. **语义风险补充扣分（0-2分）**：在规则引擎已判断的客观风险（risk_rule_deductions）基础上，识别需要语义理解的额外风险（如赛道过度拥挤、项目定位模糊）。最多额外扣2分。

3. **推荐理由**：给出3条核心支持/反对理由。

4. **风险点**：给出2条最需关注的风险。

5. **BYDFi跟进紧迫性**：基于竞品上线情况，判断 BYDFi 是否需要尽快上线该 Token（高/中/低）。

6. **一句话总结**。

## 输出要求
严格输出 JSON，不加 markdown 代码块，不加任何解释文字，直接从 {{ 开始：

{{
  "competitive_score": <0-15的整数>,
  "competitive_reason": "<1-2句说明>",
  "risk_extra_deduction": <0-2的整数>,
  "risk_extra_reason": "<如果有额外扣分，说明原因；无则留空字符串>",
  "top_reasons": ["<理由1>", "<理由2>", "<理由3>"],
  "top_risks": ["<风险1>", "<风险2>"],
  "bydfi_urgency": "<高|中|低>",
  "bydfi_urgency_reason": "<1句理由>",
  "summary": "<一句话总结推荐结论>"
}}"""


def _parse_response(text: str) -> dict:
    """解析 Claude 输出，带容错处理"""
    # 剥掉可能存在的 markdown 代码块
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    raw = match.group(1) if match else text.strip()

    # 如果文本不是从 { 开始，尝试提取 JSON 部分
    if not raw.startswith("{"):
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            raw = json_match.group(0)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # 降级：AI 分析部分返回中位分，报告标注异常
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
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("未配置 ANTHROPIC_API_KEY")

    client = anthropic.Anthropic(api_key=api_key)
    prompt = _build_prompt(token_data, rule_scores)

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = message.content[0].text
        return _parse_response(response_text)
    except anthropic.APITimeoutError:
        # 超时降级，不崩溃
        return _parse_response("")
    except anthropic.APIError as e:
        raise RuntimeError(f"Claude API 错误：{e}")
