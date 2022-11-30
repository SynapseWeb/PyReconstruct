import time

from PySide6.QtWidgets import (
    QWidget, 
    QMainWindow, 
    QInputDialog, 
    QGestureEvent
)
from PySide6.QtCore import (
    Qt, 
    QPoint, 
    QEvent
)
from PySide6.QtGui import (
    QPixmap, 
    QPen, 
    QColor, 
    QPainter, 
    QPointingDevice,
    QCursor
)

from modules.pyrecon.series import Series
from modules.pyrecon.trace import Trace

from modules.calc.pfconversions import pixmapPointToField
from modules.calc.quantification import distance

from modules.backend.field_view import FieldView
from modules.backend.object_table_manager import ObjectTableManager
from modules.backend.ztrace_table_manager import ZtraceTableManager
from modules.backend.trace_table_manager import TraceTableManager

from modules.gui.dialog import FieldTraceDialog

class FieldWidget(QWidget, FieldView):
    # mouse modes
    POINTER, PANZOOM, KNIFE, CLOSEDTRACE, OPENTRACE, STAMP = range(6)

    def __init__(self, series : Series, mainwindow : QMainWindow):
        """Create the field widget.
        
            Params:
                series (Series): the series object
                mainwindow (MainWindow): the main window that contains this widget
        """
        QWidget.__init__(self, mainwindow)
        self.mainwindow = mainwindow
        self.setMouseTracking(True)

        # enable touch gestures
        Qt.WA_AcceptTouchEvents = True
        gestures = [Qt.GestureType.PinchGesture]
        for g in gestures:
            self.grabGesture(g)
        self.is_gesturing = False

        # set initial geometry to match parent
        parent_rect = self.mainwindow.geometry()
        self.pixmap_dim = parent_rect.width(), parent_rect.height()-20
        self.setGeometry(0, 0, *self.pixmap_dim)

        self.obj_table_manager = None
        self.ztrace_table_manager = None
        self.trace_table_manager = None

        self.createField(series)

        self.show()
    
    def createField(self, series : Series):
        """Re-creates the field widget.
        
            Params:
                series (Series): the new series to load
        """
        # close the tables
        if self.obj_table_manager is not None:
            self.obj_table_manager.close()
            self.obj_table_manager = None
        if self.ztrace_table_manager is not None:
            self.ztrace_table_manager.close()
            self.ztrace_table_manager = None
        if self.trace_table_manager is not None:
            self.trace_table_manager.close()
            self.trace_table_manager = None
        
        self.series = series
        FieldView.__init__(self, series)

        # default mouse mode: pointer
        self.mouse_mode = FieldWidget.POINTER

        # ensure that the first section is found
        if self.series.current_section not in self.series.sections:
            self.series.current_section = self.series.sections.keys()[0]

        # establish misc defaults
        self.tracing_trace = Trace("TRACE", (255, 0, 255))
        self.status_list = ["Section: " + str(self.series.current_section)]
        self.is_line_tracing = False
        self.blend_sections = False
        self.lclick = False
        self.rclick = False
        self.mclick = False
        self.erasing = False

        self.generateView()
    
    def toggleBlend(self):
        """Toggle blending sections."""
        self.blend_sections = not self.blend_sections
        self.generateView()
    
    def setViewMagnification(self):
        """Set the scaling for the section view."""
        new_scale, confirmed = QInputDialog.getText(
            self,
            "View Magnification",
            "Enter view magnification:",
            text=str(round(self.scaling, 6))
        )
        if not confirmed:
            return
        
        try:
            new_scale = float(new_scale)
        except ValueError:
            return
        
        self.setScaling(new_scale)
    
    def generateView(self, generate_image=True, generate_traces=True, update=True):
        """Generate the output view.
        
            Params:
                generate_image (bool): True if image should be regenerated
                generate_traces (bool): True if traces should be regenerated
                update (bool): True if view widget should be updated
        """
        self.field_pixmap = FieldView.generateView(
            self,
            self.pixmap_dim,
            generate_image,
            generate_traces,
            blend=self.blend_sections
        )
        self.field_pixmap_copy = self.field_pixmap.copy()
        if update:
            self.update()
    
    def openObjectList(self):
        """Open an object list."""
        # create the manager if not already
        if self.obj_table_manager is None:
            self.obj_table_manager = ObjectTableManager(self.series, self.mainwindow)
        # create a new table
        self.obj_table_manager.newTable()
    
    def openZtraceList(self):
        """Open a ztrace list."""
        # create manager if not already
        if self.ztrace_table_manager is None:
            self.ztrace_table_manager = ZtraceTableManager(
                self.series,
                self.mainwindow
            )
        # create a new table
        self.ztrace_table_manager.newTable()
    
    def openTraceList(self):
        """Open a trace list."""
        # create the manager if not already
        if self.trace_table_manager is None:
            self.trace_table_manager = TraceTableManager(
                self.series,
                self.section,
                self.mainwindow
            )
        # create a new table
        self.trace_table_manager.newTable()
    
    def findContourDialog(self):
        """Open a dilog to prompt user to find contour."""
        contour_name, confirmed = QInputDialog.getText(
            self,
            "Find Contour",
            "Enter the contour name:",
        )
        if not confirmed:
            return
        self.findContour(contour_name)
    
    def paintEvent(self, event):
        """Called when self.update() and various other functions are run.
        
        Overwritten from QWidget.
        Paints self.field_pixmap onto self (the widget).
        """
        field_painter = QPainter(self)
        field_painter.drawPixmap(self.rect(), self.field_pixmap, self.field_pixmap.rect())
        field_painter.end()
    
    def resizeEvent(self, event):
        """Scale field window if main window size changes.
        
        Overwritten from QWidget Class.
        """
        # resize the mouse palette
        self.mainwindow.mouse_palette.resize()

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
        self.status_list = []

        # display current section
        section = "Section: " + str(self.series.current_section)
        self.status_list.append(section)

        # display the alignment setting
        alignment = "Alignment: " + self.series.alignment
        self.status_list.append(alignment)

        if event is not None:
            # display mouse position in the field
            self.mouse_x, self.mouse_y = event.x(), event.y()
            x, y = pixmapPointToField(self.mouse_x, self.mouse_y, self.pixmap_dim, self.series.window, self.section.mag)
            position = "x = " + str("{:.4f}".format(x)) + ", "
            position += "y = " + str("{:.4f}".format(y))
            self.status_list.append(position)

            # display the closest trace in the field
            if find_closest_trace:
                closest_trace = self.findClosestTrace(x, y)
                if closest_trace:
                    ct = "Nearest trace: " + closest_trace.name 
                    self.status_list.append(ct)
            
            # display the distance between the current position and the last point if line tracing
            if self.is_line_tracing:
                last_x, last_y = self.current_trace[-1]
                d = distance(last_x, last_y, self.mouse_x, self.mouse_y)
                d = d / self.scaling * self.section.mag
                dist = f"Line distance: {round(d, 5)}"
                self.status_list.append(dist)
         
        s = "  |  ".join(self.status_list)
        self.mainwindow.statusbar.showMessage(s)
    
    def traceDialog(self):
        """Opens dialog to edit selected traces."""
        if not self.section_layer.selected_traces:
            return
        
        new_attr, confirmed = FieldTraceDialog(
            self,
            self.section_layer.selected_traces,
        ).exec()
        if not confirmed:
            return
        
        name, color, tags = new_attr
        self.section_layer.changeTraceAttributes(
            name=name,
            color=color,
            tags=tags
        )

        self.generateView(generate_image=False)
        self.saveState() 

    def setMouseMode(self, mode : int):
        """Set the mode of the mouse.
        
            Params:
                mode (int): number corresponding to mouse mode
        """
        self.endPendingEvents()  # end any mouse-related pending events
        self.mouse_mode = mode

        # set the cursor icon
        if mode == FieldWidget.POINTER:
            cursor = QCursor(Qt.ArrowCursor)
        elif mode == FieldWidget.PANZOOM:
            cursor = QCursor(Qt.SizeAllCursor)
        elif (mode == FieldWidget.OPENTRACE or
              mode == FieldWidget.CLOSEDTRACE or
              mode == FieldWidget.KNIFE or
              mode == FieldWidget.STAMP):
            cursor = QCursor(Qt.CrossCursor)
        self.setCursor(cursor)
    
    def setTracingTrace(self, trace : Trace):
        """Set the trace used by the pencil/line tracing/stamp.
        
            Params:
                trace (Trace): the new trace to use as refernce for further tracing
        """
        self.tracing_trace = trace       

    def event(self, event):
        """Overwritten from QWidget.event.
        
        Added to catch gestures.
        """
        if event.type() == QEvent.Gesture:
            self.gestureEvent(event)
        
        return super().event(event)

    def gestureEvent(self, event : QGestureEvent):
        """Called when gestures are detected."""
        g = event.gesture(Qt.PinchGesture)

        if g.state() == Qt.GestureState.GestureStarted:
            p = g.centerPoint()
            x, y = p.x(), p.y()
            self.clicked_x, self.clicked_y = x, y

        elif g.state() == Qt.GestureState.GestureUpdated:
            self.panzoomMove(g.centerPoint().x(), g.centerPoint().y(), g.totalScaleFactor())

        elif g.state() == Qt.GestureState.GestureFinished:
            self.panzoomRelease(g.centerPoint().x(), g.centerPoint().y(), g.totalScaleFactor())
        
    def mousePressEvent(self, event):
        """Called when mouse is clicked.
        
        Overwritten from QWidget class.
        """
        # if any finger touch
        if event.pointerType() == QPointingDevice.PointerType.Finger:
            return
        
        # if any eraser touch
        elif event.pointerType() == QPointingDevice.PointerType.Eraser:
            self.erasing = True
            return

        # check what was clicked
        self.lclick = event.buttons() == Qt.LeftButton
        self.rclick = event.buttons() == Qt.RightButton
        self.mclick = event.buttons() == Qt.MiddleButton

        # pan if middle button clicked
        if self.mclick:
            self.mousePanzoomPress(event)
            return

        # pull up right-click menu if requirements met
        context_menu = self.rclick
        context_menu &= not (self.mouse_mode == FieldWidget.PANZOOM)
        context_menu &= not self.is_line_tracing
        if context_menu:
            clicked_trace = self.section_layer.getTrace(event.x(), event.y())
            if clicked_trace in self.section_layer.selected_traces:
                self.mainwindow.trace_menu.exec(event.globalPos())
            else:
                self.mainwindow.field_menu.exec(event.globalPos())
            return

        if self.mouse_mode == FieldWidget.POINTER:
            self.pointerPress(event)
        elif self.mouse_mode == FieldWidget.PANZOOM:
            self.mousePanzoomPress(event) 
        elif self.mouse_mode == FieldWidget.KNIFE:
            self.knifePress(event)
        elif (
            self.mouse_mode == FieldWidget.CLOSEDTRACE or
            self.mouse_mode == FieldWidget.OPENTRACE
        ):
            self.tracePress(event)
        elif self.mouse_mode == FieldWidget.STAMP:
            self.stampPress(event)

    def mouseMoveEvent(self, event):
        """Called when mouse is moved.
        
        Overwritten from QWidget class.
        """
        # if any finger touch
        if event.pointerType() == QPointingDevice.PointerType.Finger:
            return
        
        # if any eraser touch
        elif event.pointerType() == QPointingDevice.PointerType.Eraser:
            self.eraserMove(event)
        
        # update click status
        if not event.buttons():
            self.lclick = False
            self.rclick = False
            self.mclick = False
            self.erasing = False
        
        # panzoom if middle button clicked
        if self.mclick:
            self.mousePanzoomMove(event)
            return
        
        # update the status bar
        if (event.buttons() and self.mouse_mode == FieldWidget.PANZOOM):
            self.updateStatusBar()
        else:
            self.updateStatusBar(event)
        
        # mouse functions
        if self.mouse_mode == FieldWidget.POINTER:
                self.pointerMove(event)
        elif self.mouse_mode == FieldWidget.PANZOOM:
            self.mousePanzoomMove(event)
        elif self.mouse_mode == FieldWidget.KNIFE:
            self.knifeMove(event)
        elif (
            self.mouse_mode == FieldWidget.CLOSEDTRACE or
            self.mouse_mode == FieldWidget.OPENTRACE
        ):
            self.traceMove(event)

    def mouseReleaseEvent(self, event):
        """Called when mouse button is released.
        
        Overwritten from QWidget Class.
        """
        # if any finger touch
        if event.pointerType() == QPointingDevice.PointerType.Finger:
            return
        
        # if any eraser touch
        elif event.pointerType() == QPointingDevice.PointerType.Eraser:
            self.erasing = False
            return
        
        # panzoom if middle button
        if self.mclick:
            self.mousePanzoomRelease(event)
            self.mclick = False
            return

        if self.mouse_mode == FieldWidget.POINTER:
            self.pointerRelease(event)
        if self.mouse_mode == FieldWidget.PANZOOM:
            self.mousePanzoomRelease(event)
        elif (
            self.mouse_mode == FieldWidget.CLOSEDTRACE or
            self.mouse_mode == FieldWidget.OPENTRACE
        ):
            self.traceRelease(event)
        elif self.mouse_mode == FieldWidget.KNIFE:
            self.knifeRelease(event)
        
        self.lclick = False
        self.rclick = False
    
    def pointerPress(self, event):
        """Called when mouse is pressed in pointer mode.

        Selects/deselects the nearest trace
        """
        # select, deselect or move
        if self.lclick:
            self.is_moving_trace = False
            self.is_selecting_traces = False
            self.clicked_x, self.clicked_y = event.x(), event.y()
            self.selected_trace = self.section_layer.getTrace(
                self.clicked_x,
                self.clicked_y
            )
    
    def pointerMove(self, event):
        """Called when mouse is moved in pointer mode."""
        # left button is down and user clicked on a trace
        if self.lclick and (
            self.is_moving_trace or 
            self.selected_trace in self.section_layer.selected_traces
        ): 
            if not self.is_moving_trace:  # user has just decided to move the trace
                self.is_moving_trace = True
                # get pixel points
                self.moving_traces = []
                for trace in self.section_layer.selected_traces:
                    moving_trace = trace.copy()
                    pix_points = self.section_layer.traceToPix(trace)
                    moving_trace.points = pix_points
                    self.moving_traces.append(moving_trace)
                # remove the traces
                self.section_layer.deleteTraces()
                self.generateView(update=False)

            dx = event.x() - self.clicked_x
            dy = event.y() - self.clicked_y
            self.field_pixmap = self.field_pixmap_copy.copy()
            # redraw the traces with translatation
            painter = QPainter(self.field_pixmap)
            for trace in self.moving_traces:
                painter.setPen(QPen(QColor(*trace.color), 1))
                plot_points = [QPoint(x+dx, y+dy) for x,y in trace.points]
                if trace.closed:
                    painter.drawPolygon(plot_points)
                else:
                    painter.drawPolyline(plot_points)
            painter.end()
            
            self.update()

        # no trace was clicked on OR user clicked on unselected trace
        elif self.lclick:
            if not self.is_selecting_traces:  # user just decided to group select traces
                self.is_selecting_traces = True
                # create list
                self.selection_trace = [(self.clicked_x, self.clicked_y)]
            x = event.x()
            y = event.y()
            self.selection_trace.append((x, y))
            # draw the trace on the screen
            self.field_pixmap = self.field_pixmap_copy.copy()
            painter = QPainter(self.field_pixmap)
            pen = QPen(QColor(255, 255, 255), 1)
            pen.setDashPattern([4, 4])
            painter.setPen(pen)
            painter.drawPolygon(
                [QPoint(*p) for p in self.selection_trace]
            )
            painter.end()
            self.update()
    
    def pointerRelease(self, event):
        """Called when mouse is released in pointer mode."""
        # user moved traces
        if self.lclick and self.is_moving_trace:
            # save the traces in their final position
            self.is_moving_trace = False
            dx = event.x() - self.clicked_x
            dy = event.y() - self.clicked_y
            for trace in self.moving_traces:
                pix_points = [(x+dx, y+dy) for x,y in trace.points]
                self.section_layer.newTrace(pix_points, trace, closed=trace.closed)
            self.generateView()
            self.saveState()
        
        # user selected an area of traces
        elif self.lclick and self.is_selecting_traces:
            self.is_selecting_traces = False
            selected_traces = self.section_layer.getTraces(self.selection_trace)
            self.selectTraces(selected_traces)

        # user single-clicked a trace
        elif self.lclick and self.selected_trace:
            self.selectTrace(self.selected_trace)
    
    def eraserMove(self, event):
        """Called when the user is erasing."""
        if not self.erasing:
            return
        erased = self.section_layer.eraseArea(event.x(), event.y())
        if erased:
            self.generateView()
            self.saveState()
    
    def panzoomPress(self, x, y):
        """Initiates panning and zooming mode.
        
            Params:
                x: the x position of the start
                y: the y position of the start
        """
        self.clicked_x = x
        self.clicked_y = y
        
    def mousePanzoomPress(self, event):
        """Called when mouse is clicked in panzoom mode.
        
        Saves the position of the mouse.
        """
        if self.mainwindow.is_zooming_in:
            return
        self.panzoomPress(event.x(), event.y())
    
    def panzoomMove(self, new_x=None, new_y=None, zoom_factor=1):
        """Generates image output for panning and zooming.
        
            Params:
                new_x: the x from panning
                new_y: the y from panning
                zoom_factor: the scale from zooming
        """
        field = self.field_pixmap_copy
        # calculate pan
        if new_x is not None and new_y is not None:
            move_x = new_x - self.clicked_x
            move_y = new_y - self.clicked_y
        else:
            move_x, move_y = 0, 0
        # calculate new geometry of window based on zoom factor
        if zoom_factor is not None:
            xcoef = (self.clicked_x / self.pixmap_dim[0]) * 2
            ycoef = (self.clicked_y / self.pixmap_dim[1]) * 2
            w = self.pixmap_dim[0] * zoom_factor
            h = self.pixmap_dim[1] * zoom_factor
            x = (self.pixmap_dim[0] - w) / 2 * xcoef
            y = (self.pixmap_dim[1] - h) / 2 * ycoef
        else:
            x, y = 0, 0
            w, h = self.pixmap_dim
        # adjust field
        new_field = QPixmap(*self.pixmap_dim)
        new_field.fill(QColor(0, 0, 0))
        painter = QPainter(new_field)
        painter.drawPixmap(move_x + x, move_y + y, w, h, field)
        self.field_pixmap = new_field
        self.update()

    def mousePanzoomMove(self, event):
        """Called when mouse is moved in panzoom mode."""
        if self.mainwindow.is_zooming_in:
            return
        # if left mouse button is pressed, do panning
        if self.lclick or self.mclick:
            self.panzoomMove(new_x=event.x(), new_y=event.y())
        # if right mouse button is pressed, do zooming
        elif self.rclick:
            # up and down mouse movement only
            move_y = event.y() - self.clicked_y
            zoom_factor = 1.005 ** (move_y) # 1.005 is arbitrary
            self.panzoomMove(zoom_factor=zoom_factor)
        
    def panzoomRelease(self, new_x=None, new_y=None, zoom_factor=None):
        """Generates image output for panning and zooming.
        
            Params:
                new_x: the x from panning
                new_y: the y from panning
                zoom_factor: the scale from zooming
        """
        section = self.section

        # zoom the series window
        if zoom_factor is not None:
            x_scaling = self.pixmap_dim[0] / (self.series.window[2] / section.mag)
            y_scaling = self.pixmap_dim[1] / (self.series.window[3] / section.mag)
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
            
        # move the series window
        if new_x is not None and new_y is not None:
            x_scaling = self.pixmap_dim[0] / (self.series.window[2] / section.mag)
            y_scaling = self.pixmap_dim[1] / (self.series.window[3] / section.mag)
            move_x = -(new_x - self.clicked_x) / x_scaling * section.mag
            move_y = (new_y - self.clicked_y) / y_scaling * section.mag
            self.series.window[0] += move_x
            self.series.window[1] += move_y
        
        self.generateView()

    def mousePanzoomRelease(self, event):
        """Called when mouse is released in panzoom mode."""
        if self.mainwindow.is_zooming_in:
            return
        # set new window for panning
        if self.lclick or self.mclick:
            self.panzoomRelease(new_x=event.x(), new_y=event.y())
        # set new window for zooming
        elif self.rclick:
            move_y = event.y() - self.clicked_y
            zoom_factor = 1.005 ** (move_y)
            self.panzoomRelease(zoom_factor=zoom_factor)
    
    def tracePress(self, event):
        """Called when mouse is pressed in trace mode."""
        if self.is_line_tracing:
            self.linePress(event)
        else:
            self.click_time = time.time()
            self.last_x = event.x()
            self.last_y = event.y()
            self.current_trace = [(self.last_x, self.last_y)]
    
    def traceMove(self, event):
        """Called when mouse is moved in trace mode."""
        if self.is_line_tracing:
            self.lineMove(event)
        else:
            self.pencilMove(event)
    
    def traceRelease(self, event):
        """Called when mouse is released in trace mode."""
        # user is already line tracing
        if self.is_line_tracing:
            self.lineRelease(event)
        # user decided to line trace
        elif len(self.current_trace) == 1 or (time.time() - self.click_time < 0.01):
            self.current_trace = [self.current_trace[0]]
            self.is_line_tracing = True
        # user is not line tracing
        elif not self.is_line_tracing:
            self.pencilRelease(event)

    def pencilMove(self, event):
        """Called when mouse is moved in pencil mode with the left mouse button pressed.

        Draws continued trace on the screen.
        """
        if self.lclick:
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

    def pencilRelease(self, event):
        """Called when mouse is released in pencil mode.

        Completes and adds trace.
        """
        closed = (self.mouse_mode == FieldWidget.CLOSEDTRACE)
        if self.lclick:
            if len(self.current_trace) <= 1:
                return
            self.newTrace(
                self.current_trace,
                self.tracing_trace,
                closed=closed
            )
    
    def linePress(self, event):
        """Called when mouse is pressed in a line mode.
        
        Begins create a line trace.
        """
        closed = (self.mouse_mode == FieldWidget.CLOSEDTRACE)
        x, y = event.x(), event.y()
        if self.lclick:  # begin/add to trace if left mouse button
            if self.is_line_tracing:  # continue trace
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
            else:  # start new trace
                self.current_trace = [(x, y)]
                self.is_line_tracing = True
    
    def lineMove(self, event):
        """Called when mouse is moved in a line mode.
        
        Adds dashed lines to screen connecting the mouse pointer to the existing trace.
        """
        if self.is_line_tracing:
            closed = (self.mouse_mode == FieldWidget.CLOSEDTRACE)
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
    
    def lineRelease(self, event):
        """Called when mouse is released in line mode."""
        if self.rclick and self.is_line_tracing:  # complete existing trace if right mouse button
            closed = (self.mouse_mode == FieldWidget.CLOSEDTRACE)
            self.is_line_tracing = False
            if len(self.current_trace) > 1:
                self.newTrace(
                    self.current_trace,
                    self.tracing_trace,
                    closed=closed
                )
            else:
                self.field_pixmap = self.field_pixmap_copy.copy()
                self.update()

    
    def backspace(self):
        """Called when backspace is pressed: either delete traces or undo line trace."""
        if self.is_line_tracing and len(self.current_trace) > 1:
            closed = (self.mouse_mode == FieldWidget.CLOSEDTRACE)
            self.current_trace.pop()
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
        else:
            self.deleteTraces()
    
    def stampPress(self, event):
        """Called when mouse is pressed in stamp mode.
        
        Creates a stamp centered on the mouse location.
        """
        # get mouse coords and convert to field coords
        if self.lclick:
            pix_x, pix_y = event.x(), event.y()
            self.placeStamp(pix_x, pix_y, self.tracing_trace)
    
    def knifePress(self, event):
        """Called when mouse is pressed in knife mode.

        Begins creating a new trace.
        """
        self.last_x = event.x()
        self.last_y = event.y()
        self.knife_trace = [(self.last_x, self.last_y)]

    def knifeMove(self, event):
        """Called when mouse is moved in pencil mode with a mouse button pressed.

        Draws continued knife trace on the screen.
        """
        if self.lclick:
            # draw knife trace on pixmap
            x = event.x()
            y = event.y()
            painter = QPainter(self.field_pixmap)
            color = QColor(255,0,0)
            painter.setPen(QPen(color, 1))
            painter.drawLine(self.last_x, self.last_y, x, y)
            painter.end()
            self.knife_trace.append((x, y))
            self.last_x = x
            self.last_y = y
            self.update()

    def knifeRelease(self, event):
        """Called when mouse is released in pencil mode.

        Completes and adds trace.
        """
        if self.lclick:
            self.cutTrace(self.knife_trace)
    
    def endPendingEvents(self):
        """End ongoing events that are connected to the mouse."""
        if self.is_line_tracing:
            if len(self.current_trace) > 1:
                if self.mouse_mode == FieldWidget.CLOSEDTRACE:
                    self.section_layer.newTrace(
                        self.current_trace,
                        self.tracing_trace,
                        closed=True
                    )
                elif self.mouse_mode == FieldWidget.OPENTRACE:
                    self.section_layer.newTrace(
                        self.current_trace,
                        self.tracing_trace,
                        closed=False
                )
            self.is_line_tracing = False
            self.generateView(generate_image=False)
