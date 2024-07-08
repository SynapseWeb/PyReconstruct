import math

from PySide6.QtGui import QPainter

from .section_layer import SectionLayer
from .zarr_layer import ZarrLayer

from PyReconstruct.modules.datatypes import (
    Series,
    Transform,
    Trace,
    Flag
)
from PyReconstruct.modules.backend.func import SectionStates, SeriesStates
from PyReconstruct.modules.calc import (
    centroid,
    lineDistance,
    pixmapPointToField
)
from PyReconstruct.modules.gui.utils import notify, notifyConfirm

class FieldView():
    pass
    
    
    
    
