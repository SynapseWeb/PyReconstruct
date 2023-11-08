from PySide6.QtWidgets import QPushButton, QColorDialog
from PySide6.QtGui import QColor, QPainter

class ColorButton(QPushButton):

    def __init__(self, color : tuple, parent):
        """Create the color button widget.
        
            Params:
                color (tuple): the color for the button
                parent (QWidget): the parent widget for the button
        """
        super().__init__(parent)
        self.color = color
        self.setColor(color)
        self.clicked.connect(self.selectColor)

    def selectColor(self):
        """Called when button is clicked: prompts user to change color"""
        if self.color:
            color = QColorDialog.getColor(QColor(*self.color))
        else:
            color = QColorDialog.getColor()
        if color.isValid():
            self.setColor((color.red(), color.green(), color.blue()))
    
    def setColor(self, color):
        """Sets the visual color for the button."""
        self.color = color
        if color:
            s = f"({','.join(map(str,self.color))})"
            self.setStyleSheet(f"background-color:rgb{s}")
    
    def getColor(self):
        return self.color
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setMaximumWidth(self.height() * 2)