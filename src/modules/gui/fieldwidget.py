import os

from PySide6.QtWidgets import (QWidget, QMainWindow)
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (QPixmap, QImage, QPen, QColor, QTransform, QPainter)
os.environ['QT_IMAGEIO_MAXALLOC'] = "0"  # disable max image size

from modules.recon.section import Section
from modules.recon.trace import Trace

from modules.calc.grid import getExterior, mergeTraces, reducePoints, cutTraces
from modules.calc.quantification import getDistanceFromTrace

class FieldWidget(QWidget):
    # mouse modes
    POINTER, PANZOOM, SCALPEL, CLOSEDPENCIL, OPENPENCIL, CLOSEDLINE, OPENLINE, STAMP = range(8)

    def __init__(self, section_num : int, section : Section, window : list, parent : QMainWindow):
        """Create the field widget.
        
            Params:
                section_num (int): the section number (to display in the status bar)
                section (Section): the Section object containing the section data (tform, traces, etc)
                window (list): x, y, w, h of window in FIELD COORDINATES
                parent (MainWindow): the main window that contains this widget
        """
        super().__init__(parent)
        self.parent_widget = parent
        self.setMouseTracking(True)

        # set initial geometry to match parent
        parent_rect = self.parent_widget.geometry()
        self.pixmap_size = parent_rect.width(), parent_rect.height()-20
        self.setGeometry(0, 0, *self.pixmap_size)

        self.loadSeries(section_num, section, window)
        self.show()
    
    def loadSeries(self, section_num : int, section : Section, window : list):
        """Load a new series.

            Params:
                section_num (int): the section number (to display in the status bar)
                section (Section): the Section object containing the section data (tform, traces, etc)
                window (list): x, y, w, h of window in FIELD COORDINATES
        """
        # default mouse mode: pointer
        self.mouse_mode = FieldWidget.POINTER

        # set window from previous data
        self.current_window = window

        # establish misc defaults
        self.selected_traces = []
        self.tracing_trace = Trace("TRACE", (255, 0, 255))
        self.is_line_tracing = False
        self.all_traces_hidden = False

        self.loadSection(section_num, section)
    
    def loadSection(self, section_num : int, section : Section):
        """Load a new section into the field.
        
            Params:
                section_num (int): the section number
                section (Section): the Section object containing the section data
        """
        self.endPendingEvents()
        self.section_num = section_num

        # get data from section info
        self.mag = section.mag
        self.src = section.src

        # create transforms
        self.loadTransformation(section.tform.copy(), update=False, save_state=False)

        # create traces
        self.traces = section.traces.copy()
        for trace in self.traces:  # temporary
            trace.setHidden(False)
        self.selected_traces = []

        # reset undo-redo states
        self.current_state = [self.traces.copy(), self.tform.copy()]
        self.undo_states = []
        self.redo_states = []

        self.updateStatusBar(None)
        self.generateView()
        self.update()
    
    def loadTransformation(self, tform : list, update=True, save_state=True):
        """Load the transformation data for a given section image
        
            Params:
                tform (list): the image transform as a list (identity: 1 0 0 0 1 0)"""
        # create transforms
        self.tform = tform
        t = self.tform # identity would be: 1 0 0 0 1 0
        self.point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5]) # normal matrix for points
        self.image_tform = QTransform(t[0], -t[3], -t[1], t[4], t[2], t[5]) # changed positions for image tform
        self.base_image = QImage(self.parent_widget.wdir + self.src) # load image
        self.tformed_image = self.base_image.transformed(self.image_tform) # transform image
        # in order to place the image correctly in the field...
        self.tform_origin = self.calcTformOrigin(self.base_image, self.image_tform) # find the coordinates of the tformed image origin (bottom left corner)
        x_shift = t[2] - self.tform_origin[0] * self.mag # calculate x translation for image placement in field
        y_shift = t[5] - (self.tformed_image.height() - self.tform_origin[1]) * self.mag # calculate y translation for image placement in field
        self.image_vector = x_shift, y_shift # store as vector
        if update:
            self.updateStatusBar(None)
            self.generateView()
            self.update()
        if save_state:
            self.saveState()
    
    def changeBrightness(self, change):
        """Change the brightness of the section.
        
        Not implemented yet."""
        return
    
    def generateView(self, generate_image=True):
        """Generate the view seen by the user in the main window.
        
            Params:
                generate_image (bool): whether or not to redraw the image
            This function uses the values of self.current_window to adjust the view.
            This attribute is expected to be changed outside of this function.
        """
        # get dimensions of field window and pixmap
        # resize last known window to match proportions of current geometry
        window_x, window_y, window_w, window_h = tuple(self.current_window)
        pixmap_w, pixmap_h = tuple(self.pixmap_size)
        window_ratio = window_w/window_h
        pixmap_ratio = pixmap_w / pixmap_h
        if abs(window_ratio - pixmap_ratio) > 1e-5:
            if window_ratio < pixmap_ratio:  # increase the width
                new_w = window_h * pixmap_ratio
                new_x = window_x - (new_w - window_w) / 2
                window_w = new_w
                window_x = new_x
            else: # increase the height
                new_h = window_w / pixmap_ratio
                new_y = window_y - (new_h - window_h) / 2
                window_h = new_h
                window_y = new_y
            self.current_window = [window_x, window_y, window_w, window_h]
        if generate_image:
            # scaling: ratio of actual image dimensions to main window dimensions (should be equal)
            self.x_scaling = pixmap_w / (window_w / self.mag)
            self.y_scaling = pixmap_h / (window_h / self.mag)

            # create empty window
            self.field_pixmap = QPixmap(pixmap_w, pixmap_h)
            self.field_pixmap.fill(QColor(0, 0, 0))

            # get the coordinates to crop the image pixmap
            crop_left = (window_x - self.image_vector[0]) / self.mag
            left_empty = -crop_left if crop_left < 0 else 0
            crop_left = 0 if crop_left < 0 else crop_left

            crop_top = (window_y - self.image_vector[1] + window_h) / self.mag
            image_height = self.tformed_image.size().height()
            top_empty = (crop_top - image_height) if crop_top > image_height else 0
            crop_top = image_height if crop_top > image_height else crop_top
            crop_top = image_height - crop_top

            crop_right = (window_x - self.image_vector[0] + window_w) / self.mag
            image_width = self.tformed_image.size().width()
            crop_right = image_width if crop_right > image_width else crop_right

            crop_bottom = (window_y - self.image_vector[1]) / self.mag
            crop_bottom = 0 if crop_bottom < 0 else crop_bottom
            crop_bottom = image_height - crop_bottom

            crop_w = crop_right - crop_left
            crop_h = crop_bottom - crop_top

            # put the transformed image on the empty window
            painter = QPainter(self.field_pixmap)
            painter.drawImage(QRectF(left_empty * self.x_scaling, top_empty * self.y_scaling,
                                crop_w * self.x_scaling, crop_h * self.y_scaling),
                                self.tformed_image,
                                QRectF(crop_left, crop_top, crop_w, crop_h))
            painter.end()

            self.image_layer = self.field_pixmap.copy()
        else:
            self.field_pixmap = self.image_layer.copy()
        
        # draw all the traces
        self.traces_within_field = []
        for trace in self.traces:
            if not trace.hidden:
                within_field = self.drawTrace(trace)
                if within_field:
                    self.traces_within_field.append(trace)
        for trace in self.selected_traces:
            self.drawTrace(trace, highlight=True)
        
        self.field_pixmap_copy = self.field_pixmap.copy()
    
    def pixmapPointToField(self, x : float, y : float) -> tuple:
        """Convert main window pixmap coordinates to field window coordinates.
        
            Params:
                x (float): x-value for pixmap point
                y (float): y-value for pixmap point
            Returns:
                (tuple) converted point in field coordinates
        """
        x = x / self.x_scaling * self.mag + self.current_window[0]
        y = (self.pixmap_size[1] - y) / self.y_scaling * self.mag  + self.current_window[1]

        return x, y
    
    def fieldPointToPixmap(self, x : float, y : float) -> tuple:
        """Convert field window coordinates to main window pixmap coordinates.
        
            Params:
                x (float): x-value for field point
                y (float): y-value for field point
            Returns:
                (tuple) converted point in pixmap coordinates
        """
        x = (x - self.current_window[0]) / self.mag * self.x_scaling
        y = (y - self.current_window[1])/ self.mag * self.y_scaling
        y = self.pixmap_size[1] - y

        return round(x), round(y)
    
    def drawTrace(self, trace : Trace, highlight=False) -> bool:
        """Draw a trace on the current trace layer and return bool indicating if trace is in the current view.
        
            Params:
                trace (Trace): the trace to draw on the pixmap
                highlight (bool): whether or not the trace is being highlighted
            Returns:
                (bool) if the trace is within the current field window view
        """
        # set up painter
        painter = QPainter(self.field_pixmap)
        within_field = False
        if highlight: # create dashed white line if trace is to be highlighted
            pen = QPen(QColor(255, 255, 255), 1)
            pen.setDashPattern([2, 5])
            painter.setPen(pen)
            # # internal use: draw highlight as points
            # painter.setPen(QPen(QColor(255, 255, 255), 5))
            # for point in trace.points:
            #     x, y = self.point_tform.map(*point)
            #     x, y = self.fieldPointToPixmap(x,y)
            #     painter.drawPoint(x,y)
            # painter.end()
            # return
            # # end internal use
        else:
            painter.setPen(QPen(QColor(*trace.color), 1))
        
        # initialize window contour
        window_contour = [(0, 0), (self.pixmap_size[0], 0), (self.pixmap_size[0], self.pixmap_size[1]),
                         (0, self.pixmap_size[1])]

        # establish first point
        point = trace.points[0]
        last_x, last_y = self.point_tform.map(*point)
        last_x, last_y = self.fieldPointToPixmap(last_x, last_y)
        within_field |= 0 < last_x < self.pixmap_size[0] and 0 < last_y < self.pixmap_size[1]
        # connect points
        for i in range(1, len(trace.points)):
            point = trace.points[i]
            x, y = self.point_tform.map(*point)
            x, y = self.fieldPointToPixmap(x, y)
            within_field |= 0 < x < self.pixmap_size[0] and 0 < y < self.pixmap_size[1]
            painter.drawLine(last_x, last_y, x, y)
            # within_field |= lineIntersectsContour(last_x, last_y, x, y, window_contour)
            last_x = x
            last_y = y
        # connect last point to first point if closed
        if trace.closed:
            point = trace.points[0]
            x, y = self.point_tform.map(*point)
            x, y = self.fieldPointToPixmap(x,y)
            painter.drawLine(last_x, last_y, x, y)
            # within_field |= lineIntersectsContour(last_x, last_y, x, y, window_contour)
        painter.end()

        return within_field
    
    def calcTformOrigin(self, base_pixmap : QPixmap, tform : QTransform) -> tuple:
        """Calculate the vector for the bottom left corner of a transformed image.
        
            Params:
                base_pixmap (QPixmap): untransformed image
                tform (QTransform): transform to apply to the image
            Returns:
                (tuple) the bottom left corner coordinates of the transformed image
        """
        base_coords = base_pixmap.size() # base image dimensions
        tform_notrans = self.tformNoTrans(tform) # get tform without translation
        height_vector = tform_notrans.map(0, base_coords.height()) # create a vector for base height and transform
        width_vector = tform_notrans.map(base_coords.width(), 0) # create a vector for base width and transform
        # calculate coordinates for the top left corner of image
        if height_vector[0] < 0:
            x_orig_topleft = -height_vector[0]
        else:
            x_orig_topleft = 0
        if width_vector[1] < 0:
            y_orig_topleft = -width_vector[1]
        else:
            y_orig_topleft = 0
        # calculate coordinates for the bottom left corner of the image
        x_orig_bottomleft = x_orig_topleft + height_vector[0]
        y_orig_bottomleft = y_orig_topleft + height_vector[1]

        return x_orig_bottomleft, y_orig_bottomleft
    
    def tformNoTrans(self, tform : QTransform) -> QTransform:
        """Return a transfrom without a translation component.
        
            Params:
                tform (QTransform): the reference transform
            Returns:
                (QTransform) the reference transform without a translation component
        """
        tform_notrans = (tform.m11(), tform.m12(), tform.m21(), tform.m22(), 0, 0)
        tform_notrans = QTransform(*tform_notrans)

        return tform_notrans
    
    def updateStatusBar(self, event, find_closest_trace=True):
        """Update status bar with useful information.
        
            Params:
                event: contains data on mouse position
        """
        if event is not None:
            s = "Section: " + str(self.section_num) + "  |  "
            x, y = event.pos().x(), event.pos().y()
            x, y = self.pixmapPointToField(x, y)
            s += "x = " + str("{:.4f}".format(x)) + ", "
            s += "y = " + str("{:.4f}".format(y)) + "  |  "
            s += "Tracing: " + '"' + self.tracing_trace.name + '"'
            if find_closest_trace:
                closest_trace = self.findClosestTrace(x, y)
                if closest_trace:
                    s += "  |  Nearest trace: " + closest_trace.name
        else:
            message = self.parent_widget.statusbar.currentMessage()
            s = "Section: " + str(self.section_num) + "  " + message[message.find("|"):]
        self.parent_widget.statusbar.showMessage(s)
    
    def saveState(self):
        """Save the current traces and transform."""
        self.undo_states.append(self.current_state)
        if len(self.undo_states) > 20:  # limit the number of undo states
            self.undo_states.pop(0)
        self.current_state = [self.traces.copy(), self.tform.copy()]
        self.redo_states = []
    
    def restoreState(self):
        """Restore traces and transform stored in the current state (self.current_state)."""
        self.traces = self.current_state[0].copy()
        prev_tform = self.tform.copy()
        new_tform = self.current_state[1]
        if new_tform != prev_tform:
            self.loadTransformation(new_tform, save_state=False)
        self.selected_traces = []
        self.generateView()
        self.update()

    def undoState(self):
        """Undo last action (switch to last state)."""
        if len(self.undo_states) >= 1:
            self.redo_states.append(self.current_state)
            self.current_state = self.undo_states.pop()
            self.restoreState()
    
    def redoState(self):
        """Redo an undo (switch to last undid state)."""
        if len(self.redo_states) >= 1:
            self.undo_states.append(self.current_state)
            self.current_state = self.redo_states.pop()
            self.restoreState()
    
    def newTrace(self, pix_trace : list, name="", color=(), closed=True):
        """Create a new trace from pixel coordinates.
        
            Params:
                pix_trace (list): pixel coordinates for the new trace
                closed (bool): whether or not the new trace is closed"""
        if name == "":
            name = self.tracing_trace.name
        if color == ():
            color = self.tracing_trace.color
        if len(pix_trace) > 1:  # do not create a new trace if there is only one point
            if closed:
                pix_trace = getExterior(pix_trace)  # get exterior if closed (will reduce points)
            else:
                pix_trace = reducePoints(pix_trace, closed=False)  # only reduce points if trace is open
            new_trace = Trace(name, color, closed=closed)
            for point in pix_trace:
                field_point = self.pixmapPointToField(*point)
                rtform_point = self.point_tform.inverted()[0].map(*field_point) # apply the inverse tform to fix trace to base image
                new_trace.add(rtform_point)
            self.traces.append(new_trace)
            self.selected_traces.append(new_trace)
    
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
        self.pixmap_size = (w, h)
        self.generateView()
        self.update()
    
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
        field_x, field_y = self.pixmapPointToField(pix_x, pix_y)
        select_radius = max(self.pixmap_size) / 25 * self.mag / self.x_scaling # set radius to be 4% of widget length
        selected_trace = self.findClosestTrace(field_x, field_y, select_radius)
        # select and highlight trace if left mouse click
        if selected_trace is not None and event.button() == Qt.LeftButton:
            if not selected_trace in self.selected_traces:
                self.selected_traces.append(selected_trace)
                self.generateView(generate_image=False)
                self.update()
        # deselect and unhighlight trace if right mouse click
        elif selected_trace is not None and event.button() == Qt.RightButton:
            if selected_trace in self.selected_traces:
                self.selected_traces.remove(selected_trace)
                self.generateView(generate_image=False)
                self.update()
    
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
            new_field = QPixmap(*self.pixmap_size)
            new_field.fill(QColor(0, 0, 0))
            painter = QPainter(new_field)
            painter.drawPixmap(move_x, move_y, *self.pixmap_size, self.field_pixmap_copy)
            self.field_pixmap = new_field
            painter.end()
            self.update()
        # if right mouse button is pressed, do zooming
        elif event.buttons() == Qt.RightButton:
            # up and down mouse movement only
            move_y = event.y() - self.clicked_y
            zoom_factor = 1.005 ** (move_y) # 1.005 is arbitrary
            # calculate new geometry of window based on zoom factor
            xcoef = (self.clicked_x / self.pixmap_size[0]) * 2
            ycoef = (self.clicked_y / self.pixmap_size[1]) * 2
            w = self.pixmap_size[0] * zoom_factor
            h = self.pixmap_size[1] * zoom_factor
            x = (self.pixmap_size[0] - w) / 2 * xcoef
            y = (self.pixmap_size[1] - h) / 2 * ycoef
            # adjust field
            new_field = QPixmap(*self.pixmap_size)
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
            move_x = -(event.x() - self.clicked_x) / self.x_scaling * self.mag
            move_y = (event.y() - self.clicked_y) / self.y_scaling * self.mag
            self.current_window[0] += move_x
            self.current_window[1] += move_y
            self.generateView()
            self.update()
        # set new window for zooming
        elif event.button() == Qt.RightButton:
            move_y = event.y() - self.clicked_y
            zoom_factor = 1.005 ** (move_y)
            # calculate pixel equivalents for window view
            xcoef = (self.clicked_x / self.pixmap_size[0]) * 2
            ycoef = (self.clicked_y / self.pixmap_size[1]) * 2
            w = self.pixmap_size[0] * zoom_factor
            h = self.pixmap_size[1] * zoom_factor
            x = (self.pixmap_size[0] - w) / 2 * xcoef
            y = (self.pixmap_size[1] - h) / 2 * ycoef
            # convert pixel equivalents to field coordinates
            window_x = - x  / self.x_scaling / zoom_factor * self.mag 
            window_y = - (self.pixmap_size[1] - y - self.pixmap_size[1] * zoom_factor)  / self.y_scaling / zoom_factor * self.mag
            self.current_window[0] += window_x
            self.current_window[1] += window_y
            self.current_window[2] /= zoom_factor
            # set limit on how far user can zoom in
            if self.current_window[2] < self.mag:
                self.current_window[2] = self.mag
            self.current_window[3] /= zoom_factor
            if self.current_window[3] < self.mag:
                self.current_window[3] = self.mag
            self.generateView()
            self.update()
    
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
        self.newTrace(self.current_trace, closed=closed)
        self.saveState()
        self.generateView(generate_image=False)
        self.update()
    
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
                if closed:
                    self.newTrace(self.current_trace, closed=True)
                else:
                    self.newTrace(self.current_trace, closed=False)
                self.is_line_tracing = False
                self.saveState()
                self.generateView(generate_image=False)
                self.update()
    
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
        field_x, field_y = self.pixmapPointToField(pix_x, pix_y)
        # create stamp new trace
        new_trace = Trace(self.tracing_trace.name, self.tracing_trace.color)
        for point in self.tracing_trace.points:
            field_point = (point[0] + field_x, point[1] + field_y)
            rtform_point = self.point_tform.inverted()[0].map(*field_point)  # fix the coords to image
            new_trace.add(rtform_point)
        self.traces.append(new_trace)
        self.selected_traces.append(new_trace)
        self.saveState()
        self.generateView(generate_image=False)
        self.update()
    
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

    def scalpelRelease(self, event, closed=True):
        """Called when mouse is released in pencil mode.

        Completes and adds trace.
        
            Params:
                event: contains mouse input data
        """
        if len(self.selected_traces) == 0:
            print("Please select traces you wish to cut.")
            self.generateView(generate_image=False)
            self.update()
            return
        elif len(self.selected_traces) > 1:
            print("Please select only one trace to cut at a time.")
            self.generateView(generate_image=False)
            self.update()
            return
        trace = self.selected_traces[0]
        name = trace.name
        color = trace.color
        trace_to_cut = []
        for point in self.selected_traces[0].points:
            p = self.point_tform.map(*point)
            p = self.fieldPointToPixmap(*p)
            trace_to_cut.append(p)
        cut_traces = cutTraces(trace_to_cut, self.scalpel_trace)  # merge the pixel traces
        # create new traces
        self.deleteSelectedTraces(save_state=False)
        for trace in cut_traces:
            self.newTrace(trace, name=name, color=color)
        self.saveState()
        self.generateView(generate_image=False)
        self.update()
    
    def findTrace(self, trace_name : str, occurence=1):
        """Focus the window view on a given trace.
        
            Params:
                trace_name (str): the name of the trace to focus on
                occurence (int): find the nth trace on the section"""
        count = 0
        for trace in self.traces:
            if trace.name == trace_name:
                count += 1
                if count == occurence:
                    min_x, min_y, max_x, max_y = trace.getBounds(self.point_tform)
                    range_x = max_x - min_x
                    range_y = max_y - min_y
                    self.current_window = [min_x - range_x/2, min_y - range_y/2, range_x * 2, range_y * 2]
                    self.selected_traces = [trace]
                    self.saveState()
                    self.generateView()
                    self.update()
                
    def deselectAllTraces(self):
        """Deselect all traces."""
        self.selected_traces = []
        self.generateView(generate_image=False)
        self.update()
    
    def endPendingEvents(self):
        """End ongoing events that are connected to the mouse."""
        if self.is_line_tracing:
            if self.mouse_mode == FieldWidget.CLOSEDLINE:
                self.newTrace(self.current_trace, closed=True)
            elif self.mouse_mode == FieldWidget.OPENLINE:
                self.newTrace(self.current_trace, closed=False)
            self.is_line_tracing = False
            self.saveState()
            self.generateView(generate_image=False)
            self.update()
    
    def findClosestTrace(self, field_x : float, field_y : float, radius=0.5) -> Trace:
        """Find closest trace to field coordinates in a given radius.
        
            Params:
                field_x (float): x coordinate of search center
                field_y (float): y coordinate of search center
                radius (float): 1/2 of the side length of search square
            
            Returns:
                (Trace) the trace closest to the center
                None if no trace points are found within the radius
        """
        min_distance = -1
        closest_trace = None
        # for trace in self.traces_within_field: # check only traces within the current window view
        for trace in self.traces:
            if trace.hidden:
                continue
            points = []
            for point in trace.points:
                x, y = self.point_tform.map(*point)
                # x, y = self.fieldPointToPixmap(x, y)
                points.append((x,y))
            dist = getDistanceFromTrace(field_x, field_y, points, factor=1/self.mag)
            if closest_trace is None or dist < min_distance:
                min_distance = dist
                closest_trace = trace
        return closest_trace if min_distance <= radius else None
    
    def deleteSelectedTraces(self, save_state=True):
        """Delete selected traces.
        
            Params:
                save_state (bool): whether or not to save the state after deleting
        """
        for trace in self.selected_traces:
            self.traces.remove(trace)
        self.selected_traces = []
        if save_state:
            self.saveState()
        self.generateView(generate_image=False)
        self.update()
    
    def mergeSelectedTraces(self):
        """Merge all selected traces."""
        if len(self.selected_traces) < 2:
            print("Cannot merge fewer than two traces.")
            return
        traces = []
        first_trace = self.selected_traces[0]
        name = first_trace.name
        color = first_trace.color  # use color of first trace selected
        for trace in self.selected_traces:
            if trace.closed == False:
                print("Can only merge closed traces.")
                return
            if trace.name != name:
                print("Cannot merge differently named traces.")
                return
            # collect pixel values for trace points
            traces.append([])
            for point in trace.points:
                p = self.point_tform.map(*point)
                p = self.fieldPointToPixmap(*p)
                traces[-1].append(p)
        merged_traces = mergeTraces(traces)  # merge the pixel traces
        if merged_traces == traces:  # function returns same list if traces cannot be merged
            print("Traces cannot be merged.")
            return
        # create new merged trace
        self.deleteSelectedTraces(save_state=False)
        for trace in merged_traces:
            self.newTrace(trace, name=name, color=color)
        self.saveState()
        self.generateView(generate_image=False)
        self.update()
    
    def hideSelectedTraces(self):
        """Hide all selected traces."""
        for trace in self.selected_traces:
            trace.setHidden(True)
        self.selected_traces = []
        self.saveState()
        self.generateView(generate_image=False)
        self.update()
    
    def toggleHideAllTraces(self):
        """Hide/unhide every trace on the section."""
        if self.all_traces_hidden:
            for trace in self.traces:
                trace.setHidden(False)
            self.all_traces_hidden = False
        else:
            for trace in self.traces:
                trace.setHidden(True)
            self.all_traces_hidden = True
        self.selected_traces = []
        self.saveState()
        self.generateView(generate_image=False)
        self.update()
