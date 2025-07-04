def residual_income_value(book_value: float, residual_income: list[float], cost_of_equity: float):
    """Simple RI model (stub)."""
    pv_ri = sum(ri / ((1 + cost_of_equity) ** i) for i, ri in enumerate(residual_income, start=1))
    return book_value + pv_ri