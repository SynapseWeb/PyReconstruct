import os
from pathlib import Path


fp = os.path.realpath(__file__)
src_dir = Path(fp).parents[1]
assets_dir = os.path.join(src_dir, "assets")
img_dir = os.path.join(assets_dir, "img")

backend_series_dir = os.path.join(src_dir, "backend_series")
if not os.path.isdir(backend_series_dir):
    os.mkdir(backend_series_dir)

# Clean up
del fp
