"""Application series operations."""

import os
from typing import Optional, Union, List

from PySide6.QtCore import QSettings

from ..field.field_widget import FieldWidget

from PyReconstruct.modules.datatypes import Series
from PyReconstruct.modules.gui.palette import MousePalette
from PyReconstruct.modules.gui.dialog import FileDialog
from PyReconstruct.modules.gui.utils import get_hidden_dir


class SeriesOperations:

    def setup_series_obj (
            self,
            series_obj: Optional[Series],
            jser_fp: Union[str, List[str]]
    ) -> Optional[Series]:
        """Return a series object or None."""

        if not series_obj:  # no series object provided
            
            new_series = None

            if not jser_fp: # return if no jser filepath provided
                jser_fp = FileDialog.get("file", self, "Open Series", filter="*.jser")
                if not jser_fp:
                    return None

            ## Check for hidden series folder
            hidden_series_path = get_hidden_dir(jser_fp)
            new_series = self.processHiddenDir(hidden_series_path, jser_fp)

            ## Open jser if no unsaved data found
            if not new_series:
                new_series = Series.openJser(jser_fp)
                ## User cancelled
                if new_series is None:
                    if self.series is None:
                        exit()
                    else:
                        return None
            
            # clear the series
            if self.series and not self.series.isWelcomeSeries():
                self.series.close()

            return new_series

        else:  # series object provided
            
            if self.series and not self.series.isWelcomeSeries():
                self.series.close()  # clear current series
                
            return series_obj  # set new series


    def set_window_title(self):
        """Set main window title."""
        self.seriesModified(self.series.modified)

    def set_explorer_fp(self):
        """Set explorer filepath."""
        if not self.series.isWelcomeSeries() and self.series.jser_fp:
            settings = QSettings("KHLab", "PyReconstruct")
            settings.setValue("last_folder", os.path.dirname(self.series.jser_fp))

    def create_field(self):
        """Create field."""
        if self.field is not None:  # close previous field widget
            self.field.createField(self.series)
        else:
            self.field = FieldWidget(self.series, self)
            self.setCentralWidget(self.field)        

    def find_images(self):
        """Locate images."""
        
        images_found = self.field.section_layer.image_found
        is_zarr = self.field.section_layer.is_zarr_file

        if not images_found:
        
            src_path = os.path.join(
                os.path.dirname(self.series.jser_fp),
                os.path.basename(self.field.section.src)
            )

            if os.path.isfile(src_path):
                self.changeSrcDir(src_path)
            else:
                self.changeSrcDir(notify=True)  # prompt user to find images

        elif (images_found and
              is_zarr and
              not self.field.section_layer.is_scaled):  # prompt user to scale zarr
            reply = QMessageBox.question(
                self,
                "Zarr Scaling",
                "Zarr not scaled.\nWould you like to scale now?",
                QMessageBox.Yes,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.srcToZarr(create_new=False)

    def create_mouse_palette(self):
        """Create mouse palette and set current trace."""
        if self.mouse_palette: # close previous mouse dock
            self.mouse_palette.reset()
        else:
            self.mouse_palette = MousePalette(self)
            self.createPaletteShortcuts()
        palette_group, index = tuple(self.series.palette_index)
        self.changeTracingTrace(
            self.series.palette_traces[palette_group][index]
        ) # set the current trace

    def zarr_scaled_p(self):
        """Return true is zarr scaled."""
        is_zarr = self.field.section_layer.is_zarr_file
        try:
            scaled = self.field.section_layer.is_scaled
        except AttributeError:
            scaled = False

        test = all([is_zarr, scaled])
        print(f"{test = }")

        return all([is_zarr, scaled])

    def get_series_code(self):
        """Query user for series code if necessary."""
        if not self.series.isWelcomeSeries() and not self.series.code:
            detected_code = re.search(
                self.series.getOption("series_code_pattern"), 
                self.series.name
            )
            if detected_code:
                self.series.code = detected_code.group()
            self.setSeriesCode(cancelable=False)
            self.seriesModified()
            
