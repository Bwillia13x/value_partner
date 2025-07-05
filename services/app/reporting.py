import matplotlib.pyplot as plt
try:
    from reportlab.lib.pagesizes import A4  # type: ignore
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer  # type: ignore
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore
    from reportlab.lib.units import inch  # type: ignore
    from reportlab.lib.colors import HexColor  # type: ignore
    from reportlab.lib import colors  # type: ignore
except ImportError:  # pragma: no cover – minimal stubs when reportlab missing
    A4 = (595.27, 841.89)
    inch = 72
    colors = type("_ColorsStub", (), {"black": "black", "white": "white"})()  # type: ignore
    HexColor = lambda x: x  # type: ignore

    def _noop(*args, **kwargs):
        return None

    SimpleDocTemplate = Table = TableStyle = Paragraph = Spacer = getSampleStyleSheet = ParagraphStyle = _noop  # type: ignore

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from io import BytesIO
import base64
from .database import User, Account, Holding
from .analytics import PortfolioAnalytics, PerformanceMetrics
from .optimizer import PortfolioOptimizer
from dataclasses import dataclass


@dataclass
class ReportData:
    """Data structure for portfolio reports"""
    user_info: Dict
    portfolio_summary: Dict
    performance_metrics: Optional[PerformanceMetrics]
    asset_allocation: Dict[str, float]
    top_holdings: List[Dict]
    recent_transactions: List[Dict]
    optimization_suggestions: List[Dict]
    generated_at: datetime


