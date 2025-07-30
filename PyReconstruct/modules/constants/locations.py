import os
from pathlib import Path
from typing import List, Tuple


def getWorkingDir(image_locations: List[str]) -> Tuple[str, str]:
    """Return tuple of strings representing the working and source directories."""
    try:
            
        wdir = Path(image_locations[0]).parent
            
        if wdir.suffix == ".zarr":  # create series next to zarr if necessary
            
            sdir = str(wdir)
            wdir = str(wdir.parent)
            
        else:
            
            sdir = str(wdir)
                
    except PermissionError:
            
        print(
            "Series cannot be created adjacent to images due "
            "to user not having proper permissions. Creating "
            "in home folder instead."
        )
            
        home_string = "HOMEPATH" if os.name == "nt" else "HOME"
        wdir = os.environ.get(home_string)

    return str(wdir), str(sdir)


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

    if os.name == "nt":  # manually hide if using Windows
        import subprocess
        subprocess.check_call(["attrib", "+H", hidden_dir])
    
    return hidden_dir

fp                  =  os.path.realpath(__file__)
src_dir             =  Path(fp).parents[2]
assets_dir          =  os.path.join(src_dir, "assets")
welcome_series_dir  =  os.path.join(assets_dir, "welcome_series", ".welcome")
checker_dir         =  os.path.join(assets_dir, "checker")
img_dir             =  os.path.join(assets_dir, "img")
icon_path           =  os.path.join(img_dir, "PyReconstruct.ico")

# Clean up
del fp
