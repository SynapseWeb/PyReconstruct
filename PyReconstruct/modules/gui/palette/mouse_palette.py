import os
import re

from PySide6.QtWidgets import QWidget, QStyle, QSlider
from PySide6.QtGui import QIcon, QPixmap, QColor, QFont
from PySide6.QtCore import QSize, Qt

from .buttons import PaletteButton, ModeButton, MoveableButton
from .outlined_label import OutlinedLabel

from PyReconstruct.modules.datatypes import Series, Trace
from PyReconstruct.modules.constants import (
    locations as loc
)
from PyReconstruct.modules.gui.dialog import TracePaletteDialog, QuickDialog
from PyReconstruct.modules.gui.popup import TextWidget

class MousePalette():

    def __init__(self, mainwindow : QWidget):
        """Create the mouse dock widget object.
        
            Params:
                palette_traces (list): list of traces to include on palette
                selected_trace (Trace): the trace that is selected on the palette
                mainwindow (MainWindow): the parent main window of the dock
        """
        self.mainwindow = mainwindow
        self.series = self.mainwindow.series
        self.series : Series
        
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
        self.createModeButton("Flag", "f", 8, 8)

        # create palette buttons
        self.trace_x = 0.5
        self.trace_y = 0.99
        traces = self.series.palette_traces[self.series.palette_index[0]]
        self.palette_buttons = [None] * len(traces)
        for i, trace in enumerate(traces):  # create all the palette buttons
            self.createPaletteButton(trace, i)
        self.palette_buttons[self.series.palette_index[1]].setChecked(True)

        # create palette increments
        self.createPaletteSideButtons()
        
        self.selected_mode = "pointer"

        # create label
        self.label = OutlinedLabel(self.mainwindow)
        font = self.label.font()
        font.setFamily("Courier New")
        font.setBold(True)
        font.setPointSize(16)
        self.label.setFont(font)
        self.updateLabel()
        self.label.show()

        # create increment buttons
        self.inc_x = 0.99
        self.inc_y = 0.99
        self.createIncrementButtons()

        # create brightness/contrast buttons
        self.bc_x = 0.99
        self.bc_y = 0.8
        self.createBCButtons()

        self.palette_hidden = False
        self.inc_hidden = False
        self.bc_hidden = False
        
        self.help_widget = None
    
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

        b.setCheckable(True)
        if pos == 0:  # make the first button selected by default
            b.setChecked(True)
        b.clicked.connect(lambda : self.activateModeButton(name))
        # dictionary -- name : (button object, mouse mode, position)
        self.mode_buttons[name] = (b, mouse_mode, pos)

        # manually enter dialog function for pointer and grid
        if name == "Pointer":
            b.setRightClickEvent(self.mainwindow.modifyPointer)
        elif name == "Closed Trace" or name == "Open Trace":
            b.setRightClickEvent(self.mainwindow.changeTraceMode)
        elif name == "Grid":
            b.setRightClickEvent(self.mainwindow.modifyGrid)
        elif name == "Flag":
            b.setRightClickEvent(self.modifyFlag)
            # manually set the flag text and color
            self.setFlag()
        elif name == "Knife":
            b.setRightClickEvent(self.mainwindow.modifyKnife)

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
        y_offset += (pos//10 - 1) * self.pblen
        y += y_offset

        button.setGeometry(x, y, self.pblen, self.pblen)
    
    def placePaletteSideButtons(self):
        x, y = self.getButtonCoords("trace")

        up, down, opts, help = tuple(self.palette_side_buttons)

        x1 = x + 3 + 5 * self.pblen
        y1 = y - self.pblen
        up.setGeometry(x1, y1, self.pblen // 2, self.pblen // 2)

        y1 += self.pblen // 2 + 1
        down.setGeometry(x1, y1, self.pblen // 2, self.pblen // 2)

        y1 = y + 1 + self.pblen // 2
        help.setGeometry(x1, y1, self.pblen // 2, self.pblen // 2)

        y1 -= opts.height()
        opts.setGeometry(x1, y1, self.pblen // 2, self.pblen // 2)
    
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
    
    def createPaletteSideButtons(self):
        """Create the palette increment buttons."""
        b_up = MoveableButton(self.mainwindow, self, "trace")
        b_up.setText("+")
        f = b_up.font()
        f.setBold(True)
        b_up.setFont(f)
        b_up.clicked.connect(lambda : self.incrementPalette(True))
        b_up.show()

        b_down = MoveableButton(self.mainwindow, self, "trace")
        b_down.setText("-")
        b_down.setFont(f)
        b_down.clicked.connect(lambda : self.incrementPalette(False))
        b_down.show()

        b_opts = MoveableButton(self.mainwindow, self, "trace")
        b_opts.setText("☰")
        b_opts.clicked.connect(self.modifyAllPaletteButtons)
        b_opts.setToolTip("Modify all palettes")
        b_opts.show()

        b_help = MoveableButton(self.mainwindow, self, "trace")
        b_help.setText("?")
        b_help.setFont(f)
        b_help.clicked.connect(self.displayHelp)
        b_help.show()

        self.palette_side_buttons = [b_up, b_down, b_opts, b_help]
        self.placePaletteSideButtons()
    
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
        g, i = tuple(self.series.palette_index)
        selected_trace = self.series.palette_traces[g][i]
        n = selected_trace.name
        for c in "{}<>":
            n = n.replace(c, "")
        self.label.setText(n)

        c = selected_trace.color
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
                self.series.palette_index[1] = i
                self.updateLabel()
            else:
                button.setChecked(False)
    
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
        self.updateLabel()
    
    def pasteAttributesToButton(self, trace : Trace, use_shape=False):
        """Paste the attributes of a trace to the current button.
        
            Params:
                trace (Trace): the trace to paste
        """
        bpos = self.series.palette_index[1]
        if use_shape:
            t = trace.copy()
            t.centerAtOrigin()
        else:
            name = trace.name
            color = trace.color
            radius = trace.getRadius()
            bttn = self.palette_buttons[bpos]
            t = bttn.trace.copy()
            t.name, t.color = name, color
            t.resize(radius)
        self.modifyPaletteButton(bpos, t)
    
    def modifyPaletteButton(self, bpos : int, trace : Trace = None):
        """Opens dialog to modify palette button.
        
            Params:
                bpos (int): the position of the palette button
        """
        b = self.palette_buttons[bpos]
        if not trace:
            b.openDialog()
        else:
            b.setTrace(trace)
        g = self.series.palette_index[0]
        self.series.palette_traces[g][bpos] = b.trace
        self.paletteButtonChanged(b)
    
    def modifyPalette(self, trace_list : list):
        """Modify all of the palette traces.
        
            Params:
                trace_list (list): the list of traces to set the palette buttons
        """
        for bpos, trace in enumerate(trace_list):
            self.modifyPaletteButton(bpos, trace)
        self.activatePaletteButton(self.series.palette_index[1])
    
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

        self.inc_buttons = [self.up_bttn, self.down_bttn]
    
    def incrementSection(self, down=False):
        """Increment the section."""
        if self.is_dragging:
            return
        self.mainwindow.incrementSection(down)
    
    def placeBCButtons(self):
        """Place the brightness/contrast buttons."""
        bcx, bcy = self.getButtonCoords("bc")
        for i, (bttn, slider) in enumerate(self.bc_widgets):
            x, y = bcx, bcy
            y += (self.bcsize + 20) * i
            bttn.setGeometry(x, y, self.bcsize*2, self.bcsize)
            slider.setGeometry(x + self.bcsize*2 + 5, y, self.bcsize*4, self.bcsize)
        self.updateBC()
    
    def updateBC(self):
        """Update the brightness/contrast on the slider to the section."""
        b = self.mainwindow.field.section.brightness
        c = self.mainwindow.field.section.contrast

        b_slider_value = round((abs(b)/100) ** (1/2) * 100) * (-1 if b < 0 else 1)
        c_slider_value = round((abs(c)/100) ** (1/2) * 100) * (-1 if c < 0 else 1)

        b_bttn, b_slider = self.bc_widgets[0]
        b_bttn.setText(str(b))
        b_slider.setValue(b_slider_value)

        c_bttn, c_slider = self.bc_widgets[1]
        c_bttn.setText(str(c))
        c_slider.setValue(c_slider_value)
    
    def createBCButtons(self):
        """Create the brightnes/contrast buttons."""
        # create the brightness/contrast button/slider
        self.bc_widgets = []
        for option in ("brightness", "contrast"):
            # create button
            b = MoveableButton(self.mainwindow, self, "bc")
            icon_fp = os.path.join(loc.img_dir, f"{option}_up.png")
            pixmap = QPixmap(icon_fp)
            b.setIcon(QIcon(pixmap))
            b.setIconSize(QSize(self.bcsize*2/3, self.bcsize*2/3))
            b.show()
            # create slider
            s = QSlider(Qt.Horizontal, self.mainwindow)
            s.setMinimum(-100)
            s.setMaximum(100)
            s.show()
            self.bc_widgets.append((b, s))
        self.placeBCButtons()
        # connect functions
        self.bc_widgets[0][1].valueChanged.connect(
                self.setBrightness
        )
        self.bc_widgets[1][1].valueChanged.connect(
                self.setContrast
        )
    
    def setBrightness(self, b : int):
        """Set the brightness for the current section."""
        b = round((b/100) ** 2 * 100) * (-1 if b < 0 else 1)
        if b == self.mainwindow.field.section.brightness:
            return
        self.mainwindow.field.section_layer.setBrightness(b)
        self.mainwindow.field.updateData()
        self.updateBC()
        self.mainwindow.field.generateView(generate_traces=False)
        self.mainwindow.seriesModified(True)
    
    def setContrast(self, c : int):
        """Set the contrast for the current section."""
        c = round((c/100) ** 2 * 100) * (-1 if c < 0 else 1)
        if c == self.mainwindow.field.section.contrast:
            return
        self.mainwindow.field.section_layer.setContrast(c)
        self.mainwindow.field.updateData()
        self.updateBC()
        self.mainwindow.field.generateView(generate_traces=False)
        self.mainwindow.seriesModified(True)
    
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
            "trace": (fx1 + self.pblen*5, fx2 - self.pblen*5.5 - 3, fy1 + self.pblen, fy2 - self.pblen),
            "inc": (fx1, fx2 - self.ibw, fy1, fy2 - self.ibh*2 - 15),
            "bc": (fx1, fx2 - 6*self.bcsize - 5, fy1, fy2 - 2*self.bcsize - 20)
        }

    def togglePalette(self):
        """Hide/Unhide the mouse palette."""
        self.palette_hidden = not self.palette_hidden
        for w in (self.palette_buttons + [self.label]):
            w.hide() if self.palette_hidden else w.show()
    
    def toggleIncrement(self):
        """Hide/Unhide the increment buttons."""
        self.inc_hidden = not self.inc_hidden
        for b in self.inc_buttons:
            b.hide() if self.inc_hidden else b.show()
    
    def toggleBC(self):
        """Hide/Unhide the brightness/contrast buttons."""
        self.bc_hidden = not self.bc_hidden
        for b, s in self.bc_widgets:
            b.hide() if self.bc_hidden else b.show()
            s.hide() if self.bc_hidden else s.show()
    
    def resetPos(self):
        """Reset the positions of the buttons."""
        self.mode_x = 0.99
        self.mode_y = 0.01
        
        self.trace_x = 0.5
        self.trace_y = 0.99

        self.inc_x = 0.99
        self.inc_y = 0.99

        self.bc_x = 0.99
        self.bc_y = 0.8

        self.resize()
    
    def incrementPalette(self, up):
        """Increment the palette.
            
            Params:
                up (bool): True if increment higher, False if increment lower
        """
        if self.is_dragging:
            return
        
        def incStr(s):
            min = 0
            max = 10**len(s) - 1
            n = int(s) + (1 if up else -1)
            if n < min: n = max
            elif n > max: n = min
            return str(n).rjust(len(s), "0")
        
        def replace(match):
            return "{" + incStr(match.group(1)) + "}"
        
        pattern = r"\{(\d+)\}"

        for bpos, w in enumerate(self.palette_buttons):
            n = re.sub(pattern, replace, w.trace.name)
            new_trace = w.trace.copy()
            new_trace.name = n
            self.modifyPaletteButton(bpos, new_trace)
    
    def incrementButton(self, bpos : int = None, up=True):
        """Increment a specific button.
        
            Params:
                bpos (int): the position of the button to increment
                up (bool): True if increment the number higher
        """
        if self.is_dragging:
            return
        
        if not bpos:
            bpos = self.series.palette_index[1]


        pattern = r"\<(\d+)\>"
        name = self.palette_buttons[bpos].trace.name
        if not re.search(pattern, name):
            return
        
        def incStr(s):
            min = 0
            max = 10**len(s) - 1
            n = int(s) + (1 if up else -1)
            if n < min: n = max
            elif n > max: n = min
            return str(n).rjust(len(s), "0")

        def replace(match):
            return "<" + incStr(match.group(1)) + ">"
        
        n = re.sub(pattern, replace, name)
        new_trace = self.palette_buttons[bpos].trace.copy()
        new_trace.name = n
        self.modifyPaletteButton(bpos, new_trace)
        
    def modifyAllPaletteButtons(self):
        """Modify all the palette buttons through a single dialog."""
        if self.is_dragging:
            return
               
        # run the widget
        response, confirmed = TracePaletteDialog(self.mainwindow, self.series).exec()
        if not confirmed:
            return
        
        self.modifyPalette(self.series.palette_traces[self.series.palette_index[0]])
        self.activatePaletteButton(self.series.palette_index[1])
    
    def setFlag(self, name : str = None, color : tuple = None, font_size : int = None, display_flags : str = None):
        """Set the default flag in the palette."""
        regenerate_view = False
        if name is not None:
            self.series.setOption("flag_name", name)
        
        if color is None:
            color = self.series.getOption("flag_color")
        else:
            self.series.setOption("flag_color", color)
        
        if font_size is None:
            font_size = self.series.getOption("flag_size")
        elif font_size != self.series.getOption("flag_size"):
            self.series.setOption("flag_size", font_size)
            regenerate_view = True
        
        if display_flags is not None and display_flags != self.series.getOption("show_flags"):
            self.series.setOption("show_flags", display_flags)
            self.mainwindow.field.section.selected_flags = []
            regenerate_view = True
        
        if regenerate_view:
            self.mainwindow.field.generateView(generate_image=False)
        
        button = self.mode_buttons["Flag"][0]
        button.setFont(QFont("Courier New", 20, QFont.Bold))
        button.setText("⚑")
        s = f"({','.join(map(str, color))})"
        button.setStyleSheet(f"color:rgb{s}")
    
    def modifyFlag(self):
        """Modify the default flag."""
        show_flags = self.series.getOption("show_flags")
        structure = [
            ["Default name:", ("text", self.series.getOption("flag_name"))],
            ["Default color:", ("color", self.series.getOption("flag_color"))],
            ["Size of all flags: ", ("int", self.series.getOption("flag_size"), tuple(range(1, 100)))],
            ["Display"],
            [("radio",
              ("All flags", show_flags == "all"),
              ("Only unresolved flags", show_flags == "unresolved"),
              ("No flags", show_flags == "none")
            )]
        ]
        response, confirmed = QuickDialog.get(self.mainwindow, structure, "Flag")
        if not confirmed:
            return
        
        if response[3][0][1]: show_flags = "all"
        elif response[3][2][1]: show_flags = "none"
        else: show_flags = "unresolved"
        
        self.setFlag(response[0], response[1], response[2], show_flags)
    
    def displayHelp(self):
        """Display the help associated with the trace palette."""
        if self.help_widget and self.help_widget.isVisible():
            self.help_widget.close()
        self.help_widget = TextWidget(
            self.mainwindow, 
            palette_help, 
            "Palette Help", 
            html=True
        )
        
    def resize(self):
        """Move the buttons to fit the main window."""
        for mbname in self.mode_buttons:
            button, mode, pos = self.mode_buttons[mbname]
            self.placeModeButton(button, pos)
        for i, pb in enumerate(self.palette_buttons):
            self.placePaletteButton(pb, i)
        self.placePaletteSideButtons()
        self.placeLabel()
        self.placeIncrementButtons()
        self.placeBCButtons()
    
    def reset(self):
        """Reset the mouse palette when opening a new series."""
        self.close()
        self.__init__(self.mainwindow)

    def close(self):
        """Close all buttons"""
        for bname in self.mode_buttons:
            button, _, __ = self.mode_buttons[bname]
            button.close()
        for pb in self.palette_buttons:
            pb.close()
        for b in self.palette_side_buttons:
            b.close()
        self.label.close()
        for b in self.inc_buttons:
            b.close()
        for b, s in self.bc_widgets:
            b.close()
            s.close()
        
palette_help = """<b>Palette Help</b>
<br><br>
The trace palette is how you modify the traces you make in the field.
Each palette button has a trace, and when you create traces in the field,
the traces you create will match the name, color, and other settings set through the palette buttons.
<br><br>
Right-click on a palette button to edit its trace.
Additionally, you can edit every palette trace at once by clicking on the "☰" icon (directly above the help icon).
<br><br>
Any whitespace and commas are NOT accepted in trace names, and will be replaced with underscores.
<br><br>
<b>SPECIAL CHARACTERS &lt;#&gt;</b>:
<br><br>
If you enter a number within the "&lt;" and "&gt;" symbols, the number inside the symbols will be incremented every time you create a trace.
The "&lt;&gt;" symbols will not be included in the trace name.
<br><br>
Example: "my_trace&lt;01&gt;"
<br><br>
The first trace created will be "my_trace01", the next trace created will be "my_trace02", and so on.
<br><br>
<b>SPECIAL CHARACTERS {#}</b>:
<br><br>
If you enter a number within the "{" and "}" symbols, the number inside the symbols
will be incremented ONLY when you press the "+" or "-" buttons at the right side of the palette.
The "{}" symbols will not be included in the trace name.
Note that ALL traces in the palette that follow this pattern will be incremented when the "+" or "-" buttons are pressed.
<br><br>
Example: "a_trace_{01}" and "b_trace_{05}" (two separate buttons)
<br><br>
These buttons will trace as "a_trace_01" and "b_trace_05".
When the user presses the "+" button, these buttons will now trace as "a_trace_02" and "b_trace_06".
"""