class PortfolioReporting:
    """Advanced portfolio reporting and PDF generation"""
    
    def __init__(self, db: Session):
        self.db = db
        self.analytics = PortfolioAnalytics(db)
        self.optimizer = PortfolioOptimizer(db)
    
    def generate_comprehensive_report(self, user_id: int) -> ReportData:
        """Generate comprehensive portfolio report data"""
        
        # Get user info
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        user_info = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "created_at": user.created_at
        }
        
        # Get portfolio summary
        portfolio_summary = self._get_portfolio_summary(user_id)
        
        # Get performance metrics
        performance_metrics = self.analytics.calculate_performance_metrics(user_id)
        
        # Get asset allocation
        asset_allocation = self.analytics.get_asset_allocation(user_id)
        
        # Get top holdings
        top_holdings = self._get_top_holdings(user_id)
        
        # Get recent transactions
        recent_transactions = self._get_recent_transactions(user_id)
        
        # Get optimization suggestions
        optimization_suggestions = self.optimizer.get_rebalancing_recommendations(user_id)
        
        return ReportData(
            user_info=user_info,
            portfolio_summary=portfolio_summary,
            performance_metrics=performance_metrics,
            asset_allocation=asset_allocation,
            top_holdings=top_holdings,
            recent_transactions=recent_transactions,
            optimization_suggestions=optimization_suggestions,
            generated_at=datetime.now()
        )
    
    def _get_portfolio_summary(self, user_id: int) -> Dict:
        """Get portfolio summary statistics"""
        
        accounts = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_active == True
        ).all()
        
        total_value = 0
        account_count = len(accounts)
        investment_accounts = 0
        
        for account in accounts:
            total_value += account.current_balance
            if account.account_type.value in ['investment', 'retirement']:
                investment_accounts += 1
        
        return {
            "total_value": total_value,
            "account_count": account_count,
            "investment_accounts": investment_accounts,
            "last_sync": max([acc.updated_at for acc in accounts]) if accounts else None
        }
    
    def _get_top_holdings(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get top holdings by market value"""
        
        accounts = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.account_type.in_(['investment', 'retirement'])
        ).all()
        
        holdings = []
        for account in accounts:
            account_holdings = self.db.query(Holding).filter(
                Holding.account_id == account.id
            ).all()
            
            for holding in account_holdings:
                holdings.append({
                    "symbol": holding.symbol,
                    "name": holding.name,
                    "quantity": holding.quantity,
                    "market_value": holding.market_value,
                    "cost_basis": holding.cost_basis,
                    "unrealized_gain": holding.market_value - (holding.cost_basis or 0) if holding.cost_basis else 0
                })
        
        # Sort by market value and return top holdings
        holdings.sort(key=lambda x: x["market_value"], reverse=True)
        return holdings[:limit]
    
    def _get_recent_transactions(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get recent transactions"""
        
        from .database import Transaction
        
        transactions = self.db.query(Transaction).filter(
            Transaction.user_id == user_id
        ).order_by(Transaction.date.desc()).limit(limit).all()
        
        return [
            {
                "date": trans.date,
                "description": trans.description,
                "amount": trans.amount,
                "transaction_type": trans.transaction_type.value,
                "symbol": trans.symbol,
                "quantity": trans.quantity
            }
            for trans in transactions
        ]
    
    def generate_pdf_report(self, user_id: int, filename: Optional[str] = None) -> bytes:
        """Generate PDF report"""
        
        # Get report data
        report_data = self.generate_comprehensive_report(user_id)
        
        # Create PDF document
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=HexColor('#1f2937')
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=HexColor('#374151')
        )
        
        # Build PDF content
        content = []
        
        # Title
        content.append(Paragraph("Portfolio Performance Report", title_style))
        content.append(Spacer(1, 20))
        
        # Report info
        report_info = [
            ["Report Generated:", report_data.generated_at.strftime("%Y-%m-%d %H:%M:%S")],
            ["User:", report_data.user_info["email"]],
            ["Total Portfolio Value:", f"${report_data.portfolio_summary['total_value']:,.2f}"],
            ["Number of Accounts:", str(report_data.portfolio_summary["account_count"])]
        ]
        
        info_table = Table(report_info, colWidths=[2*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        
        content.append(info_table)
        content.append(Spacer(1, 30))
        
        # Performance Metrics
        if report_data.performance_metrics:
            content.append(Paragraph("Performance Metrics", heading_style))
            
            metrics_data = [
                ["Metric", "Value"],
                ["Total Return", f"{report_data.performance_metrics.total_return:.2%}"],
                ["Annualized Return", f"{report_data.performance_metrics.annualized_return:.2%}"],
                ["Volatility", f"{report_data.performance_metrics.volatility:.2%}"],
                ["Sharpe Ratio", f"{report_data.performance_metrics.sharpe_ratio:.2f}"],
                ["Max Drawdown", f"{report_data.performance_metrics.max_drawdown:.2%}"],
                ["Alpha", f"{report_data.performance_metrics.alpha:.2%}"],
                ["Beta", f"{report_data.performance_metrics.beta:.2f}"]
            ]
            
            metrics_table = Table(metrics_data, colWidths=[2.5*inch, 2.5*inch])
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#f3f4f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            content.append(metrics_table)
            content.append(Spacer(1, 30))
        
        # Asset Allocation
        if report_data.asset_allocation:
            content.append(Paragraph("Asset Allocation", heading_style))
            
            allocation_data = [["Asset Class", "Percentage", "Value"]]
            total_value = report_data.portfolio_summary["total_value"]
            
            for asset_class, percentage in report_data.asset_allocation.items():
                value = percentage * total_value
                allocation_data.append([
                    asset_class.title(),
                    f"{percentage:.1%}",
                    f"${value:,.2f}"
                ])
            
            allocation_table = Table(allocation_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
            allocation_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#f3f4f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            content.append(allocation_table)
            content.append(Spacer(1, 30))
        
        # Top Holdings
        if report_data.top_holdings:
            content.append(Paragraph("Top Holdings", heading_style))
            
            holdings_data = [["Symbol", "Name", "Quantity", "Market Value", "Unrealized Gain"]]
            
            for holding in report_data.top_holdings[:5]:  # Top 5 for PDF
                holdings_data.append([
                    holding["symbol"],
                    holding["name"][:20] + "..." if len(holding["name"]) > 20 else holding["name"],
                    f"{holding['quantity']:.2f}",
                    f"${holding['market_value']:,.2f}",
                    f"${holding['unrealized_gain']:,.2f}"
                ])
            
            holdings_table = Table(holdings_data, colWidths=[0.8*inch, 1.8*inch, 0.8*inch, 1.2*inch, 1.2*inch])
            holdings_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#f3f4f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            content.append(holdings_table)
            content.append(Spacer(1, 30))
        
        # Optimization Suggestions
        if report_data.optimization_suggestions:
            content.append(Paragraph("Rebalancing Recommendations", heading_style))
            
            suggestions_text = []
            for suggestion in report_data.optimization_suggestions[:3]:  # Top 3 suggestions
                suggestions_text.append(
                    f"• {suggestion['action']} {suggestion['symbol']}: "
                    f"Current weight {suggestion['current_weight']:.1%}, "
                    f"Target weight {suggestion['target_weight']:.1%}, "
                    f"Drift {suggestion['drift']:.1%}"
                )
            
            suggestions_para = Paragraph("<br/>".join(suggestions_text), styles['Normal'])
            content.append(suggestions_para)
        
        # Build PDF
        doc.build(content)
        
        # Return PDF bytes
        buffer.seek(0)
        return buffer.read()
    
    def generate_chart_image(self, user_id: int, chart_type: str = "performance") -> str:
        """Generate chart image and return base64 encoded string"""
        
        plt.style.use('seaborn-v0_8')
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if chart_type == "performance":
            # Generate performance chart
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            
            returns_df = self.analytics.calculate_portfolio_returns(user_id, start_date, end_date)
            
            if not returns_df.empty:
                ax.plot(returns_df['date'], returns_df['portfolio_value'], linewidth=2, color='#3b82f6')
                ax.set_title('Portfolio Performance (1 Year)', fontsize=16, fontweight='bold')
                ax.set_xlabel('Date')
                ax.set_ylabel('Portfolio Value ($)')
                ax.grid(True, alpha=0.3)
                
                # Format y-axis as currency
                ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        elif chart_type == "allocation":
            # Generate allocation pie chart
            allocation = self.analytics.get_asset_allocation(user_id)
            
            if allocation:
                labels = [key.title() for key in allocation.keys()]
                sizes = [value * 100 for value in allocation.values()]
                colors = plt.cm.Set3(range(len(labels)))
                
                ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
                ax.set_title('Asset Allocation', fontsize=16, fontweight='bold')
        
        # Save to base64 string
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)
        
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        
        plt.close()
        
        return image_base64