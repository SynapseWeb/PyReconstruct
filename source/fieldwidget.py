from PySide2.QtWidgets import QWidget
from PySide2.QtCore import Qt
from PySide2.QtGui import (QPixmap, QPen, QColor, QTransform, QPainter)

from grid import getExterior, mergeTraces, reducePoints
from trace import Trace

class FieldWidget(QWidget):
    POINTER, PANZOOM, CLOSEDPENCIL, OPENPENCIL, CLOSEDLINE, OPENLINE, STAMP = range(7)  # mouse modes

    def __init__(self, section_num, section, window, parent):
        # add parent if provided (this should be the case)
        super().__init__(parent)
        self.parent_widget = parent

        # set geometry to match parent
        parent_rect = self.parent_widget.geometry()
        self.pixmap_size = parent_rect.width(), parent_rect.height()
        self.setGeometry(parent_rect)
        
        # default mouse mode: pointer
        self.mouse_mode = FieldWidget.POINTER
        self.setMouseTracking(True)

        # resize last known window to match proportions of current geometry
        window[3] = window[2]/self.pixmap_size[0] * self.pixmap_size[1]
        self.current_window = window

        # establish misc defaults
        self.selected_traces = []
        self.tracing_trace = Trace("TRACE", (255, 0, 255))
        self.is_line_tracing = False
        self.all_traces_hidden = False

        self.field_pixmap = QPixmap()

        self.loadSection(section_num, section)
        self.show()
    
    def setTracingTrace(self, trace):
        self.tracing_trace = trace
    
    def loadSection(self, section_num, section):
        """Load a new section into the field"""
        self.section_num = section_num

        # create transforms
        t = section.tform # identity would be: 1 0 0 0 1 0
        self.point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5]) # normal matrix for points
        self.image_tform = QTransform(t[0], t[1], t[3], t[4], t[2], t[5]) # changed positions for image tform
        self.mag = section.mag # get magnification
        base_pixmap = QPixmap(self.parent_widget.wdir + section.src) # load image
        self.image_pixmap = base_pixmap.transformed(self.image_tform) # transform image
        self.calcTformOrigin(base_pixmap, self.image_tform) # find the coordinates of the tformed image origin (bottom left corner)
        x_shift = t[2] - self.tform_origin[0]*self.mag # calculate x translation for image placement in field
        y_shift = t[5] - (self.image_pixmap.height() - self.tform_origin[1]) * self.mag # calculate y translation for image placement in field
        self.image_vector = x_shift, y_shift # store as vector

        # create traces
        self.traces = section.traces.copy()
        for trace in self.traces:
            trace.setHidden(False)
        self.selected_traces = []

        self.updateStatusBar(None)
        self.generateView()
        self.update()
    
    def updateStatusBar(self, event):
        """Update status bar with useful information"""
        if event:
            s = "Section: " + str(self.section_num) + "  |  "
            x, y = event.pos().x(), event.pos().y()
            x, y = self.pixmapPointToField((x, y))
            s += "x = " + str("{:.4f}".format(x)) + ", "
            s += "y = " + str("{:.4f}".format(y)) + "  |  "
            s += "Tracing: " + '"' + self.tracing_trace.name + '"'
            closest_trace = self.findClosestTrace(x, y)
            if closest_trace:
                s += "  |  Nearest trace: " + closest_trace.name
        else:
            message = self.parent_widget.statusbar.currentMessage()
            s = "Section: " + str(self.section_num) + "  " + message[message.find("|"):]
        self.parent_widget.statusbar.showMessage(s)

    def resizeEvent(self, event):
        """Scale field window if main window size changes"""
        w = event.size().width()
        h = event.size().height()
        x_scale = w / self.pixmap_size[0]
        y_scale = h / self.pixmap_size[1]
        self.pixmap_size = (w, h)
        self.current_window[2] *= x_scale
        self.current_window[3] *= y_scale
        self.generateView()
        self.update()
    
    def setMouseMode(self, mode):
        """Set the mode of the mouse"""
        self.mouse_mode = mode
    
    def mousePressEvent(self, event):
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

    def mouseMoveEvent(self, event):
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

    def mouseReleaseEvent(self, event):
        if self.mouse_mode == FieldWidget.POINTER:
            self.pointerRelease(event)
        if self.mouse_mode == FieldWidget.PANZOOM:
            self.panzoomRelease(event)
        elif self.mouse_mode == FieldWidget.CLOSEDPENCIL:
            self.pencilRelease(event, closed=True)
        elif self.mouse_mode == FieldWidget.OPENPENCIL:
            self.pencilRelease(event, closed=False)
        
    def panzoomPress(self, event):
        """Mouse is clicked in panzoom mode"""
        self.clicked_x = event.x()
        self.clicked_y = event.y()

    def panzoomMove(self, event):
        """Mouse is moved in panzoom mode"""
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
        """Mouse is released in panzoom mode"""

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

            xcoef = (self.clicked_x / self.pixmap_size[0]) * 2
            ycoef = (self.clicked_y / self.pixmap_size[1]) * 2
            w = self.pixmap_size[0] * zoom_factor
            h = self.pixmap_size[1] * zoom_factor
            x = (self.pixmap_size[0] - w) / 2 * xcoef
            y = (self.pixmap_size[1] - h) / 2 * ycoef

            window_x = - x  / self.x_scaling / zoom_factor * self.mag
            window_y = - (self.pixmap_size[1] - y - self.pixmap_size[1] * zoom_factor)  / self.y_scaling / zoom_factor * self.mag
            self.current_window[0] += window_x
            self.current_window[1] += window_y
            self.current_window[2] /= zoom_factor
            if self.current_window[2] < self.mag:
                self.current_window[2] = self.mag
            self.current_window[3] /= zoom_factor
            if self.current_window[3] < self.mag:
                self.current_window[3] = self.mag
            self.generateView()
            self.update()
    
    def pencilPress(self, event):
        """Mouse is pressed in pencil mode"""
        self.last_x = event.x()
        self.last_y = event.y()
        self.current_trace = [(self.last_x, self.last_y)]

    def pencilMove(self, event):
        """Mouse is moved in pencil mode"""
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
        """Mouse is released in pencil mode"""
        # calculate actual trace coordinates on the field and reload field view
        self.newTrace(self.current_trace, closed=closed)
    
    def pointerPress(self, event):
        """Mouse is pressed in pointer mode"""
        pix_x, pix_y = event.x(), event.y()
        field_x, field_y = self.pixmapPointToField((pix_x, pix_y))
        radius = max(self.pixmap_size) / 25 * self.mag / self.x_scaling # set radius to be 4% of widget length
        selected_trace = self.findClosestTrace(field_x, field_y, radius)
        
        # select and highlight trace if left button
        if selected_trace != None and event.button() == Qt.LeftButton:
            if not selected_trace in self.selected_traces:
                self.selected_traces.append(selected_trace)
                self.generateView(generate_image=False)
                self.update()
        # deselect and unhighlight trace if right button
        elif selected_trace != None and event.button() == Qt.RightButton:
            if selected_trace in self.selected_traces:
                self.drawTrace(selected_trace)
                self.selected_traces.remove(selected_trace)
                self.update()
    
    def stampPress(self, event):
        pix_x, pix_y = event.x(), event.y()
        field_x, field_y = self.pixmapPointToField((pix_x, pix_y))
        new_trace = Trace(self.tracing_trace.name, self.tracing_trace.color)
        for point in self.tracing_trace.points:
            new_trace.add((point[0] + field_x, point[1] + field_y))
        self.traces.append(new_trace)
        self.selected_traces.append(new_trace)
        self.generateView(generate_image=False)
        self.update()
    
    def linePress(self, event, closed=True):
        x, y = event.x(), event.y()
        if event.button() == Qt.LeftButton:
            if self.is_line_tracing:
                self.current_trace.append((x, y))
                self.field_pixmap = self.field_pixmap_copy.copy()
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
                self.current_trace = [(x, y)]
                self.is_line_tracing = True
        elif event.button() == Qt.RightButton:
            if self.is_line_tracing:
                if closed:
                    self.newTrace(self.current_trace, closed=True)
                else:
                    self.newTrace(self.current_trace, closed=False)
                self.is_line_tracing = False
    
    def lineMove(self, event, closed=True):
        x, y = event.x(), event.y()
        self.field_pixmap = self.field_pixmap_copy.copy()
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
        pen.setDashPattern([2,5])
        painter.setPen(pen)
        painter.drawLine(*self.current_trace[-1], x, y)
        if closed:
            painter.drawLine(*self.current_trace[0], x, y)
        self.update()
    
    def newTrace(self, pix_trace, closed=True):
        if len(pix_trace) > 1:
            if closed:
                pix_trace = getExterior(pix_trace)
            else:
                pix_trace = reducePoints(pix_trace)
            new_trace = Trace(self.tracing_trace.name, self.tracing_trace.color, closed=closed)
            for point in pix_trace:
                field_point = self.pixmapPointToField(point)
                rtform_point = self.point_tform.inverted()[0].map(*field_point) # apply the inverse tform to fix trace to image
                new_trace.add(rtform_point)
            self.traces.append(new_trace)
            self.selected_traces.append(new_trace)
            self.generateView(generate_image=False)
            self.update()

    def deselectAllTraces(self):
        """Deselect all traces (Ctrl+D)"""
        for trace in self.selected_traces:
            self.drawTrace(trace)
        self.selected_traces = []
        self.update()
    
    def pointerMove(self, event):
        """Mouse is moved in pointer mode"""
        return
    
    def pointerRelease(self, event):
        """Mouse is released in pointer mode"""
        return
    
    def findClosestTrace(self, field_x, field_y, radius=1):
        """Find closest trace to field coordinates in a given radius"""
        left = field_x - radius
        right = field_x + radius
        bottom = field_y - radius
        top = field_y + radius
        min_distance = -1
        closest_trace = None
        for trace in self.traces_within_field: # check only traces within the current window view
            for point in trace.points:
                x, y = self.point_tform.map(*point)
                if left < x < right and bottom < y < top:
                    distance = ((x - field_x)**2 + (y - field_y)**2) ** (0.5)
                    if not closest_trace or distance < min_distance:
                        min_distance = distance
                        closest_trace = trace
        return closest_trace

    def drawTrace(self, trace, highlight=False):
        """Draw a trace on the current trace layer and return bool indicating if trace is in the current view"""
        # set up painter
        painter = QPainter(self.field_pixmap)
        within_field = False
        if highlight: # create dashed white line if trace is to be highlighted
            pen = QPen(QColor(255, 255, 255), 1)
            pen.setDashPattern([2, 5])
            painter.setPen(pen)
        else:
            painter.setPen(QPen(QColor(*trace.color), 1))
        
        # establish first point
        point = trace.points[0]
        last_x, last_y = self.point_tform.map(*point)
        last_x, last_y = self.fieldPointToPixmap((last_x, last_y))
        if 0 < last_x < self.pixmap_size[0] and 0 < last_y < self.pixmap_size[1]:
            within_field = True
        # connect points
        for i in range(1, len(trace.points)):
            point = trace.points[i]
            x, y = self.point_tform.map(*point)
            x, y = self.fieldPointToPixmap((x, y))
            painter.drawLine(last_x, last_y, x, y)
            if 0 < x < self.pixmap_size[0] and 0 < y < self.pixmap_size[1]:
                within_field = True
            last_x = x
            last_y = y
        # connect last point to first point if closed
        if trace.closed:
            point = trace.points[0]
            x, y = self.point_tform.map(*point)
            x, y = self.fieldPointToPixmap((x,y))
            painter.drawLine(last_x, last_y, x, y)
        painter.end()

        return within_field
    
    def deleteSelectedTraces(self):
        """Delete selected traces"""
        for trace in self.selected_traces:
            self.traces.remove(trace)
        self.selected_traces = []
        self.generateView(generate_image=False)
        self.update()
    
    def mergeSelectedTraces(self):
        """Merge all selected traces"""
        if len(self.selected_traces) <= 1:
            print("Cannot merge one or less traces.")
            return
        traces = []
        first_trace = self.selected_traces[0]
        name = first_trace.name
        color = first_trace.color
        for trace in self.selected_traces:
            if trace.closed == False:
                print("Can only merge closed traces.")
                return
            if trace.name != name:
                print("Cannot merge differently named traces.")
                return
            traces.append([])
            for point in trace.points:
                p = self.fieldPointToPixmap(point)
                traces[-1].append(p)
        merged_traces = mergeTraces(traces)
        if merged_traces == traces:
            print("Traces already merged.")
            return
        self.deleteSelectedTraces()
        for trace in merged_traces:
            new_trace = Trace(name, color)
            new_trace.color = color
            for point in trace:
                field_point = self.pixmapPointToField(point)
                new_trace.add(field_point)
            self.traces.append(new_trace)
            self.selected_traces.append(new_trace)
            self.generateView(generate_image=False)
            self.update()
    
    def hideSelectedTraces(self):
        for trace in self.selected_traces:
            trace.setHidden(True)
        self.selected_traces = []
        self.generateView(generate_image=False)
        self.update()
    
    def toggleHideAllTraces(self):
        if self.all_traces_hidden:
            for trace in self.traces:
                trace.setHidden(False)
            self.all_traces_hidden = False
        else:
            for trace in self.traces:
                trace.setHidden(True)
            self.all_traces_hidden = True
        self.generateView(generate_image=False)
        self.update()

    def pixmapPointToField(self, point):
        """Convert main window coordinates to field window coordinates"""
        x = (point[0]) / self.x_scaling * self.mag + self.current_window[0]
        y = (self.pixmap_size[1] - (point[1])) / self.y_scaling * self.mag  + self.current_window[1]
        return x, y
    
    def fieldPointToPixmap(self, point):
        """Convert field window coordinates to main window coordinates"""
        x = (point[0] - self.current_window[0]) / self.mag * self.x_scaling
        y = (point[1] - self.current_window[1])/ self.mag * self.y_scaling
        y = self.pixmap_size[1] - y
        return round(x), round(y)
    
    def calcTformOrigin(self, base_pixmap, tform):
        """Calculate the vector for the bottom left corner of a transformed image"""
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

        self.tform_origin = x_orig_bottomleft, y_orig_bottomleft
    
    def tformNoTrans(self, tform):
        """Return a transfrom without translation"""
        tform_notrans = (tform.m11(), tform.m12(), tform.m21(), tform.m22(), 0, 0)
        tform_notrans = QTransform(*tform_notrans)
        return tform_notrans
    
    def generateView(self, generate_image=True):
        """Generate the view seen by the user in the main window"""
        # get dimensions of field window and pixmap
        window_x, window_y, window_w, window_h = tuple(self.current_window)
        pixmap_w, pixmap_h = tuple(self.pixmap_size)

        if generate_image:
            # scaling: ratio of actual image dimensions to main window dimensions
            self.x_scaling = pixmap_w / (window_w / self.mag)
            self.y_scaling = pixmap_h / (window_h / self.mag)
            if abs(self.x_scaling - self.y_scaling) > 1e-5: # scaling should be the same for x and y
                print("ERROR: X and Y scaling are not equal")

            # create empty window
            self.field_pixmap = QPixmap(pixmap_w, pixmap_h)
            self.field_pixmap.fill(QColor(0, 0, 0))

            # get the coordinates to crop the image pixmap
            crop_left = (window_x - self.image_vector[0]) / self.mag
            left_empty = -crop_left if crop_left < 0 else 0
            crop_left = 0 if crop_left < 0 else crop_left

            crop_top = (window_y - self.image_vector[1] + window_h) / self.mag
            image_height = self.image_pixmap.size().height()
            top_empty = (crop_top - image_height) if crop_top > image_height else 0
            crop_top = image_height if crop_top > image_height else crop_top
            crop_top = image_height - crop_top

            crop_right = (window_x - self.image_vector[0] + window_w) / self.mag
            image_width = self.image_pixmap.size().width()
            crop_right = image_width if crop_right > image_width else crop_right

            crop_bottom = (window_y - self.image_vector[1]) / self.mag
            crop_bottom = 0 if crop_bottom < 0 else crop_bottom
            crop_bottom = image_height - crop_bottom

            crop_w = crop_right - crop_left
            crop_h = crop_bottom - crop_top

            # put the transformed image on the empty window
            painter = QPainter(self.field_pixmap)
            painter.drawPixmap(left_empty * self.x_scaling, top_empty * self.y_scaling,
                                crop_w * self.x_scaling, crop_h * self.y_scaling,
                                self.image_pixmap,
                                crop_left, crop_top, crop_w, crop_h)
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
                    if trace in self.selected_traces:
                        self.drawTrace(trace, highlight=True)
        
        self.field_pixmap_copy = self.field_pixmap.copy()
    
    def paintEvent(self, event):
        field_painter = QPainter(self)
        field_painter.drawPixmap(self.rect(), self.field_pixmap, self.field_pixmap.rect())
        field_painter.end()