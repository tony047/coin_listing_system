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
    - CoinGecko Watchlist 用户数：14分（主力指标，反映真实持仓/关注人数）
    - Telegram 成员数：6分（辅助，如有数据则加分）
    注：CoinGecko 免费版 Reddit/Twitter 数据已不可用（均为0），改用 watchlist_portfolio_users
    """
    score = 0
    details = {}
    warnings = []

    # Watchlist 用户数（14分）—— CoinGecko 独有，反映真实关注人数
    watchlist = data.get("watchlist_users")
    if watchlist is None:
        wl_score = 0
        details["watchlist_data_available"] = False
    else:
        details["watchlist_data_available"] = True
        if watchlist >= 1_000_000:
            wl_score = 14
        elif watchlist >= 500_000:
            wl_score = 11
        elif watchlist >= 100_000:
            wl_score = 8
        elif watchlist >= 10_000:
            wl_score = 5
        elif watchlist > 0:
            wl_score = 2
        else:
            wl_score = 0
    score += wl_score
    details["watchlist_score"] = wl_score
    details["watchlist_users"] = watchlist

    # Telegram 成员（6分，辅助指标）
    telegram = data.get("telegram_members")
    if telegram and telegram > 0:
        if telegram >= 100_000:
            tg_score = 6
        elif telegram >= 10_000:
            tg_score = 4
        elif telegram >= 1_000:
            tg_score = 2
        else:
            tg_score = 1
    else:
        tg_score = 0
    score += tg_score
    details["telegram_score"] = tg_score
    details["telegram_members"] = telegram

    # 异常检测：高社区关注 + 低流动性（可能是炒作 Token）
    volume = data.get("volume_24h_usd") or 0
    if (watchlist or 0) >= 100_000 and volume < 1_000_000:
        warnings.append("高社区关注/低流动性异常：Watchlist 用户超10万但24h交易量不足$1M，数据可信度存疑")

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


def score_tokenomics(tokenomics_data: dict) -> dict:
    """
    Tokenomics 健康度评分（满分 10，扣分制）
    
    规则：
    - 基础分 10 分
    - 流通比例 < 20%：-3 分（砸盘风险高）
    - 流通比例 < 30%（但 >= 20%）：-2 分
    - 无最大供应量限制（无限通胀）：-1 分
    - 数据不可用时：返回满分 10（不扣分），标注 data_available: false
    
    Args:
        tokenomics_data: analyze_tokenomics() 返回的 Tokenomics 数据
    
    Returns:
        {
            'score': int,
            'max': 10,
            'details': dict,
            'deductions': list,
            'data_available': bool
        }
    """
    base_score = 10
    deductions = []
    details = {}
    
    # 检查数据可用性
    data_available = tokenomics_data.get("data_available", False)
    
    if not data_available:
        # 数据不可用时返回满分，不扣分
        return {
            "score": base_score,
            "max": 10,
            "details": {
                "message": "Tokenomics 数据不可用，不进行扣分"
            },
            "deductions": [],
            "data_available": False
        }
    
    # 提取关键指标
    circulation_ratio = tokenomics_data.get("circulation_ratio")
    has_max_supply = tokenomics_data.get("has_max_supply", False)
    
    # 记录详情
    details["total_supply"] = tokenomics_data.get("total_supply")
    details["circulating_supply"] = tokenomics_data.get("circulating_supply")
    details["max_supply"] = tokenomics_data.get("max_supply")
    details["circulation_ratio"] = circulation_ratio
    details["has_max_supply"] = has_max_supply
    details["is_deflationary"] = tokenomics_data.get("is_deflationary", False)
    details["supply_concentration"] = tokenomics_data.get("supply_concentration", "UNKNOWN")
    
    # 评分规则 1：流通比例过低
    if circulation_ratio is not None:
        if circulation_ratio < 0.2:
            # 流通比例 < 20%：扣 3 分
            deductions.append({
                "reason": "流通比例过低（< 20%）",
                "points": 3,
                "detail": f"流通比例 {circulation_ratio:.1%}，砸盘风险高"
            })
        elif circulation_ratio < 0.3:
            # 流通比例 20%-30%：扣 2 分
            deductions.append({
                "reason": "流通比例较低（20%-30%）",
                "points": 2,
                "detail": f"流通比例 {circulation_ratio:.1%}，存在一定砸盘风险"
            })
    
    # 评分规则 2：无最大供应量限制（无限通胀）
    if not has_max_supply:
        deductions.append({
            "reason": "无最大供应量限制",
            "points": 1,
            "detail": "可能存在无限通胀风险"
        })
    
    # 计算最终分数
    total_deduction = sum(d["points"] for d in deductions)
    final_score = max(0, base_score - total_deduction)
    
    return {
        "score": final_score,
        "max": 10,
        "details": details,
        "deductions": deductions,
        "data_available": True
    }


def score_onchain(onchain_data: dict) -> dict:
    """
    链上健康度评分（满分 10，扣分制）
    
    规则：
    - 基础分 10 分
    - Top 10 持有者占比 > 60%：-4 分（极端集中，CRITICAL）
    - Top 10 持有者占比 > 40%（但 <= 60%）：-2 分（HIGH）
    - 持有者总数 < 1000：-3 分（极少人持有）
    - 持有者总数 < 5000（但 >= 1000）：-1 分
    - 数据不可用（UNKNOWN）：返回满分 10（不扣分），标注 data_available: false
    
    Args:
        onchain_data: get_onchain_data() 返回的链上数据
    
    Returns:
        {
            'score': int,
            'max': 10,
            'details': dict,
            'deductions': list,
            'data_available': bool
        }
    """
    base_score = 10
    deductions = []
    details = {}
    
    # 检查数据可用性
    data_available = onchain_data.get("data_available", False)
    concentration_risk = onchain_data.get("concentration_risk", "UNKNOWN")
    
    if not data_available or concentration_risk == "UNKNOWN":
        # 数据不可用时返回满分，不扣分
        return {
            "score": base_score,
            "max": 10,
            "details": {
                "message": "链上数据不可用，不进行扣分",
                "data_source": onchain_data.get("data_source", "none")
            },
            "deductions": [],
            "data_available": False
        }
    
    # 提取关键指标
    top_holders_pct = onchain_data.get("top_holders_pct")
    total_holders = onchain_data.get("total_holders")
    
    # 记录详情
    details["chain"] = onchain_data.get("chain")
    details["contract_address"] = onchain_data.get("contract_address")
    details["top_holders_pct"] = top_holders_pct
    details["total_holders"] = total_holders
    details["concentration_risk"] = concentration_risk
    details["data_source"] = onchain_data.get("data_source")
    
    # 评分规则 1：Top 10 持有者占比过高
    if top_holders_pct is not None:
        if top_holders_pct > 0.6:
            # Top 10 持有 > 60%：扣 4 分
            deductions.append({
                "reason": "Top 10 持有者占比过高（> 60%）",
                "points": 4,
                "detail": f"Top 10 持有占比 {top_holders_pct:.1%}，极端集中，砸盘风险极高"
            })
        elif top_holders_pct > 0.4:
            # Top 10 持有 40%-60%：扣 2 分
            deductions.append({
                "reason": "Top 10 持有者占比较高（40%-60%）",
                "points": 2,
                "detail": f"Top 10 持有占比 {top_holders_pct:.1%}，存在一定砸盘风险"
            })
    
    # 评分规则 2：持有者总数过少
    if total_holders is not None and total_holders > 0:
        if total_holders < 1000:
            # 持有者 < 1000：扣 3 分
            deductions.append({
                "reason": "持有者总数过少（< 1000）",
                "points": 3,
                "detail": f"持有者仅 {total_holders} 人，流动性差，容易被控盘"
            })
        elif total_holders < 5000:
            # 持有者 1000-5000：扣 1 分
            deductions.append({
                "reason": "持有者总数较少（1000-5000）",
                "points": 1,
                "detail": f"持有者 {total_holders} 人，流动性一般"
            })
    
    # 计算最终分数
    total_deduction = sum(d["points"] for d in deductions)
    final_score = max(0, base_score - total_deduction)
    
    return {
        "score": final_score,
        "max": 10,
        "details": details,
        "deductions": deductions,
        "data_available": True
    }


def compute_rule_scores(data: dict, tokenomics_data: dict = None, onchain_data: dict = None) -> dict:
    """
    计算所有维度规则评分（7维度）+ 规则风险评分
    返回完整评分结果，供 claude_analyzer 使用
    
    权重分配（总分100）：
    - market（市场规模）: 25分
    - community（社区活跃度）: 15分
    - technical（技术实力）: 15分
    - competitive（竞争位置）: 15分（由Claude评定）
    - risk（风险信号）: 10分
    - tokenomics（代币经济）: 10分
    - onchain（链上健康度）: 10分
    
    Args:
        data: Token 数据字典
        tokenomics_data: Tokenomics 分析数据，为 None 时使用默认满分
        onchain_data: 链上数据，为 None 时使用默认满分
    
    Returns:
        包含各维度评分的字典
    """
    # 计算原始评分
    market_raw = score_market(data)
    community_raw = score_community(data)
    technical_raw = score_technical(data)
    risk_rules_raw = score_risk_rules(data)

    # 等比例缩放到新满分值
    # market: 原满分30 → 新满分25，缩放系数 25/30
    market = {
        "score": round(market_raw["score"] * 25 / 30),
        "max": 25,
        "details": market_raw.get("details", {}),
        "original_score": market_raw["score"],
        "original_max": 30,
    }
    
    # community: 原满分20 → 新满分15，缩放系数 15/20
    community = {
        "score": round(community_raw["score"] * 15 / 20),
        "max": 15,
        "details": community_raw.get("details", {}),
        "warnings": community_raw.get("warnings", []),
        "original_score": community_raw["score"],
        "original_max": 20,
    }
    
    # technical: 原满分20 → 新满分15，缩放系数 15/20
    technical = {
        "score": round(technical_raw["score"] * 15 / 20),
        "max": 15,
        "details": technical_raw.get("details", {}),
        "original_score": technical_raw["score"],
        "original_max": 20,
    }
    
    # risk: 原满分15 → 新满分10，缩放系数 10/15
    risk_rules = {
        "score": round(risk_rules_raw["score"] * 10 / 15),
        "max": 10,
        "base": risk_rules_raw.get("base", 15),
        "deductions": risk_rules_raw.get("deductions", []),
        "total_deduction": risk_rules_raw.get("total_deduction", 0),
        "original_score": risk_rules_raw["score"],
        "original_max": 15,
    }
    
    # Tokenomics 评分（满分10）
    if tokenomics_data:
        tokenomics = score_tokenomics(tokenomics_data)
    else:
        tokenomics = {
            "score": 10,
            "max": 10,
            "data_available": False,
            "details": {"message": "Tokenomics 数据未提供，使用默认满分"},
            "deductions": [],
        }
    
    # 链上健康度评分（满分10）
    if onchain_data:
        onchain = score_onchain(onchain_data)
    else:
        onchain = {
            "score": 10,
            "max": 10,
            "data_available": False,
            "details": {"message": "链上数据未提供，使用默认满分"},
            "deductions": [],
        }

    subtotal = market["score"] + community["score"] + technical["score"]

    return {
        "market": market,
        "community": community,
        "technical": technical,
        "risk_rules": risk_rules,
        "tokenomics": tokenomics,
        "onchain": onchain,
        "subtotal_rules": subtotal,  # 前3维度合计（不含 Claude 的后2维度）
        "warnings": community.get("warnings", []),
    }
