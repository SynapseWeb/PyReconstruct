from PySide2.QtWidgets import QDockWidget, QWidget, QLineEdit, QColorDialog
from PySide2.QtGui import QColor
from PySide2.QtCore import Qt

from palettebutton import PaletteButton
from colorbutton import ColorButton

class EditPaletteWidget(QDockWidget):

    def __init__(self, palette_traces, parent, button_size=30):
        super().__init__(parent)
        self.parent_widget = parent
        self.bsize = button_size
        self.setFloating(True)
        self.setAllowedAreas(Qt.NoDockWidgetArea)
        self.setWindowTitle("Edit Trace Palette")
        self.setFixedSize(5*self.bsize, 2*self.bsize + 60)
        self.central_widget = QWidget()
        self.setWidget(self.central_widget)
        self.palette_buttons = []
        for i in range(len(palette_traces)):
            self.createPaletteButton(palette_traces[i], i % 5, i//5)
        
        self.le = QLineEdit(self.central_widget)
        self.le.move(10, self.bsize*2 + 10)
        self.cb = ColorButton(self.central_widget)
        self.cb.clicked.connect(self.editPaletteButtonColor)
        self.cb.move(10, self.bsize*2 + 30)

        self.show()
    
    def editPaletteButtonColor(self):
        color = QColorDialog.getColor()
        self.cb.setColor(color)
        for button in self.palette_buttons:
            if button.isChecked():
                trace = button.trace
                trace.color = (color.red(), color.green(), color.blue())
                button.setTrace(trace)

    def paletteButtonClicked(self):
        sender = self.sender()
        for button in self.palette_buttons:
            if button != sender and button.isChecked():
                self.editPaletteButtonName(button)
        for button in self.palette_buttons:
            if button == sender:
                button.setChecked(True)
                self.le.setText(button.trace.name)
                self.cb.setColor(QColor(*button.trace.color))
            else:
                button.setChecked(False)
    
    def createPaletteButton(self, trace, row, col):
        b = PaletteButton(self.central_widget)
        b.setGeometry(row*self.bsize, 5 + col*self.bsize, self.bsize, self.bsize)
        b.setTrace(trace)
        b.setCheckable(True)
        b.clicked.connect(self.paletteButtonClicked)
        self.palette_buttons.append(b)
    
    def editPaletteButtonName(self, button):
        trace = button.trace
        trace.name = self.le.text()
        button.setTrace(trace)
    
    def closeEvent(self, event):
        traces = []
        for button in self.palette_buttons:
            if button.isChecked():
                trace = button.trace
                trace.name = self.le.text()
                button.setTrace(trace)
            traces.append(button.trace)
        self.parent_widget.editTracePalette(traces)
        event.accept()

