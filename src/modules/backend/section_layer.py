from PySide6.QtGui import QPainter

from modules.backend.image_layer import ImageLayer
from modules.backend.trace_layer import TraceLayer

from modules.recon.section import Section

class SectionLayer(ImageLayer, TraceLayer):

    def __init__(self, section : Section, src_dir : str):
        ImageLayer.__init__(self, section, src_dir)
        TraceLayer.__init__(self, section)
    
    def generateView(self, pixmap_dim : tuple, window : list, generate_image=True, generate_traces=True):
        """Generate the pixmap view for the section.
        
            Params:
                pixmap_dim (tuple): the dimensions of the view
                window (list): the x, y, w, h of the field view
                generate_image (bool): whether or not to regenerate the image
                generate_traces (bool): whether or not to regenerate the traces"""
        # generate layers
        if generate_image:
            self.image_layer = self.generateImageLayer(pixmap_dim, window)
        if generate_traces:
            self.trace_layer = self.generateTraceLayer(pixmap_dim, window)
        # combine pixmaps
        view = self.image_layer.copy()
        painter = QPainter(view)
        painter.drawPixmap(0, 0, self.trace_layer)
        painter.end()

        return view

