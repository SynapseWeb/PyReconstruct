import os
import sys
import json
from ClosedContour import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *
from PySide2.QtCore import *

class Trace():

    def __init__(self, name):
        self.points = []
        self.color = (0, 0, 0)
        self.name = name
        self.closed = True
    
    def add(self, point):
        """Add a point to the trace"""
        self.points.append(point)
    
    def setClosed(self, closed : bool):
        """Set closed status of the trace"""
        self.closed = closed

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.menubar = self.menuBar()
        self.filemenu = self.menubar.addMenu("File")
        self.new_act = self.filemenu.addAction("New")
        self.new_act.triggered.connect(self.newSeries) # create a new series
        self.open_act = self.filemenu.addAction("Open")
        self.open_act.triggered.connect(self.openSeries) # open an existing series
        self.field = None
        self.setMouseTracking(True)
        self.setGeometry(100, 100, 500, 500)
        self.show()
    
    def newSeries(self):
        """Create a new series from a set of images"""
        # get images from user
        image_locations, extensions = QFileDialog.getOpenFileNames(self, "Select Images", filter="*.jpg *.jpeg *.png *.tif *.tiff")
        if len(image_locations) == 0:
            return
        
        # get calibration (microns per pix) from user
        mag, confirmed = QInputDialog.getDouble(self, "Section Calibration",
                                                "What is the calibration for this series?",
                                                0.00254, minValue=0, decimals=6)
        if not confirmed:
            return
        
        # change working directory to folder with images
        first_image = image_locations[0]
        if "/" in first_image:
            file_path = first_image[:first_image.rfind("/")]
            os.chdir(file_path)
        
        # get the name of the series from user
        series_name, confirmed = QInputDialog.getText(self, "Series Name", "What is the name of this series?")
        if not confirmed:
            return
        
        # create series data file (.ser)
        series_data = {}
        series_data["sections"] = []
        series_data["current_section"] = 0
        series_data["window"] = [0, 0, 1, 1]
        for i in range(len(image_locations)):
            series_data["sections"].append(series_name + "." + str(i))
        with open(series_name + ".ser", "w") as series_file:
            series_file.write(json.dumps(series_data, indent=2))
        
        # create section files (.#)
        for i in range(len(image_locations)):
            section_data = {}
            section_data["src"] = image_locations[i][image_locations[i].rfind("/")+1:]
            section_data["mag"] = mag
            section_data["tform"] = [1, 0, 0, 0, 1, 0]
            section_data["traces"] = []
            with open(series_name + "." + str(i), "w") as section_file:
                section_file.write(json.dumps(section_data, indent=2))
    
        # open series after creating
        self.openSeries(series_name + ".ser")
    
    def openSeries(self, series=None):
        if series: # if series is provided (only the case if opening from new)
            with open(series, "r") as series_file:
                self.series_data = json.load(series_file)
        else: 
            # get series file from user
            series, extension = QFileDialog.getOpenFileName(self, "Select Series", filter="*.ser")
            if series == "":
                return
            with open(series, "r") as series_file:
                self.series_data = json.load(series_file)
        self.series_file_path = series

        # change working directory to series location
        if "/" in series:
            file_path = series[:series.rfind("/")]
            os.chdir(file_path)
        
        # get the last known section and load data
        self.section_num = self.series_data["current_section"]
        with open(self.series_data["sections"][self.section_num], "r") as section_file:
            self.section_data = json.load(section_file)
        
        # create trace field for given section on last known window
        self.initField(self.section_data, self.series_data["window"])
    
    def initField(self, section_data, window):
        """Create the field for tracing"""
        # set the main window to be slightly less than the size of the monitor
        screen = QApplication.primaryScreen()
        screen_rect = screen.size()
        x = 50
        y = 80
        w = screen_rect.width() - 100
        h = screen_rect.height() - 160
        self.setGeometry(x, y, w, h)

        # create status bar (at bottom of window)
        self.statusbar = self.statusBar()

        # create the field and set as main widget
        self.field = Field(self.section_num, section_data, window, self)
        self.setCentralWidget(self.field)

        # create toolbar for interacting with field
        self.toolbar = self.addToolBar("Mouse Modes")
        pointer_act = self.toolbar.addAction("POINTER")
        pointer_act.setIcon(QIcon(QPixmap("pointer.png")))
        pointer_act.triggered.connect(self.toPointer)
        panzoom_act = self.toolbar.addAction("PAN/ZOOM")
        panzoom_act.setIcon(QIcon(QPixmap("panzoom.png")))
        panzoom_act.triggered.connect(self.toPanzoom)
        pencil_act = self.toolbar.addAction("PENCIL")
        pencil_act.setIcon(QIcon(QPixmap("pencil.png")))
        pencil_act.triggered.connect(self.toPencil)
        name_act = self.toolbar.addAction("PENCIL NAME")
        name_act.setIcon(QIcon(QPixmap("name.png")))
        name_act.triggered.connect(self.changePencilName)
        color_act = self.toolbar.addAction("PENCIL COLOR")
        color_act.setIcon(QIcon(QPixmap("color.png")))
        color_act.triggered.connect(self.changePencilColor)

        # create shortcuts
        merge_sc = QShortcut(QKeySequence("Ctrl+M"), self)
        merge_sc.activated.connect(self.field.mergeSelectedTraces)
        deselect_sc = QShortcut(QKeySequence("Ctrl+D"), self)
        deselect_sc.activated.connect(self.field.deselectAllTraces)
    
    def toPointer(self):
        """Set mouse mode to pointer"""
        self.field.setMouseMode(Field.POINTER)

    def toPanzoom(self):
        """Set mouse mode to panzoom"""
        self.field.setMouseMode(Field.PANZOOM)

    def toPencil(self):
        """Set mouse mode to pencil"""
        self.field.setMouseMode(Field.PENCIL)

    def changePencilColor(self):
        """Change the field pencil color"""
        new_color = QColorDialog.getColor()
        self.field.setPencilColor(new_color)

    def changePencilName(self):
        """Change the field pencil name"""
        new_name, confirmed = QInputDialog.getText(self, "Pencil Name", "Enter the new pencil name:")
        if confirmed and new_name != "":
            self.field.setPencilName(new_name)
    
    def keyPressEvent(self, event):
        # do not respond to keyboard if field is not created
        if not self.field:
            return
        # if PgUp is pressed
        elif event.key() == 16777238 and self.section_num < len(self.series_data["sections"])-1:
            self.changeSection(self.section_num + 1)
        # if PgDn is pressed
        elif event.key() == 16777239 and self.section_num > 0:
            self.changeSection(self.section_num - 1)
        # if Del is pressed
        elif event.key() == 16777223:
            self.field.deleteSelectedTraces()
    
    def wheelEvent(self, event):
        # do not respond to mouse wheel if field is not created
        if not self.field:
            return
        # if scroll up
        elif event.angleDelta().y() > 0  and self.section_num < len(self.series_data["sections"])-1:
            self.changeSection(self.section_num + 1)
        # if scroll down
        elif event.angleDelta().y() < 0 and self.section_num > 0:
            self.changeSection(self.section_num - 1)
    
    def changeSection(self, section_num):
        """Change the section of the field"""
        self.saveFieldTraces()
        self.section_num = section_num
        self.series_data["current_section"] = self.section_num
        with open(self.series_data["sections"][self.section_num], "r") as section_file:
            self.section_data = json.load(section_file)
        self.field.loadSection(self.section_num, self.section_data)
    
    def saveFieldTraces(self):
        """Save the current field traces in the corresponding section file"""
        traces = self.field.traces
        self.section_data["traces"] = []
        for trace in traces:
            trace_data = {}
            trace_data["name"] = trace.name
            trace_data["color"] = trace.color
            trace_data["closed"] = trace.closed
            trace_data["points"] = trace.points
            self.section_data["traces"].append(trace_data)
        with open(self.series_data["sections"][self.section_num], "w") as section_file:
            section_file.write(json.dumps(self.section_data, indent=2))
    
    def closeEvent(self, event):
        """Save traces, section num, and window if user exits"""
        if not self.field: # do not do anything if field is not created
            event.accept()
            return
        self.saveFieldTraces()
        self.series_data["window"] = self.field.current_window
        with open(self.series_file_path, "w") as series_file:
            series_file.write(json.dumps(self.series_data, indent=2))
        event.accept()

