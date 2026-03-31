"""
可视化模块
生成 Plotly 雷达图
"""

import plotly.graph_objects as go


def build_radar_chart(scores: dict, lang: str = "zh") -> go.Figure:
    """
    生成5维度雷达图
    scores 格式：
    {
        "market": {"score": 22, "max": 30},
        "community": {"score": 14, "max": 20},
        "technical": {"score": 15, "max": 20},
        "competitive": {"score": 12, "max": 15},
        "risk": {"score": 10, "max": 15},
    }
    """
    # 多语言标签
    labels = {
        "zh": ["市场规模", "社区活跃度", "技术实力", "竞争位置", "风险信号"],
        "en": ["Market Cap", "Community", "Technology", "Competition", "Risk"]
    }
    categories = labels.get(lang, labels["zh"])
    keys = ["market", "community", "technical", "competitive", "risk"]

    # 归一化到百分比，方便雷达图展示
    values = [
        round(scores[k]["score"] / scores[k]["max"] * 100)
        for k in keys
    ]
    # 闭合雷达图
    values_closed = values + [values[0]]
    categories_closed = categories + [categories[0]]

    fig = go.Figure(
        data=go.Scatterpolar(
            r=values_closed,
            theta=categories_closed,
            fill="toself",
            fillcolor="rgba(99, 179, 237, 0.35)",  # 更鲜艳的蓝色填充
            line=dict(color="#3B82F6", width=3),  # 更明显的边界线
            marker=dict(size=8, color="#3B82F6"),  # 顶点标记
            hovertemplate="%{theta}: %{r}%<extra></extra>",
        )
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",  # 透明背景
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                ticksuffix="%",
                tickfont=dict(
                    size=12, 
                    color="#a1a1aa",  # 灰色刻度文字
                    family="system-ui, -apple-system, sans-serif"
                ),
                tickangle=0,
                gridcolor="rgba(255,255,255,0.1)",  # 网格线颜色
            ),
            angularaxis=dict(
                tickfont=dict(
                    size=14, 
                    color="#e4e4e7",  # 明亮的白色标签
                    family="system-ui, -apple-system, sans-serif"
                ),
                gridcolor="rgba(255,255,255,0.15)",  # 更清晰的网格线
                linecolor="rgba(255,255,255,0.3)",
            ),
            bgcolor="rgba(0,0,0,0)",  # 极坐标背景透明
        ),
        showlegend=False,
        margin=dict(l=60, r=60, t=50, b=50),
        height=380,
    )

    return fig
