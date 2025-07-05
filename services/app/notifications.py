import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import os
from .database import User, Strategy, StrategyHolding
from .analytics import PortfolioAnalytics
from .optimizer import PortfolioOptimizer
from dataclasses import dataclass


@dataclass
class NotificationPreferences:
    """User notification preferences"""
    email_enabled: bool = True
    rebalance_alerts: bool = True
    performance_reports: bool = True
    market_alerts: bool = False
    threshold_alerts: bool = True
    frequency: str = "daily"  # daily, weekly, monthly


@dataclass
class AlertCondition:
    """Alert condition configuration"""
    type: str  # drift, performance, volatility, drawdown
    threshold: float
    comparison: str  # gt, lt, eq
    enabled: bool = True


class NotificationService:
    """Service for handling portfolio notifications and alerts"""
    
    def __init__(self, db: Session):
        self.db = db
        self.analytics = PortfolioAnalytics(db)
        self.optimizer = PortfolioOptimizer(db)
        
        # Email configuration
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_username)
    
    def check_rebalancing_alerts(self, user_id: int) -> List[Dict]:
        """Check for rebalancing alerts based on drift thresholds"""
        
        alerts = []
        
        # Get user's strategies
        strategies = self.db.query(Strategy).filter(Strategy.user_id == user_id).all()
        
        for strategy in strategies:
            # Get target allocation
            target_holdings = self.db.query(StrategyHolding).filter(
                StrategyHolding.strategy_id == strategy.id
            ).all()
            
            if not target_holdings:
                continue
            
            # Get current allocation
            current_portfolio = self.optimizer._get_current_portfolio(user_id)
            current_weights = self.optimizer._normalize_weights(current_portfolio)
            
            # Check for drift
            for target_holding in target_holdings:
                symbol = target_holding.symbol
                target_weight = target_holding.target_weight
                current_weight = current_weights.get(symbol, 0)
                drift = abs(current_weight - target_weight)
                
                if drift > strategy.rebalance_threshold / 100:
                    alerts.append({
                        "type": "rebalance_drift",
                        "strategy_name": strategy.name,
                        "symbol": symbol,
                        "current_weight": current_weight,
                        "target_weight": target_weight,
                        "drift": drift,
                        "threshold": strategy.rebalance_threshold / 100,
                        "severity": "HIGH" if drift > 0.1 else "MEDIUM",
                        "created_at": datetime.now()
                    })
        
        return alerts
    
    def check_performance_alerts(self, user_id: int) -> List[Dict]:
        """Check for performance-based alerts"""
        
        alerts = []
        
        # Get performance metrics
        metrics = self.analytics.calculate_performance_metrics(user_id, 30)  # 30-day performance
        
        if not metrics:
            return alerts
        
        # Check for significant drawdown
        if metrics.max_drawdown < -0.1:  # More than 10% drawdown
            alerts.append({
                "type": "max_drawdown",
                "value": metrics.max_drawdown,
                "threshold": -0.1,
                "severity": "HIGH",
                "message": f"Portfolio has experienced a {metrics.max_drawdown:.1%} drawdown",
                "created_at": datetime.now()
            })
        
        # Check for low Sharpe ratio
        if metrics.sharpe_ratio < 0.5:
            alerts.append({
                "type": "low_sharpe",
                "value": metrics.sharpe_ratio,
                "threshold": 0.5,
                "severity": "MEDIUM",
                "message": f"Portfolio Sharpe ratio is low at {metrics.sharpe_ratio:.2f}",
                "created_at": datetime.now()
            })
        
        # Check for high volatility
        if metrics.volatility > 0.25:  # More than 25% annualized volatility
            alerts.append({
                "type": "high_volatility",
                "value": metrics.volatility,
                "threshold": 0.25,
                "severity": "MEDIUM",
                "message": f"Portfolio volatility is high at {metrics.volatility:.1%}",
                "created_at": datetime.now()
            })
        
        return alerts
    
    def check_all_alerts(self, user_id: int) -> Dict[str, List[Dict]]:
        """Check all types of alerts for a user"""
        
        return {
            "rebalancing": self.check_rebalancing_alerts(user_id),
            "performance": self.check_performance_alerts(user_id)
        }
    
    def send_email_notification(self, 
                              to_email: str, 
                              subject: str, 
                              body: str, 
                              html_body: Optional[str] = None,
                              attachments: Optional[List[Dict]] = None) -> bool:
        """Send email notification"""
        
        if not self.smtp_username or not self.smtp_password:
            print("Email configuration not set up")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(body, 'plain'))
            
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))
            
            # Add attachments
            if attachments:
                for attachment in attachments:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment['data'])
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {attachment["filename"]}'
                    )
                    msg.attach(part)
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            text = msg.as_string()
            server.sendmail(self.from_email, to_email, text)
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def send_rebalancing_alert(self, user_id: int, alerts: List[Dict]) -> bool:
        """Send rebalancing alert email"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.email:
            return False
        
        if not alerts:
            return True
        
        # Create email content
        subject = "Portfolio Rebalancing Alert"
        
        body = f"Dear {user.name or 'Investor'},\n\n"
        body += "Your portfolio has drifted from target allocations and may need rebalancing:\n\n"
        
        for alert in alerts:
            body += f"• {alert['symbol']} in {alert['strategy_name']} strategy:\n"
            body += f"  Current: {alert['current_weight']:.1%}, Target: {alert['target_weight']:.1%}\n"
            body += f"  Drift: {alert['drift']:.1%} (Threshold: {alert['threshold']:.1%})\n\n"
        
        body += "Consider rebalancing your portfolio to maintain your target allocation.\n\n"
        body += "Best regards,\nValue Partner Platform"
        
        # HTML version
        html_body = f"""
        <html>
        <body>
            <h2>Portfolio Rebalancing Alert</h2>
            <p>Dear {user.name or 'Investor'},</p>
            <p>Your portfolio has drifted from target allocations and may need rebalancing:</p>
            <ul>
        """
        
        for alert in alerts:
            html_body += f"""
                <li><strong>{alert['symbol']}</strong> in {alert['strategy_name']} strategy:
                    <ul>
                        <li>Current: {alert['current_weight']:.1%}</li>
                        <li>Target: {alert['target_weight']:.1%}</li>
                        <li>Drift: {alert['drift']:.1%} (Threshold: {alert['threshold']:.1%})</li>
                    </ul>
                </li>
            """
        
        html_body += """
            </ul>
            <p>Consider rebalancing your portfolio to maintain your target allocation.</p>
            <p>Best regards,<br>Value Partner Platform</p>
        </body>
        </html>
        """
        
        return self.send_email_notification(user.email, subject, body, html_body)
    
    def send_performance_alert(self, user_id: int, alerts: List[Dict]) -> bool:
        """Send performance alert email"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.email:
            return False
        
        if not alerts:
            return True
        
        subject = "Portfolio Performance Alert"
        
        body = f"Dear {user.name or 'Investor'},\n\n"
        body += "Your portfolio performance requires attention:\n\n"
        
        for alert in alerts:
            body += f"• {alert['message']}\n"
        
        body += "\nPlease review your portfolio and consider adjusting your strategy.\n\n"
        body += "Best regards,\nValue Partner Platform"
        
        return self.send_email_notification(user.email, subject, body)
    
    def send_daily_summary(self, user_id: int) -> bool:
        """Send daily portfolio summary"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.email:
            return False
        
        # Get portfolio summary
        current_value = self.analytics.get_current_portfolio_value(user_id)
        allocation = self.analytics.get_asset_allocation(user_id)
        
        # Get performance metrics
        metrics = self.analytics.calculate_performance_metrics(user_id, 1)  # 1-day performance
        
        subject = "Daily Portfolio Summary"
        
        body = f"Dear {user.name or 'Investor'},\n\n"
        body += "Here's your daily portfolio summary:\n\n"
        body += f"Current Portfolio Value: ${current_value:,.2f}\n"
        
        if metrics:
            body += f"Today's Return: {metrics.total_return:.2%}\n"
        
        body += "\nAsset Allocation:\n"
        for asset_class, percentage in allocation.items():
            body += f"• {asset_class.title()}: {percentage:.1%}\n"
        
        body += "\nBest regards,\nValue Partner Platform"
        
        return self.send_email_notification(user.email, subject, body)
    
    def process_all_notifications(self) -> Dict[str, int]:
        """Process all pending notifications for all users"""
        
        results = {
            "users_processed": 0,
            "rebalancing_alerts_sent": 0,
            "performance_alerts_sent": 0,
            "daily_summaries_sent": 0,
            "errors": 0
        }
        
        # Get all users with active accounts
        users = self.db.query(User).filter(User.plaid_access_token.isnot(None)).all()
        
        for user in users:
            try:
                results["users_processed"] += 1
                
                # Check alerts
                all_alerts = self.check_all_alerts(user.id)
                
                # Send rebalancing alerts
                if all_alerts["rebalancing"]:
                    if self.send_rebalancing_alert(user.id, all_alerts["rebalancing"]):
                        results["rebalancing_alerts_sent"] += 1
                
                # Send performance alerts
                if all_alerts["performance"]:
                    if self.send_performance_alert(user.id, all_alerts["performance"]):
                        results["performance_alerts_sent"] += 1
                
                # Send daily summary (could be configured per user)
                if self.send_daily_summary(user.id):
                    results["daily_summaries_sent"] += 1
                    
            except Exception as e:
                print(f"Error processing notifications for user {user.id}: {e}")
                results["errors"] += 1
        
        return results