import os

from PySide6.QtWidgets import QWidget, QMainWindow, QMessageBox, QFileDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPen, QColor, QPainter
os.environ['QT_IMAGEIO_MAXALLOC'] = "0"  # disable max image size

from modules.pyrecon.series import Series
from modules.pyrecon.trace import Trace

from modules.calc.pfconversions import pixmapPointToField

from modules.backend.field_view import FieldView

from modules.gui.attributedialog import AttributeDialog

class FieldWidget(QWidget, FieldView):
    # mouse modes
    POINTER, PANZOOM, SCALPEL, CLOSEDPENCIL, OPENPENCIL, CLOSEDLINE, OPENLINE, STAMP = range(8)

    def __init__(self, series : Series, parent : QMainWindow):
        """Create the field widget.
        
            Params:
                series (Series): the series object
                parent (MainWindow): the main window that contains this widget
        """
        QWidget.__init__(self, parent)
        self.parent_widget = parent
        self.setMouseTracking(True)

        # set initial geometry to match parent
        parent_rect = self.parent_widget.geometry()
        self.pixmap_dim = parent_rect.width(), parent_rect.height()-20
        self.setGeometry(0, 0, *self.pixmap_dim)

        self.createField(series)

        self.show()
    
    def createField(self, series : Series):
        """Re-creates the field widget.
        
            Params:
                series (Series): the new series to load
        """
        self.series = series
        FieldView.__init__(self, series)

        # default mouse mode: pointer
        self.mouse_mode = FieldWidget.POINTER

        # ensure that the first section is found
        if self.series.current_section not in self.series.sections:
            self.series.current_section = self.series.sections.keys()[0]

        # establish misc defaults
        self.tracing_trace = Trace("TRACE", (255, 0, 255))
        self.is_line_tracing = False
        self.blend_sections = False

        self.generateView()
    
    def toggleBlend(self):
        self.blend_sections = not self.blend_sections
        self.generateView()
    
    def generateView(self, generate_image=True, generate_traces=True, update=True):
        self.field_pixmap = FieldView.generateView(
            self,
            self.pixmap_dim,
            generate_image,
            generate_traces,
            blend=self.blend_sections
        )
        self.field_pixmap_copy = self.field_pixmap.copy()
        self.update()
    
    def paintEvent(self, event):
        """Called when self.update() and various other functions are run.
        
        Overwritten from QWidget.
        Paints self.field_pixmap onto self (the widget).

            Params:
                event: unused
        """
        field_painter = QPainter(self)
        field_painter.drawPixmap(self.rect(), self.field_pixmap, self.field_pixmap.rect())
        field_painter.end()
    
    def resizeEvent(self, event):
        """Scale field window if main window size changes.
        
        Overwritten from QWidget Class.

            Params:
                event: contains data on window size
        """
        w = event.size().width()
        h = event.size().height()
        self.pixmap_dim = (w, h)
        self.generateView()
    
    def updateStatusBar(self, event=None, find_closest_trace=True):
        """Update status bar with useful information.
        
            Params:
                event: contains data on mouse position
                find_closest_trace (bool): whether or not to display closest trace
        """
        if event is not None:
            section = "Section: " + str(self.series.current_section)

            x, y = event.pos().x(), event.pos().y()
            x, y = pixmapPointToField(x, y, self.pixmap_dim, self.series.window, self.section.mag)
            position = "x = " + str("{:.4f}".format(x)) + ", "
            position += "y = " + str("{:.4f}".format(y))

            alignment = "Alignment: " + self.series.alignment

            tracing = "Tracing: " + '"' + self.tracing_trace.name + '"'

            if find_closest_trace:
                closest_trace = self.findClosestTrace(x, y)
                if closest_trace:
                    ct = "Nearest trace: " + closest_trace.name 
                else:
                    ct = ""
            else:
                ct = ""
            if ct == "":
                self.status_list = [section, position, alignment, tracing]
            else:
                self.status_list = [section, position, alignment, tracing, ct]
        else:
            self.status_list[0] = "Section: " + str(self.series.current_section) 
        s = "  |  ".join(self.status_list)
        self.parent_widget.statusbar.showMessage(s)
    
    def changeTraceAttributes(self):
        """Change the trace attributes for a given trace"""
        if len(self.section_layer.selected_traces) == 0:  # skip if no traces selected
            return
        name = self.section_layer.selected_traces[0].name
        color = self.section_layer.selected_traces[0].color
        for trace in self.section_layer.selected_traces[1:]:
            if trace.name != name:
                name = ""
            if trace.color != color:
                color = None
        attr_input = AttributeDialog(name=name, color=color).exec()
        if attr_input is None:
            return
        self.section_layer.changeTraceAttributes(*attr_input)
        self.saveState()
        self.generateView(generate_image=False)
        
    
    def mousePressEvent(self, event):
        """Called when mouse is clicked.
        
        Overwritten from QWidget class.

            Params:
                event: contains mouse input data
        """
        if self.mouse_mode == FieldWidget.POINTER:
            self.pointerPress(event)
        elif self.mouse_mode == FieldWidget.PANZOOM:
            self.panzoomPress(event) 
        elif self.mouse_mode == FieldWidget.OPENPENCIL or self.mouse_mode == FieldWidget.CLOSEDPENCIL:
            self.pencilPress(event)
        elif self.mouse_mode == FieldWidget.STAMP:
            self.stampPress(event)
        elif self.mouse_mode == FieldWidget.CLOSEDLINE:
            self.linePress(event, closed=True)
        elif self.mouse_mode == FieldWidget.OPENLINE:
            self.linePress(event, closed=False)
        elif self.mouse_mode == FieldWidget.SCALPEL:
            self.scalpelPress(event)

    def mouseMoveEvent(self, event):
        """Called when mouse is moved.
        
        Overwritten from QWidget class.
        
            Params:
                event: contains mouse input data
        """
        if (event.buttons() and self.mouse_mode != FieldWidget.PANZOOM) or self.is_line_tracing:
            self.updateStatusBar(event, find_closest_trace=False)
        elif not event.buttons():
            self.updateStatusBar(event)
        if self.mouse_mode == FieldWidget.POINTER and event.buttons():
            self.pointerMove(event)
        elif self.mouse_mode == FieldWidget.PANZOOM and event.buttons():
            self.panzoomMove(event)
        elif (self.mouse_mode == FieldWidget.OPENPENCIL or self.mouse_mode == FieldWidget.CLOSEDPENCIL) and event.buttons():
            self.pencilMove(event)
        elif self.mouse_mode == FieldWidget.CLOSEDLINE and self.is_line_tracing:
            self.lineMove(event, closed=True)
        elif self.mouse_mode == FieldWidget.OPENLINE and self.is_line_tracing:
            self.lineMove(event, closed=False)
        elif self.mouse_mode == FieldWidget.SCALPEL and event.buttons():
            self.scalpelMove(event)

    def mouseReleaseEvent(self, event):
        """Called when mouse button is released.
        
        Overwritten from QWidget Class.
        
            Params:
                event: contains mouse input data
        """
        if self.mouse_mode == FieldWidget.POINTER:
            self.pointerRelease(event)
        if self.mouse_mode == FieldWidget.PANZOOM:
            self.panzoomRelease(event)
        elif self.mouse_mode == FieldWidget.CLOSEDPENCIL:
            self.pencilRelease(event, closed=True)
        elif self.mouse_mode == FieldWidget.OPENPENCIL:
            self.pencilRelease(event, closed=False)
        elif self.mouse_mode == FieldWidget.SCALPEL:
            self.scalpelRelease(event)
    
    def setMouseMode(self, mode : int):
        """Set the mode of the mouse.
        
            Params:
                mode (int): number corresponding to mouse mode
        """
        self.endPendingEvents()  # end any mouse-related pending events
        self.mouse_mode = mode
    
    def setTracingTrace(self, trace : Trace):
        """Set the trace used by the pencil/line tracing/stamp.
        
            Params:
                trace (Trace): the new trace to use as refernce for further tracing
        """
        self.tracing_trace = trace
    
    def pointerPress(self, event):
        """Called when mouse is pressed in pointer mode.

        Selects/deselcts the nearest trace
        
            Params:
                event: contains mouse input data
        """
        pix_x, pix_y = event.x(), event.y()
        deselect = (event.buttons() == Qt.RightButton)
        self.selectTrace(pix_x, pix_y, deselect=deselect)
    
    def pointerMove(self, event):
        """Called when mouse is moved in pointer mode.
        
        Not implemented yet.
        """
        return
    
    def pointerRelease(self, event):
        """Called when mouse is released in pointer mode.
        
        Not implemented yet.
        """
        return
        
    def panzoomPress(self, event):
        """Called when mouse is clicked in panzoom mode.
        
        Saves the position of the mouse.

            Params:
                event: contains mouse input data
        """
        self.clicked_x = event.x()
        self.clicked_y = event.y()

    def panzoomMove(self, event):
        """Called when mouse is moved in panzoom mode.
        
        Generates image outputfor panning and zooming.

            Params:
                event: contains mouse input data
        """
        # if left mouse button is pressed, do panning
        if event.buttons() == Qt.LeftButton:
            move_x = (event.x() - self.clicked_x)
            move_y = (event.y() - self.clicked_y)
            # move field with mouse
            new_field = QPixmap(*self.pixmap_dim)
            new_field.fill(QColor(0, 0, 0))
            painter = QPainter(new_field)
            painter.drawPixmap(move_x, move_y, *self.pixmap_dim, self.field_pixmap_copy)
            self.field_pixmap = new_field
            painter.end()
            self.update()
        # if right mouse button is pressed, do zooming
        elif event.buttons() == Qt.RightButton:
            # up and down mouse movement only
            move_y = event.y() - self.clicked_y
            zoom_factor = 1.005 ** (move_y) # 1.005 is arbitrary
            # calculate new geometry of window based on zoom factor
            xcoef = (self.clicked_x / self.pixmap_dim[0]) * 2
            ycoef = (self.clicked_y / self.pixmap_dim[1]) * 2
            w = self.pixmap_dim[0] * zoom_factor
            h = self.pixmap_dim[1] * zoom_factor
            x = (self.pixmap_dim[0] - w) / 2 * xcoef
            y = (self.pixmap_dim[1] - h) / 2 * ycoef
            # adjust field
            new_field = QPixmap(*self.pixmap_dim)
            new_field.fill(QColor(0, 0, 0))
            painter = QPainter(new_field)
            painter.drawPixmap(x, y, w, h,
                                self.field_pixmap_copy)
            self.field_pixmap = new_field
            painter.end()
            self.update()

    def panzoomRelease(self, event):
        """Called when mouse is released in panzoom mode.

        Adjusts new window view.
        
            Params:
                event: contains mouse input data
        """
        # set new window for panning
        if event.button() == Qt.LeftButton:
            section = self.section
            x_scaling = self.pixmap_dim[0] / (self.series.window[2] / section.mag)
            y_scaling = self.pixmap_dim[1] / (self.series.window[3] / section.mag)
            move_x = -(event.x() - self.clicked_x) / x_scaling * section.mag
            move_y = (event.y() - self.clicked_y) / y_scaling * section.mag
            self.series.window[0] += move_x
            self.series.window[1] += move_y
            self.generateView()
        # set new window for zooming
        elif event.button() == Qt.RightButton:
            section = self.section
            x_scaling = self.pixmap_dim[0] / (self.series.window[2] / section.mag)
            y_scaling = self.pixmap_dim[1] / (self.series.window[3] / section.mag)
            move_y = event.y() - self.clicked_y
            zoom_factor = 1.005 ** (move_y)
            # calculate pixel equivalents for window view
            xcoef = (self.clicked_x / self.pixmap_dim[0]) * 2
            ycoef = (self.clicked_y / self.pixmap_dim[1]) * 2
            w = self.pixmap_dim[0] * zoom_factor
            h = self.pixmap_dim[1] * zoom_factor
            x = (self.pixmap_dim[0] - w) / 2 * xcoef
            y = (self.pixmap_dim[1] - h) / 2 * ycoef
            # convert pixel equivalents to field coordinates
            window_x = - x  / x_scaling / zoom_factor * section.mag 
            window_y = - (self.pixmap_dim[1] - y - self.pixmap_dim[1] * zoom_factor)  / y_scaling / zoom_factor * section.mag
            self.series.window[0] += window_x
            self.series.window[1] += window_y
            self.series.window[2] /= zoom_factor
            # set limit on how far user can zoom in
            if self.series.window[2] < section.mag:
                self.series.window[2] = section.mag
            self.series.window[3] /= zoom_factor
            if self.series.window[3] < section.mag:
                self.series.window[3] = section.mag
            self.generateView()
    
    def pencilPress(self, event):
        """Called when mouse is pressed in pencil mode.

        Begins creating a new trace.
        
            Params:
                event: contains mouse input data
        """
        self.last_x = event.x()
        self.last_y = event.y()
        self.current_trace = [(self.last_x, self.last_y)]

    def pencilMove(self, event):
        """Called when mouse is moved in pencil mode with the left mouse button pressed.

        Draws continued trace on the screen.
        
            Params:
                event: contains mouse input data
        """
        # draw trace on pixmap
        x = event.x()
        y = event.y()
        painter = QPainter(self.field_pixmap)
        color = QColor(*self.tracing_trace.color)
        painter.setPen(QPen(color, 1))
        painter.drawLine(self.last_x, self.last_y, x, y)
        painter.end()
        self.current_trace.append((x, y))
        self.last_x = x
        self.last_y = y
        self.update()

    def pencilRelease(self, event, closed=True):
        """Called when mouse is released in pencil mode.

        Completes and adds trace.
        
            Params:
                event: contains mouse input data
        """
        if len(self.current_trace) <= 1:
            return
        self.newTrace(
            self.current_trace,
            name=self.tracing_trace.name,
            color=self.tracing_trace.color,
            closed=closed
        )
    
    def linePress(self, event, closed=True):
        """Called when mouse is pressed in a line mode.
        
        Begins create a line trace.
        
            Params:
                event: contains mouse input data
        """
        x, y = event.x(), event.y()
        if event.button() == Qt.LeftButton:  # begin/add to trace if left mouse button
            if self.is_line_tracing:  # start new trace
                self.current_trace.append((x, y))
                self.field_pixmap = self.field_pixmap_copy.copy()  # operate on original pixmap
                painter = QPainter(self.field_pixmap)
                color = QColor(*self.tracing_trace.color)
                painter.setPen(QPen(color, 1))
                if closed:
                    start = 0
                else:
                    start = 1
                for i in range(start, len(self.current_trace)):
                    painter.drawLine(*self.current_trace[i-1], *self.current_trace[i])
                painter.end()
                self.update()
            else:  # add to existing
                self.current_trace = [(x, y)]
                self.is_line_tracing = True
        elif event.button() == Qt.RightButton:  # complete existing trace if right mouse button
            if self.is_line_tracing:
                self.newTrace(self.current_trace,
                    name=self.tracing_trace.name,
                    color=self.tracing_trace.color,
                    closed=closed
                )
                self.is_line_tracing = False
    
    def lineMove(self, event, closed=True):
        """Called when mouse is moved in a line mode.
        
        Adds dashed lines to screen connecting the mouse pointer to the existing trace.
        
            Params:
                event: contains mouse input data
        """
        x, y = event.x(), event.y()
        self.field_pixmap = self.field_pixmap_copy.copy()
        # draw solid lines for existing trace
        painter = QPainter(self.field_pixmap)
        color = QColor(*self.tracing_trace.color)
        pen = QPen(color, 1)
        painter.setPen(pen)
        if closed:
            start = 0
        else:
            start = 1
        for i in range(start, len(self.current_trace)):
            painter.drawLine(*self.current_trace[i-1], *self.current_trace[i])
        # draw dashed lines that connect to mouse pointer
        pen.setDashPattern([2,5])
        painter.setPen(pen)
        painter.drawLine(*self.current_trace[-1], x, y)
        if closed:
            painter.drawLine(*self.current_trace[0], x, y)
        self.update()
    
    def stampPress(self, event):
        """Called when mouse is pressed in stamp mode.
        
        Creates a stamp centered on the mouse location.
        
            Params:
                event: contains mouse input data
        """
        # get mouse coords and convert to field coords
        pix_x, pix_y = event.x(), event.y()
        self.placeStamp(pix_x, pix_y, self.tracing_trace)
    
    def scalpelPress(self, event):
        """Called when mouse is pressed in scalpel mode.

        Begins creating a new trace.
        
            Params:
                event: contains mouse input data
        """
        self.last_x = event.x()
        self.last_y = event.y()
        self.scalpel_trace = [(self.last_x, self.last_y)]

    def scalpelMove(self, event):
        """Called when mouse is moved in pencil mode with a mouse button pressed.

        Draws continued scalpel trace on the screen.
        
            Params:
                event: contains mouse input data
        """
        # draw scalpel trace on pixmap
        x = event.x()
        y = event.y()
        painter = QPainter(self.field_pixmap)
        color = QColor(255,0,0)
        painter.setPen(QPen(color, 1))
        painter.drawLine(self.last_x, self.last_y, x, y)
        painter.end()
        self.scalpel_trace.append((x, y))
        self.last_x = x
        self.last_y = y
        self.update()

    def scalpelRelease(self, event):
        """Called when mouse is released in pencil mode.

        Completes and adds trace.
        
            Params:
                event: contains mouse input data
        """
        self.cutTrace(self.scalpel_trace)
    
    def endPendingEvents(self):
        """End ongoing events that are connected to the mouse."""
        if self.is_line_tracing:
            if self.mouse_mode == FieldWidget.CLOSEDLINE:
                self.section_layer.newTrace(self.current_trace, closed=True)
            elif self.mouse_mode == FieldWidget.OPENLINE:
                self.section_layer.newTrace(self.current_trace, closed=False)
            self.is_line_tracing = False
            self.generateView(generate_image=False)
