import os
import uuid

def make_unique_id() -> int:
    """Return a uuid."""

    return uuid.uuid4().int


def determine_cpus(percent_usage: int) -> int:
    """Determine max numbers of cores to use."""
    
    cpus = int(os.cpu_count() * (percent_usage / 100))

    return cpus or 1
