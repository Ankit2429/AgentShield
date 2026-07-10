def generate_timestamp() -> str:
    from datetime import datetime
    return datetime.utcnow().isoformat()
