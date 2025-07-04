def epv(normalized_earnings: float, cost_of_capital: float) -> float:
    """Earnings Power Value = normalized earnings / cost of capital (stub)."""
    if cost_of_capital == 0:
        raise ValueError("Cost of capital cannot be zero")
    return normalized_earnings / cost_of_capital