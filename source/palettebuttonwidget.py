from PySide2.QtWidgets import QWidget, QDockWidget, QPushButton
from PySide2.QtGui import QIcon, QPixmap
from PySide2.QtCore import QSize, Qt

from palettebutton import PaletteButton

class PaletteButtonWidget(QWidget):

    def __init__(self, palette_traces, parent, button_size=30):
        super().__init__(parent)
        self.parent_widget = parent
        self.bsize = button_size
        self.central_widget = QWidget()
        self.setFixedSize(self.bsize*5, self.bsize*2)

        self.palette_buttons = []
        for i in range(len(palette_traces)):
            self.createPaletteButton(palette_traces[i], i % 5, 2 + i//5)
    
    def paletteButtonClicked(self):
        sender = self.sender()
        for button in self.palette_buttons:
            if button == sender:
                button.setChecked(True)
                self.parent_widget.changeTracingTrace(button.trace)
            else:
                button.setChecked(False)
    
    def createPaletteButton(self, trace, row, col):
        b = PaletteButton(self.central_widget)
        b.setGeometry(row*self.bsize, 5 + col*self.bsize, self.bsize, self.bsize)
        b.setTrace(trace)
        b.setCheckable(True)
        b.clicked.connect(self.paletteButtonClicked)
        self.palette_buttons.append(b)
        