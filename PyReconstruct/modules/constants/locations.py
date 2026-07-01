import os
from pathlib import Path

def createHiddenDir(jser_dir, series_name):
    """Create a hidden folder to contain the individual section and series files."""    
    hidden_dir = os.path.join(jser_dir, f".{series_name}")
    # check if the folder exists, delete if it does
    if os.path.isdir(hidden_dir):
        for f in os.listdir(hidden_dir):
            os.remove(os.path.join(hidden_dir, f))
        os.rmdir(hidden_dir)
    # create the folder
    os.mkdir(hidden_dir)
    if os.name == "nt":  # manually hide if windows
        import subprocess
        subprocess.check_call(["attrib", "+H", hidden_dir])
    
    return hidden_dir

from .frozen import is_frozen, bundle_base

if is_frozen():  # assets bundled at <_MEIPASS>/PyReconstruct/assets
    src_dir = bundle_base() / "PyReconstruct"
else:
    src_dir = Path(os.path.realpath(__file__)).parents[2]

assets_dir          =  os.path.join(src_dir, "assets")
welcome_series_dir  =  os.path.join(assets_dir, "welcome_series", ".welcome")
checker_dir         =  os.path.join(assets_dir, "checker")
img_dir             =  os.path.join(assets_dir, "img")
icon_path           =  os.path.join(img_dir, "PyReconstruct.ico")
