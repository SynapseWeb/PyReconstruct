import os
import time

from PySide6.QtWidgets import (
    QMainWindow,
    QTextEdit,
)
from PySide6.QtGui import (
    QPainter,
    QCursor,
    QAction
)
from PySide6.QtCore import (
    QTimer,
    Qt
)

from PyReconstruct.modules.datatypes import Series, Section, Trace, Transform
from PyReconstruct.modules.backend.view import SectionLayer, ZarrLayer
from PyReconstruct.modules.backend.func import SeriesStates
from PyReconstruct.modules.backend.table import TableManager


class FieldWidgetBase:
    """
    Initialize the defaults and their types.
    Define the generateView function.
    Handle the series states.
    Handle section changes.
    Handle the table manager.
    Handling reloading the view (when section data is changed).
    """
    
    def initAttrs(self, series : Series, mainwindow : QMainWindow):
        
        self.mainwindow                     = mainwindow
        self.series                         = series

        self.section : Section              = None
        self.b_section : Section            = None
        
        self.pixmap_dim : tuple             = None
        self.section_layer : SectionLayer   = None

        self.table_manager : TableManager   = None
        self.focus_table_id : int           = None

        self.propagate_tform : bool         = False

        self.hide_trace_layer : bool        = False
        self.show_all_traces : bool         = False
        self.hide_image : bool              = False
        self.blend_sections : bool          = False

        self.current_trace : list           = []
        self.moving_traces : list           = None
        self.moving_points : list           = None
        self.moving_flags : list            = None

        self.mouse_mode : int               = 0

        self.is_selecting_traces : bool     = False
        self.is_drawing_rad : bool          = False
        self.is_line_tracing : bool         = False
        self.is_moving_trace : bool         = False
        self.is_panzooming : bool           = False
        self.is_gesturing : bool            = False
        self.is_scissoring : bool           = False

        self.closed_trace_shape             = "trace"

        self.tracing_trace : Trace          = None
        self.hosted_trace : Trace           = None

        self.mouse_x : int                  = 0
        self.mouse_y : int                  = 0
        self.clicked_x : int                = 0
        self.clicked_y : int                = 0
        self.clicked_trace                  = None

        self.lclick : bool                  = False
        self.rclick : bool                  = False
        self.mclick : bool                  = False

        self.mouse_boundary_timer : QTimer  = None
        self.hover_display_timer : QTimer   = None
        self.hover_display : QTextEdit      = None
        self.displayed_item                 = None

        self.single_click : bool            = False
        self.click_time : float             = None
        self.max_click_time : float         = 0.15

        self.timer : QTimer                 = None
        self.time : str                     = None

        self.selected_trace_names : set     = {}
        self.selected_ztrace_names : set    = {}

        self.pencil_r : QCursor             = None
        self.pencil_l : QCursor             = None

        self.edit_flag_event : QAction      = None
    
    def createField(self, series : Series):
        """Re-creates the field widget when a new series is opened.
        
            Params:
                series (Series): the new series to load
        """
        self.series = series 

        ## Close manager if exists
        if self.table_manager:
            self.table_manager.closeAll()

        ## Load section
        self.section = self.series.loadSection(self.series.current_section)
        
        ## Load/clear series states
        self.clearStates()
        self.series_states[self.section]  # initialize the current section

        ## Create section view
        self.section_layer = SectionLayer(self.section, self.series)

        ## Create zarr view if applicable
        self.createZarrLayer()
        
        ## Reset b section and layer
        self.b_section = None
        self.b_section_layer = None

        ## Hide/show defaults
        self.hide_trace_layer = False
        self.show_all_traces = False
        self.hide_image = False

        ## Propagate tform defaults
        self.propagate_tform = False
        self.stored_tform = Transform.identity()
        self.propagated_sections = set()

        ## Clear copy/paste clipboard
        self.clipboard = []

        ## Create new manager
        self.table_manager = TableManager(
            self.series,
            self.section,
            self.series_states,
            self.mainwindow,
        )

        ## Reset cursor
        self.mouse_mode = 0
        self.setCursor(QCursor(Qt.ArrowCursor))
        
        ## Ensure first section is found
        if self.series.current_section not in self.series.sections:
            self.series.current_section = self.series.sections.keys()[0]

        # GUI defaults
        self.tracing_trace = Trace("TRACE", (255, 0, 255))
        self.status_list = ["Section: " + str(self.series.current_section)]
        
        ## Blend default
        self.blend_sections       = False
        
        ## Click defaults
        self.lclick               = False
        self.rclick               = False
        self.mclick               = False

        ## Mouse tool defaults
        self.is_panzooming        = False
        self.is_gesturing         = False
        self.is_line_tracing      = False
        self.is_moving_trace      = False
        self.is_selecting_traces  = False
        self.is_scissoring        = False
        self.closed_trace_shape   = "trace"

        ## Clear selected
        self.selected_trace_names = {}
        self.selected_ztrace_names = {}

        ## Set up timer
        if not self.series.isWelcomeSeries():
            self.time = str(round(time.time()))
            open(os.path.join(self.series.getwdir(), self.time), "w").close()
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.markTime)
            self.timer.start(5000)

        self.generateView()
    
    def createZarrLayer(self):
        """Create a zarr layer."""
        if self.series.zarr_overlay_fp and self.series.zarr_overlay_group:
            self.zarr_layer = ZarrLayer(self.series)
        else:
            self.zarr_layer = None
    
    def resizeWindow(self, pixmap_dim : tuple) -> None:
        """Convert the window to match the proportions of the pixmap.

        Nothing is returned; self.series.window is modified.
        
            Params:
                pixmap_dim (tuple): the w and h of the pixmap view
        """
        # get dimensions of field window and pixmap
        window_x, window_y, window_w, window_h = tuple(self.series.window)
        if window_w == 0: window_w = 1e-3
        if window_h == 0: window_h = 1e-3  # prevent dividing by zero
        pixmap_w, pixmap_h = tuple(pixmap_dim)
        window_ratio = window_w/window_h
        pixmap_ratio = pixmap_w / pixmap_h

        # resize window to match proportions of current geometry
        if abs(window_ratio - pixmap_ratio) > 1e-6:
            # increase the width
            if window_ratio < pixmap_ratio: 
                new_w = window_h * pixmap_ratio
                new_x = window_x - (new_w - window_w) / 2
                window_w = new_w
                window_x = new_x
            # increase the height
            else:
                new_h = window_w / pixmap_ratio
                new_y = window_y - (new_h - window_h) / 2
                window_h = new_h
                window_y = new_y
            self.series.window = [window_x, window_y, window_w, window_h]
    
    def generateView(self, generate_image=True, generate_traces=True, update=True) -> None:
        """Generate the output view.

        Nothing is returned: self.field_pixmap is set with the view.
        
            Params:
                generate_image (bool): True if image should be regenerated
                generate_traces (bool): True if traces should be regenerated
                update (bool): True if view widget should be updated
        """
        ## Resize series window to match view proportions
        self.resizeWindow(self.pixmap_dim)

        ## Calculate scaling
        _, _, window_w, window_h = tuple(self.series.window)
        pixmap_w, pixmap_h = tuple(self.pixmap_dim)
        
        ## Scaling: Screen pixels to image pixels ratio (should be equal)
        x_scaling = pixmap_w / (window_w / self.section.mag)
        y_scaling = pixmap_h / (window_h / self.section.mag)
        
        assert(abs(x_scaling - y_scaling) < 1e-6)
        
        self.scaling = x_scaling

        ## Generate section view
        view = self.section_layer.generateView(
            self.pixmap_dim,
            self.series.window,
            generate_image=generate_image,
            generate_traces=generate_traces,
            hide_traces=self.hide_trace_layer,
            show_all_traces=self.show_all_traces,
            hide_image=self.hide_image
        )

        # blend b section if requested
        if self.blend_sections and self.b_section is not None:
            # generate b section view
            b_view = self.b_section_layer.generateView(
                self.pixmap_dim,
                self.series.window,
                generate_image=generate_image,
                generate_traces=generate_traces,
                hide_traces=self.hide_trace_layer,
                show_all_traces=self.show_all_traces,
                hide_image=self.hide_image
            )
            # overlay a and b sections
            painter = QPainter(view)
            painter.setOpacity(0.5)
            painter.drawPixmap(0, 0, b_view)
            painter.end()
        
        # overlay zarr if requested
        if self.zarr_layer:
            zarr_layer = self.zarr_layer.generateZarrLayer(
                self.section,
                self.pixmap_dim,
                self.series.window
            )
            if zarr_layer:
                painter = QPainter(view)
                if not self.hide_image:
                    painter.setOpacity(0.3)
                painter.drawPixmap(0, 0, zarr_layer)
                painter.end()
        
        self.field_pixmap = view

        # update the scale bar
        if self.mainwindow.mouse_palette:
            self.mainwindow.mouse_palette.setScale()

        self.mainwindow.checkActions()
        if update:
            self.update()
    
    def clearStates(self) -> None:
        """Create/clear the states for each section."""
        self.series_states = SeriesStates(self.series)

    def saveState(self) -> None:
        """Save the current traces and transform.
        
        ALSO updates the lists.
        """
        # save the current state
        section_states = self.series_states[self.series.current_section]
        section_states.addState(self.section, self.series)

        # update the data/tables
        self.updateData()

        # check if a series undo/redo has been overwritten
        self.series_states.checkOverwrite(self.section.n)

        # notify that the series has been edited
        self.mainwindow.seriesModified(True)
        self.mainwindow.checkActions()

    def undoState(self, redo=False) -> None:
        """Undo last action (switch to last state)."""
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return

        # end any pending events
        self.endPendingEvents()  # function extended in inherited class
        
        # clear selected straces
        self.section.selected_traces = []
        self.section.selected_ztraces = []

        # get the last undo state
        self.series_states.undoSection(self.section, redo)

        # update the data/tables
        self.updateData()
        
        self.generateView()
    
    def seriesUndo(self, redo=False) -> None:
        """Undo an action across the series.
        
            Params:
                redo (bool): True if should redo instead of undo
        """
        self.series_states.undoState(redo)
        self.reload()
        self.table_manager.recreateTables()
    
    def swapABsections(self) -> None:
        """Switch the A and B sections.
        
        Called when the user switches between the two currently loaded sections.
        """
        self.section, self.b_section = self.b_section, self.section
        self.section_layer, self.b_section_layer = self.b_section_layer, self.section_layer
        if self.section is not None:
            self.series.current_section = self.section.n
    
    def changeSection(self, new_section_num : int) -> None:
        """Change the displayed section.
        
            Params:
                new_section_num (int): the new section number to display
        """
        # check if requested section exists
        if new_section_num not in self.series.sections:
            return
        
        # check if already on section
        if new_section_num == self.series.current_section:
            return
        
        # move current section data to b section
        self.swapABsections()

        # load new section if required
        if new_section_num != self.series.current_section:
            # load section
            self.section = self.series.loadSection(new_section_num)
            # load section view
            self.section_layer = SectionLayer(self.section, self.series)
            # set new current section
            self.series.current_section = new_section_num
            # clear selected traces
            self.section.selected_traces = []
        
        # create section undo/redo state object if needed
        states = self.series_states[new_section_num]
        if not states.initialized:
            states.initialize(self.section, self.series)
        
        # reload trace list
        self.table_manager.changeSection(self.section)
        
        # propagate transform if requested
        if (self.propagate_tform and
            not self.section.align_locked and
            new_section_num not in self.propagated_sections):
            current_tform = self.section.tform
            new_tform = self.stored_tform * current_tform
            self.section_layer.changeTform(new_tform)
            self.propagated_sections.add(new_section_num)

        # generate view and update status bar
        self.generateView()
    
    def reload(self, clear_states=False) -> None:
        """Reload the section data (used if section files were modified, usually through object list).
        
            Params:
                clear_states (bool): True if ALL undo states should be cleared (rare)
        """
        # reload the actual sections
        self.section = self.series.loadSection(self.series.current_section)
        self.section_layer.section = self.section
        self.table_manager.changeSection(self.section)
        if self.b_section:
            self.b_section = self.series.loadSection(self.b_section.n)
            self.b_section_layer.section = self.b_section
        # clear all the section states
        if clear_states:
            self.clearStates()
        # clear the selected traces
        self.section.selected_traces = []
        if self.b_section:
            self.b_section.selected_traces = []
        # update the palette
        self.mainwindow.mouse_palette.updateBC()
        
        self.generateView()

        # notify that the series has been modified
        self.mainwindow.seriesModified(True)
    
    def reloadImage(self) -> None:
        """Reload the section images (used if transform or image source is modified)."""
        self.section_layer.loadImage()
        if self.b_section is not None:
            self.b_section_layer.loadImage()
        self.generateView()
    
    def openList(self, list_type : str):
        """Open a list.
        
            Params:
                list_type (str): object, trace, section, ztrace, or flag
        """
        self.table_manager.newTable(list_type, self.section)
    
    def updateData(self, clear_tracking=True) -> None:
        """Update the series data object and the tables.
        
            Params:
                clear_tracking (bool): True if tracking vars in Section and Series should be cleared after they are checked
        """
        # update the series data tracker
        self.series.data.updateSection(
            self.section, 
            update_traces=True,
            all_traces=False
        )

        self.table_manager.updateAll(clear_tracking)
        
    def update(self) -> None: ...
