from PySide2.QtWidgets import QWidget, QPushButton
from PySide2.QtGui import QIcon, QPixmap
from PySide2.QtCore import QSize

class ModeButtonWidget(QWidget):

    def __init__(self, parent, button_size=30):
        super().__init__(parent)
        self.parent_widget = parent
        self.bsize = button_size
        self.setFixedSize(self.bsize*5, self.bsize*2)

        self.mode_buttons = {}
        self.createModeButton("pointer", 0, 0, parent.toPointer)
        self.createModeButton("panzoom", 1, 0, parent.toPanzoom)
        self.createModeButton("pencil", 0, 1, parent.toPencil)
    
    def modeButtonClicked(self):
        sender = self.sender()
        for name, button in self.mode_buttons.items():
            if button[0] == sender:
                button[0].setChecked(True)
                button[1]()
            else:
                button[0].setChecked(False)      

    def createModeButton(self, name, row, col, func):
        b = QPushButton(self.central_widget)
        pixmap = QPixmap(name + ".png").scaled(self.bsize, self.bsize)
        b.setIcon(QIcon(pixmap))
        b.setIconSize(QSize(self.bsize, self.bsize))
        b.setGeometry(row*self.bsize, col*self.bsize, self.bsize, self.bsize)
        b.setCheckable(True)
        if (row, col) == (0, 0):
            b.setChecked(True)
        b.clicked.connect(self.modeButtonClicked)
        self.mode_buttons[name] = (b, func)
        