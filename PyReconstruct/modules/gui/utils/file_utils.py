"""File utility functions."""

from pathlib import Path
from typing import Union


def get_hidden_dir(jser_fp: Union[str, Path]) -> Path:
    """Return a string representing the hidden directory."""

    if not isinstance(jser_fp, Path):
        jser_fp = Path(jser_fp)

    sname = jser_fp.stem
    return jser_fp.with_name(f".{sname}")
