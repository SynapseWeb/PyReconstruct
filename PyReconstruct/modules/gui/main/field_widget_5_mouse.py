import os
import time

from PySide6.QtCore import (
    Qt, 
    QTimer,
)
from PySide6.QtGui import (
    QPixmap, 
    QColor,
    QPainter, 
    QCursor,
)

from PyReconstruct.modules.calc import pixmapPointToField, distance, colorize, ellipseFromPair, lineDistance
from PyReconstruct.modules.gui.dialog import QuickDialog
from PyReconstruct.modules.gui.utils import notify
from PyReconstruct.modules.constants import locations as loc

from .field_widget_4_data import FieldWidgetData

POINTER, PANZOOM, KNIFE, SCISSORS, CLOSEDTRACE, OPENTRACE, STAMP, GRID, FLAG, HOST = range(10)

class FieldWidgetMouse(FieldWidgetData):
    """
    MOUSE FUNCTIONS
    ---------------
    These functions are directly called when user performs mouse actions
    in the field.
    """

    def setMouseMode(self, mode : int):
        """Set the mode of the mouse.
        
            Params:
                mode (int): number corresponding to mouse mode
        """
        self.endPendingEvents()  # end any mouse-related pending events
        self.mouse_mode = mode

        # set the cursor icon
        if mode in (POINTER, HOST):
            cursor = QCursor(Qt.ArrowCursor)
        elif mode == PANZOOM:
            cursor = QCursor(Qt.SizeAllCursor)
        elif mode == KNIFE:
            cursor = QCursor(
                QPixmap(os.path.join(loc.img_dir, "knife.cur")),
                hotX=5, hotY=5
            )
        elif (mode == OPENTRACE or
              mode == CLOSEDTRACE):
            cursor = self.pencil_l if self.series.getOption("left_handed") else self.pencil_r
        elif (mode == STAMP or
              mode == GRID):
            cursor = QCursor(Qt.CrossCursor)
        elif mode == SCISSORS:
            cursor = QCursor(Qt.CrossCursor)
        elif mode == FLAG:
            cursor = QCursor(Qt.WhatsThisCursor)
        self.setCursor(cursor)

    def checkMouseBoundary(self):
        """Move the window if the mouse is close to the boundary."""
        x, y = self.mouse_x, self.mouse_y

        # check if mouse is is wthin 2% of screen boundary
        xmin, xmax = round(self.width() * 0.02), round(self.width() * .98)
        ymin, ymax = round(self.height() * 0.02), round(self.height() * .98)

        shift = [0, 0]

        if x <= xmin:
            shift[0] -= xmin
        elif x >= xmax:
            shift[0] += xmin
        if y <= ymin:
            shift[1] -= ymin
        elif y >= ymax:
            shift[1] += ymin
        
        # move the window and current trace
        if shift[0] or shift[1]:
            s = self.section.mag / self.section_layer.scaling
            w = self.series.window
            w[0] += shift[0] * s
            w[1] -= shift[1] * s
            self.current_trace = [(x-shift[0], y-shift[1]) for x, y in self.current_trace]
            self.generateView()
    
    def activateMouseBoundaryTimer(self):
        """Activate the timer to check the mouse boundary."""
        if self.mouse_boundary_timer is None:
            self.mouse_boundary_timer = QTimer(self)
            self.mouse_boundary_timer.timeout.connect(self.checkMouseBoundary)
            self.mouse_boundary_timer.start(100)
    
    def deactivateMouseBoundaryTimer(self):
        """Deactivate the timer to check the mouse near boundary."""
        if self.mouse_boundary_timer:
            self.mouse_boundary_timer.stop()
            self.mouse_boundary_timer = None
    
    def isSingleClicking(self):
        """Check if user is single-clicking.
        
            Returns:
                (bool) True if user is single-clicking
        """
        if self.single_click or (time.time() - self.click_time <= self.max_click_time):
            return True
        else:
            return False
    
    def autoMerge(self):
        """Automatically merge the selected traces of the same name."""
        # merge with existing selected traces of the same name
        if not self.series.getOption("auto_merge"):
            return
        traces_to_merge = []
        for t in self.section.selected_traces:
            if t.name == self.tracing_trace.name and t.closed:
                traces_to_merge.append(t)
        if len(traces_to_merge) > 1:
            self.mergeTraces(restrict=traces_to_merge)

    def pointerPress(self, event):
        """Called when mouse is pressed in pointer mode.

        Selects/deselects the nearest trace
        """
        # select, deselect or move
        if self.lclick:
            self.is_moving_trace = False
            self.is_selecting_traces = False
            self.clicked_x, self.clicked_y = event.x(), event.y()
            self.selected_trace, self.selected_type = self.section_layer.getTrace(
                self.clicked_x,
                self.clicked_y
            )
    
    def pointerMove(self, event):
        """Called when mouse is moved in pointer mode."""
        # ignore if not clicking
        if not self.lclick:
            return
        
        # keep track of possible lasso if insufficient time has passed
        if self.isSingleClicking():
            self.current_trace.append((event.x(), event.y()))
            return
        
        # left button is down and user clicked on a trace
        if (
            self.is_moving_trace or 
            self.selected_trace in self.section.selected_traces or
            self.selected_trace in self.section.selected_ztraces or
            self.selected_trace in self.section.selected_flags
        ): 
            if not self.is_moving_trace:  # user has just decided to move the trace
                self.is_moving_trace = True
                # clear lasso trace
                self.current_trace = []
                # get pixel points
                self.moving_traces = []
                self.moving_points = []
                self.moving_flags = []
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
                for flag in self.section.selected_flags:
                    # hide the flag
                    self.section.temp_hide.append(flag)
                    # get point and other data
                    pix_point = self.section_layer.pointToPix((flag.x, flag.y))
                    color = flag.color
                    self.moving_flags.append((pix_point, color))

                self.generateView(update=False)
            
            self.update()

        # no trace was clicked on OR user clicked on unselected trace
        # draw lasso for selecting traces
        else:
            if not self.is_selecting_traces:  # user just decided to group select traces
                self.is_selecting_traces = True
                self.activateMouseBoundaryTimer()
            if self.series.getOption("pointer")[0] == "rect":
                x2, y2 = event.x(), event.y()
                if self.current_trace:
                    x1, y1 = self.current_trace[0]
                else:
                    x1, y1 = x2, y2

                self.current_trace = [
                    (x1, y1),
                    (x2, y1),
                    (x2, y2),
                    (x1, y2)
                ]
                
            else:
                x = event.x()
                y = event.y()
                self.current_trace.append((x, y))

            # draw to screen
            self.update()
    
    def pointerRelease(self, event):
        """Called when mouse is released in pointer mode."""

        ## User single-clicked
        if self.lclick and self.isSingleClicking():
            
            ## If user selected a label id
            if self.zarr_layer and self.zarr_layer.selectID(
                self.mouse_x, self.mouse_y
            ):
                self.generateView(update=False)
                
            ## If user selected a trace
            elif self.selected_trace:
                
                ## normal trace selected
                if self.selected_type == "trace":
                    if not self.series.getAttr(self.selected_trace.name, "locked"):
                        self.selectTrace(self.selected_trace)
                        
                ## z-trace selected
                elif self.selected_type == "ztrace_pt":
                    self.selectZtrace(self.selected_trace)
                    
                ## flag selected
                elif self.selected_type == "flag":
                    self.selectFlag(self.selected_trace)
        
        ## User moved traces
        elif self.lclick and self.is_moving_trace:
            
            ## Unhide traces
            self.section.temp_hide = []
            
            ## Save traces in final position
            self.is_moving_trace = False
            dx = (event.x() - self.clicked_x) * self.series.screen_mag
            dy = (event.y() - self.clicked_y) * self.series.screen_mag * -1
            self.section.translateTraces(dx, dy)
            self.generateView(update=False)
            self.saveState()
        
        ## User selected an area (lasso) of traces
        elif self.lclick and self.is_selecting_traces:
            
            self.is_selecting_traces = False
            self.deactivateMouseBoundaryTimer()
            selected_traces = self.section_layer.getTraces(self.current_trace)
            if selected_traces:
                self.selectTraces(selected_traces, [])
        
        # clear any traces made
        self.current_trace = []
        self.update()
    
    def panzoomPress(self, x, y):
        """Initiates panning and zooming mode.
        
            Params:
                x: the x position of the start
                y: the y position of the start
        """
        self.clicked_x = x
        self.clicked_y = y
        self.endPendingEvents()
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

        ## Start line tracing of only trace mode set
        trace_mode = self.series.getOption("trace_mode")
        if trace_mode == "poly":
            self.is_line_tracing = True
            self.activateMouseBoundaryTimer()
            self.mainwindow.checkActions()

    def traceMove(self, event):
        """Called when mouse is moved in trace mode."""
        
        if self.is_line_tracing:
            
            self.update()
            
        else:
            
            self.pencilMove(event)
    
    def traceRelease(self, event):
        """Called when mouse is released in trace mode."""
        
        trace_mode = self.series.getOption("trace_mode")

        ## User is already line tracing
        if self.is_line_tracing:
            self.lineRelease(event)

        ## User decided to line trace (in combo trace_mode)
        elif trace_mode == "combo" and self.isSingleClicking():
            self.current_trace = [self.current_trace[0]]
            self.is_line_tracing = True
            self.activateMouseBoundaryTimer()
            self.mainwindow.checkActions()

        ## User is not line tracing
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
            
            if self.closed_trace_shape == "trace" or self.mouse_mode == OPENTRACE:
                
                self.current_trace.append((x, y))
                
            elif self.closed_trace_shape == "rect":
                
                x1, y1 = self.current_trace[0]
                self.current_trace = [
                    (x1, y1),
                    (x, y1),
                    (x, y),
                    (x1, y)
                ]
                
            elif self.closed_trace_shape == "circle":
                
                self.current_trace = ellipseFromPair(self.clicked_x, self.clicked_y, x, y)
                
            self.last_x = x
            self.last_y = y
            
            self.update()

    def pencilRelease(self, event):
        """Called when mouse is released in pencil mode.

        Completes and adds trace.
        """
        closed = (self.mouse_mode == CLOSEDTRACE)
        
        if self.lclick:
            
            if len(self.current_trace) < 2:
                return

            self.newTrace(
                self.current_trace,
                self.tracing_trace,
                closed=closed,
                simplify=self.series.getOption("roll_average")
            )
            
            if closed and len(self.current_trace) > 2:
                self.autoMerge()
                
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
    
    def lineRelease(self, event=None, override=False, log_event=True):
        """Called when mouse is released in line mode."""
        
        if override or self.rclick and self.is_line_tracing:  # complete existing trace if right mouse button
            closed = (self.mouse_mode == CLOSEDTRACE)
            self.is_line_tracing = False
            self.deactivateMouseBoundaryTimer()
            if len(self.current_trace) > 1:
                current_trace_copy = self.current_trace.copy()
                self.newTrace(
                    current_trace_copy,
                    self.tracing_trace,
                    closed=closed,
                    log_event=(log_event and (not self.is_scissoring))
                )
                if log_event and self.is_scissoring:
                    self.series.addLog(self.tracing_trace.name, self.section.n, "Modify trace(s)")
                if closed and len(self.current_trace) > 2:
                    self.autoMerge()
            self.current_trace = []

            if self.is_scissoring:
                self.is_scissoring = False
                self.setMouseMode(SCISSORS)
                self.setTracingTrace(
                    self.series.palette_traces[self.series.palette_index[0]][self.series.palette_index[1]]
                )

                ## NOTE: saveState is usually invoked through newTrace; however,
                ## because this event is not logged through that function,
                ## saveState must be called here explicitly.
                
                self.saveState() 
                self.generateView()
                
            else:
                
                self.update()
    
    def stampPress(self, event):
        """Called when mouse is pressed in stamp mode.
        
        Creates a stamp centered on the mouse location.
        """
        # get mouse coords and convert to field coords
        if self.lclick:
            self.is_drawing_rad = False
            self.clicked_x, self.clicked_y = event.x(), event.y()
    
    def stampMove(self, event):
        """Called when mouse is moved in stamp mode."""
        if not self.lclick:
            return
        
        self.current_trace = [
            (self.clicked_x, self.clicked_y),
            (event.x(), event.y())
        ]

        if not self.isSingleClicking():
            self.is_drawing_rad = True

        self.update()
    
    def stampRelease(self, event):
        """Called when mouse is released in stamp mode."""
        # user single-clicked
        if self.lclick and self.isSingleClicking():
            self.placeStamp(event.x(), event.y(), self.tracing_trace)
        # user defined a radius
        elif self.lclick and self.is_drawing_rad:
            x, y = event.x(), event.y()
            r = distance(
                *pixmapPointToField(
                    self.clicked_x,
                    self.clicked_y,
                    self.pixmap_dim,
                    self.series.window,
                    self.section.mag
                ),
                *pixmapPointToField(
                    x,
                    y,
                    self.pixmap_dim,
                    self.series.window,
                    self.section.mag
                ),
            ) / 2
            stamp = self.tracing_trace.copy()
            stamp.resize(r)
            center = (
                (x + self.clicked_x) / 2,
                (y + self.clicked_y) / 2
            )
            self.placeStamp(*center, stamp)
        
        self.current_trace = []
        self.is_drawing_rad = False
        self.update()
    
    def gridPress(self, event):
        """Creates a grid on the mouse location."""
        # get mouse coords and convert to field coords
        if self.lclick:
            pix_x, pix_y = event.x(), event.y()
            print(f"{pix_x = }")
            print(f"{pix_y = }")
            self.placeGrid(
                pix_x, pix_y,
                self.tracing_trace,
                *tuple(self.series.getOption("grid"))
            )
    
    def gridRelease(self, event):
        """Called when mouse is released in grid mode."""
        self.update()
    
    def scissorsPress(self, event):
        """Identifies the nearest trace and allows user to poly edit it."""
        # select, deselect or move
        if self.lclick:
            self.selected_trace, self.selected_type = self.section_layer.getTrace(
                self.clicked_x,
                self.clicked_y
            )
            if self.selected_type == "trace":
                if self.series.getAttr(self.selected_trace.name, "locked"):
                    self.notifyLocked(self.selected_trace.name)
                    return
                self.is_scissoring = True
                self.deselectAllTraces()
                self.section.deleteTraces([self.selected_trace], log_event=False)
                self.generateView(generate_image=False)
                self.current_trace = self.section_layer.traceToPix(self.selected_trace)

                # find the index of the closest point
                least_dist = distance(self.clicked_x, self.clicked_y, *self.current_trace[0])
                least_i = 0
                for (i, p) in enumerate(self.current_trace):
                    d = distance(self.clicked_x, self.clicked_y, *p)
                    if d < least_dist:
                        least_dist = d
                        least_i = i

                # reverse the trace if closed (to operate same as legacy version)
                if self.selected_trace.closed:
                    self.mouse_mode = CLOSEDTRACE
                    self.current_trace = self.current_trace[least_i:] + self.current_trace[:least_i]
                    self.current_trace.reverse()
                else:
                    self.mouse_mode = OPENTRACE
                    # calculate distance for each segment
                    seg1 = self.current_trace[:least_i+1]
                    seg2 = self.current_trace[least_i:]
                    if lineDistance(seg2, closed=False) > lineDistance(seg1, closed=False):
                        self.current_trace = seg2[::-1]
                    else:
                        self.current_trace = seg1
                self.is_line_tracing = True
                self.activateMouseBoundaryTimer()
                self.mainwindow.checkActions()
                self.tracing_trace = self.selected_trace
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
    
    def flagRelease(self, event):
        """Called when mouse is released in flag mode."""
        if self.lclick and self.series.getOption("show_flags") != "none":
            default_name = self.series.getOption("flag_name")
            if not default_name:
                self.section.save()  # ensure all flags are in the series data object
                flag_count = self.series.data.getFlagCount()
                default_name = f"flag_{flag_count + 1}"
            structure = [
                ["Name:", (True, "text", default_name)],
                ["Color:", ("color", self.series.getOption("flag_color")), ""],
                ["Comment (opt):"],
                [("textbox", "")]
            ]
            response, confirmed = QuickDialog.get(self, structure, "Flag")
            if not confirmed:
                return
            
            pix_x, pix_y = event.x(), event.y()
            title = response[0]
            color = response[1]
            comment = response[2]
            self.placeFlag(
                title,
                pix_x, pix_y,
                color,
                comment
            )

        self.update()
    
    def hostPress(self, event):
        """Called when mouse is pressed in host mode."""
        pass
    
    def hostMove(self, event):
        """Called when mouse is moved in host mode."""
        if self.hosted_trace:
            self.current_trace = self.current_trace[:1]
            self.current_trace.append((self.mouse_x, self.mouse_y))

    def hostRelease(self, event):
        """Called when mouse is released in host mode."""
        # cancel operation if user right-clicked
        if self.rclick and self.hosted_trace:
            self.hosted_trace = None
            self.current_trace = []
            self.update()
            return
        
        closest, closest_type = self.section_layer.getTrace(self.mouse_x, self.mouse_y)
        if self.hosted_trace:
            if closest_type == "trace":
                host = closest.name
                hosted = self.hosted_trace.name
                if host == hosted:
                    notify("An object cannot be a host of itself.")
                elif hosted in self.series.getObjHosts(host, traverse=True):
                    notify("Objects cannot be hosts of each other.")
                else:
                    self.series_states.addState()
                    self.series.host_tree.add(
                        hosted, 
                        [host],
                    )
                    self.table_manager.updateObjects(self.series.host_tree.getObjToUpdate([hosted, host]))
            self.hosted_trace = None
            self.current_trace = []
        else:
            if closest_type == "trace":
                self.hosted_trace = closest
                self.current_trace = [(self.mouse_x, self.mouse_y)]
            else:
                self.hosted_trace = None
                self.current_trace = []
        self.update()
