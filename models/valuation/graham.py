import math

__all__ = ["graham_number", "margin_of_safety"]


def graham_number(eps: float, book_value_per_share: float) -> float:
    """Return Graham Number = sqrt(22.5 * EPS * BVPS).

    22.5 = 15 (max P/E) * 1.5 (max P/B) as suggested by Ben Graham.
    """
    if eps < 0 or book_value_per_share < 0:
        raise ValueError("EPS and BVPS must be non-negative for Graham Number")
    return math.sqrt(22.5 * eps * book_value_per_share)


def margin_of_safety(intrinsic_value: float, market_price: float) -> float:
    """Return margin-of-safety percentage given intrinsic and market price.

    Positive → undervalued; Negative → overvalued.
    """
    if intrinsic_value == 0:
        raise ValueError("Intrinsic value cannot be zero")
    return (intrinsic_value - market_price) / intrinsic_value