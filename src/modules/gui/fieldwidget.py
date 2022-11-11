import os

from PySide6.QtWidgets import QWidget, QMainWindow, QInputDialog, QColorDialog, QMenu
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap, QPen, QColor, QPainter
os.environ['QT_IMAGEIO_MAXALLOC'] = "0"  # disable max image size

from modules.pyrecon.series import Series
from modules.pyrecon.trace import Trace

from modules.calc.pfconversions import pixmapPointToField

from modules.backend.field_view import FieldView
from modules.backend.gui_functions import populateMenu

class FieldWidget(QWidget, FieldView):
    # mouse modes
    POINTER, PANZOOM, SCALPEL, CLOSEDPENCIL, OPENPENCIL, CLOSEDLINE, OPENLINE, STAMP = range(8)

    def __init__(self, series : Series, mainwindow : QMainWindow):
        """Create the field widget.
        
            Params:
                series (Series): the series object
                parent (MainWindow): the main window that contains this widget
        """
        QWidget.__init__(self, mainwindow)
        self.mainwindow = mainwindow
        self.setMouseTracking(True)

        # set initial geometry to match parent
        parent_rect = self.mainwindow.geometry()
        self.pixmap_dim = parent_rect.width(), parent_rect.height()-20
        self.setGeometry(0, 0, *self.pixmap_dim)

        self.createField(series)
        self.createMenus()

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
        self.status_list = ["Section: " + str(self.series.current_section)]
        self.is_line_tracing = False
        self.blend_sections = False
        self.lclick = False
        self.rclick = False

        self.generateView()
    
    def createMenus(self):
        """Create the menus for the field widget."""
        menu_list = [
            ("editname_act", "Edit trace name...", "", self.changeTraceName),
            ("editcolor_act", "Edit trace color...", "", self.changeTraceColor),
            ("edittags_act", "Edit trace tags...", "", self.changeTraceTags)
        ]
        self.context_menu = QMenu(self)
        populateMenu(self, self.context_menu, menu_list)
    
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
        if update:
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
        self.mainwindow.statusbar.showMessage(s)
    
    def changeTraceName(self):
        """Change the name of the selected traces."""
        first_name = self.section_layer.selected_traces[0].name
        for trace in self.section_layer.selected_traces[1:]:
            if trace.name != first_name:
                first_name = ""
                break

        name, confirmed = QInputDialog.getText(
            self,
            "Change Trace Name",
            "Enter the new trace name:",
            text=first_name
        )
        if not confirmed or not name:
            return
        
        self.section_layer.changeTraceAttributes(name=name)
        self.saveState()
    
    def changeTraceColor(self):
        """Change the color of the selected traces."""
        first_color = self.section_layer.selected_traces[0].color
        same_color = True
        for trace in self.section_layer.selected_traces[1:]:
            if trace.color != first_color:
                same_color = False
                break
        
        if same_color:
            c = QColorDialog.getColor(QColor(*first_color))
        else:
            c = QColorDialog.getColor()
        if not c:
            return
        color = (c.red(), c.green(), c.blue())
        self.section_layer.changeTraceAttributes(color=color)
        self.generateView()
        self.saveState()

    def changeTraceTags(self):
        """Change the tags of the selected traces."""
        # get the existing tags
        existing_tags = self.section_layer.selected_traces[0].tags
        for trace in self.section_layer.selected_traces:
            if trace.tags != existing_tags:
                existing_tags = set()
        existing_tags = ", ".join(existing_tags)

        tags, confirmed = QInputDialog.getText(
            self,
            "Change Trace Tags",
            "Enter the new tags:",
            text=existing_tags
        )
        if not confirmed or not tags:
            return
        
        tags = set(tags.split(", "))
        
        self.section_layer.changeTraceAttributes(tags=tags)
        self.saveState()
    
    def rightClickMenu(self, event):
        """Called when context mennu should be pulled up."""
        clicked_trace = self.section_layer.getTrace(event.x(), event.y())
        if clicked_trace in self.section_layer.selected_traces:
            self.context_menu.exec(event.globalPos())
        
    def mousePressEvent(self, event):
        """Called when mouse is clicked.
        
        Overwritten from QWidget class.

            Params:
                event: contains mouse input data
        """
        # check what was clicked
        self.lclick = event.buttons() == Qt.LeftButton
        self.rclick = event.buttons() == Qt.RightButton

        # pull up right-click menu if requirements met
        context_menu = True
        context_menu = (self.rclick and 
                        not self.is_line_tracing and
                        self.section_layer.selected_traces)
        if context_menu:
            self.rightClickMenu(event)   

        if self.mouse_mode == FieldWidget.POINTER:
            self.pointerPress(event)
        elif self.mouse_mode == FieldWidget.PANZOOM:
            self.panzoomPress(event) 
        elif self.mouse_mode == FieldWidget.SCALPEL:
            self.scalpelPress(event)
        elif self.mouse_mode == FieldWidget.CLOSEDPENCIL:
            self.pencilPress(event)
        elif self.mouse_mode == FieldWidget.OPENPENCIL:
            self.pencilPress(event)
        elif self.mouse_mode == FieldWidget.CLOSEDLINE:
            self.linePress(event, closed=True)
        elif self.mouse_mode == FieldWidget.OPENLINE:
            self.linePress(event, closed=False)
        elif self.mouse_mode == FieldWidget.STAMP:
            self.stampPress(event)

    def mouseMoveEvent(self, event):
        """Called when mouse is moved.
        
        Overwritten from QWidget class.
        
            Params:
                event: contains mouse input data
        """
        # update click status
        if not event.buttons():
            self.lclick = False
            self.rclick = False
        
        # update the status bar
        if (event.buttons() and self.mouse_mode == FieldWidget.PANZOOM):
            self.updateStatusBar()
        else:
            self.updateStatusBar(event)
        
        # mouse functions
        if self.mouse_mode == FieldWidget.POINTER:
                self.pointerMove(event)
        elif self.mouse_mode == FieldWidget.PANZOOM:
            self.panzoomMove(event)
        elif self.mouse_mode == FieldWidget.SCALPEL:
            self.scalpelMove(event)
        elif self.mouse_mode == FieldWidget.OPENPENCIL:
            self.pencilMove(event)
        elif self.mouse_mode == FieldWidget.CLOSEDPENCIL:
            self.pencilMove(event)
        if self.mouse_mode == FieldWidget.CLOSEDLINE:
            self.lineMove(event, closed=True)
        elif self.mouse_mode == FieldWidget.OPENLINE:
            self.lineMove(event, closed=False)

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

        Selects/deselects the nearest trace
        
            Params:
                event: contains mouse input data
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
                self.section_layer.deleteSelectedTraces()
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
        if self.lclick:
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
        elif self.rclick:
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
        if self.lclick:
            section = self.section
            x_scaling = self.pixmap_dim[0] / (self.series.window[2] / section.mag)
            y_scaling = self.pixmap_dim[1] / (self.series.window[3] / section.mag)
            move_x = -(event.x() - self.clicked_x) / x_scaling * section.mag
            move_y = (event.y() - self.clicked_y) / y_scaling * section.mag
            self.series.window[0] += move_x
            self.series.window[1] += move_y
            self.generateView()
        # set new window for zooming
        elif self.rclick:
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

    def pencilRelease(self, event, closed=True):
        """Called when mouse is released in pencil mode.

        Completes and adds trace.
        
            Params:
                event: contains mouse input data
        """
        if self.lclick:
            if len(self.current_trace) <= 1:
                return
            self.newTrace(
                self.current_trace,
                self.tracing_trace,
                closed=closed
            )
    
    def linePress(self, event, closed=True):
        """Called when mouse is pressed in a line mode.
        
        Begins create a line trace.
        
            Params:
                event: contains mouse input data
        """
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
        elif self.rclick:  # complete existing trace if right mouse button
            if self.is_line_tracing:
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
    
    def lineMove(self, event, closed=True):
        """Called when mouse is moved in a line mode.
        
        Adds dashed lines to screen connecting the mouse pointer to the existing trace.
        
            Params:
                event: contains mouse input data
        """
        if self.is_line_tracing:
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
    
    def backspace(self):
        """Called when backspace is pressed: either delete traces or undo line trace."""
        if self.is_line_tracing and len(self.current_trace) > 1:
            self.current_trace.pop()
            self.field_pixmap = self.field_pixmap_copy.copy()  # operate on original pixmap
            painter = QPainter(self.field_pixmap)
            color = QColor(*self.tracing_trace.color)
            painter.setPen(QPen(color, 1))
            if self.mouse_mode == FieldWidget.CLOSEDLINE:
                start = 0
            if self.mouse_mode == FieldWidget.OPENLINE:
                start = 1
            for i in range(start, len(self.current_trace)):
                painter.drawLine(*self.current_trace[i-1], *self.current_trace[i])
            painter.end()
            self.update()
        else:
            self.deleteSelectedTraces()
    
    def stampPress(self, event):
        """Called when mouse is pressed in stamp mode.
        
        Creates a stamp centered on the mouse location.
        
            Params:
                event: contains mouse input data
        """
        # get mouse coords and convert to field coords
        if self.lclick:
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
        if self.lclick:
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
        if self.lclick:
            self.cutTrace(self.scalpel_trace)
    
    def endPendingEvents(self):
        """End ongoing events that are connected to the mouse."""
        if self.is_line_tracing:
            if self.mouse_mode == FieldWidget.CLOSEDLINE:
                self.section_layer.newTrace(
                    self.current_trace,
                    self.tracing_trace,
                    closed=True
                )
            elif self.mouse_mode == FieldWidget.OPENLINE:
                self.section_layer.newTrace(
                    self.current_trace,
                    self.tracing_trace,
                    closed=False
            )
            self.is_line_tracing = False
            self.generateView(generate_image=False)
