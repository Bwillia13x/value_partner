def ncav_ratio(price: float, net_current_asset_value: float) -> float:
    """Price / NCAV ratio (stub)."""
    if net_current_asset_value == 0:
        raise ValueError("NCAV cannot be zero")
    return price / net_current_asset_value