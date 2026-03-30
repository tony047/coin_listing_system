"""
规则评分引擎
负责前3个维度的规则化评分：市场规模、社区活跃度、技术实力
以及客观风险信号的规则判断（不依赖 Claude）
"""

from typing import Optional


def score_market(data: dict) -> dict:
    """
    市场规模评分（满分 30）
    - 市值排名：15分
    - 24h 交易量：10分
    - 30日价格波动率：5分
    """
    score = 0
    details = {}

    # 市值排名（15分）
    rank = data.get("market_cap_rank")
    if rank is not None:
        if rank <= 20:
            rank_score = 15
        elif rank <= 100:
            rank_score = 10
        elif rank <= 500:
            rank_score = 6
        else:
            rank_score = 3
    else:
        rank_score = 0
    score += rank_score
    details["market_cap_rank_score"] = rank_score
    details["market_cap_rank"] = rank

    # 24h 交易量（10分）
    volume = data.get("volume_24h_usd") or 0
    if volume >= 500_000_000:
        vol_score = 10
    elif volume >= 100_000_000:
        vol_score = 7
    elif volume >= 10_000_000:
        vol_score = 5
    else:
        vol_score = 2
    score += vol_score
    details["volume_score"] = vol_score
    details["volume_24h_usd"] = volume

    # 30日价格波动率（5分，波动越低越稳定分越高）
    change_30d = data.get("price_change_30d")
    if change_30d is None:
        volatility_score = 0
    else:
        abs_change = abs(change_30d)
        if abs_change < 30:
            volatility_score = 5
        elif abs_change <= 60:
            volatility_score = 3
        else:
            volatility_score = 1
    score += volatility_score
    details["volatility_score"] = volatility_score
    details["price_change_30d"] = change_30d

    return {"score": score, "max": 30, "details": details}


def score_community(data: dict) -> dict:
    """
    社区活跃度评分（满分 20）
    - Telegram 成员数：12分（主力指标）
    - Reddit 订阅数：8分（辅助指标）
    注：CoinGecko 免费版不提供 Twitter 粉丝数
    """
    score = 0
    details = {}
    warnings = []

    # Telegram 成员（12分）
    telegram = data.get("telegram_members")
    if telegram is None:
        tg_score = 0
        details["telegram_data_available"] = False
    else:
        details["telegram_data_available"] = True
        if telegram >= 100_000:
            tg_score = 12
        elif telegram >= 10_000:
            tg_score = 9
        elif telegram >= 1_000:
            tg_score = 5
        elif telegram > 0:
            tg_score = 2
        else:
            tg_score = 0
    score += tg_score
    details["telegram_score"] = tg_score
    details["telegram_members"] = telegram

    # Reddit 订阅数（8分）
    reddit = data.get("reddit_subscribers")
    if reddit is None:
        reddit_score = 0
        details["reddit_data_available"] = False
    else:
        details["reddit_data_available"] = True
        if reddit >= 500_000:
            reddit_score = 8
        elif reddit >= 100_000:
            reddit_score = 6
        elif reddit >= 10_000:
            reddit_score = 4
        elif reddit > 0:
            reddit_score = 2
        else:
            reddit_score = 0
    score += reddit_score
    details["reddit_score"] = reddit_score
    details["reddit_subscribers"] = reddit

    # 异常检测：高社区 + 低流动性
    volume = data.get("volume_24h_usd") or 0
    total_community = (telegram or 0) + (reddit or 0)
    if total_community >= 100_000 and volume < 1_000_000:
        warnings.append("高社区/低流动性异常：社区规模较大但24h交易量不足$1M，数据可信度存疑")

    return {"score": score, "max": 20, "details": details, "warnings": warnings}


def score_technical(data: dict) -> dict:
    """
    技术实力评分（满分 20）
    数据全部来自 CoinGecko developer_data，无需 GitHub API
    - GitHub Star 数：10分
    - 近4周提交活跃度：10分
    """
    score = 0
    details = {}

    # GitHub Star 数（10分）
    stars = data.get("github_stars")
    if stars is None:
        star_score = 0
        details["has_github"] = False
    else:
        details["has_github"] = True
        if stars >= 10_000:
            star_score = 10
        elif stars >= 1_000:
            star_score = 7
        elif stars >= 100:
            star_score = 4
        else:
            star_score = 1
    score += star_score
    details["star_score"] = star_score
    details["github_stars"] = stars

    # 近4周提交活跃度（10分）
    commits = data.get("commit_count_4_weeks")
    if commits is None:
        commit_score = 0
        details["commit_data_available"] = False
    else:
        details["commit_data_available"] = True
        if commits >= 50:
            commit_score = 10
        elif commits >= 10:
            commit_score = 7
        elif commits > 0:
            commit_score = 3
        else:
            commit_score = 0
    score += commit_score
    details["commit_score"] = commit_score
    details["commit_count_4_weeks"] = commits

    return {"score": score, "max": 20, "details": details}


def score_risk_rules(data: dict) -> dict:
    """
    规则引擎风险扣分（基础分15，扣减后最低0）
    只判断有明确数据依据的客观风险
    Claude 负责语义层的额外判断（最多额外扣2分）
    """
    base = 15
    deductions = []

    # 代码长期停止更新（>4周无提交且有 GitHub）
    commits = data.get("commit_count_4_weeks")
    has_github = data.get("github_stars") is not None
    if has_github and commits == 0:
        deductions.append({
            "risk": "代码近4周零提交",
            "deduction": 5,
            "detail": f"commit_count_4_weeks = 0，项目可能停止维护"
        })

    # 无开源代码
    if not has_github:
        deductions.append({
            "risk": "无 GitHub 开源代码",
            "deduction": 3,
            "detail": "CoinGecko 未关联 GitHub 仓库"
        })

    # 近期价格剧烈下跌
    change_30d = data.get("price_change_30d")
    if change_30d is not None and change_30d < -50:
        deductions.append({
            "risk": "近30日价格大幅下跌",
            "deduction": 3,
            "detail": f"30日涨跌幅：{change_30d:.1f}%"
        })

    # 高市值低社区（市值 Top 100 但粉丝不足 10k）
    rank = data.get("market_cap_rank")
    twitter = data.get("twitter_followers")
    if rank and rank <= 100 and twitter is not None and twitter < 10_000:
        deductions.append({
            "risk": "高市值/低社区严重不匹配",
            "deduction": 2,
            "detail": f"市值排名 #{rank}，Twitter 粉丝仅 {twitter}"
        })

    total_deduction = sum(d["deduction"] for d in deductions)
    final_score = max(0, base - total_deduction)

    return {
        "score": final_score,
        "max": 15,
        "base": base,
        "deductions": deductions,
        "total_deduction": total_deduction,
    }


def compute_rule_scores(data: dict) -> dict:
    """
    计算前3个维度规则评分 + 规则风险评分
    返回完整评分结果，供 claude_analyzer 使用
    """
    market = score_market(data)
    community = score_community(data)
    technical = score_technical(data)
    risk_rules = score_risk_rules(data)

    subtotal = market["score"] + community["score"] + technical["score"]

    return {
        "market": market,
        "community": community,
        "technical": technical,
        "risk_rules": risk_rules,
        "subtotal_rules": subtotal,  # 前3维度合计（不含 Claude 的后2维度）
        "warnings": community.get("warnings", []),
    }
