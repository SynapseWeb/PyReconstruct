import os

from PySide6.QtWidgets import QWidget, QStyle
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QSize

from .buttons import PaletteButton, ModeButton, MoveableButton
from .outlined_label import OutlinedLabel

from modules.datatypes import Series, Trace
from modules.constants import (
    locations as loc
)

class MousePalette():

    def __init__(self, palette_traces : list, selected_trace : Trace, mainwindow : QWidget, ):
        """Create the mouse dock widget object.
        
            Params:
                palette_traces (list): list of traces to include on palette
                selected_trace (Trace): the trace that is selected on the palette
                mainwindow (MainWindow): the parent main window of the dock
        """
        self.mainwindow = mainwindow
        
        self.mblen = 40  # mode button size
        self.pblen = 40  # palette button size
        self.ibw = 90  # inc button width
        self.ibh = 35  # inc button height
        self.bcsize = 30  # brightness/contrast button size

        self.is_dragging = False

        # create mode buttons
        self.mode_x = 0.99
        self.mode_y = 0.01
        self.mode_buttons = {}
        self.createModeButton("Pointer", "p", 0, 0)
        self.createModeButton("Pan/Zoom", "z", 1, 1)
        self.createModeButton("Knife", "k", 2, 2)
        self.createModeButton("Scissors", "x", 3, 3)
        self.createModeButton("Closed Trace", "c", 4, 4)
        self.createModeButton("Open Trace", "o", 5, 5)
        self.createModeButton("Stamp", "s", 6, 6)
        self.createModeButton("Grid", "g", 7, 7)

        # create palette buttons
        self.trace_x = 0.5
        self.trace_y = 0.99
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
        self.inc_x = 0.99
        self.inc_y = 0.99
        self.createIncrementButtons()

        # create brightness/contrast buttons
        self.bc_x = 0.99
        self.bc_y = 0.8
        self.createBCButtons()
    
    def placeModeButton(self, button, pos : int):
        """Place the mode button in the main window.
        
            Params:
                button (ModeButton): the button to place
                pos (int): the position of the button
        """
        x, y = self.getButtonCoords("mode")
        y += (10 + self.mblen) * pos
        button.setGeometry(x, y, self.mblen, self.mblen)
    
    def createModeButton(self, name : str, sc : str, pos : int, mouse_mode : int):
        """Creates a new mouse mode button.
        
            Params:
                name (str): the name of the button (and PNG file)
                sc (str): the shortcut character for the button
                pos (int): the position of the button
                mouse_mode (int): the mode this button is connected to
        """
        b = ModeButton(self.mainwindow, self)

        # filter name to get filename
        stripped_name = name
        characters_to_remove = (" ", "/")
        for c in characters_to_remove:
            stripped_name = stripped_name.replace(c, "")
        stripped_name = stripped_name.lower()
        # open the icon file
        icon_fp = os.path.join(loc.img_dir, stripped_name + ".png")
        pixmap = QPixmap(icon_fp)

        self.placeModeButton(b, pos)

        # format the button
        b.setIcon(QIcon(pixmap))
        b.setIconSize(QSize(self.mblen, self.mblen))
        # b.setText(name)
        b.setToolTip(f"{name} ({sc})")

        # manually enter dialog function for pointer and grid
        if name == "Pointer":
            b.contextMenuEvent = self.mainwindow.modifyPointer
        elif name == "Closed Trace":
            b.contextMenuEvent = self.mainwindow.changeClosedTraceMode
        elif name == "Grid":
            b.contextMenuEvent = self.mainwindow.modifyGrid

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
        x, y = self.getButtonCoords("trace")
        if pos % 10 // 5 > 0:
            x_offset = 1
        else:
            x_offset = -1
        x_offset += (-5 + pos % 10) * self.pblen
        x += x_offset

        if pos//10 > 0:
            y_offset = 1
        else:
            y_offset = -1
        y_offset += -(-(pos//10) + 1) * self.pblen
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
        x, y = self.getButtonCoords("trace")
        self.label.resize(self.label.sizeHint())
        x -= self.label.width() / 2
        if self.trace_y > 0.5:
            y -= self.pblen + self.label.height() + 5
        else:
            y += self.pblen + 5
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
        if self.is_dragging:
            for name, button_info in self.mode_buttons.items():
                button, mode, pos = button_info
                if name == bname:
                    button.setChecked(not button.isChecked())    
                    return

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
        if self.is_dragging:
            for i, button in enumerate(self.palette_buttons):
                if i == bpos:
                    button.setChecked(not button.isChecked())    
                    return
        
        for i, button in enumerate(self.palette_buttons):
            if i == bpos:
                if self.is_dragging:
                    button.setChecked(not button.isChecked())
                    return
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
    
    def modifyPalette(self, trace_list : list):
        """Modify all of the palette traces.
        
            Params:
                trace_list (list): the list of traces to set the palette buttons
        """
        if len(trace_list) != len(self.palette_traces):
            return
        self.palette_traces = trace_list
        for b, t in zip(self.palette_buttons, self.palette_traces):
            b.setTrace(t)
        self.activatePaletteButton(0)
    
    def resetPalette(self):
        """Reset the palette to the default traces."""
        self.modifyPalette(Series.getDefaultPaletteTraces())
    
    def placeIncrementButtons(self):
        """Place the increment buttons on the field"""
        x, y = self.getButtonCoords("inc")
        self.up_bttn.setGeometry(x, y, self.ibw, self.ibh)
        y = y + self.ibh + 15
        self.down_bttn.setGeometry(x, y, self.ibw, self.ibh)
    
    def createIncrementButtons(self):
        """Create the section increment buttons."""        
        self.up_bttn = MoveableButton(self.mainwindow, self, "inc")
        up_icon = self.up_bttn.style().standardIcon(
            QStyle.SP_TitleBarShadeButton
        )
        self.up_bttn.setIcon(up_icon)
        self.up_bttn.clicked.connect(self.incrementSection)
        self.up_bttn.setToolTip("Next section (PgUp)")

        self.down_bttn = MoveableButton(self.mainwindow, self, "inc")
        down_icon = self.up_bttn.style().standardIcon(
            QStyle.SP_TitleBarUnshadeButton
        )
        self.down_bttn.setIcon(down_icon)
        self.down_bttn.clicked.connect(lambda : self.incrementSection(down=True))
        self.down_bttn.setToolTip("Previous section (PgDown)")

        self.placeIncrementButtons()

        self.up_bttn.show()
        self.down_bttn.show()

        self.corner_buttons.append(self.up_bttn)
        self.corner_buttons.append(self.down_bttn)
    
    def incrementSection(self, down=False):
        """Increment the section."""
        if self.is_dragging:
            return
        self.mainwindow.incrementSection(down)
    
    def placeBCButtons(self):
        """Place the brightness/contrast buttons."""
        bcx, bcy = self.getButtonCoords("bc")
        for i, b in enumerate(self.bc_buttons):
            x, y = bcx, bcy
            grid_position = (i%2, i//2)
            x += (self.bcsize + 10) * grid_position[0]
            y += (20 + self.bcsize) * grid_position[1]
            b.setGeometry(x, y, self.bcsize, self.bcsize)
    
    def createBCButtons(self):
        """Create the brightnes/contrast buttons."""
        self.bc_buttons = []
        for option in ("brightness", "contrast"):
            for direction in ("down", "up"):
                b = MoveableButton(self.mainwindow, self, "bc")
                # get the icons
                icon_fp = os.path.join(loc.img_dir, f"{option}_{direction}.png")
                pixmap = QPixmap(icon_fp)
                b.setIcon(QIcon(pixmap))
                b.setIconSize(QSize(self.bcsize*2/3, self.bcsize*2/3))
                # connect to mainwindow function
                b.clicked.connect(lambda o=option, d=direction: self.changeBC(o, d))
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
    
    def changeBC(self, option, direction):
        """Change the brightness/contrast of the field."""
        if not self.is_dragging:
            self.mainwindow.editImage(option, direction)
    
    def getButtonCoords(self, group):
        """Get the coordinates for a button group.
        
            Params:
                group (str): the name of the button group.
        """
        x1, x2, y1, y2 = self.getBounds()[group]
        x = getattr(self, f"{group}_x")
        y = getattr(self, f"{group}_y")
        x = (x * (x2 - x1)) + x1
        y = (y * (y2 - y1)) + y1
        return x, y

    def moveButton(self, dx, dy, group):
        """Move a button group.
        
            Params:
                dx (int): the x-value movement for the button
                dy (int): the y-value movement for the button
                group (str): the name of the button group
        """
        x1, x2, y1, y2 = self.getBounds()[group]
        current_x, current_y = self.getButtonCoords(group)
        new_x = ((current_x + dx) - x1) / (x2 - x1)
        if new_x < 0: new_x = 0
        elif new_x > 1: new_x = 1
        new_y = ((current_y + dy) - y1) / (y2 - y1)
        if new_y < 0: new_y = 0
        elif new_y > 1: new_y = 1
        setattr(self, f"{group}_x", new_x)
        setattr(self, f"{group}_y", new_y)

        # special case: move selected traces if needed
        if group == "mode":
            self.mainwindow.field.update()

    def getBounds(self):
        """Get the bounds for the buttons."""
        fx1 = self.mainwindow.field.x()
        fx2 = fx1 + self.mainwindow.field.width()
        fy1 = self.mainwindow.field.y()
        fy2 = fy1 + self.mainwindow.field.height()

        return {
            "mode": (fx1, fx2 - self.mblen, fy1, fy2 - (self.mblen + 10) * len(self.mode_buttons) + 10),
            "trace": (fx1 + self.pblen*5, fx2 - self.pblen*5, fy1 + self.pblen, fy2 - self.pblen),
            "inc": (fx1, fx2 - self.ibw, fy1, fy2 - self.ibh*2 - 15),
            "bc": (fx1, fx2 - 2*self.bcsize - 10, fy1, fy2 - 2*self.bcsize - 20)
        }

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
        
