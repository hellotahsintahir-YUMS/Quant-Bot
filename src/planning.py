"""Per-user, recommendations-only investment planning."""
from __future__ import annotations

from typing import Dict, Iterable, List


def recommend_stocks(signals: Iterable[Dict], limit: int = 5) -> List[Dict]:
    """Rank BUY signals by technical strength without placing trades."""
    candidates = [
        signal for signal in signals
        if signal.get("action") == "BUY" and signal.get("price", 0) > 0
    ]
    return sorted(
        candidates,
        key=lambda signal: (
            float(signal.get("signal_strength", 0)),
            int(signal.get("signal_score", 0)),
        ),
        reverse=True,
    )[:limit]


def calculate_allocations(
    budget: float,
    selected_symbols: Iterable[str],
    signals_by_symbol: Dict[str, Dict],
    reserve_pct: float = 0.0,
) -> List[Dict]:
    """Allocate investable cash by positive signal strength."""
    if budget <= 0:
        raise ValueError("Budget must be greater than zero.")
    if not 0 <= reserve_pct < 1:
        raise ValueError("Reserve percentage must be between 0 and 100.")

    selected = list(dict.fromkeys(selected_symbols))
    selected_signals = [
        signals_by_symbol[symbol] for symbol in selected
        if symbol in signals_by_symbol and signals_by_symbol[symbol].get("price", 0) > 0
    ]
    if not selected_signals:
        return []

    investable = budget * (1 - reserve_pct)
    weights = [
        max(float(signal.get("signal_strength", 0)), 1.0)
        for signal in selected_signals
    ]
    total_weight = sum(weights)
    allocations = []
    for signal, weight in zip(selected_signals, weights):
        amount = investable * weight / total_weight
        price = float(signal["price"])
        shares = int(amount // price)
        allocations.append({
            "symbol": signal["symbol"],
            "action": signal.get("action", "HOLD"),
            "price": price,
            "signal_strength": float(signal.get("signal_strength", 0)),
            "recommended_amount": round(amount, 2),
            "recommended_shares": shares,
            "uninvested_amount": round(amount - shares * price, 2),
        })
    return allocations
