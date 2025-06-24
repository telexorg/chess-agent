def safe_get(obj, *attrs):
    for attr in attrs:
        obj = getattr(obj, attr, None)
        if obj is None:
            return None
    return obj