from PySide2.QtWidgets import QPushButton, QColorDialog
from PySide2.QtGui import QColor, QPixmap, QIcon

class ColorButton(QPushButton):

    def __init__(self, parent):
        super().__init__(parent)
    
    def setColor(self, color):
        pixmap = QPixmap(self.size())
        pixmap.fill(color)
        self.setIcon(QIcon(pixmap))
        self.update()