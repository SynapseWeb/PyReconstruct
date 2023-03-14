from PySide6.QtGui import QPainter

from .image_layer import ImageLayer
from .trace_layer import TraceLayer

from modules.pyrecon import (
    Series,
    Section,
    Transform
)

class SectionLayer(ImageLayer, TraceLayer):

    def __init__(self, section : Section, series : Series):
        """Create the section layer object.
        
            Params:
                section (Section): the section object for the layer
                series (Series): the series object
        """
        ImageLayer.__init__(self, section, series)
        TraceLayer.__init__(self, section, series)
    
    def generateView(
        self,
        pixmap_dim : tuple,
        window : list,
        generate_image=True,
        generate_traces=True,
        hide_traces=False,
        show_all_traces=False
        ):
        """Generate the pixmap view for the section.
        
            Params:
                pixmap_dim (tuple): the dimensions of the view
                window (list): the x, y, w, h of the field view
                generate_image (bool): whether or not to regenerate the image
                generate_traces (bool): whether or not to regenerate the traces
        """
        # set the series screen mag
        self.series.screen_mag = window[2] / pixmap_dim[0]

        # generate image
        if generate_image:
            self.image_layer = self.generateImageLayer(pixmap_dim, window)
        
        # if user requests traces to be hidden
        if hide_traces:
            return self.image_layer.copy()        
            
        if generate_traces:
            self.trace_layer = self.generateTraceLayer(
                pixmap_dim,
                window,
                show_all_traces,
                generate_image
            )
        
        # combine pixmaps
        view = self.image_layer.copy()
        painter = QPainter(view)
        painter.drawPixmap(0, 0, self.trace_layer)
        painter.end()

        return view
    
    def changeTform(self, new_tform : Transform):
        """Set the transform for the image.
        
            Params:
                new_tform (Transform): the new transform to set for the section
        """
        self.section.tforms[self.series.alignment] = new_tform

