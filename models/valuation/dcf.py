def discounted_cash_flow(cash_flows, discount_rate=0.1, terminal_growth=0.03):
    """Very simplified two-stage DCF calculation (stub)."""
    pv_operating = sum(cf / ((1 + discount_rate) ** i) for i, cf in enumerate(cash_flows, start=1))
    terminal_value = cash_flows[-1] * (1 + terminal_growth) / (discount_rate - terminal_growth)
    pv_terminal = terminal_value / ((1 + discount_rate) ** len(cash_flows))
    return pv_operating + pv_terminal