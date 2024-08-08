import json
import hashlib


def print_flush(s: str):
    """Correct I/O buffering."""

    print(s, flush=True)


def flatten_list(nested_list):
    """Recursively flatten lists to handle groups."""

    if not (bool(nested_list)):  # if empty list

        return nested_list

    if isinstance(nested_list[0], list):

        return flatten_list(*nested_list[:1]) + flatten_list(nested_list[1:])

    return nested_list[:1] + flatten_list(nested_list[1:])


def get_sha1sum(filepath):
    """Get sha1sum of jser file."""
    
    with open(filepath, 'r') as source:

        obj = json.load(source)

    ## Make src_dir empty str as differs betweeen users
    obj["series"]["src_dir"] = ""

    ## Sort keys and encode
    obj = json.dumps(obj, sort_keys=True).encode("utf-8")

    return hashlib.sha1(obj).hexdigest()


def print_summary(series, window, start, end, mag, zarr_fp):
    
    print(
        f"\nSeries \"{series.name}\" exported as zarr\n\n"
        f"Window:          {[round(elem, 2) for elem in window]}\n"
        f"Sections:        {start}-{end}\n"
        f"Zarr mag:        {mag}\n"
        f"Zarr location:   {zarr_fp}\n\n"
    )
