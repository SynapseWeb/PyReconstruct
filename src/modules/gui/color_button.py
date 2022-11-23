from PySide6.QtWidgets import QPushButton, QColorDialog
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtCore import Qt

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
        color = QColorDialog.getColor()
        self.setColor((color.red(), color.green(), color.blue()))
    
    def setColor(self, color):
        """Sets the visual color for the button."""
        self.color = color
        self.pixmap = QPixmap(self.size())
        if self.color is None:
            self.pixmap.fill(Qt.transparent)
        else:
            self.pixmap.fill(QColor(*self.color))
        self.setIcon(QIcon(self.pixmap))
    
    def getColor(self):
        return self.color
    
    def resizeEvent(self, event):
        """Called when button is resized."""
        super().resizeEvent(event)
        self.setColor(self.color)

