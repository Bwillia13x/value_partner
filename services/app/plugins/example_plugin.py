def predict(payload):
    """Echo plugin that returns input payload with extra field."""
    payload["echo"] = True
    return payload