"""
报告导出模块
支持 PDF 和 Markdown 格式导出
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO
from typing import Dict, Any, Optional
import os
from datetime import datetime


class PDFExporter:
    """PDF 报告导出器"""
    
    # 颜色定义
    COLORS = {
        'primary': HexColor('#6384ff'),
        'success': HexColor('#22c55e'),
        'warning': HexColor('#eab308'),
        'danger': HexColor('#ef4444'),
        'gray': HexColor('#6b7280'),
        'light_gray': HexColor('#f3f4f6'),
    }
    
    def __init__(self):
        """初始化 PDF 导出器"""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """设置自定义样式"""
        # 标题样式
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=self.COLORS['primary'],
            spaceAfter=30,
            alignment=TA_CENTER,
        ))
        
        # 副标题样式
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=self.COLORS['gray'],
            spaceAfter=20,
            alignment=TA_CENTER,
        ))
        
        # 章节标题样式
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=black,
            spaceBefore=20,
            spaceAfter=10,
        ))
        
        # 正文样式
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14,
            spaceAfter=8,
        ))
        
        # 结论样式
        self.styles.add(ParagraphStyle(
            name='Verdict',
            parent=self.styles['Normal'],
            fontSize=14,
            alignment=TA_CENTER,
            spaceBefore=10,
            spaceAfter=10,
        ))
    
    def _fmt_usd(self, value: Optional[float]) -> str:
        """格式化美元金额"""
        if value is None:
            return "N/A"
        if value >= 1_000_000_000:
            return f"${value / 1_000_000_000:.2f}B"
        if value >= 1_000_000:
            return f"${value / 1_000_000:.1f}M"
        return f"${value:,.0f}"
    
    def _get_verdict_style(self, total_score: int) -> ParagraphStyle:
        """根据分数获取结论样式"""
        if total_score >= 75:
            color = self.COLORS['success']
        elif total_score >= 55:
            color = self.COLORS['warning']
        else:
            color = self.COLORS['danger']
        
        return ParagraphStyle(
            name='DynamicVerdict',
            parent=self.styles['Verdict'],
            textColor=color,
            fontSize=16,
        )
    
    def export(self, result: Dict[str, Any]) -> bytes:
        """
        导出 PDF 报告
        
        Args:
            result: 评估结果字典
            
        Returns:
            PDF 文件字节流
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )
        
        elements = []
        token = result['token_data']
        scores = result['final_scores']
        ai = result['ai_result']
        total = result['total_score']
        
        # 标题
        elements.append(Paragraph(
            "Token Lens 上币评估报告",
            self.styles['CustomTitle']
        ))
        
        # 副标题
        elements.append(Paragraph(
            f"{token['name']} ({token['symbol']})",
            self.styles['CustomSubtitle']
        ))
        
        # 评估时间和结论
        elapsed = result.get('elapsed_seconds', 0)
        verdict_text = self._get_verdict_text(total)
        verdict_style = self._get_verdict_style(total)
        
        elements.append(Paragraph(
            f"综合评分：{total} / 100",
            self.styles['Verdict']
        ))
        elements.append(Paragraph(verdict_text, verdict_style))
        elements.append(Paragraph(
            f"分析耗时：{elapsed:.1f} 秒 | 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            self.styles['CustomSubtitle']
        ))
        
        elements.append(Spacer(1, 20))
        
        # 基础数据表格
        elements.append(Paragraph("📊 基础数据", self.styles['SectionTitle']))
        
        basic_data = [
            ['指标', '数值'],
            ['市值排名', f"#{token.get('market_cap_rank', 'N/A')}"],
            ['市值', self._fmt_usd(token.get('market_cap_usd'))],
            ['24h 交易量', self._fmt_usd(token.get('volume_24h_usd'))],
            ['30日涨跌', f"{token.get('price_change_30d', 0):.1f}%" if token.get('price_change_30d') else 'N/A'],
            ['CoinGecko 关注', f"{token.get('watchlist_users', 0):,}" if token.get('watchlist_users') else 'N/A'],
            ['GitHub Stars', str(token.get('github_stars', 'N/A')) if token.get('github_stars') else 'N/A'],
            ['近4周提交数', str(token.get('commit_count_4_weeks', 'N/A')) if token.get('commit_count_4_weeks') is not None else 'N/A'],
        ]
        
        table = Table(basic_data, colWidths=[6*cm, 8*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), self.COLORS['light_gray']),
            ('GRID', (0, 0), (-1, -1), 0.5, self.COLORS['gray']),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, self.COLORS['light_gray']]),
        ]))
        elements.append(table)
        
        elements.append(Spacer(1, 20))
        
        # 评分详情表格
        elements.append(Paragraph("📈 各维度评分", self.styles['SectionTitle']))
        
        dim_labels = {
            'market': '市场规模',
            'community': '社区活跃度',
            'technical': '技术实力',
            'competitive': '竞争位置',
            'risk': '风险信号',
        }
        
        score_data = [['维度', '得分', '满分', '百分比']]
        for key, label in dim_labels.items():
            s = scores[key]
            pct = s['score'] / s['max'] * 100
            score_data.append([label, str(s['score']), str(s['max']), f"{pct:.0f}%"])
        
        score_data.append(['总分', str(total), '100', f"{total}%"])
        
        score_table = Table(score_data, colWidths=[5*cm, 3*cm, 3*cm, 3*cm])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, self.COLORS['gray']),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [white, self.COLORS['light_gray']]),
            ('BACKGROUND', (0, -1), (-1, -1), self.COLORS['light_gray']),
        ]))
        elements.append(score_table)
        
        elements.append(Spacer(1, 20))
        
        # AI 分析
        elements.append(Paragraph("🤖 AI 分析", self.styles['SectionTitle']))
        
        # 推荐理由
        elements.append(Paragraph("<b>✅ 推荐理由</b>", self.styles['CustomBody']))
        for reason in ai.get('top_reasons', []):
            elements.append(Paragraph(f"• {reason}", self.styles['CustomBody']))
        
        elements.append(Spacer(1, 10))
        
        # 风险点
        elements.append(Paragraph("<b>⚠️ 风险点</b>", self.styles['CustomBody']))
        for risk in ai.get('top_risks', []):
            elements.append(Paragraph(f"• {risk}", self.styles['CustomBody']))
        
        elements.append(Spacer(1, 20))
        
        # BYDFi 建议
        elements.append(Paragraph("🏦 BYDFi 跟进建议", self.styles['SectionTitle']))
        
        urgency = ai.get('bydfi_urgency', '中')
        urgency_text = f"紧迫性：{urgency} - {ai.get('bydfi_urgency_reason', '')}"
        elements.append(Paragraph(urgency_text, self.styles['CustomBody']))
        
        listed = token.get('listed_on_major', [])
        if listed:
            elements.append(Paragraph(
                f"已上线主流交易所：{', '.join(listed)}",
                self.styles['CustomBody']
            ))
        
        bydfi_status = '✅ 已上线 BYDFi' if token.get('listed_on_bydfi') else '❌ 未上线 BYDFi'
        elements.append(Paragraph(bydfi_status, self.styles['CustomBody']))
        
        # 页脚
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(
            "—— Token Lens 自动生成 · BYDFi AI Reforge Hackathon ——",
            self.styles['CustomSubtitle']
        ))
        
        # 构建 PDF
        doc.build(elements)
        return buffer.getvalue()
    
    def _get_verdict_text(self, total_score: int) -> str:
        """获取结论文本"""
        if total_score >= 75:
            return "🟢 强烈推荐上币"
        elif total_score >= 55:
            return "🟡 建议观望"
        else:
            return "🔴 不建议上币"


def export_pdf(result: Dict[str, Any]) -> bytes:
    """
    导出 PDF 报告的便捷函数
    
    Args:
        result: 评估结果
        
    Returns:
        PDF 字节流
    """
    exporter = PDFExporter()
    return exporter.export(result)
