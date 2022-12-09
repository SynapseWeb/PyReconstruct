import os
from pathlib import Path

def createHiddenDir(jser_dir, series_name):
    """Create a hidden folder to contain the individual section and series files."""    
    # create and hide the folder
    hidden_dir = os.path.join(jser_dir, f".{series_name}")
    os.mkdir(hidden_dir)
    if os.name == "nt":
        import subprocess
        subprocess.check_call(["attrib", "+H", hidden_dir])
    
    return hidden_dir

fp = os.path.realpath(__file__)
src_dir = Path(fp).parents[1]
assets_dir = os.path.join(src_dir, "assets")
img_dir = os.path.join(assets_dir, "img")

# Clean up
del fp
