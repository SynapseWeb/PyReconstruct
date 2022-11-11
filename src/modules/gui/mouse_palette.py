import os

from PySide6.QtWidgets import QWidget, QPushButton
from PySide6.QtGui import QIcon, QPixmap, QFont
from PySide6.QtCore import QSize

from modules.gui.palette_button import PaletteButton
from modules.gui.field_widget import FieldWidget
from modules.gui.outlined_label import OutlinedLabel

from modules.pyrecon.trace import Trace

from constants import locations as loc

class MousePalette():

    def __init__(self, palette_traces : list, selected_trace : Trace, mainwindow : QWidget):
        """Create the mouse dock widget object.
        
            Params:
                palette_traces (list): list of traces to include on palette
                selected_trace (Trace): the trace that is selected on the palette
                parent (QWidget): the parent widget of the dock
                button_size (int): the size of the buttons on the dock
        """
        self.mainwindow = mainwindow
        
        self.mbwidth = 40
        self.mbheight = 40

        self.pblen = 40

        self.mode_buttons = {}
        self.createModeButton("Pointer", "p", 0, FieldWidget.POINTER)
        self.createModeButton("Pan/Zoom", "z", 1, FieldWidget.PANZOOM)
        self.createModeButton("Knife", "k", 2, FieldWidget.KNIFE)
        self.createModeButton("Closed Trace", "c", 3, FieldWidget.CLOSEDTRACE)
        self.createModeButton("Open Trace", "o", 4, FieldWidget.OPENTRACE)
        self.createModeButton("Stamp", "s", 5, FieldWidget.STAMP)

        self.palette_traces = palette_traces
        self.palette_buttons = [None] * 20
        for i in range(len(palette_traces)):  # create all the palette buttons
            trace = palette_traces[i]
            self.createPaletteButton(trace, i)
        for button in self.palette_buttons:  # highlight the first match for the selected trace
            if button.trace.isSameTrace(selected_trace):
                button.setChecked(True)
                break
        
        self.selected_mode = "pointer"
        self.selected_trace = selected_trace

        self.label = OutlinedLabel(self.mainwindow)
        self.label.setFont(QFont("Courier New", 16, QFont.Bold))
        self.updateLabel()
        self.label.show()
    
    def placeModeButton(self, button : QPushButton, pos : int):
        """Place the mode button in the main window.
        
            Params:
                button (QPushButton): the button to place
                pos (int): the position of the button
        """
        x = self.mainwindow.width() - self.mbwidth - 10
        y = 40 + (10 + self.mbheight) * pos
        button.setGeometry(x, y, self.mbwidth, self.mbheight)
    
    def createModeButton(self, name : str, sc : str, pos : int, mouse_mode : int):
        """Creates a new mouse mode button.
        
            Params:
                name (str): the name of the button (and PNG file)
                pos (int): the position of the button
                mouse_mode (int): the mode this button is connected to
        """
        b = QPushButton(self.mainwindow)

        # filter name to get filename
        stripped_name = name
        characters_to_remove = (" ", "/")
        for c in characters_to_remove:
            stripped_name = stripped_name.replace(c, "")
        stripped_name = stripped_name.lower()
        # open the icon file
        icon_fp = os.path.join(loc.img_dir, stripped_name + ".png")
        pixmap = QPixmap(icon_fp)#.scaled(self.mbheight, self.mbheight)

        self.placeModeButton(b, pos)

        # format the button
        b.setIcon(QIcon(pixmap))
        b.setIconSize(QSize(self.mbheight, self.mbheight))
        # b.setText(name)
        b.setToolTip(f"{name} ({sc})")

        b.setCheckable(True)
        if pos == 0:  # make the first button selected by default
            b.setChecked(True)
        b.clicked.connect(lambda : self.activateModeButton(name))
        # dictionary -- name : (button object, mouse mode, position)
        self.mode_buttons[name] = (b, mouse_mode, pos)

        b.show()
    
    def placePaletteButton(self, button : PaletteButton, pos : int):
        """Place the palette button in the main window.
        
            Params:
                button (PaletteButton): the palette button to move
                pos (int): its position"""
        # place the palette button in the middle of the FIELD (not mainwindow)
        if pos % 10 // 5 > 0:
            x_offset = 1
        else:
            x_offset = -1
        x_offset += (-5 + pos % 10) * self.pblen
        x = self.mainwindow.field.x() + (self.mainwindow.field.width() / 2)
        x += x_offset

        if pos//10 > 0:
            y_offset = 1
        else:
            y_offset = -1
        y_offset += -(-(pos//10) + 2) * self.pblen - 30
        y = self.mainwindow.height()
        y += y_offset

        button.setGeometry(x, y, self.pblen, self.pblen)

    def createPaletteButton(self, trace : Trace, pos : int):
        """Create a palette button on the dock.
        
            Params:
                trace (Trace): the trace to go on the button
                pos (int): the position of the button (assumes 20 buttons)
        """
        b = PaletteButton(self.mainwindow, manager=self)

        self.placePaletteButton(b, pos)

        b.setTrace(trace)
        b.setCheckable(True)
        b.clicked.connect(lambda : self.activatePaletteButton(pos))
        self.palette_buttons[pos] = b
        b.show()
    
    def placeLabel(self):
        """Place the trace palette label."""
        self.label.resize(self.label.sizeHint())
        x = self.mainwindow.field.x() + self.mainwindow.field.width() / 2 - self.label.width() / 2
        y = self.mainwindow.height() - (2 * self.pblen) - self.label.height() - 40
        self.label.move(x, y)

    def updateLabel(self):
        """Update the name of the trace palette label."""
        self.label.setText(self.selected_trace.name)
        c = self.selected_trace.color
        self.label.setTextColor(c)
        black_outline = c[0] + 3*c[1] + c[2] > 400
        if black_outline:
            self.label.setOutlineColor((0,0,0))
        else:
            self.label.setOutlineColor((255,255,255))
        self.placeLabel()
    
    def activateModeButton(self, bname : str):
        """Executed when any mouse mode button is clicked: changes mouse mode.
        
            Params:
                bname (str): the name of the clicked button
        """
        for name, button_info in self.mode_buttons.items():
            button, mode, pos = button_info
            if name == bname:
                button.setChecked(True)
                self.mainwindow.changeMouseMode(mode)
                self.selected_mode = name
            else:
                button.setChecked(False)      
    
    def activatePaletteButton(self, bpos : int):
        """Executed when palette button is clicked: changes mouse trace.
        
            Params:
                bpos (int): the position of the palette button
        """
        for i, button in enumerate(self.palette_buttons):
            if i == bpos:
                button.setChecked(True)
                self.mainwindow.changeTracingTrace(button.trace)
                self.selected_trace = button.trace
                self.updateLabel()
            else:
                button.setChecked(False)
    
    def modifyPaletteButton(self, bpos : int):
        """Opens dialog to modify palette button.
        
            Params:
                bpos (int): the position of the palette button
        """
        b = self.palette_buttons[bpos]
        b.openDialog()
    
    def paletteButtonChanged(self, button : PaletteButton):
        """Executed when user changes palette trace: ensure that tracing pencil is updated.
        
            Params:
                button (PaletteButton): the button that was changed
        """
        for b in self.palette_buttons:
            if b.isChecked() and b == button:
                self.mainwindow.changeTracingTrace(button.trace)
                self.selected_trace = b.trace
        self.updateLabel()
    
    def resize(self):
        """Move the buttons to fit the main window."""
        for mbname in self.mode_buttons:
            button, mode, pos = self.mode_buttons[mbname]
            self.placeModeButton(button, pos)
        for i, pb in enumerate(self.palette_buttons):
            self.placePaletteButton(pb, i)
        self.placeLabel()
    
    def close(self):
        """Close all buttons"""
        for bname in self.mode_buttons:
            button, _, __ = self.mode_buttons[bname]
            button.close()
        for pb in self.palette_buttons:
            pb.close()
        self.label.close()
        
