"""
可视化模块
生成 Plotly 雷达图
"""

import plotly.graph_objects as go


def build_radar_chart(scores: dict) -> go.Figure:
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
    categories = ["市场规模", "社区活跃度", "技术实力", "竞争位置", "风险信号"]
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
            fillcolor="rgba(99, 132, 255, 0.3)",
            line=dict(color="rgba(99, 132, 255, 0.9)", width=2),
            hovertemplate="%{theta}: %{r}%<extra></extra>",
        )
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                ticksuffix="%",
                tickfont=dict(size=10),
            )
        ),
        showlegend=False,
        margin=dict(l=40, r=40, t=40, b=40),
        height=350,
    )

    return fig
