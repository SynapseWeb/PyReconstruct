from PySide2.QtWidgets import QWidget, QDockWidget, QPushButton
from PySide2.QtGui import QIcon, QPixmap
from PySide2.QtCore import QSize, Qt

from gui.palettebutton import PaletteButton
from gui.fieldwidget import FieldWidget
from recon.trace import Trace
from constants import locations as loc

class MouseDockWidget(QDockWidget):

    def __init__(self, palette_traces : list, selected_trace : Trace, parent : QWidget, button_size=30):
        """Create the mouse dock widget object.
        
            Params:
                palette_traces (list): list of traces to include on palette
                selected_trace (Trace): the trace that is selected on the palette
                parent (QWidget): the parent widget of the dock
                button_size (int): the size of the buttons on the dock"""
        super().__init__(parent)
        self.parent_widget = parent
        self.setFloating(True)  # create as a separate window
        self.setFeatures(QDockWidget.DockWidgetFloatable |
                         QDockWidget.DockWidgetMovable)  # dock cannot be closed
        self.setAllowedAreas(Qt.NoDockWidgetArea)  # dock cannot be reattached to the window
        self.setWindowTitle(" ")  # no title for the dock
        self.bsize = button_size
        self.central_widget = QWidget()
        self.resize(self.bsize*10, 5 + self.bsize*4)

        self.mode_buttons = {}
        self.createModeButton("pointer", 0, 0, FieldWidget.POINTER)
        self.createModeButton("panzoom", 1, 0, FieldWidget.PANZOOM)
        self.createModeButton("scalpel", 2, 0, FieldWidget.SCALPEL)

        self.createModeButton("closedpencil", 0, 1, FieldWidget.CLOSEDPENCIL)
        self.createModeButton("openpencil", 1, 1, FieldWidget.OPENPENCIL)
        self.createModeButton("closedline", 2, 1, FieldWidget.CLOSEDLINE)
        self.createModeButton("openline", 3, 1, FieldWidget.OPENLINE)
        self.createModeButton("stamp", 4, 1, FieldWidget.STAMP)

        self.palette_traces = palette_traces
        self.palette_buttons = []
        for i in range(len(palette_traces)):  # create all the palette buttons
            trace = palette_traces[i]
            self.createPaletteButton(trace, i % 10, i//10)
        for button in self.palette_buttons:  # highlight the first match for the selected trace
            if button.trace.isSameTrace(selected_trace):
                button.setChecked(True)
                self.setWindowTitle(selected_trace.name)
                break
        self.central_widget.paletteButtonChanged = self.paletteButtonChanged # there's no way in hell this is good practice but it works

        self.selected_mode = "pointer"
        self.selected_trace = selected_trace.name
        self.updateTitle()

        self.setWidget(self.central_widget)
        self.show()
    
    def updateTitle(self):
        s = "Tool: " + self.selected_mode + "  |  Tracing: " + self.selected_trace
        self.setWindowTitle(s)
    
    def modeButtonClicked(self):
        """Executed when any mouse mode button is clicked: changes mouse mode."""
        sender = self.sender()
        for name, button in self.mode_buttons.items():
            if button[0] == sender:
                button[0].setChecked(True)
                self.parent_widget.changeMouseMode(button[1])
                self.selected_mode = name
                self.updateTitle()
            else:
                button[0].setChecked(False)      

    def createModeButton(self, name : str, x : int, y : int, mouse_mode : int):
        """Creates a new mouse mode button on the dock.
        
            Params:
                name (str): the name of the button (and PNG file)
                x (int): the x position of the button on the button grid
                y (int): the y position of the button on the button grid
                mouse_mode (int): the mode this button is connected to
        """
        b = QPushButton(self.central_widget)
        pixmap = QPixmap(loc.img_dir + "/" + name + ".png").scaled(self.bsize, self.bsize)
        b.setIcon(QIcon(pixmap))
        b.setIconSize(QSize(self.bsize, self.bsize))
        b.setGeometry(x*self.bsize, y*self.bsize, self.bsize, self.bsize)
        b.setCheckable(True)
        if (x, y) == (0, 0):  # make the first button selected by default
            b.setChecked(True)
        b.clicked.connect(self.modeButtonClicked)
        # dictionary -- name : (button object, mouse mode)
        self.mode_buttons[name] = (b, mouse_mode)
    
    def paletteButtonClicked(self):
        """Executed when palette button is clicked: changes mouse trace."""
        sender = self.sender()
        for button in self.palette_buttons:
            if button == sender:
                button.setChecked(True)
                self.parent_widget.changeTracingTrace(button.trace)
                self.selected_trace = button.trace.name
                self.updateTitle()
            else:
                button.setChecked(False)
    
    def paletteButtonChanged(self, button : PaletteButton):
        """Executed when user changes palette trace: ensure that tracing pencil is updated.
        
            Params:
                button (PaletteButton): the button that was changed
        """
        for b in self.palette_buttons:
            if b.isChecked() and b == button:
                self.parent_widget.changeTracingTrace(button.trace)
    
    def createPaletteButton(self, trace : Trace, x : int, y : int):
        """Create a palette button on the dock.
        
            Params:
                trace (Trace): the trace to go on the button
                x (int): the x position of the button on the button grid
                y (int): the y position of the button on the button grid
        """
        b = PaletteButton(self.central_widget)
        b.setGeometry(x*self.bsize, 5 + (2+y)*self.bsize, self.bsize, self.bsize)
        b.setTrace(trace)
        b.setCheckable(True)
        b.clicked.connect(self.paletteButtonClicked)
        self.palette_buttons.append(b)
    
    def getPaletteTraces(self):
        """Returns a list of the current palette traces."""
        return self.palette_traces
