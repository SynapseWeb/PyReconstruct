"""Application view operations.

Trace visibility and opacity, scale bar, curation toggle, etc.
"""

import os

from PySide6.QtWidgets import QInputDialog, QApplication
from PySide6.QtGui import QPainter, QImage, QPixmap
from PySide6.QtCore import Qt

from PyReconstruct.modules.datatypes import Trace
from PyReconstruct.modules.gui.palette import ZarrPalette
from PyReconstruct.modules.gui.dialog import FileDialog, ImportSeriesDialog, QuickDialog
from PyReconstruct.modules.gui.utils import notify, get_center_pixel
from PyReconstruct.modules.backend.autoseg import labelsToObjects


class ViewOperations:

    def setFillOpacity(self, opacity : float = None):
        """Set the opacity of the trace highlight.
        
            Params:
                opacity (float): the new fill opacity
        """
        if opacity is None:
            opacity, confirmed = QInputDialog.getText(
                self,
                "Fill Opacity",
                "Enter fill opacity (0-1):",
                text=str(round(self.series.getOption("fill_opacity"), 3))
            )
            if not confirmed:
                return
        
        try:
            opacity = float(opacity)
        except ValueError:
            return
        
        if not (0 <= opacity <= 1):
            return
        
        self.series.setOption("fill_opacity", opacity)
        self.field.generateView(generate_image=False)
    
    def toggleZtraces(self):
        """Toggle whether ztraces are shown."""
        self.field.deselectAllTraces()
        self.series.setOption("show_ztraces", not self.series.getOption("show_ztraces"))
        self.field.generateView(generate_image=False)
    
    def setZarrLayer(self, zarr_dir=None):
        """Set a zarr layer."""
        if not zarr_dir:
            zarr_dir = FileDialog.get(
                "dir",
                self,
                "Select overlay zarr",
            )
            if not zarr_dir: return

        self.series.zarr_overlay_fp = zarr_dir
        self.series.zarr_overlay_group = None

        groups = []
        for g in os.listdir(zarr_dir):
            if os.path.isdir(os.path.join(zarr_dir, g)):
                groups.append(g)

        self.zarr_palette = ZarrPalette(groups, self)
    
    def setLayerGroup(self, group_name):
        """Set the specific group displayed in the zarr layer."""
        if not group_name:
            group_name = None
        if self.zarr_palette.cb.currentText != group_name:
            self.zarr_palette.cb.setCurrentText(group_name)
        self.series.zarr_overlay_group = group_name
        self.field.createZarrLayer()
        self.field.generateView()
    
    def removeZarrLayer(self):
        """Remove an existing zarr layer."""
        self.series.zarr_overlay_fp = None
        self.series.zarr_overlay_group = None
        if self.zarr_palette:
            self.zarr_palette.close()
        self.field.createZarrLayer()
        self.field.generateView()

    def hideSeriesTraces(self, hidden=True):
        """Hide or unhide all traces in the entire series.
        
            Params:
                hidden (bool) True if traces will be hidden
        """
        self.saveAllData()
        self.series.hideAllTraces(hidden)
        self.field.reload()
    
    def setFindZoom(self):
        """Set the magnification for find contour."""
        z, confirmed = QInputDialog.getInt(
            self,
            "Find Contour Zoom",
            "Enter the find contour zoom (0-100):",
            value=self.series.getOption("find_zoom"),
            minValue=0,
            maxValue=100
        )
        if not confirmed:
            return

        self.series.setOption("find_zoom", z)
    
    def importFromSeries(self):
        """Import from another series."""
        jser_fp = FileDialog.get(
            "file",
            self,
            "Select Series",
            filter="*.jser"
        )
        if not jser_fp: return  # exit function if user does not provide series

        self.saveAllData()

        # open the other series
        o_series = Series.openJser(jser_fp)

        # check the manigifcations
        if not checkMag(self.series, o_series):
            o_series.close()
            return
        
        response, confirmed = ImportSeriesDialog(self, self.series, o_series).exec()
        if not confirmed or not response:
            o_series.close()
            return
        
        if "traces" in response:
            (
                srange,
                regex_filters,
                group_filters,
                threshold,
                flag_conflicts,
                check_history,
                import_obj_attrs,
                keep_above,
                keep_below,
            ) = tuple(response["traces"])

            self.series.importTraces(
                o_series, 
                srange, 
                regex_filters,
                group_filters,
                threshold, 
                flag_conflicts, 
                check_history,
                import_obj_attrs,
                keep_above,
                keep_below, 
                self.field.series_states
            )
        
        if "z-traces" in response:
            regex_filters = response["z-traces"][0]
            import_attrs = response["z-traces"][1][0][1]
            self.series.importZtraces(
                o_series, 
                regex_filters,
                import_attrs,
                series_states=self.field.series_states
            )
            
        if "flags" in response:
            srange = (
                response["flags"][0],
                response["flags"][1] + 1
            )
            self.series.importFlags(
                o_series, 
                srange,
                self.field.series_states
            )
        
        if "attributes" in response:
            bools = [b for n, b in response["attributes"][0]]
            if bools[0]:
                self.series.importObjectGroups(o_series)
            if bools[1]:
                self.series.importHostTree(o_series)
            if bools[2]:
                self.series.importUserCols(o_series)
            if bools[3]:
                self.series.importZtraceGroups(o_series)
            if bools[4]:
                self.series.importObjAttrs(o_series)
        
        if "alignments" in response:
            import_as = response["alignments"]
            self.series.importTransforms(
                o_series,
                import_as,
                self.field.series_states
            )
            self.createContextMenus()

        if "palettes" in response:
            import_as = response["palettes"]
            self.series.importPalettes(  # cannot be undone
                o_series,
                import_as
            )

        if "brightness/contrast profiles" in response:
            import_as = response["brightness/contrast profiles"]
            self.series.importBC(  # cannot be undone
                o_series,
                import_as
            )

        # close other series
        o_series.close()

        # refresh the data and lists
        self.field.reload()
        self.field.table_manager.refresh()

        notify("Import successful.")
    
    def importFromZarrLabels(self):
        """Import label data from a neuroglancer zarr."""
        zarr_fp = FileDialog.get(
            "dir",
            self,
            "Select Zarr File"
        )
        if not zarr_fp:
            return
                
        if not zarr_fp.endswith("zarr"):  # TODO: Validate zarrs more appropriately
            notify("Selected file is not a valid zarr.")
        
        groups = [f for f in os.listdir(zarr_fp) if not f.startswith(".") and not f=="raw"]

        structure = [
            ["Label group names:"],
            [(True, "multicombo", groups, [])],
        ]
        response, confirmed = QuickDialog.get(self, structure, "Import Labels")
        if not confirmed:
            return
        
        groups = response[0]
        
        for group in groups:
            if group in os.listdir(zarr_fp):
                labelsToObjects(
                    self.series,
                    zarr_fp,
                    group,
                )
                self.field.reload()
        
    def toggleGroupViz(self, group):
        """Toggle visibility of a group."""

        group_viz = self.series.groups_visibility
        group_viz[group] = not group_viz[group]

        self.field.reload()
    
    def saveFieldView(self, save_to_file=False) -> None:
        """Export mainwindow to clipboard."""

        exported_image = QImage(
            self.rect().width(),
            self.rect().height(),
            QImage.Format_ARGB32
        )
        
        exported_image.fill(Qt.transparent)

        ## Draw base image
        with QPainter(exported_image) as painter:

            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

            painter.drawImage(
                exported_image.rect(),
                QImage(self.field.section.src_fp),
                self.rect()
            )

        ## Capture paint events in a separate step
        temp_pixmap = QPixmap(exported_image.size())
        temp_pixmap.fill(Qt.transparent)

        with QPainter(temp_pixmap) as temp_painter:
            
            # Call the widget's paint method and replay paint events
            self.render(
                temp_painter,
                QPoint(0, 0),  # target position
                QRegion(self.rect()),  # source region
                QWidget.RenderFlag.DrawChildren | QWidget.RenderFlag.DrawWindowBackground
            )

        ## Combine layers
        with QPainter(exported_image) as painter:
            painter.drawPixmap(0, 0, temp_pixmap)

        if save_to_file:

            fp = FileDialog.get(
                "save",
                self,
                "Field view",
                file_name=f"field_sec_{self.series.current_section}.png",
                filter="*.tif, *.tiff, *.jpeg, *jgp, *.png"
            )
            
            if not fp: return False
            
            exported_image.save(fp)

        else:
            
            ## Create clipboard and set
            clipboard = QApplication.clipboard()
        
            clipboard.setPixmap(
                QPixmap.fromImage(exported_image)
            )

        return None

    def addScaleBar(self):
        """Add scale bar to the field."""

        structure = [
            ["Width (μm):", (True, "float", 2.0), " "],
            ["Height (μm):", (True, "float", 0.2), " "]
        ]

        response, confirmed = QuickDialog.get(
            self, structure, "Scale bar settings"
        )
        
        if not confirmed:
            return

        w, h = response
        
        scale_bar_trace = Trace.get_scale_bar()
        pix_x, pix_y = get_center_pixel(self)

        self.field.placeGrid(
            pix_x, pix_y,
            scale_bar_trace,
            w, h, 0, 0, 1, 1,
            scale_bar=True
        )
    
    def toggleCuration(self):
        """Quick shortcut to toggle curation on/off for the tables."""
        self.field.table_manager.toggleCuration()
    
