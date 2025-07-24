"""Application file operations.

Create/open/save series, backups, etc.
"""

import os
import shutil
import time
from typing import Tuple, Optional
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QInputDialog, QMessageBox

from PyReconstruct.modules.datatypes import Series
from PyReconstruct.modules.gui.palette import MousePalette
from PyReconstruct.modules.gui.utils import (
    get_welcome_setup,
    saveNotify,
    unsavedNotify,
    get_hidden_dir
)
from PyReconstruct.modules.gui.dialog import FileDialog, BackupDialog, BackupCommentDialog
from PyReconstruct.modules.backend.func import xmlToJSON
from PyReconstruct.modules.backend.autoseg import zarrToNewSeries

from ..field.field_widget import FieldWidget


class FileOperations:
    """File operations for MainWindow."""
    
    def openWelcomeSeries(self):
        """Open a welcome series."""

        w_ser, w_secs, w_src = get_welcome_setup()
        welcome_series = Series(w_ser, w_secs)
        welcome_series.src_dir = w_src
            
        self.openSeries(series_obj=welcome_series)
        
    def openSeries(self, series_obj=None, jser_fp=None, query_prev=True):
        """Open an existing series and create the field.
        
            Params:
                series_obj (Series): the series object (optional)
                query_prev (bool): True if query user about saving data
        """

        should_continue, first_open = self.prepOpenSeries(query_prev)
        
        if not should_continue:
            return  # exit if user cancelled
    
        if not series_obj:  # if no series obj provided
            
            ## Get new series
            new_series = None

            if not jser_fp: # return if no series provided
                jser_fp = FileDialog.get("file", self, "Open Series", filter="*.jser")
                if not jser_fp:
                    return

            ## Check for hidden series folder
            hidden_series_path = get_hidden_dir(jser_fp)
            new_series = self.processHiddenDir(hidden_series_path, jser_fp)

            # open the JSER file if no unsaved series was opened
            if not new_series:
                new_series = Series.openJser(jser_fp)
                # user pressed cancel
                if new_series is None:
                    if self.series is None:
                        exit()
                    else:
                        return
            
            # clear the series
            if self.series and not self.series.isWelcomeSeries():
                self.series.close()

            self.series = new_series

        # else series already provided
        else:
            # clear current series
            if self.series and not self.series.isWelcomeSeries():
                self.series.close()
                
            # set new series
            self.series = series_obj
        
        # set the title of the main window
        self.seriesModified(self.series.modified)

        # set explorer filepath
        if not self.series.isWelcomeSeries() and self.series.jser_fp:
            settings = QSettings("KHLab", "PyReconstruct")
            settings.setValue("last_folder", os.path.dirname(self.series.jser_fp))

        # create field
        if self.field is not None:  # close previous field widget
            self.field.createField(self.series)
        else:
            self.field = FieldWidget(self.series, self)
            self.setCentralWidget(self.field)

        # create mouse palette
        if self.mouse_palette: # close previous mouse dock
            self.mouse_palette.reset()
        else:
            self.mouse_palette = MousePalette(self)
            self.createPaletteShortcuts()
        palette_group, index = tuple(self.series.palette_index)
        self.changeTracingTrace(
            self.series.palette_traces[palette_group][index]
        ) # set the current trace

        # ensure that images are found
        if not self.field.section_layer.image_found:
            # check jser directory
            src_path = os.path.join(
                os.path.dirname(self.series.jser_fp),
                os.path.basename(self.field.section.src)
            )
            images_found = os.path.isfile(src_path)
            
            if images_found:
                self.changeSrcDir(src_path)
            else:
                self.changeSrcDir(notify=True)
        # prompt user to scale zarr images if not scaled
        elif (self.field.section_layer.image_found and 
            self.field.section_layer.is_zarr_file and
            not self.field.section_layer.is_scaled):
            reply = QMessageBox.question(
                self,
                "Zarr Scaling",
                "Zarr not scaled.\nWould you like to scale now?",
                QMessageBox.Yes,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.srcToZarr(create_new=False)
        
        # get the series code from the user if needed
        if not self.series.isWelcomeSeries() and not self.series.code:
            detected_code = re.search(
                self.series.getOption("series_code_pattern"), 
                self.series.name
            )
            if detected_code:
                self.series.code = detected_code.group()
            self.setSeriesCode(cancelable=False)
            self.seriesModified()
        
        # notify new users of any warnings
        if not first_open:
            self.notifyNewEditor()
        
        # create the menus
        self.createMenuBar()
        self.createContextMenus()
        if not self.actions_initialized:
            self.createShortcuts()
        self.actions_initialized = True

        # add the series to recently opened
        self.addToRecentSeries()
        
    def prepOpenSeries(self, query_prev=True) -> Tuple[bool, bool]:
        """Prepare to open an existing series.

        Returns:
            tuple: (should_continue, first_open)
                - should_continue: False if operation should be cancelled
                - first_open: True if this is the first series opened this session
        """

        if self.series:  # series open and save yes
            first_open = False
            if query_prev:
                response = self.saveToJser(notify=True, close=True)
                if response == "cancel":
                    return False, False  # indicate user cancelled operation
                else:
                    pass
            else:
                self.series.close()
        else:
            first_open = True  # first series to open this session
    
        return True, first_open
    
    def processHiddenDir(self, hidden_series_path: Path, jser_fp: str) -> Optional[Series]:
        """Process a hidden directory."""

        if not hidden_series_path.exists():
            return

        new_series = None
        new_series_fp = ""
        sections = {}

        for f in hidden_series_path.iterdir():
            
            ## Check if series is currently being worked on
            if not f.name.count('.'):  # no extension = timer file
                current_time = round(time.time())
                time_diff = current_time - int(f.name)

                if time_diff <= 7:  # the series is currently being operated on
                    QMessageBox.information(
                        self,
                        "Series In Use",
                        "This series is already open in another window.",
                        QMessageBox.Ok
                    )

                    if not self.series:
                        exit()
                    else:
                        return
            else:
                ext = f.suffix[1:]  # Remove the leading dot
                if ext.isnumeric():
                    sections[int(ext)] = f.name
                elif ext == "ser":
                    new_series_fp = f

        ## If .ser file found
        if new_series_fp:
            ## Query user about opening previously unsaved series
            open_unsaved = unsavedNotify()
            if open_unsaved:
                new_series = Series(str(new_series_fp), sections)
                new_series.modified = True
                new_series.jser_fp = jser_fp
            else:
                # remove the folder if not needed
                for f in hidden_series_path.iterdir():
                    f.unlink()  # Delete file
                    hidden_series_path.rmdir()  # Remove directory
        else:
            # remove the folder if no series file detected
            for f in hidden_series_path.iterdir():
                f.unlink()  # Delete file
            shutil.rmtree(hidden_series_path)  # Remove directory

        return new_series

    def newSeries(
        self,
        image_locations : list = None,
        series_name : str = None,
        mag : float = None,
        thickness : float = None,
        from_zarr : bool = False
    ):
        """Create a new series from a set of images.
        
            Params:
                image_locations (list): the filepaths for the section images.
        """

        ## Save existing backend series
        self.saveToJser(notify=True, close=False)
        
        ## Query user for images
        if not image_locations:
            if from_zarr:
                valid_zarr = False
                while not valid_zarr:
                    zarr_fp = FileDialog.get(
                        "dir",
                        self,
                        "Select Zarr"
                    )
                    if not zarr_fp: return
                    
                    # get the image names in the zarr
                    if "scale_1" in os.listdir(zarr_fp):
                        valid_zarr = True
                        image_locations = []
                        for f in os.listdir(os.path.join(zarr_fp, "scale_1")):
                            if not f.startswith("."):
                                image_locations.append(os.path.join(zarr_fp, "scale_1", f))
                    else:
                        notify("Please select a valid zarr file.")                
            else:
                image_locations = FileDialog.get(
                    "files",
                    self,
                    "Select Images",
                    filter="*.jpg *.jpeg *.png *.tif *.tiff *.bmp"
                )
                if len(image_locations) == 0: return
        
        ## Query user for series name
        if series_name is None:
            series_name, confirmed = QInputDialog.getText(
                self, "New Series", "Enter series name:")
            if not confirmed:
                return
            
        ## Query user for calibration (microns per px)
        if mag is None:
            mag, confirmed = QInputDialog.getDouble(
                self, "New Series", "Enter image calibration (μm/px):",
                0.00254, minValue=0.000001, decimals=6)
            if not confirmed:
                return
            
        ## Query user for section thickness (microns)
        if thickness is None:
            thickness, confirmed = QInputDialog.getDouble(
                self, "New Series", "Enter section thickness (μm):",
                0.05, minValue=0.000001, decimals=6)
            if not confirmed:
                return

        ## Create new series
        series = Series.new(
            sorted(image_locations),
            series_name,
            mag,
            thickness
        )
    
        ## Open series
        ## No need to query user about saving prev (already done above)
        self.openSeries(series, query_prev=False)

        ## Set view to entire image
        self.field.home()

        ## Prompt user to save series
        self.saveAsToJser()
    
    def newFromXML(self, series_fp : str = None):
        """Create a new series from a set of XML files.
        
            Params:
                series_fp (str): the filepath for the XML series
        """

        # get xml series from user
        if not series_fp:
            series_fp = FileDialog.get(
                "file",
                self,
                "Select XML Series",
                filter="*.ser"
            )
            if not series_fp: return  # exit function if no series provided

        # convert the series
        series = xmlToJSON(os.path.dirname(series_fp))

        if not series:
            return

        # open new series
        self.openSeries(series)

        # prompt user to save series
        self.saveAsToJser()
    
    def newFromNgZarr(self):
        """Create a new series from a neuroglancer zarr."""
        zarr_fp = FileDialog.get(
            "dir",
            self,
            "Select Zarr File"
        )
        if not zarr_fp:
            return
                
        if not zarr_fp.endswith("zarr"):
            notify("Selected file is not a valid zarr.")
        
        groups = [f for f in os.listdir(zarr_fp) if not f.startswith(".") and not f=="raw"]

        structure = [
            ["New series name:", (True, "text", ""), " "],
            ["Labels to import:"],
            [("multicombo", groups, [])],
        ]
        response, confirmed = QuickDialog.get(self, structure, "New from NG Zarr")
        if not confirmed:
            return
        
        name = response[0]
        label_groups = [g for g in response[1] if g in groups]

        series = zarrToNewSeries(zarr_fp, label_groups, name)

        if not series:
            return

        # open new series
        self.openSeries(series)

        # set view to home
        self.field.home()

        # prompt user to save series
        self.saveAsToJser()
    
    def saveAllData(self):
        """Write current series and section data into hidden files."""

        if self.series.isWelcomeSeries():
            return

        self.field.section.save(update_series_data=False)

        self.series.save()

    def saveToJser(self, notify=False, close=False):
        """Store data in JSER file.
        
        Params:
            notify (bool): If true, display notification.
            close (bool): If true, delete hidden series files.
        """

        ## If welcome series, close without saving
        if self.series.isWelcomeSeries():
            return

        ## Populate hidden files with unsaved data
        self.saveAllData()

        ## Notify (query) user when series modified
        if notify and self.series.modified:
            save = saveNotify()
            if save == "no":
                if close:
                    self.series.close()
                return
            elif save == "cancel":
                return "cancel"
        
        # User closing and series not modified
        if close and not self.series.modified:
            self.series.close()
            return

        ## Save-as if no jser filepath
        if not self.series.jser_fp:
            self.saveAsToJser(close=close)
        else:  
            self.backup(check_auto=True)
            self.series.saveJser(close=close)
        
        # mark series as unmodified
        self.seriesModified(False)

    def saveAsToJser(self, close=False):
        """Prompt user for save location."""
        
        ## Store series data in hidden files
        self.saveAllData()

        ## If welcome series, close without saving
        if self.series.isWelcomeSeries():
            return

        ## Query user for location
        new_jser_fp = FileDialog.get(
            "save",
            self,
            "Save Series",
            filter="*.jser",
            file_name=f"{self.series.name}.jser"
        )
        if not new_jser_fp: return
        
        ## Move hidden folder to new jser directory        
        self.series.move(
            new_jser_fp,
            self.field.section,
            self.field.b_section
        )
        
        # clear section states
        self.field.series_states.clear()
        self.field.series_states[self.field.section]
        if self.field.b_section:
            self.field.series_states[self.field.b_section]
        
        # save file
        self.backup(check_auto=True)
        self.series.saveJser(close=close)

        # mark series as unmodified
        self.seriesModified(False)
    
    def backup(self, check_auto=False, comment=""):
        """Automatically backup the jser if requested."""
        if check_auto and not self.series.getOption("autobackup"):
            return
        
        # make sure the backup directory exists
        if not os.path.isdir(self.series.getOption("backup_dir")):
            notify(
                "Backup folder not found.\n" + 
                "Please set the backup folder in following dialog."
            )
            self.series.setOption("backup_dir", "")
            self.setBackup()
        
        # double check if user entered a valid backup directory
        if os.path.isdir(self.series.getOption("backup_dir")):
            fp = self.series.getBackupPath(comment)
            self.series.saveJser(fp)
        else:
            notify(
                "Backup folder not found.\n" +
                "Backup file not saved."
            )
            self.series.setOption("backup_dir", "")
            self.series.setOption("autobackup", False)
    
    def setBackup(self):
        """Set up backup directory and settings."""
        confirmed = BackupDialog(self, self.series).exec()
        self.seriesModified()
    
    def manualBackup(self):
        """Back up series to a specified location."""
        self.saveAllData()

        response, confirmed = BackupCommentDialog(self, self.series).exec()
        if not confirmed:
            return
        
        comment, open_settings = response
        if open_settings:
            self.setBackup()
            self.manualBackup()
        else:
            self.backup(comment=comment)
    
