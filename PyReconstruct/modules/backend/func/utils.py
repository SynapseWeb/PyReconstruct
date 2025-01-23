import os
import uuid
from contextlib import redirect_stdout


def make_unique_id() -> int:
    """Return a uuid."""

    return uuid.uuid4().int


def determine_cpus(percent_usage: int) -> int:
    """Determine max numbers of cores to use."""
    
    cpus = int(os.cpu_count() * (percent_usage / 100))

    return cpus or 1


def stdout_to_devnull(func):
    """Silence stdout by redirecting to devnull.

    Use as @stdout_to_devnull decorator or as stdout_to_devnull(func)(args)
    """

    def wrapper(*args, **kwargs):
        
        with open(os.devnull, 'w') as devnull:
            with redirect_stdout(devnull):
                return func(*args, **kwargs)
            
    return wrapper
