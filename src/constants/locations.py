import os
from pathlib import Path


fp = os.path.realpath(__file__)
src_dir = Path(fp).parents[1]
assets_dir = os.path.join(src_dir, "assets")
img_dir = os.path.join(assets_dir, "img")

# Clean up
del fp
