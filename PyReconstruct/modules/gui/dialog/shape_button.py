from PySide6.QtWidgets import QPushButton

from .shapes import ShapesDialog, shapeToIcon

class ShapeButton(QPushButton):

    def __init__(self, points : list, parent):
        """Create the shape button widget.
        
            Params:
                color (tuple): the color for the button
                parent (QWidget): the parent widget for the button
        """
        super().__init__(parent)
        self.setShape(points)
        self.clicked.connect(self.selectShape)

    def selectShape(self):
        """Called when button is clicked: prompts user to change shape"""
        points, confirmed = ShapesDialog(self).exec()
        if confirmed:
            self.setShape(points)
    
    def setShape(self, points):
        """Sets the shape for the button."""
        self.points = points
        if points:
            self.setIcon(shapeToIcon(points, size=min(self.width(), self.height())))
    
    def getShape(self):
        return self.points
    
    def resizeEvent(self, event):
        """Called when button is resized."""
        super().resizeEvent(event)
        self.setShape(self.points)