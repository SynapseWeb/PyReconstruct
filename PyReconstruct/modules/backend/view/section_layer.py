from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtCore import Qt

from .image_layer import ImageLayer
from .trace_layer import TraceLayer

from PyReconstruct.modules.datatypes import (
    Series,
    Section
)


class SectionLayer(ImageLayer, TraceLayer):

    def __init__(self, section : Section, series : Series, load_image_layer=True):
        """Create the section layer object.
        
            Params:
                section (Section): the section object for the layer
                series (Series): the series object
        """
        if load_image_layer:
            ImageLayer.__init__(self, section, series)
            
        TraceLayer.__init__(self, section, series)
    
    def generateView(
        self,
        pixmap_dim : tuple,
        window : list,
        generate_image=True,
        generate_traces=True,
        hide_traces=False,
        show_all_traces=False,
        hide_image=False
        ):
        """Generate pixmap view for a section.
        
            Params:
                pixmap_dim (tuple): the dimensions of the view
                window (list): the x, y, w, h of the field view
                generate_image (bool): whether or not to regenerate the image
                generate_traces (bool): whether or not to regenerate the traces
        """
        ## Save attributes
        self.series.window = window
        self.pixmap_dim = pixmap_dim
        
        ## Set series screen mag and scaling
        self.series.screen_mag = window[2] / pixmap_dim[0]
        self.scaling = pixmap_dim[0] / (window[2] / self.section.mag)

        ## Generate image
        if hide_image:
            self.image_layer = QPixmap(*pixmap_dim)
            self.image_layer.fill(Qt.black)
        elif generate_image:
            self.image_layer = self.generateImageLayer(pixmap_dim, window)
        
        ## Hide all traces if requested
        if hide_traces:
            return self.image_layer.copy()        

        if generate_traces:
            self.trace_layer = self.generateTraceLayer(
                pixmap_dim,
                window,
                show_all_traces,
                generate_image
            )
        
        ## Combine pixmaps
        view = self.image_layer.copy()
        painter = QPainter(view)
        painter.drawPixmap(0, 0, self.trace_layer)
        painter.end()

        return view

