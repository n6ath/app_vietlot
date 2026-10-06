"""Optional ML validation; predictions are eligible only when beating rule baseline."""
def walk_forward_validate(*args, **kwargs):
    return {"baseline_score": 0.0, "ml_score": 0.0, "ml_enabled": False,
            "reason": "No ML model is enabled by default."}
