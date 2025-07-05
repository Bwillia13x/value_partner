from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import yfinance as yf
from dataclasses import dataclass
from enum import Enum
import logging

from .database import Transaction, TransactionType
from .analytics import PortfolioAnalytics
from .order_management import OrderManagementSystem, OrderRequest, OrderType, OrderSide, TimeInForce

logger = logging.getLogger(__name__)

class TaxLotMethod(Enum):
    FIFO = "fifo"  # First In, First Out
    LIFO = "lifo"  # Last In, First Out
    HIFO = "hifo"  # Highest In, First Out
    SPECIFIC_ID = "specific_id"  # Specific identification

@dataclass
class TaxLot:
    """Represents a tax lot (a specific purchase of shares)"""
    symbol: str
    purchase_date: datetime
    quantity: float
    cost_basis: float
    current_price: float
    market_value: float
    unrealized_gain_loss: float
    holding_period_days: int
    is_long_term: bool  # > 365 days
    transaction_id: Optional[int] = None
    
    @property
    def cost_per_share(self) -> float:
        return self.cost_basis / self.quantity if self.quantity > 0 else 0
    
    @property
    def unrealized_gain_loss_per_share(self) -> float:
        return self.current_price - self.cost_per_share
    
    @property
    def unrealized_gain_loss_percent(self) -> float:
        return (self.unrealized_gain_loss / self.cost_basis) * 100 if self.cost_basis > 0 else 0

@dataclass
class TaxLossHarvestingCandidate:
    """Represents a candidate for tax-loss harvesting"""
    symbol: str
    tax_lots: List[TaxLot]
    total_unrealized_loss: float
    potential_tax_savings: float
    replacement_candidates: List[str]  # Similar securities to avoid wash sale
    last_sale_date: Optional[datetime] = None
    wash_sale_period_active: bool = False
    
@dataclass
class TaxLossHarvestingRecommendation:
    """Tax-loss harvesting recommendation"""
    candidate: TaxLossHarvestingCandidate
    lots_to_sell: List[TaxLot]
    estimated_tax_savings: float
    replacement_security: Optional[str] = None
    reasoning: str = ""
    urgency: str = "medium"  # low, medium, high
    
