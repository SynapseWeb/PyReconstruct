from PySide2.QtWidgets import QWidget, QDockWidget, QPushButton
from PySide2.QtGui import QIcon, QPixmap
from PySide2.QtCore import QSize, Qt

from palettebutton import PaletteButton

class MouseDockWidget(QDockWidget):

    def __init__(self, palette_traces, parent, button_size=30):
        super().__init__(parent)
        self.parent_widget = parent
        self.setFloating(True)
        self.setFeatures(QDockWidget.DockWidgetFloatable |
                         QDockWidget.DockWidgetMovable)
        self.setAllowedAreas(Qt.NoDockWidgetArea)
        self.setWindowTitle(" ")
        self.bsize = button_size
        self.central_widget = QWidget()
        self.setFixedSize(self.bsize*5, 5 + self.bsize*4)

        self.mode_buttons = {}
        self.createModeButton("pointer", 0, 0, parent.toPointer)
        self.createModeButton("panzoom", 1, 0, parent.toPanzoom)
        self.createModeButton("pencil", 0, 1, parent.toPencil)

        self.palette_traces = palette_traces
        self.palette_buttons = []
        for i in range(len(palette_traces)):
            self.createPaletteButton(palette_traces[i], i % 5, i//5)

        self.setWidget(self.central_widget)
        self.show()
    
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
    
    def paletteButtonClicked(self):
        sender = self.sender()
        for button in self.palette_buttons:
            if button == sender:
                button.setChecked(True)
                self.parent_widget.changeTracingTrace(button.trace)
            else:
                button.setChecked(False)
    
    def createPaletteButton(self, trace, x, y):
        b = PaletteButton(self.central_widget)
        b.setGeometry(x*self.bsize, 5 + (2+y)*self.bsize, self.bsize, self.bsize)
        b.setTrace(trace)
        b.setCheckable(True)
        b.clicked.connect(self.paletteButtonClicked)
        self.palette_buttons.append(b)
    
    def getPaletteTraces(self):
        return self.palette_traces
    
    def setPaletteTraces(self, palette_traces):
        if len(palette_traces) != len(self.palette_buttons):
            print("ERROR: Number palette traces do not match number of buttons")
            return
        self.palette_traces = palette_traces
        for button, trace in zip(self.palette_buttons, palette_traces):
            button.setTrace(trace)