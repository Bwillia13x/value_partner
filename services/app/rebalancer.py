from typing import List, Dict
from .database import Holding, Strategy

class Rebalancer:
    def __init__(self, current_holdings: List[Holding], target_strategy: Strategy):
        self.current_holdings = current_holdings
        self.target_strategy = target_strategy

    def calculate_trades(self) -> List[Dict]:
        """
        Calculates the trades required to align the current portfolio with the target strategy.
        Returns a list of trades, e.g., [{'symbol': 'AAPL', 'action': 'buy', 'quantity': 10.5}]
        """
        current_portfolio_value = sum(h.market_value for h in self.current_holdings)
        current_allocations = {h.symbol: h.market_value / current_portfolio_value for h in self.current_holdings}

        target_allocations = {h.symbol: h.target_weight for h in self.target_strategy.holdings}

        trades = []

        # Determine trades for assets in the target strategy
        for symbol, target_weight in target_allocations.items():
            current_weight = current_allocations.get(symbol, 0)
            weight_diff = target_weight - current_weight

            if abs(weight_diff) > 0.001:  # Only trade if the difference is significant
                trade_value = weight_diff * current_portfolio_value
                # This is a simplified calculation; a real implementation would need the current price
                # For now, we'll placeholder the quantity calculation
                # In a real scenario, you'd fetch the current price for the symbol
                # and calculate quantity = trade_value / price
                # For this example, we'll just use the trade value as a proxy for quantity
                action = 'buy' if trade_value > 0 else 'sell'
                trades.append({'symbol': symbol, 'action': action, 'value': abs(trade_value)})

        # Determine trades for assets not in the target strategy (sell all)
        for symbol, current_weight in current_allocations.items():
            if symbol not in target_allocations:
                trade_value = current_weight * current_portfolio_value
                trades.append({'symbol': symbol, 'action': 'sell', 'value': trade_value})

        return trades
