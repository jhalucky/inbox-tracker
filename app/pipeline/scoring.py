def apply_sender_weight(urgency: int, importance_weight: float) -> float:
    weight = max(0.0, importance_weight)
    return min(5.0, urgency * weight)
