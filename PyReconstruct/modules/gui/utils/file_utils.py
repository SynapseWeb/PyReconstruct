"""File utility functions."""

from pathlib import Path
from typing import Union


def ensure_path_obj(fp: Union[str, Path]) -> Path:
    """Ensure object is a Path object."""

    if not isinstance(fp, Path):
        fp = Path(fp)

    return fp


def get_hidden_dir(jser_fp: Union[str, Path]) -> Path:
    """Return Path object representing the hidden directory."""

    jser_fp = ensure_path_obj(jser_fp)
    sname = jser_fp.stem
    return jser_fp.with_name(f".{sname}")


def get_ser_file(jser_fp: Union[str, Path]) -> Path:
    """Return Path object representing .ser file."""

    jser_fp = ensure_path_obj(jser_fp)
    hidden_dir = get_hidden_dir(jser_fp)

    return hidden_dir / f"{jser_fp.stem}.ser"

    
