import os
import json

from .locations import assets_dir

def getDefaultPaletteTraces():
    """Function to store data for default trace palette"""
    with open(os.path.join(assets_dir, "welcome_series", "welcome.ser"), "r") as f:
        welcome_json = json.load(f)
    
    return welcome_json["palette_traces"]
