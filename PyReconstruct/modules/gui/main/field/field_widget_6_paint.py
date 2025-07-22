from PySide6.QtWidgets import (
    QTextEdit,
)
from PySide6.QtCore import (
    QPoint, 
    QLine,
)
from PySide6.QtGui import (
    QPen,
    QColor,
    QPainter, 
    QFont,
)

from PyReconstruct.modules.calc import colorize
from PyReconstruct.modules.backend.view import drawArrow
from PyReconstruct.modules.gui.utils import drawOutlinedText
from PyReconstruct.modules.datatypes import Flag, Trace

from .field_widget_5_mouse import (
    FieldWidgetMouse,
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

class FieldWidgetPaint(FieldWidgetMouse):
    """
    PAINT FUNCTIONS
    ---------------
    These functions are related to the act of creating the view in the field.
    They include painting the appropriate border, painting any lines made by
    the user, and writing the text to the screen.
    """
    
    def drawBorder(self, painter : QPainter, color : tuple):
        """Draw a border around the field (called during paintEvent).
        
            Params:
                painter (QPainter): the painter for the field
                color(tuple): the color for the border
        """
        pen = QPen(QColor(*color), 8)
        if self.border_exists:
            pen.setDashPattern([2, 2, 2, 2])
        painter.setPen(pen)
        w, h = self.width(), self.height()
        points = [
            (0, 0),
            (0, h),
            (w, h),
            (w, 0)
        ]
        for i in range(len(points)):
            painter.drawLine(*points[i-1], *points[i])
        self.border_exists = True

    def paintBorder(self, field_painter : QPainter):
        """Paint the borders for the field."""
        # draw record dot on the screen if recording transforms
        if self.propagate_tform:
            field_painter.setBrush(QColor(255, 0, 0))
            field_painter.drawEllipse(20, 20, 40, 40)
        
        # add red border if trace layer is hidden
        self.border_exists = False
        if self.hide_trace_layer:
            self.drawBorder(field_painter, (255, 0, 0))
        # add green border if all traces are being shown
        elif self.show_all_traces:
            self.drawBorder(field_painter, (0, 255, 0))
        # add magenta border if image is hidden
        if self.hide_image:
            self.drawBorder(field_painter, (255, 0, 255))
        # add cyan border if sections are being blended
        if self.blend_sections:
            self.drawBorder(field_painter, (0, 255, 255))
    
    def paintWorkingTrace(self, field_painter : QPainter):
        """Paint the work trace on the field."""
        # draw the working trace on the screen
        if self.current_trace:
            pen = None
            # if drawing lasso
            if ((self.mouse_mode == POINTER and self.is_selecting_traces) or
                (self.mouse_mode == STAMP and self.is_drawing_rad)
            ):
                closed = True
                pen = QPen(QColor(255, 255, 255), 1)
                pen.setDashPattern([4, 4])
            # if drawing host line
            if self.mouse_mode == HOST:
                closed = False
                pen = QPen(QColor(255, 255, 255), 2)
            # if drawing knife
            elif self.mouse_mode == KNIFE:
                closed = False
                pen = QPen(QColor(255, 0, 0), 1)
            # if drawing trace
            elif (
                self.mouse_mode == OPENTRACE or
                self.mouse_mode == CLOSEDTRACE
            ):
                closed = (self.mouse_mode == CLOSEDTRACE and self.is_line_tracing or
                          self.mouse_mode == CLOSEDTRACE and self.closed_trace_shape != "trace")
                color = QColor(*self.tracing_trace.color)
                pen = QPen(color, 1)
            
            # draw current trace if exists
            if pen:
                if self.mouse_mode == HOST:
                    if len(self.current_trace) > 1:
                        line = QLine(*self.current_trace[0], *self.current_trace[1])
                        drawArrow(field_painter, line, False, True)
                else:
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
            # redraw flag with translation
            for (x, y), color in self.moving_flags:
                field_painter.setPen(QPen(QColor(*color), 6))
                field_painter.setFont(QFont("Courier New", self.series.getOption("flag_size"), QFont.Bold))
                qpoint = QPoint(x+dx, y+dy)
                field_painter.drawText(qpoint, "⚑")

    def paintText(self, field_painter : QPainter):
        """Paint the corner text onto the field."""
        # place text on other side of mode palette (if applicable)
        if self.mainwindow.mouse_palette.mode_x > .5:
            x = 10
            right_justified = False
        else:
            x = self.width() - 10
            right_justified = True
        y = 0
        
        # draw the name of the closest trace on the screen
        # draw the selected traces to the screen
        ct_size = 12
        st_size = 14
        closest = None
        closest_type = None
        close_hover_display = True  # assume the hover display will be closed
        if (
            not (self.lclick or self.rclick or self.mclick) and
            not self.is_gesturing
        ):
            # get closest trace
            closest, closest_type = self.section_layer.getTrace(self.mouse_x, self.mouse_y)

            # get zarr label
            if self.zarr_layer:
                label_id = self.zarr_layer.getID(self.mouse_x, self.mouse_y)
            else:
                label_id = None

            if (
                self.mouse_mode == POINTER or
                self.mouse_mode == HOST and not self.hosted_trace
            ):
                # prioritize showing label name
                if label_id is not None:
                    pos = self.mouse_x, self.mouse_y
                    c = colorize(label_id)
                    drawOutlinedText(
                        field_painter,
                        *pos,
                        str(label_id),
                        c,
                        None,
                        ct_size
                    )
                # if no label found, check for closest traces
                else:
                    # check for ztrace segments
                    if not closest:
                        closest = self.section_layer.getZsegment(self.mouse_x, self.mouse_y)
                        closest_type = "ztrace_seg"
                    
                    # draw name of closest trace
                    if closest:
                        if closest_type == "trace":
                            name = closest.name
                            if closest.negative:
                                name += " (negative)"
                        elif closest_type == "ztrace_seg":
                            name = f"{closest.name} (ztrace)"
                        # ztrace tuple returned
                        elif closest_type == "ztrace_pt":
                            closest = closest[0]
                            name = f"{closest.name} (ztrace)"
                        # flag returned
                        elif closest_type == "flag":
                            name = closest.name
                        
                        if self.series.getOption("display_closest"):
                            # set up the corner display for the attributes
                            if closest_type in ("trace", "flag"):
                                if closest != self.displayed_item:
                                    self.closeHoverDisplay()
                                    self.displayed_item = closest
                                    self.hover_display_timer.start(1000)
                                close_hover_display = False

                            # display the name of the item by the mouse
                            mouse_x, mouse_y = self.mouse_x, self.mouse_y
                            if self.series.getOption("left_handed"): mouse_x += 10
                            c = closest.color
                            drawOutlinedText(
                                field_painter,
                                mouse_x, mouse_y,
                                name,
                                c,
                                None,
                                ct_size,
                                not self.series.getOption("left_handed")
                            )
            elif self.mouse_mode == HOST and self.hosted_trace:
                # set up text position
                mouse_x, mouse_y = self.mouse_x, self.mouse_y
                if self.series.getOption("left_handed"): mouse_x += 10
                # display the proposed host relationship by the mouse
                t = [
                    self.hosted_trace.name,
                    " hosted by ",
                    closest.name if closest_type == "trace" else "..."
                ]
                t_copy = t.copy()
                for i, text in enumerate(t_copy):
                    for j in range(len(t_copy)):
                        if j < i:
                            t[i] = " "*len(t_copy[j]) + t[i]
                        elif j > i:
                            t[i] += " "*len(t_copy[j])
                c = [
                    self.hosted_trace.color,
                    (255, 255, 255),
                    closest.color if closest_type == "trace" else (255, 255, 255)
                ]
                for text, color in zip(t, c):
                    drawOutlinedText(
                        field_painter,
                        mouse_x, mouse_y,
                        text,
                        color,
                        None,
                        ct_size,
                        not self.series.getOption("left_handed")
                    )
            
            # get the names of the selected traces
            names = {}
            counter = 0
            height = self.height()
            for trace in self.section.selected_traces:
                # check for max number
                if counter * (st_size + 10) + 20 > height / 3:
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
                if counter * (st_size + 10) + 20 > height / 3:
                    names["..."] = 1
                    break
                if ztrace.name in names:
                    names[ztrace.name] += 1
                else:
                    names[ztrace.name] = 1
                    counter += 1
            self.selected_ztrace_names = names

        # draw the names of the blended sections
        if self.blend_sections and self.b_section:
            y += 20
            drawOutlinedText(
                field_painter,
                x, y,
                f"Blended sections: {self.b_section.n} and {self.section.n}",
                (255, 255, 255),
                (0, 0, 0),
                st_size,
                right_justified
            )
            y += st_size
        
        # draw the number of selected flags
        if self.section.selected_flags:
            y += 20
            l = len(self.section.selected_flags)
            drawOutlinedText(
                field_painter,
                x, y,
                f"{l} flag{'s' if l > 1 else ''} selected",
                (255, 255, 255),
                (0, 0, 0),
                st_size,
                right_justified
            )
            y += st_size
        
        # draw the names of the selected traces
        if self.selected_trace_names:
            y += 20
            drawOutlinedText(
                field_painter,
                x, y,
                "Selected Traces:",
                (255, 255, 255),
                (0, 0, 0),
                st_size,
                right_justified
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
                    right_justified
                )
            y += st_size
        
        # draw the names of the selected ztraces
        if self.selected_ztrace_names:
            y += 20
            drawOutlinedText(
                field_painter,
                x, y,
                "Selected Ztraces:",
                (255, 255, 255),
                (0, 0, 0),
                st_size,
                right_justified
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
                    right_justified
                )
            y += st_size
        
        # close the flag display if needed
        if close_hover_display:
            self.closeHoverDisplay()

        # update the status bar
        if not self.is_panzooming:
            if closest_type == "flag":
                self.updateStatusBar()
            else:
                self.updateStatusBar(closest)
    
    def closeHoverDisplay(self):
        """Close the hover information display."""
        if self.hover_display:
            self.hover_display.close()
            self.hover_display = None
        self.displayed_item = None
        if self.hover_display_timer.isActive():
            self.hover_display_timer.stop()
    
    def displayHoverInfo(self):
        """Display the information for an item that has been hovered over."""
        text = ""
        if type(self.displayed_item) is Flag:
            # create text edit display for comments
            comments = []
            for c in self.displayed_item.comments:
                t = c.text.replace("\n", "<br>")
                comments.append(
                    f"<b>{c.user}</b> ({c.date}):<br>{t}"
                )
            text = "<hr>".join(comments)
        elif type(self.displayed_item) is Trace:
            t = self.displayed_item
            lines = []
            # lines.append([f"<b>{t.name}</b>"])
            def addLine(header, desc):
                if desc: lines.append(f"<b>{header}</b> {desc}")
            
            addLine("Host:", ", ".join(self.series.getObjHosts(t.name)))
            addLine("Comment:", self.series.getAttr(t.name, "comment"))
            addLine("Object Alignment:", self.series.getAttr(t.name, "alignment"))
            addLine("Object Groups:", ", ".join(self.series.object_groups.getObjectGroups(t.name)))
            addLine("Trace Tags:", ", ".join(t.tags))
            cat_cols = self.series.getAttr(t.name, "user_columns")
            for col_name, opt in cat_cols.items():
                addLine(f"{col_name}:", opt)

            text = "<hr>".join(lines)
        
        if not text:
            return
        
        # create the widget
        self.hover_display = QTextEdit(self.mainwindow, text=text)
        # show
        self.hover_display.show()
        # adjust the width and height
        self.hover_display.resize(self.width() // 5, 1)
        h = self.hover_display.document().size().toSize().height() + 3
        if h == 3:
            self.hover_display.setText("X")
            h = self.hover_display.document().size().toSize().height()
            self.hover_display.setText("")
        elif h > self.height() - 6:
            h = self.height() - 6
        self.hover_display.resize(self.width() // 5, h)
        # move to proper location
        right_justified = self.mainwindow.mouse_palette.mode_x <= .5
        if right_justified:
            self.hover_display.move(
                self.x() + self.width() - self.hover_display.width() - 3,
                self.y() + self.height() - self.hover_display.height() - 3
            )
        else:
            self.hover_display.move(
                self.x() + 3,
                self.y() + self.height() - self.hover_display.height() - 3
            )
        # scroll all the way down
        sb = self.hover_display.verticalScrollBar()
        sb.setValue(sb.maximum())