class Field(QWidget):
    POINTER, PANZOOM, PENCIL = range(3) # mouse modes

    def __init__(self, section_num, section_data, window, parent=None):
        # add parent if provided (this should be the case)
        if parent:
            super().__init__(parent)
            self.parent_widget = parent
        else:
            super().__init__()
            self.parent_widget = None

        # set geometry to match parent if provided
        if self.parent_widget:
            parent_rect = self.parent_widget.geometry()
            self.pixmap_size = parent_rect.width(), parent_rect.height()
            self.setGeometry(parent_rect)
        else:
            self.pixmap_size = (500, 500)
            self.setGeometry(100, 100, 500, 500)
        
        # default mouse mode: panzoom
        self.mouse_mode = Field.PANZOOM
        self.setMouseTracking(True)

        # create layers
        self.image_layer = QLabel(self)
        self.trace_layer = QLabel(self)
        self.trace_layer.setMouseTracking(True)

        # resize last known window to match proportions of current geometry
        window[3] = window[2]/self.pixmap_size[0] * self.pixmap_size[1]
        self.current_window = window

        # establish defaults
        self.selected_traces = []
        self.pencil_name = "TRACE"
        self.tracing_pencil = QPen(QColor(255, 0, 255), 1)

        self.loadSection(section_num, section_data)
        self.show()
    
    def setPencilColor(self, color):
        """Set the pencil color for traces"""
        self.tracing_pencil = QPen(color, 1)
    
    def setPencilName(self, name):
        """Set the pencil name for traces"""
        self.pencil_name = name
    
    def loadSection(self, section_num, section_data):
        """Load a new section into the field"""
        self.section_num = section_num

        # create transforms
        t = section_data["tform"] # identity would be: 1 0 0 0 1 0
        self.point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5]) # normal matrix for points
        self.image_tform = QTransform(t[0], t[1], t[3], t[4], t[2], t[5]) # changed positions for image tform
        self.mag = section_data["mag"] # get magnification
        base_pixmap = QPixmap(section_data["src"]) # load image
        self.image_pixmap = base_pixmap.transformed(self.image_tform) # transform image
        self.calcTformOrigin(base_pixmap, self.image_tform) # find the coordinates of the tformed image origin (bottom left corner)
        x_shift = t[2] - self.tform_origin[0]*self.mag # calculate x translation for image placement in field
        y_shift = t[5] - (self.image_pixmap.height() - self.tform_origin[1]) * self.mag # calculate y translation for image placement in field
        self.image_vector = x_shift, y_shift # store as vector

        # create traces
        self.traces = []
        self.selected_traces = []
        for trace_data in section_data["traces"]:
            name = trace_data["name"]
            trace = Trace(name)
            trace.color = trace_data["color"]
            trace.points = trace_data["points"]
            trace.closed = trace_data["closed"]
            self.traces.append(trace)

        self.updateStatusBar(None)
        self.generateView()
        self.image_layer.adjustSize()
        self.trace_layer.adjustSize()
    
    def updateStatusBar(self, event):
        """Update status bar with useful information"""
        if self.parent_widget:
            if event:
                s = "Section: " + str(self.section_num) + "  |  "
                x, y = event.pos().x(), event.pos().y()
                x, y = self.pixmapPointToField((x, y))
                s += "x = " + str("{:.4f}".format(x)) + ", "
                s += "y = " + str("{:.4f}".format(y)) + "  |  "
                s += "Tracing: " + '"' + self.pencil_name + '"'
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
        self.image_layer.adjustSize()
        self.trace_layer.adjustSize()
    
    def setMouseMode(self, mode):
        """Set the mode of the mouse"""
        self.mouse_mode = mode
    
    def mousePressEvent(self, event):
        if self.mouse_mode == Field.POINTER:
            self.pointerPress(event)
        elif self.mouse_mode == Field.PANZOOM:
            self.panzoomPress(event)
        elif self.mouse_mode == Field.PENCIL:
            self.pencilPress(event)

    def mouseMoveEvent(self, event):
        if not event.buttons():
            self.updateStatusBar(event)
            return
        if self.mouse_mode == Field.POINTER:
            self.pointerMove(event)
        elif self.mouse_mode == Field.PANZOOM:
            self.panzoomMove(event)
        elif self.mouse_mode == Field.PENCIL:
            self.pencilMove(event)

    def mouseReleaseEvent(self, event):
        if self.mouse_mode == Field.POINTER:
            self.pointerRelease(event)
        if self.mouse_mode == Field.PANZOOM:
            self.panzoomRelease(event)
        elif self.mouse_mode == Field.PENCIL:
            self.pencilRelease(event)
        
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

            # move image and trace layers with the mouse
            new_image_layer = QPixmap(*self.pixmap_size)
            new_image_layer.fill(QColor(0, 0, 0))
            painter = QPainter(new_image_layer)
            painter.drawPixmap(move_x, move_y, *self.pixmap_size, self.image_layer_pixmap)
            painter.end()
            new_trace_layer = QPixmap(*self.pixmap_size)
            new_trace_layer.fill(QColor(0, 0, 0, 0))
            painter = QPainter(new_trace_layer)
            painter.drawPixmap(move_x, move_y, *self.pixmap_size, self.trace_layer_pixmap)
            painter.end()

            self.image_layer.setPixmap(new_image_layer)
            self.trace_layer.setPixmap(new_trace_layer)

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

            # adjust layers
            new_image_layer = QPixmap(*self.pixmap_size)
            new_image_layer.fill(QColor(0, 0, 0))
            painter = QPainter(new_image_layer)
            painter.drawPixmap(x, y, w, h,
                                self.image_layer_pixmap)
            painter.end()
            new_trace_layer = QPixmap(*self.pixmap_size)
            new_trace_layer.fill(QColor(0, 0, 0, 0))
            painter = QPainter(new_trace_layer)
            painter.drawPixmap(x, y, w, h,
                                self.trace_layer_pixmap)
            painter.end()
        
            self.image_layer.setPixmap(new_image_layer)
            self.trace_layer.setPixmap(new_trace_layer)

    def panzoomRelease(self, event):
        """Mouse is released in panzoom mode"""

        # set new window for panning
        if event.button() == Qt.LeftButton:
            move_x = -(event.x() - self.clicked_x) / self.x_scaling * self.mag
            move_y = (event.y() - self.clicked_y) / self.y_scaling * self.mag
            self.current_window[0] += move_x
            self.current_window[1] += move_y
            self.generateView()

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
        painter = QPainter(self.trace_layer_pixmap)
        painter.setPen(self.tracing_pencil)
        painter.drawLine(self.last_x, self.last_y, x, y)
        self.current_trace.append((x, y))
        self.last_x = x
        self.last_y = y
        self.trace_layer.setPixmap(self.trace_layer_pixmap)
        painter.end()

    def pencilRelease(self, event):
        """Mouse is released in pencil mode"""
        # calculate actual trace coordinates on the field and reload field view
        trace_grid = Grid(self.current_trace)
        trace_grid.generateGrid()
        self.current_trace = trace_grid.getExteriorPoints()
        new_trace = Trace(self.pencil_name)
        color = self.tracing_pencil.color()
        new_trace.color = (color.red(), color.green(), color.blue())
        for point in self.current_trace:
            field_point = self.pixmapPointToField(point)
            rtform_point = self.point_tform.inverted()[0].map(*field_point) # apply the inverse tform to fix trace to image
            new_trace.add(rtform_point)
        self.traces.append(new_trace)
        self.generateView(generate_image=False)
        self.selected_traces.append(new_trace)
        self.drawTrace(new_trace, highlight=True)
    
    def pointerPress(self, event):
        """Mouse is pressed in pointer mode"""
        pix_x, pix_y = event.x(), event.y()
        field_x, field_y = self.pixmapPointToField((pix_x, pix_y))
        radius = max(self.pixmap_size) / 25 * self.mag / self.x_scaling # set radius to be 4% of widget length
        selected_trace = self.findClosestTrace(field_x, field_y, radius)
        
        # select and highlight trace if left button
        if selected_trace != None and event.button() == Qt.LeftButton:
            if not selected_trace in self.selected_traces:
                self.drawTrace(selected_trace, highlight=True)
                self.selected_traces.append(selected_trace)
        # deselect and unhighlight trace if right button
        elif selected_trace != None and event.button() == Qt.RightButton:
            if selected_trace in self.selected_traces:
                self.drawTrace(selected_trace)
                self.selected_traces.remove(selected_trace)
    
    def deselectAllTraces(self):
        for trace in self.selected_traces:
            self.drawTrace(trace)
        self.selected_traces = []
    
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
                x = point[0]
                y = point[1]
                if left < point[0] < right and bottom < point[1] < top:
                    distance = ((x - field_x)**2 + (y - field_y)**2) ** (0.5)
                    if not closest_trace or distance < min_distance:
                        min_distance = distance
                        closest_trace = trace
        return closest_trace

    def drawTrace(self, trace, highlight=False):
        """Draw a trace on the current trace layer and return bool indicating if trace is in the current view"""
        # set up painter
        painter = QPainter(self.trace_layer_pixmap)
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
        if highlight:
            painter.drawPoint(last_x, last_y)
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

        self.trace_layer.setPixmap(self.trace_layer_pixmap)
        return within_field
    
    def deleteSelectedTraces(self):
        """Delete selected traces"""
        for trace in self.selected_traces:
            self.traces.remove(trace)
        self.selected_traces = []
        self.generateView(generate_image=False)
    
    def mergeSelectedTraces(self):
        if len(self.selected_traces) <= 1:
            print("Cannot merge one or less traces.")
            return
        contours = []
        first_trace = self.selected_traces[0]
        name = first_trace.name
        color = first_trace.color
        for trace in self.selected_traces:
            if trace.name != name:
                print("Cannot merge differently named traces")
                return
            contours.append([])
            for point in trace.points:
                p = self.fieldPointToPixmap(point)
                contours[-1].append(p)
        grid = Grid()
        for contour in contours:
            grid.addClosedContour(contour)
        grid.generateGrid()
        merged_contours = grid.getMergedPoints()
        if not merged_contours:
            print("Contours already merged.")
            return
        self.deleteSelectedTraces()
        for contour in merged_contours:
            new_trace = Trace(name)
            new_trace.color = color
            for point in contour:
                field_point = self.pixmapPointToField(point)
                rtform_point = self.point_tform.inverted()[0].map(*field_point) # apply the inverse tform to fix trace to image
                new_trace.add(rtform_point)
            self.traces.append(new_trace)
            self.generateView(generate_image=False)
            self.selected_traces.append(new_trace)
            self.drawTrace(new_trace, highlight=True)


    def pixmapPointToField(self, point):
        """Convert main window coordinates to field window coordinates"""
        x = (point[0] + 0.5) / self.x_scaling * self.mag + self.current_window[0]
        y = (self.pixmap_size[1] - (point[1] + 0.5)) / self.y_scaling * self.mag  + self.current_window[1]
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
            window_pixmap = QPixmap(pixmap_w, pixmap_h)
            window_pixmap.fill(QColor(0, 0, 0))

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
            painter = QPainter(window_pixmap)
            painter.drawPixmap(left_empty * self.x_scaling, top_empty * self.y_scaling,
                               crop_w * self.x_scaling, crop_h * self.y_scaling,
                               self.image_pixmap,
                               crop_left, crop_top, crop_w, crop_h)
            painter.end()
            
            self.image_layer_pixmap = window_pixmap
            self.image_layer.setPixmap(window_pixmap)
        
        # draw all the traces
        self.trace_layer_pixmap = QPixmap(pixmap_w, pixmap_h)
        self.trace_layer_pixmap.fill(QColor(0, 0, 0, 0))
        self.trace_layer.setPixmap(self.trace_layer_pixmap)
        self.traces_within_field = []
        for trace in self.traces:
            within_field = self.drawTrace(trace)
            if within_field:
                self.traces_within_field.append(trace)
                if trace in self.selected_traces:
                    self.drawTrace(trace, highlight=True)

# adjust dpi scaling
if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

app = QApplication(sys.argv)
main_window = MainWindow()
app.exec_()