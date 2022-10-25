from PySide6.QtGui import QPainter

from modules.backend.image_layer import ImageLayer
from modules.backend.trace_layer import TraceLayer

from modules.pyrecon.section import Section

class SectionLayer(ImageLayer, TraceLayer):

    def __init__(self, section : Section, src_dir : str, alignment : str):
        ImageLayer.__init__(self, section, src_dir, alignment)
        TraceLayer.__init__(self, section, alignment)
    
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
    
    def changeAlignment(self, new_alignment : str):
        """Set the alignment to use for the section.
        
            Params:
                new_alignment (str): the name for the new alignment
        """
        self.alignment = new_alignment
    
    def changeTform(self, new_tform : list):
        """Set the transform for the image.
        
            Params:
                tform (list): the transform as a list of numbers
        """
        self.section.tforms[self.alignment] = new_tform

