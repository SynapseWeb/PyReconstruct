import os
import json

from .locations import welcome_series_dir

def getDefaultPaletteTraces():
    """Function to store data for default trace palette"""
    with open(os.path.join(welcome_series_dir, "welcome.ser"), "r") as f:
        welcome_json = json.load(f)
    
    return welcome_json["palette_traces"]
