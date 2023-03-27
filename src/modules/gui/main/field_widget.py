import os
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
    QEvent,
    QTimer
)
from PySide6.QtGui import (
    QPixmap, 
    QPen,
    QBrush,
    QColor,
    QFont, 
    QPainter, 
    QPainterPath,
    QPointingDevice,
    QCursor
)

from modules.datatypes import Series, Trace, Ztrace
from modules.calc import pixmapPointToField, distance
from modules.backend.view import FieldView
from modules.backend.table import (
    ObjectTableManager,
    SectionTableManager,
    TraceTableManager,
    ZtraceTableManager
)
from modules.gui.dialog import TraceDialog, ZtraceDialog
from modules.gui.utils import notify
from modules.constants import locations as loc

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

        # table defaults
        self.obj_table_manager = None
        self.ztrace_table_manager = None
        self.trace_table_manager = None
        self.section_table_manager = None

        # misc defaults
        self.current_trace = []
        self.max_click_time = 0.15
        self.mouse_x = 0
        self.mouse_y = 0

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
        if self.section_table_manager is not None:
            self.section_table_manager.close()
            self.section_table_manager = None
        
        self.series = series
        FieldView.__init__(self, series)

        # default mouse mode: pointer
        self.mouse_mode = FieldWidget.POINTER
        self.setCursor(QCursor(Qt.ArrowCursor))

        # ensure that the first section is found
        if self.series.current_section not in self.series.sections:
            self.series.current_section = self.series.sections.keys()[0]

        # establish misc defaults
        self.tracing_trace = Trace("TRACE", (255, 0, 255))
        self.status_list = ["Section: " + str(self.series.current_section)]
        self.blend_sections = False
        self.lclick = False
        self.rclick = False
        self.mclick = False

        self.erasing = False
        self.is_panzooming = False
        self.is_gesturing = False
        self.is_line_tracing = False
        self.is_moving_trace = False
        self.is_selecting_traces = False

        self.selected_trace_names = {}
        self.selected_ztrace_names = {}

        # set up the timer
        if not self.series.isWelcomeSeries():
            self.time = str(round(time.time()))
            open(os.path.join(self.series.getwdir(), self.time), "w").close()
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.markTime)
            self.timer.start(5000)

        self.generateView()
    
    def checkActions(self, context_menu=False, clicked_trace=None):
        """Check for actions that should be enabled or disabled
        
            Params:
                context_menu (bool): True if context menu is being generated
                clicked_trace (Trace): the trace that was clicked on IF the cotext menu is being generated
        """
        # if both traces and ztraces are highlighted or nothing is highlighted, only allow general field options
        if not (bool(self.section.selected_traces) ^ 
                bool(self.section.selected_ztraces)
        ):
            for a in self.mainwindow.trace_actions:
                a.setEnabled(False)
            for a in self.mainwindow.ztrace_actions:
                a.setEnabled(False)
        # if selected trace in highlighted traces
        elif ((not context_menu and self.section.selected_traces) or
              (context_menu and clicked_trace in self.section.selected_traces)
        ):
            for a in self.mainwindow.ztrace_actions:
                a.setEnabled(False)
            for a in self.mainwindow.trace_actions:
                a.setEnabled(True)
        # if selected ztrace in highlighted ztraces
        elif ((not context_menu and self.section.selected_ztraces) or
              (context_menu and clicked_trace in self.section.selected_ztraces)
        ):
            for a in self.mainwindow.trace_actions:
                a.setEnabled(False)
            for a in self.mainwindow.ztrace_actions:
                a.setEnabled(True)
        else:
            for a in self.mainwindow.trace_actions:
                a.setEnabled(False)
            for a in self.mainwindow.ztrace_actions:
                a.setEnabled(False)
        
        # check clipboard for paste options
        if self.clipboard:
            self.mainwindow.paste_act.setEnabled(True)
        else:
            self.mainwindow.paste_act.setEnabled(False)
            self.mainwindow.pasteattributes_act.setEnabled(False)
        
        # check for backup directory
        self.mainwindow.backup_act.setChecked(bool(self.series.options["backup_dir"]))

    def markTime(self):
        """Keep track of the time on the series file."""
        try:
            for f in os.listdir(self.series.getwdir()):
                if "." not in f and f.isnumeric():
                    os.remove(os.path.join(self.series.getwdir(), f))
                    break
            self.time = str(round(time.time()))
            open(os.path.join(self.series.getwdir(), self.time), "w").close()
        except FileNotFoundError:
            pass
    
    def toggleBlend(self):
        """Toggle blending sections."""
        self.blend_sections = not self.blend_sections
        self.generateView()
    
    def setViewMagnification(self):
        """Set the scaling for the section view."""
        new_mag, confirmed = QInputDialog.getText(
            self,
            "View Magnification",
            "Enter view magnification (pixels per micron):",
            text=str(round(1 / self.series.screen_mag, 6))
        )
        if not confirmed:
            return
        
        try:
            new_mag = float(new_mag)
        except ValueError:
            return
        
        self.setView(new_mag)
    
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
        try:
            self.checkActions()
        except AttributeError:
            pass
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
    
    def openSectionList(self):
        """Open a section list."""
        # create the manager is not already
        if self.section_table_manager is None:
            self.section_table_manager = SectionTableManager(
                self.series,
                self.mainwindow
            )
        # create a new table
        self.section_table_manager.newTable()
    
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

        # draw the field
        field_painter.drawPixmap(0, 0, self.field_pixmap)

        # add red border if trace layer is hidden
        if self.hide_trace_layer:
            field_painter.setPen(QPen(QColor(255, 0, 0), 8))
            w, h = self.width(), self.height()
            points = [
                (0, 0),
                (0, h),
                (w, h),
                (w, 0)
            ]
            for i in range(len(points)):
                field_painter.drawLine(*points[i-1], *points[i])
        
        # add green border if all traces are being shown
        if self.show_all_traces:
            field_painter.setPen(QPen(QColor(0, 255, 0), 8))
            w, h = self.width(), self.height()
            points = [
                (0, 0),
                (0, h),
                (w, h),
                (w, 0)
            ]
            for i in range(len(points)):
                field_painter.drawLine(*points[i-1], *points[i])

        # draw the working trace on the screen
        if self.current_trace:
            pen = None
            # if drawing lasso
            if self.mouse_mode == FieldWidget.POINTER and self.is_selecting_traces:
                closed = True
                pen = QPen(QColor(255, 255, 255), 1)
                pen.setDashPattern([4, 4])
            # if drawing knife
            elif self.mouse_mode == FieldWidget.KNIFE:
                closed = False
                pen = QPen(QColor(255, 0, 0), 1)
            # if drawing trace
            elif (
                self.mouse_mode == FieldWidget.OPENTRACE or
                self.mouse_mode == FieldWidget.CLOSEDTRACE
            ):
                closed = (self.mouse_mode == FieldWidget.CLOSEDTRACE and self.is_line_tracing)
                color = QColor(*self.tracing_trace.color)
                pen = QPen(color, 1)
            
            # draw current trace if exists
            if pen:
                field_painter.setPen(pen)
                if closed:
                    start = 0
                else:
                    start = 1
                for i in range(start, len(self.current_trace)):
                    field_painter.drawLine(*self.current_trace[i-1], *self.current_trace[i])
                # draw dashed lines that connect to mouse pointer
                if self.is_line_tracing:
                    pen.setDashPattern([2,5])
                    field_painter.setPen(pen)
                    field_painter.drawLine(*self.current_trace[-1], self.mouse_x, self.mouse_y)
                    if closed:
                        field_painter.drawLine(*self.current_trace[0], self.mouse_x, self.mouse_y)
            
        # unique method for drawing moving traces
        elif self.is_moving_trace:
            dx = self.mouse_x - self.clicked_x
            dy = self.mouse_y - self.clicked_y
            # redraw the traces with translatation
            for points, color, closed in self.moving_traces:
                field_painter.setPen(QPen(QColor(*color), 1))
                plot_points = [QPoint(x+dx, y+dy) for x,y in points]
                if closed:
                    field_painter.drawPolygon(plot_points)
                else:
                    field_painter.drawPolyline(plot_points)
            # redraw points with translation
            for (x, y), color in self.moving_points:
                field_painter.setPen(QPen(QColor(*color), 6))
                qpoint = QPoint(x+dx, y+dy)
                field_painter.drawPoint(qpoint)
        
        # get handedness from mouse palette
        left_handed = self.mainwindow.mouse_palette.left_handed
        
        # draw the name of the closest trace on the screen
        # draw the selected traces to the screen
        ct_size = 12
        st_size = 14
        if (
            not (self.lclick or self.rclick or self.mclick) and
            not self.is_gesturing
        ):
            # get closest trace
            closest_trace = self.section_layer.getTrace(self.mouse_x, self.mouse_y)
            # check for ztrace segments
            if not closest_trace:
                closest_trace = self.section_layer.getZsegment(self.mouse_x, self.mouse_y)
            
            # draw name of closest trace
            if closest_trace:
                if type(closest_trace) is Trace:
                    name = closest_trace.name
                    if closest_trace.negative:
                        name += " (negative)"
                elif type(closest_trace) is Ztrace:
                    name = f"{closest_trace.name} (ztrace)"
                # ztrace tuple returned
                elif type(closest_trace) is tuple:
                    closest_trace = closest_trace[0]
                    name = f"{closest_trace.name} (ztrace)"
                
                closest_trace
                pos = self.mouse_x, self.mouse_y
                c = closest_trace.color
                black_outline = c[0] + 3*c[1] + c[2] > 400
                drawOutlinedText(
                    field_painter,
                    *pos,
                    name,
                    c,
                    (0,0,0) if black_outline else (255,255,255),
                    ct_size,
                    left_handed
                )
        
            # get the names of the selected traces
            names = {}
            counter = 0
            height = self.height()
            for trace in self.section.selected_traces:
                # check for max number
                if counter * (st_size + 10) + 20 > height / 2:
                    names["..."] = 1
                    break
                if trace.name in names:
                    names[trace.name] += 1
                else:
                    names[trace.name] = 1
                    counter += 1
            self.selected_trace_names = names
            
            names = {}
            counter = 0
            for ztrace, i in self.section.selected_ztraces:
                # check for max number
                if counter * (st_size + 10) + 20 > height / 2:
                    names["..."] = 1
                    break
                if ztrace.name in names:
                    names[ztrace.name] += 1
                else:
                    names[ztrace.name] = 1
                    counter += 1
            self.selected_ztrace_names = names
        
        # draw the names of the selected traces
        if self.selected_trace_names:
            x = self.width() - 10 if left_handed else 10
            y = 20
            drawOutlinedText(
                field_painter,
                x, y,
                "Selected Traces:",
                (255, 255, 255),
                (0, 0, 0),
                st_size,
                not left_handed
            )
            for name, n in self.selected_trace_names.items():
                y += st_size + 10
                if n == 1:
                    text = name
                else:
                    text = f"{name} * {n}"
                drawOutlinedText(
                    field_painter,
                    x, y,
                    text,
                    (255, 255, 255),
                    (0, 0, 0),
                    st_size,
                    not left_handed
                )
        
        # draw the names of the selected ztraces
        if self.selected_ztrace_names:
            if not self.selected_trace_names:
                x = self.width() - 10 if left_handed else 10
                y = 20
            else:
                y += st_size + 20
            drawOutlinedText(
                field_painter,
                x, y,
                "Selected Ztraces:",
                (255, 255, 255),
                (0, 0, 0),
                st_size,
                not left_handed
            )
            for name, n in self.selected_ztrace_names.items():
                y += st_size + 10
                if n == 1:
                    text = name
                else:
                    text = f"{name} * {n}"
                drawOutlinedText(
                    field_painter,
                    x, y,
                    text,
                    (255, 255, 255),
                    (0, 0, 0),
                    st_size,
                    not left_handed
                )
        
        field_painter.end()

        # update the status bar
        if not self.is_panzooming:
            self.updateStatusBar()
    
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
    
    def updateStatusBar(self):
        """Update status bar with useful information.
        
            Params:
                event: contains data on mouse position
        """
        self.status_list = []

        # display current section
        section = "Section: " + str(self.series.current_section)
        self.status_list.append(section)

        # display the alignment setting
        alignment = "Alignment: " + self.series.alignment
        self.status_list.append(alignment)

        # display mouse position in the field
        x, y = pixmapPointToField(
            self.mouse_x, 
            self.mouse_y, 
            self.pixmap_dim, 
            self.series.window, 
            self.section.mag
        )
        position = "x = " + str("{:.4f}".format(x)) + ", "
        position += "y = " + str("{:.4f}".format(y))
        self.status_list.append(position)
        
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
        # do not run if both types of traces are selected or none are selected
        if bool(self.section.selected_traces) ^ bool(self.section.selected_ztraces):
            return
        # run the ztrace dialog if only ztraces selected
        elif self.section.selected_ztraces:
            self.ztraceDialog()
            return
        
        new_attr, confirmed = TraceDialog(
            self,
            self.section.selected_traces,
        ).exec()
        if not confirmed:
            return
        
        name, color, tags, mode = new_attr
        self.section.editTraceAttributes(
            traces=self.section.selected_traces,
            name=name,
            color=color,
            tags=tags,
            mode=mode
        )

        self.generateView(generate_image=False)
        self.saveState() 

    def ztraceDialog(self):
        """Opens a dialog to edit selected traces."""
        if not self.section.selected_ztraces:
            return
        
        # check only one ztrace selected
        first_ztrace, i = self.section.selected_ztraces[0]
        for ztrace, i in self.section.selected_ztraces:
            if ztrace != first_ztrace:
                notify("Please modify only one ztrace at a time.")
                return
        
        name = first_ztrace.name
        color = first_ztrace.color
        new_attr, confirmed = ZtraceDialog(
            self,
            name,
            color
        ).exec()
        if not confirmed:
            return
        
        new_name, new_color = new_attr
        self.series.editZtraceAttributes(
            ztrace,
            new_name,
            new_color
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
        elif mode == FieldWidget.KNIFE:
            cursor = QCursor(
                QPixmap(os.path.join(loc.img_dir, "knife.cur")),
                hotX=5, hotY=5
            )
        elif (mode == FieldWidget.OPENTRACE or
              mode == FieldWidget.CLOSEDTRACE):
            cursor = QCursor(
                QPixmap(os.path.join(loc.img_dir, "pencil.cur")),
                hotX=5, hotY=5
            )
        elif mode == FieldWidget.STAMP:
            cursor = QCursor(Qt.CrossCursor)
        self.setCursor(cursor)
    
    def setTracingTrace(self, trace : Trace):
        """Set the trace used by the pencil/line tracing/stamp.
        
            Params:
                trace (Trace): the new trace to use as refernce for further tracing
        """
        self.endPendingEvents()
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
            self.is_gesturing = True
            p = self.mapFromGlobal(g.centerPoint())
            x, y = p.x(), p.y()
            self.panzoomPress(x, y)

        elif g.state() == Qt.GestureState.GestureUpdated:
            p = self.mapFromGlobal(g.centerPoint())
            x, y = p.x(), p.y()
            self.panzoomMove(x, y, g.totalScaleFactor())

        elif g.state() == Qt.GestureState.GestureFinished:
            self.is_gesturing = False
            p = self.mapFromGlobal(g.centerPoint())
            x, y = p.x(), p.y()
            self.panzoomRelease(x, y, g.totalScaleFactor())
        
    def mousePressEvent(self, event):
        """Called when mouse is clicked.
        
        Overwritten from QWidget class.
        """
        self.mouse_x = event.x()
        self.mouse_y = event.y()
        self.click_time = time.time()

        # ignore ALL finger touch for windows
        if os.name == "nt":
            if event.pointerType() == QPointingDevice.PointerType.Finger:
                return


        # if any finger touch
        if self.is_gesturing:
            return
        
        # if any eraser touch
        if event.pointerType() == QPointingDevice.PointerType.Eraser:
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
            self.checkActions(context_menu=True, clicked_trace=clicked_trace)
            self.mainwindow.field_menu.exec(event.globalPos())
            self.checkActions()
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
        # keep track of position
        self.mouse_x = event.x()
        self.mouse_y = event.y()

        # ignore ALL finger touch for windows
        if os.name == "nt":
            if event.pointerType() == QPointingDevice.PointerType.Finger:
                return

        # if any finger touch
        if self.is_gesturing:
            return
        
        # if any eraser touch
        elif event.pointerType() == QPointingDevice.PointerType.Eraser:
            self.eraserMove(event)
        
        # check if user is zooming with the mouse wheel
        if self.mainwindow.is_zooming:
            self.panzoomRelease(zoom_factor=self.mainwindow.zoom_factor)
            self.mainwindow.is_zooming = False
        
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
        
        # update the screen if not pressing buttons
        if not event.buttons():
            self.update()
        
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
        # ignore ALL finger touch for windows
        if os.name == "nt":
            if event.pointerType() == QPointingDevice.PointerType.Finger:
                return
        
        # if any finger touch
        if self.is_gesturing:
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
        elif self.mouse_mode == FieldWidget.STAMP:
            self.stampRelease(event)
        
        self.lclick = False
        self.rclick = False
        self.mclick = False
    
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
        # ignore if not clicking
        if not self.lclick:
            return
        
        # keep track of possible lasso if insufficient time has passed
        if (time.time() - self.click_time <= self.max_click_time):
            self.current_trace.append((event.x(), event.y()))
            return
        
        # left button is down and user clicked on a trace
        if (
            self.is_moving_trace or 
            self.selected_trace in self.section.selected_traces or
            self.selected_trace in self.section.selected_ztraces
        ): 
            if not self.is_moving_trace:  # user has just decided to move the trace
                self.is_moving_trace = True
                # clear lasso trace
                self.current_trace = []
                # get pixel points
                self.moving_traces = []
                self.moving_points = []
                for trace in self.section.selected_traces:
                    # hide the trace
                    self.section.temp_hide.append(trace)
                    # get points and other data
                    pix_points = self.section_layer.traceToPix(trace)
                    color = trace.color
                    closed = trace.closed
                    self.moving_traces.append((pix_points, color, closed))
                for ztrace, i in self.section.selected_ztraces:
                    # hide the ztrace
                    self.section.temp_hide.append(ztrace)
                    # get points and other data
                    point = ztrace.points[i][:2]
                    pix_point = self.section_layer.pointToPix(point)
                    color = ztrace.color
                    self.moving_points.append((pix_point, color))

                self.generateView(update=False)
            
            self.update()

        # no trace was clicked on OR user clicked on unselected trace
        # draw lasso for selecting traces
        else:
            if not self.is_selecting_traces:  # user just decided to group select traces
                self.is_selecting_traces = True
            x = event.x()
            y = event.y()
            self.current_trace.append((x, y))
            # draw the trace on the screen
            self.update()
    
    def pointerRelease(self, event):
        """Called when mouse is released in pointer mode."""

        # user single-clicked a trace
        if ((time.time() - self.click_time <= self.max_click_time) and 
        self.lclick and self.selected_trace
        ):
            # if user selected a normal trace
            if type(self.selected_trace) is Trace:
                self.selectTrace(self.selected_trace)
            # if user selected a ztrace
            elif type(self.selected_trace)is tuple:
                self.selectZtrace(self.selected_trace)
        
        # user moved traces
        elif self.lclick and self.is_moving_trace:
            # unhide the traces
            self.section.temp_hide = []
            # save the traces in their final position
            self.is_moving_trace = False
            dx = (event.x() - self.clicked_x) * self.series.screen_mag
            dy = (event.y() - self.clicked_y) * self.series.screen_mag * -1
            self.section.translateTraces(dx, dy)
            self.generateView(update=False)
            self.saveState()
        
        # user selected an area (lasso) of traces
        elif self.lclick and self.is_selecting_traces:
            self.is_selecting_traces = False
            selected = self.section_layer.getTraces(self.current_trace)
            if selected:
                traces, ztraces = selected
                self.selectTraces(traces, ztraces)
        
        # clear any traces made
        self.current_trace = []
        self.update()
    
    def eraserMove(self, event):
        """Called when the user is erasing."""
        if not self.erasing:
            return
        erased = self.section_layer.eraseArea(event.x(), event.y())
        if erased:
            self.generateView(generate_image=False)
            self.saveState()
    
    def panzoomPress(self, x, y):
        """Initiates panning and zooming mode.
        
            Params:
                x: the x position of the start
                y: the y position of the start
        """
        self.clicked_x = x
        self.clicked_y = y
        self.field_pixmap_copy = self.field_pixmap.copy()
        
    def mousePanzoomPress(self, event):
        """Called when mouse is clicked in panzoom mode.
        
        Saves the position of the mouse.
        """
        if self.mainwindow.is_zooming:
            return
        self.panzoomPress(event.x(), event.y())
    
    def panzoomMove(self, new_x=None, new_y=None, zoom_factor=1):
        """Generates image output for panning and zooming.
        
            Params:
                new_x: the x from panning
                new_y: the y from panning
                zoom_factor: the scale from zooming
        """
        self.is_panzooming = True
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
        if self.mainwindow.is_zooming:
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
        
        self.is_panzooming = False        
        self.generateView()

    def mousePanzoomRelease(self, event):
        """Called when mouse is released in panzoom mode."""
        if self.mainwindow.is_zooming:
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
            self.last_x = event.x()
            self.last_y = event.y()
            self.current_trace = [(self.last_x, self.last_y)]
    
    def traceMove(self, event):
        """Called when mouse is moved in trace mode."""
        if self.is_line_tracing:
            self.update()
        else:
            self.pencilMove(event)
    
    def traceRelease(self, event):
        """Called when mouse is released in trace mode."""
        # user is already line tracing
        if self.is_line_tracing:
            self.lineRelease(event)
        # user decided to line trace
        elif len(self.current_trace) == 1 or (time.time() - self.click_time <= self.max_click_time):
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
            self.current_trace = []
    
    def linePress(self, event):
        """Called when mouse is pressed in a line mode.
        
        Begins create a line trace.
        """
        x, y = event.x(), event.y()
        if self.lclick:  # begin/add to trace if left mouse button
            if self.is_line_tracing:  # continue trace
                self.current_trace.append((x, y))
                self.update()
            else:  # start new trace
                self.current_trace = [(x, y)]
                self.is_line_tracing = True
    
    def lineRelease(self, event):
        """Called when mouse is released in line mode."""
        if self.rclick and self.is_line_tracing:  # complete existing trace if right mouse button
            closed = (self.mouse_mode == FieldWidget.CLOSEDTRACE)
            self.is_line_tracing = False
            if len(self.current_trace) > 1:
                current_trace_copy = self.current_trace.copy()
                self.current_trace = []
                self.newTrace(
                    current_trace_copy,
                    self.tracing_trace,
                    closed=closed
                )
            else:
                self.current_trace = []
                self.update()
    
    def backspace(self):
        """Called when backspace OR Del is pressed: either delete traces or undo line trace."""
        if self.is_line_tracing and len(self.current_trace) > 1:
            self.current_trace.pop()
            self.update()
        elif len(self.current_trace) == 1:
            self.is_line_tracing = False
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
    
    def stampRelease(self, event):
        """Called when mouse is released in stamp mode."""
        self.update()
    
    def knifePress(self, event):
        """Called when mouse is pressed in knife mode.

        Begins creating a new trace.
        """
        self.last_x = event.x()
        self.last_y = event.y()
        self.current_trace = [(self.last_x, self.last_y)]

    def knifeMove(self, event):
        """Called when mouse is moved in pencil mode with a mouse button pressed.

        Draws continued knife trace on the screen.
        """
        if self.lclick:
            # draw knife trace on pixmap
            x = event.x()
            y = event.y()
            self.current_trace.append((x, y))
            self.update()

    def knifeRelease(self, event):
        """Called when mouse is released in pencil mode.

        Completes and adds trace.
        """
        if self.lclick:
            self.cutTrace(self.current_trace)
        self.current_trace = []
        self.update()
    
    def endPendingEvents(self):
        """End ongoing events that are connected to the mouse."""
        if self.is_line_tracing or self.current_trace:
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
            self.current_trace = []
            self.generateView(generate_image=False)


def drawOutlinedText(painter : QPainter, x : int, y : int, text : str, c1 : tuple, c2 : tuple, size : int, left_justified=True):
    """Draw outlined text using a QPainter object.
    
        Params:
            painter (QPainter): the QPainter object to use
            x (int): the x-pos of the text
            y (int): the y-pos of the text
            text (str): the text to write to the screen
            c1 (tuple): the primary color of the text
            c2 (tuple): the outline color of the text
            size (int): the size of the text
            left_justified (bool): True if text is left justified
    """
    # add justification
    if not left_justified:
        x -= int(len(text) * (size * 0.812))
    
    w = 1  # outline thickness
    path = QPainterPath()
    font = QFont("Courier New", size, QFont.Bold)
    path.addText(x, y, font, text)

    pen = QPen(QColor(*c2), w * 2)
    brush = QBrush(QColor(*c1))
    painter.strokePath(path, pen)
    painter.fillPath(path, brush)
