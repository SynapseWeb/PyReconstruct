"""Fast JSON (de)serialization with a stdlib fallback.

Uses orjson when it is installed (much faster dumps, faster loads) and falls
back to the stdlib json on any error. The fallback means this can never be
*less* capable than json -- important on the save path, where a serialization
failure would risk losing data (e.g. orjson rejects NaN/Inf and exotic keys
that json silently coerces).

fast_dumps always returns UTF-8 bytes, so callers open files in binary mode.
fast_loads accepts either bytes or str.
"""

import json

try:
    import orjson
    _HAVE_ORJSON = True
except ImportError:  # pragma: no cover - orjson is a listed dependency
    orjson = None
    _HAVE_ORJSON = False


def fast_loads(data):
    """Parse JSON from bytes or str."""
    if _HAVE_ORJSON:
        try:
            return orjson.loads(data)
        except Exception:
            pass
    if isinstance(data, (bytes, bytearray)):
        data = data.decode("utf-8")
    return json.loads(data)


def fast_dumps(obj) -> bytes:
    """Serialize an object to compact UTF-8 JSON bytes."""
    if _HAVE_ORJSON:
        try:
            return orjson.dumps(obj, option=orjson.OPT_NON_STR_KEYS)
        except Exception:
            pass
    return json.dumps(obj).encode("utf-8")
