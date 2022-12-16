import os

from PySide6.QtWidgets import QWidget, QPushButton, QStyle
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor
from PySide6.QtCore import QSize, QRect

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
                mainwindow (MainWindow): the parent main window of the dock
        """
        self.mainwindow = mainwindow
        self.left_handed = False
        
        self.mbwidth = 40
        self.mbheight = 40

        self.pblen = 40

        # create mode buttons
        self.mode_buttons = {}
        self.createModeButton("Pointer", "p", 0, FieldWidget.POINTER)
        self.createModeButton("Pan/Zoom", "z", 1, FieldWidget.PANZOOM)
        self.createModeButton("Knife", "k", 2, FieldWidget.KNIFE)
        self.createModeButton("Closed Trace", "c", 3, FieldWidget.CLOSEDTRACE)
        self.createModeButton("Open Trace", "o", 4, FieldWidget.OPENTRACE)
        self.createModeButton("Stamp", "s", 5, FieldWidget.STAMP)

        # create palette buttons
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
        self.show_corner_buttons = True

        # create label
        self.label = OutlinedLabel(self.mainwindow)
        font = self.label.font()
        font.setFamily("Courier New")
        font.setBold(True)
        font.setPointSize(16)
        self.label.setFont(font)
        self.updateLabel()
        self.label.show()

        self.corner_buttons = []

        # create increment buttons
        self.ibw = 90
        self.ibh = 35
        self.createIncrementButtons()

        # create brightness/contrast buttons
        self.bcsize = 30
        self.createBCButtons()
    
    def toggleHandedness(self):
        """Toggle the position of the buttons."""
        self.left_handed = not self.left_handed
        self.resize()
    
    def placeModeButton(self, button, pos : int):
        """Place the mode button in the main window.
        
            Params:
                button (ScreenButton): the button to place
                pos (int): the position of the button
        """
        if self.left_handed:
            x = self.mainwindow.field.x() + 10
        else:
            x = self.mainwindow.width() - self.mbwidth - 10
        y = 40 + (10 + self.mbheight) * pos
        button.setGeometry(x, y, self.mbwidth, self.mbheight)
    
    def createModeButton(self, name : str, sc : str, pos : int, mouse_mode : int):
        """Creates a new mouse mode button.
        
            Params:
                name (str): the name of the button (and PNG file)
                sc (str): the shortcut character for the button
                pos (int): the position of the button
                mouse_mode (int): the mode this button is connected to
        """
        b = ScreenButton(self.mainwindow)

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
                pos (int): its position
        """
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
    
    def setPaletteButtonTip(self, b : PaletteButton, pos : int):
        """Set the tool tip for a palette button.
        
            Params:
                b (PaletteButton): the palette button to modify
                pos (int): the position of the button
        """
        kbd = ""
        if pos // 10 > 0:
            kbd += "Shift+"
        kbd += str((pos + 1) % 10)
        tooltip = f"{b.trace.name} ({kbd})"
        b.setToolTip(tooltip)

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
        self.setPaletteButtonTip(b, pos)
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
        for pos, b in enumerate(self.palette_buttons):
            if b == button:
                self.setPaletteButtonTip(b, pos)
                if b.isChecked():
                    self.mainwindow.changeTracingTrace(button.trace)
                    self.selected_trace = b.trace
        self.updateLabel()
    
    def placeIncrementButtons(self):
        """Place the increment buttons on the field"""
        if self.left_handed:
            x = self.mainwindow.field.x() + 10
        else:
            x = self.mainwindow.width() - self.ibw - 10
        y = self.mainwindow.height() - (self.ibh + 15) * 2 - 20
        self.up_bttn.setGeometry(x, y, self.ibw, self.ibh)
        y = self.mainwindow.height() - (self.ibh + 15) - 20
        self.down_bttn.setGeometry(x, y, self.ibw, self.ibh)
    
    def createIncrementButtons(self):
        """Create the section increment buttons."""        
        self.up_bttn = ScreenButton(self.mainwindow)
        up_icon = self.up_bttn.style().standardIcon(
            QStyle.SP_TitleBarShadeButton
        )
        self.up_bttn.setIcon(up_icon)
        self.up_bttn.pressed.connect(self.mainwindow.incrementSection)
        self.up_bttn.setToolTip("Next section (PgUp)")

        self.down_bttn = ScreenButton(self.mainwindow)
        down_icon = self.up_bttn.style().standardIcon(
            QStyle.SP_TitleBarUnshadeButton
        )
        self.down_bttn.setIcon(down_icon)
        self.down_bttn.pressed.connect(lambda : self.mainwindow.incrementSection(down=True))
        self.down_bttn.setToolTip("Previous section (PgDown)")

        self.placeIncrementButtons()

        self.up_bttn.show()
        self.down_bttn.show()

        self.corner_buttons.append(self.up_bttn)
        self.corner_buttons.append(self.down_bttn)
    
    def placeBCButtons(self):
        """Place the brightness/contrast buttons."""
        for i, b in enumerate(self.bc_buttons):
            grid_position = (i%2, i//2)
            if self.left_handed:
                x = self.mainwindow.field.x() + 10 + (self.bcsize + 10) * grid_position[0]
            else:
                x = self.mainwindow.width() - (10 + self.bcsize) * 2
                x += (self.bcsize + 10) * grid_position[0]
            y = self.mainwindow.height() - 200 - (20 + self.bcsize) * grid_position[1]
            b.setGeometry(x, y, self.bcsize, self.bcsize)
    
    def createBCButtons(self):
        """Create the brightnes/contrast buttons."""
        self.bc_buttons = []
        for option in ("contrast", "brightness"):
            for direction in ("down", "up"):
                b = ScreenButton(self.mainwindow)
                # get the icons
                icon_fp = os.path.join(loc.img_dir, f"{option}_{direction}.png")
                pixmap = QPixmap(icon_fp)
                b.setIcon(QIcon(pixmap))
                b.setIconSize(QSize(self.bcsize*2/3, self.bcsize*2/3))
                # connect to mainwindow function
                b.pressed.connect(lambda o=option, d=direction: self.mainwindow.editImage(o, d))
                # set the button tool tip
                if option == "contrast" and direction == "down":
                    tooltip = "Decrease contrast ([)"
                elif option == "contrast" and direction == "up":
                    tooltip = "Increase contrast (])"
                elif option == "brightness" and direction == "down":
                    tooltip = "Decrease brightness (-)"
                elif option == "brightness" and direction == "up":
                    tooltip = "Increase brightness (=)"
                b.setToolTip(tooltip)
                # set button as continuous
                b.setAutoRepeat(True)
                b.setAutoRepeatDelay(0)
                b.show()
                self.bc_buttons.append(b)
                self.corner_buttons.append(b)
        self.placeBCButtons()
    
    def toggleCornerButtons(self):
        """Toggle whether the corner buttons are shown."""
        if self.show_corner_buttons:
            self.show_corner_buttons = False
            for b in self.corner_buttons:
                b.hide()
        else:
            self.show_corner_buttons = True
            for b in self.corner_buttons:
                b.show()

    def resize(self):
        """Move the buttons to fit the main window."""
        for mbname in self.mode_buttons:
            button, mode, pos = self.mode_buttons[mbname]
            self.placeModeButton(button, pos)
        for i, pb in enumerate(self.palette_buttons):
            self.placePaletteButton(pb, i)
        self.placeLabel()
        self.placeIncrementButtons()
        self.placeBCButtons()
    
    def reset(self, palette_traces : list, selected_trace : Trace):
        """Reset the mouse palette when opening a new series.
        
            Params:
                palette_traces (list): the new palette traces
                selected_trace (trace): the new selected trace on the palette
        """
        self.close()
        self.__init__(palette_traces, selected_trace, self.mainwindow)

    def close(self):
        """Close all buttons"""
        for bname in self.mode_buttons:
            button, _, __ = self.mode_buttons[bname]
            button.close()
        for pb in self.palette_buttons:
            pb.close()
        self.label.close()
        for b in self.corner_buttons:
            b.close()

class ScreenButton(QPushButton):

    def paintEvent(self, event):
        """Add a highlighting border to selected buttons."""
        super().paintEvent(event)
        if self.isChecked():
            painter = QPainter(self)
            painter.setPen(QPen(QColor(255, 255, 0), 2))
            painter.setOpacity(1)
            w, h = self.width(), self.height()
            painter.drawRect(QRect(0, 0, w, h))
        
