import time
from functools import wraps


def ttl_cache(seconds: int):
    def decorator(func):
        _cache: dict = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.monotonic()
            if key in _cache and now - _cache[key][0] < seconds:
                return _cache[key][1]
            result = func(*args, **kwargs)
            _cache[key] = (now, result)
            return result

        return wrapper

    return decorator
