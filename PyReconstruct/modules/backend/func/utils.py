import uuid


def make_unique_id() -> int:
    """Return a uuid."""

    return uuid.uuid4().int