class TaxLossHarvestingEngine:
    """Tax-loss harvesting analysis and execution engine"""
    
    def __init__(self, db: Session):
        self.db = db
        self.analytics = PortfolioAnalytics(db)
        self.order_management = OrderManagementSystem(db)
        
        # Tax settings (these could be user-configurable)
        self.short_term_tax_rate = 0.37  # Ordinary income tax rate
        self.long_term_tax_rate = 0.20   # Long-term capital gains tax rate
        self.wash_sale_days = 30         # IRS wash sale rule
        
    def get_tax_lots(self, user_id: int, symbol: Optional[str] = None) -> List[TaxLot]:
        """Get all tax lots for a user's portfolio"""
        
        # Get all purchase transactions
        query = self.db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type.in_([TransactionType.PURCHASE, TransactionType.DIVIDEND])
        )
        
        if symbol:
            query = query.filter(Transaction.symbol == symbol)
            
        purchase_transactions = query.order_by(Transaction.date.asc()).all()
        
        tax_lots = []
        
        for transaction in purchase_transactions:
            if not transaction.symbol or not transaction.quantity:
                continue
                
            # Get current price
            current_price = self._get_current_price(transaction.symbol)
            if current_price is None:
                continue
                
            quantity = transaction.quantity
            cost_basis = abs(transaction.amount)  # Amount is negative for purchases
            market_value = quantity * current_price
            unrealized_gain_loss = market_value - cost_basis
            
            holding_period_days = (datetime.now() - transaction.date).days
            is_long_term = holding_period_days > 365
            
            tax_lot = TaxLot(
                symbol=transaction.symbol,
                purchase_date=transaction.date,
                quantity=quantity,
                cost_basis=cost_basis,
                current_price=current_price,
                market_value=market_value,
                unrealized_gain_loss=unrealized_gain_loss,
                holding_period_days=holding_period_days,
                is_long_term=is_long_term,
                transaction_id=transaction.id
            )
            
            tax_lots.append(tax_lot)
            
        return tax_lots
    
    def identify_harvesting_candidates(self, user_id: int, 
                                     min_loss_threshold: float = 100.0) -> List[TaxLossHarvestingCandidate]:
        """Identify securities with unrealized losses suitable for tax-loss harvesting"""
        
        tax_lots = self.get_tax_lots(user_id)
        
        # Group by symbol
        lots_by_symbol = {}
        for lot in tax_lots:
            if lot.symbol not in lots_by_symbol:
                lots_by_symbol[lot.symbol] = []
            lots_by_symbol[lot.symbol].append(lot)
        
        candidates = []
        
        for symbol, lots in lots_by_symbol.items():
            # Calculate total unrealized loss
            total_unrealized_loss = sum(lot.unrealized_gain_loss for lot in lots if lot.unrealized_gain_loss < 0)
            
            if abs(total_unrealized_loss) >= min_loss_threshold:
                # Check for wash sale period
                last_sale_date = self._get_last_sale_date(user_id, symbol)
                wash_sale_period_active = False
                
                if last_sale_date:
                    days_since_sale = (datetime.now() - last_sale_date).days
                    wash_sale_period_active = days_since_sale <= self.wash_sale_days
                
                # Get replacement candidates
                replacement_candidates = self._get_replacement_candidates(symbol)
                
                # Calculate potential tax savings
                potential_tax_savings = self._calculate_tax_savings(lots, total_unrealized_loss)
                
                candidate = TaxLossHarvestingCandidate(
                    symbol=symbol,
                    tax_lots=lots,
                    total_unrealized_loss=total_unrealized_loss,
                    potential_tax_savings=potential_tax_savings,
                    replacement_candidates=replacement_candidates,
                    last_sale_date=last_sale_date,
                    wash_sale_period_active=wash_sale_period_active
                )
                
                candidates.append(candidate)
        
        # Sort by potential tax savings (descending)
        candidates.sort(key=lambda x: x.potential_tax_savings, reverse=True)
        
        return candidates
    
    def generate_harvesting_recommendations(self, user_id: int, 
                                          method: TaxLotMethod = TaxLotMethod.HIFO) -> List[TaxLossHarvestingRecommendation]:
        """Generate tax-loss harvesting recommendations"""
        
        candidates = self.identify_harvesting_candidates(user_id)
        recommendations = []
        
        for candidate in candidates:
            if candidate.wash_sale_period_active:
                continue  # Skip securities in wash sale period
            
            # Select lots to sell based on method
            lots_to_sell = self._select_lots_to_sell(candidate.tax_lots, method)
            
            if not lots_to_sell:
                continue
                
            estimated_tax_savings = self._calculate_tax_savings(lots_to_sell, 
                                                              sum(lot.unrealized_gain_loss for lot in lots_to_sell))
            
            # Determine replacement security
            replacement_security = None
            if candidate.replacement_candidates:
                replacement_security = candidate.replacement_candidates[0]  # Use first candidate
            
            # Generate reasoning
            reasoning = self._generate_reasoning(candidate, lots_to_sell, estimated_tax_savings)
            
            # Determine urgency
            urgency = self._determine_urgency(candidate, lots_to_sell)
            
            recommendation = TaxLossHarvestingRecommendation(
                candidate=candidate,
                lots_to_sell=lots_to_sell,
                estimated_tax_savings=estimated_tax_savings,
                replacement_security=replacement_security,
                reasoning=reasoning,
                urgency=urgency
            )
            
            recommendations.append(recommendation)
        
        return recommendations
    
    def execute_tax_loss_harvesting(self, user_id: int, 
                                  recommendation: TaxLossHarvestingRecommendation) -> Dict[str, any]:
        """Execute tax-loss harvesting recommendation"""
        
        try:
            results = {
                "sell_orders": [],
                "buy_orders": [],
                "estimated_tax_savings": recommendation.estimated_tax_savings,
                "success": False
            }
            
            # Create sell orders for selected lots
            total_quantity_to_sell = sum(lot.quantity for lot in recommendation.lots_to_sell)
            
            sell_order_request = OrderRequest(
                symbol=recommendation.candidate.symbol,
                side=OrderSide.SELL,
                quantity=total_quantity_to_sell,
                order_type=OrderType.MARKET,
                time_in_force=TimeInForce.DAY
            )
            
            sell_order = self.order_management.create_order(user_id, sell_order_request)
            sell_success = self.order_management.submit_order(sell_order.id)
            
            results["sell_orders"].append({
                "order_id": sell_order.id,
                "symbol": recommendation.candidate.symbol,
                "quantity": total_quantity_to_sell,
                "submitted": sell_success
            })
            
            # If replacement security specified, create buy order
            if recommendation.replacement_security and sell_success:
                # Calculate equivalent dollar amount
                replacement_price = self._get_current_price(recommendation.replacement_security)
                if replacement_price:
                    replacement_quantity = (total_quantity_to_sell * recommendation.candidate.tax_lots[0].current_price) / replacement_price
                    
                    buy_order_request = OrderRequest(
                        symbol=recommendation.replacement_security,
                        side=OrderSide.BUY,
                        quantity=replacement_quantity,
                        order_type=OrderType.MARKET,
                        time_in_force=TimeInForce.DAY
                    )
                    
                    buy_order = self.order_management.create_order(user_id, buy_order_request)
                    buy_success = self.order_management.submit_order(buy_order.id)
                    
                    results["buy_orders"].append({
                        "order_id": buy_order.id,
                        "symbol": recommendation.replacement_security,
                        "quantity": replacement_quantity,
                        "submitted": buy_success
                    })
            
            results["success"] = sell_success
            
            logger.info(f"Executed tax-loss harvesting for user {user_id}: {recommendation.candidate.symbol}")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to execute tax-loss harvesting: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d", interval="1d")
            if not data.empty:
                return float(data['Close'].iloc[-1])
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
        return None
    
    def _get_last_sale_date(self, user_id: int, symbol: str) -> Optional[datetime]:
        """Get the last sale date for a symbol"""
        last_sale = self.db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.symbol == symbol,
            Transaction.transaction_type == TransactionType.SALE
        ).order_by(Transaction.date.desc()).first()
        
        return last_sale.date if last_sale else None
    
    def _get_replacement_candidates(self, symbol: str) -> List[str]:
        """Get replacement security candidates to avoid wash sale"""
        # This is a simplified implementation
        # In practice, you'd want more sophisticated sector/industry matching
        
        sector_etfs = {
            # Technology
            'AAPL': ['XLK', 'VGT', 'FTEC'],
            'MSFT': ['XLK', 'VGT', 'FTEC'],
            'GOOGL': ['XLK', 'VGT', 'FTEC'],
            'AMZN': ['XLY', 'VCR', 'FDIS'],
            
            # Healthcare
            'JNJ': ['XLV', 'VHT', 'FHLC'],
            'UNH': ['XLV', 'VHT', 'FHLC'],
            
            # Finance
            'JPM': ['XLF', 'VFH', 'FNCL'],
            'BAC': ['XLF', 'VFH', 'FNCL'],
            
            # Energy
            'XOM': ['XLE', 'VDE', 'FENY'],
            'CVX': ['XLE', 'VDE', 'FENY'],
        }
        
        return sector_etfs.get(symbol, ['SPY', 'VTI', 'IVV'])  # Default to broad market ETFs
    
    def _calculate_tax_savings(self, lots: List[TaxLot], total_loss: float) -> float:
        """Calculate potential tax savings from realizing losses"""
        if total_loss >= 0:
            return 0
        
        # Separate short-term and long-term losses
        short_term_loss = sum(lot.unrealized_gain_loss for lot in lots 
                            if lot.unrealized_gain_loss < 0 and not lot.is_long_term)
        long_term_loss = sum(lot.unrealized_gain_loss for lot in lots 
                           if lot.unrealized_gain_loss < 0 and lot.is_long_term)
        
        # Calculate tax savings
        short_term_savings = abs(short_term_loss) * self.short_term_tax_rate
        long_term_savings = abs(long_term_loss) * self.long_term_tax_rate
        
        return short_term_savings + long_term_savings
    
    def _select_lots_to_sell(self, lots: List[TaxLot], method: TaxLotMethod) -> List[TaxLot]:
        """Select which lots to sell based on method"""
        
        # Only consider lots with losses
        loss_lots = [lot for lot in lots if lot.unrealized_gain_loss < 0]
        
        if not loss_lots:
            return []
        
        if method == TaxLotMethod.FIFO:
            return sorted(loss_lots, key=lambda x: x.purchase_date)
        elif method == TaxLotMethod.LIFO:
            return sorted(loss_lots, key=lambda x: x.purchase_date, reverse=True)
        elif method == TaxLotMethod.HIFO:
            return sorted(loss_lots, key=lambda x: x.cost_per_share, reverse=True)
        else:  # SPECIFIC_ID - select lots with highest losses
            return sorted(loss_lots, key=lambda x: x.unrealized_gain_loss)
    
    def _generate_reasoning(self, candidate: TaxLossHarvestingCandidate, 
                          lots_to_sell: List[TaxLot], estimated_tax_savings: float) -> str:
        """Generate reasoning for the recommendation"""
        
        total_loss = sum(lot.unrealized_gain_loss for lot in lots_to_sell)
        
        reasoning = f"Harvesting ${abs(total_loss):,.2f} in losses from {candidate.symbol} "
        reasoning += f"could save approximately ${estimated_tax_savings:,.2f} in taxes. "
        
        if candidate.replacement_candidates:
            reasoning += f"Consider replacing with {candidate.replacement_candidates[0]} to maintain market exposure."
        
        return reasoning
    
    def _determine_urgency(self, candidate: TaxLossHarvestingCandidate, 
                         lots_to_sell: List[TaxLot]) -> str:
        """Determine urgency of the recommendation"""
        
        # High urgency if:
        # 1. Large potential tax savings
        # 2. Near year-end
        # 3. Positions approaching long-term status
        
        if candidate.potential_tax_savings > 5000:
            return "high"
        elif candidate.potential_tax_savings > 1000:
            return "medium"
        else:
            return "low"
    
    def get_tax_loss_summary(self, user_id: int) -> Dict[str, any]:
        """Get comprehensive tax-loss harvesting summary"""
        
        candidates = self.identify_harvesting_candidates(user_id)
        recommendations = self.generate_harvesting_recommendations(user_id)
        
        total_unrealized_losses = sum(abs(c.total_unrealized_loss) for c in candidates)
        total_potential_savings = sum(c.potential_tax_savings for c in candidates)
        
        return {
            "total_unrealized_losses": total_unrealized_losses,
            "total_potential_tax_savings": total_potential_savings,
            "num_candidates": len(candidates),
            "num_recommendations": len(recommendations),
            "wash_sale_blocked": len([c for c in candidates if c.wash_sale_period_active]),
            "candidates": [{
                "symbol": c.symbol,
                "unrealized_loss": c.total_unrealized_loss,
                "potential_savings": c.potential_tax_savings,
                "wash_sale_blocked": c.wash_sale_period_active
            } for c in candidates],
            "recommendations": [{
                "symbol": r.candidate.symbol,
                "estimated_tax_savings": r.estimated_tax_savings,
                "replacement_security": r.replacement_security,
                "reasoning": r.reasoning,
                "urgency": r.urgency
            } for r in recommendations]
        }