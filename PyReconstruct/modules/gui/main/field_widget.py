"""The field widget."""


import os
import time

from PySide6.QtWidgets import (
    QMainWindow, 
    QWidget,
    QGestureEvent,
)
from PySide6.QtCore import (
    Qt, 
    QEvent,
    QTimer,
)
from PySide6.QtGui import (
    QPixmap, 
    QPainter, 
    QPointingDevice,
    QCursor,
    QTransform,
    QAction
)

from PyReconstruct.modules.gui.utils import get_clicked
from PyReconstruct.modules.datatypes import Series
from PyReconstruct.modules.constants import locations as loc

from .field_widget_5_mouse import (
    POINTER, 
    PANZOOM, 
    KNIFE, 
    SCISSORS, 
    CLOSEDTRACE, 
    OPENTRACE, 
    STAMP, 
    GRID, 
    FLAG, 
    HOST
)
from .field_widget_7_view import FieldWidgetView


class FieldWidget(QWidget, FieldWidgetView):
    """
    This is the final class that handles all of the GUI functions.
    """

    def __init__(self, series : Series, mainwindow : QMainWindow):
        """Create the field widget.
        
            Params:
                series (Series): the series object
                mainwindow (MainWindow): the main window that contains this widget
        """
        super().__init__(mainwindow)
        self.initAttrs(series, mainwindow)

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

        # pencil cursors
        pencil_pm = QPixmap(os.path.join(loc.img_dir, "pencil.cur"))
        self.pencil_r = QCursor(
            pencil_pm,
            hotX=5, hotY=5
        )
        self.pencil_l = QCursor(
            pencil_pm.transformed(QTransform(-1, 0, 0, 1, 0, 0)),
            hotX=pencil_pm.width()-5, hotY=5
        )

        # set up the information display widget
        self.hover_display_timer = QTimer(self)
        self.hover_display_timer.setSingleShot(True)
        self.hover_display_timer.timeout.connect(
            self.displayHoverInfo
        )

        # set up flag edit event
        self.edit_flag_event = QAction(self)
        self.edit_flag_event.triggered.connect(self.editFlag)
        self.trigger_edit_flag = False

        # set the cursor
        self.mouse_mode = POINTER
        self.setCursor(QCursor(Qt.ArrowCursor))

        self.createField(series)

        self.show()
    
    def resizeEvent(self, event):
        """Scale field window if main window size changes.
        
        Overwritten from QWidget Class.
        """
        # resize the mouse palette
        self.mainwindow.mouse_palette.resize()

        # resize the zarr palette
        if self.mainwindow.zarr_palette:
            self.mainwindow.zarr_palette.placeWidgets()
        
        # ensure field is below palettes
        self.lower()

        w = event.size().width()
        h = event.size().height()
        self.pixmap_dim = (w, h)
        self.generateView()

    def paintEvent(self, event):
        """Called when self.update() and various other functions are run.
        
        Overwritten from QWidget.
        Paints self.field_pixmap onto self (the widget).
        """
        field_painter = QPainter(self)

        # draw the field
        field_painter.drawPixmap(0, 0, self.field_pixmap)
        self.paintBorder(field_painter)
        self.paintWorkingTrace(field_painter)
        self.paintText(field_painter)

        field_painter.end()

    def event(self, event):
        """Overwritten from QWidget.event.
        
        Added to catch gestures and zorder events.
        """
        if event.type() == QEvent.Gesture:
            self.gestureEvent(event)
        elif event.type() == QEvent.ZOrderChange:
            r = super().event(event)
            self.lower()
            return r
        
        return super().event(event)

    def gestureEvent(self, event : QGestureEvent):
        """Called when gestures are detected."""
        g = event.gesture(Qt.PinchGesture)

        if g.state() == Qt.GestureState.GestureStarted:
            self.is_gesturing = True
            p = g.centerPoint()
            if os.name == "nt":
                p = self.mapFromGlobal(p)
            self.clicked_x, self.clicked_y = p.x(), p.y()
            self.panzoomPress(self.clicked_x, self.clicked_y)

        elif g.state() == Qt.GestureState.GestureUpdated:
            p = g.centerPoint()
            if os.name == "nt":
                p = self.mapFromGlobal(p)
            x, y = p.x(), p.y()
            self.panzoomMove(x, y, g.totalScaleFactor())

        elif g.state() == Qt.GestureState.GestureFinished:
            self.is_gesturing = False
            p = g.centerPoint()
            if os.name == "nt":
                p = self.mapFromGlobal(p)
            x, y = p.x(), p.y()
            self.panzoomRelease(x, y, g.totalScaleFactor())
        
    def mousePressEvent(self, event):
        """Called when mouse is clicked.
        
        Overwritten from QWidget class.
        """
        # check what was clicked
        self.lclick, self.mclick, self.rclick = get_clicked(event)

        # ignore middle clicks combined with other clicks
        if self.mclick and (self.lclick or self.rclick):
            if self.is_panzooming:
                self.lclick = False
                self.rclick = False
            else:
                self.mclick = False
            return
        # favor right click if both left and right are clicked
        if self.lclick and self.rclick:
            if not self.is_line_tracing:
                self.current_trace = []
            self.lclick = False

        self.setFocus()
        self.mouse_x = event.x()
        self.mouse_y = event.y()
        if not self.is_gesturing:
            self.clicked_x = self.mouse_x
            self.clicked_y = self.mouse_y
        self.click_time = time.time()
        self.single_click = True

        # ignore ALL finger touch for windows
        if os.name == "nt":
            if event.pointerType() == QPointingDevice.PointerType.Finger:
                return

        # if any finger touch
        if self.is_gesturing:
            return

        # pan if middle button clicked
        if self.mclick:
            self.mousePanzoomPress(event)
            return

        # pull up right-click menu if requirements met
        context_menu = (
            self.rclick and
            not (self.mouse_mode == PANZOOM) and
            not self.is_line_tracing and
            not self.hosted_trace
        )
        if context_menu:
            clicked_label = None
            if self.zarr_layer:
                clicked_label = self.zarr_layer.getID(event.x(), event.y())
            self.clicked_trace, clicked_type = self.section_layer.getTrace(event.x(), event.y())
            self.mainwindow.checkActions(context_menu=True, clicked_trace=self.clicked_trace, clicked_label=clicked_label)
            self.lclick, self.rclick, self.mclick = False, False, False
            if clicked_label:
                self.mainwindow.label_menu.exec(event.globalPos())
            elif clicked_type == "flag":
                self.trigger_edit_flag = True
            else:
                self.mainwindow.field_menu.exec(event.globalPos())
            self.mainwindow.checkActions()
            return

        if self.mouse_mode == POINTER:
            self.pointerPress(event)
        elif self.mouse_mode == PANZOOM:
            self.mousePanzoomPress(event) 
        elif self.mouse_mode == KNIFE:
            self.knifePress(event)
        elif self.mouse_mode == SCISSORS:
            self.scissorsPress(event)
        
        elif self.usingLocked():
            self.notifyLocked(self.tracing_trace.name)

        elif (
            self.mouse_mode == CLOSEDTRACE or
            self.mouse_mode == OPENTRACE
        ):
            self.tracePress(event)
        elif self.mouse_mode == STAMP:
            self.stampPress(event)
        elif self.mouse_mode == GRID:
            self.gridPress(event)
        elif self.mouse_mode == HOST:
            self.hostPress(event)

    def mouseMoveEvent(self, event):
        """Called when mouse is moved.
        
        Overwritten from QWidget class.
        """
        # keep track of position
        self.mouse_x = event.x()
        self.mouse_y = event.y()
        self.single_click = False

        # ignore ALL finger touch for windows
        if os.name == "nt":
            if event.pointerType() == QPointingDevice.PointerType.Finger:
                return

        # if any finger touch
        if self.is_gesturing:
            return
        
        # check if user is zooming with the mouse wheel
        if self.mainwindow.is_zooming:
            self.panzoomRelease(zoom_factor=self.mainwindow.zoom_factor)
            self.mainwindow.is_zooming = False
        
        # update click status
        if not event.buttons():
            self.lclick = False
            self.rclick = False
            self.mclick = False
        
        # panzoom if middle button clicked
        if self.mclick:
            self.mousePanzoomMove(event)
            return
        
        # update the screen if not pressing buttons
        if not event.buttons():
            self.update()
        
        # mouse functions
        if self.mouse_mode == POINTER:
            self.pointerMove(event)
        elif self.mouse_mode == PANZOOM:
            self.mousePanzoomMove(event)
        elif self.mouse_mode == KNIFE:
            self.knifeMove(event)

        elif self.usingLocked():
            pass
        
        elif (
            self.mouse_mode == CLOSEDTRACE or
            self.mouse_mode == OPENTRACE
        ):
            self.traceMove(event)
        elif self.mouse_mode == STAMP:
            self.stampMove(event)
        elif self.mouse_mode == HOST:
            self.hostMove(event)

    def mouseReleaseEvent(self, event):
        """Called when mouse button is released.
        
        Overwritten from QWidget Class.
        """
        # wait until all buttons are released
        if event.buttons(): return
        
        # ignore ALL finger touch for windows
        if os.name == "nt":
            if event.pointerType() == QPointingDevice.PointerType.Finger:
                return
        
        # if any finger touch
        if self.is_gesturing:
            return
        
        # panzoom if middle button
        if self.mclick:
            self.mousePanzoomRelease(event)
            self.mclick = False
            return
        
        # modify flags as requested
        if self.trigger_edit_flag:
            self.edit_flag_event.trigger()
            self.trigger_edit_flag = False
            return

        if self.mouse_mode == POINTER:
            self.pointerRelease(event)
        elif self.mouse_mode == PANZOOM:
            self.mousePanzoomRelease(event)
        elif self.mouse_mode == KNIFE:
            self.knifeRelease(event)
        elif self.mouse_mode == FLAG:
            self.flagRelease(event)

        elif self.usingLocked():
            pass

        elif (
            self.mouse_mode == CLOSEDTRACE or
            self.mouse_mode == OPENTRACE
        ):
            self.traceRelease(event)
        elif self.mouse_mode == STAMP:
            self.stampRelease(event)
        elif self.mouse_mode == GRID:
            self.gridRelease(event)
        elif self.mouse_mode == HOST:
            self.hostRelease(event)
        
        self.lclick = False
        self.rclick = False
        self.mclick = False
        self.single_click = False


