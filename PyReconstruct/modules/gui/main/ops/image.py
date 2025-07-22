"""Application image operations."""

import sys
import subprocess
from pathlib import Path

from PySide6.QtWidgets import QInputDialog, QMessageBox

from PyReconstruct.modules.gui.utils import notify
from PyReconstruct.modules.datatypes import Transform
from PyReconstruct.modules.gui.dialog import (
    FileDialog,
    AlignmentDialog,
    BCProfilesDialog,
    QuickDialog
)
from PyReconstruct.modules.constants import assets_dir
from PyReconstruct.modules.backend.func import determine_cpus
from PyReconstruct.modules.backend.view import optimizeSeriesBC


class ImageOperations:

    def changeSrcDir(self, new_src_dir : str = None, notify=False):
        """Open a series of dialogs to change the image source directory.
        
            Params:
                new_src_dir (str): the new image directory
                notify (bool): True if user is to be notified with a pop-up
        """
        if notify:
            reply = QMessageBox.question(
                self,
                "Images Not Found",
                "Images not found.\nWould you like to locate them?",
                QMessageBox.Yes,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        if new_src_dir is None:
            new_src_dir = FileDialog.get(
                "dir",
                self,
                "Select folder containing images",
            )
        if not new_src_dir: return
        
        self.series.src_dir = new_src_dir
        if self.field:
            self.field.reloadImage()
        self.seriesModified(True)
        
        # prompt user to scale zarr images if not scaled
        if (self.field.section_layer.image_found and 
            self.field.section_layer.is_zarr_file and
            not self.field.section_layer.is_scaled):
            reply = QMessageBox.question(
                self,
                "Zarr Scaling",
                "Zarr file not scaled.\nWould you like to update the zarr with scales?",
                QMessageBox.Yes,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.srcToZarr(create_new=False)
    
    def srcToZarr(self, create_new=True):
        """Convert the series images to scaled zarr."""
        if not self.field.section_layer.image_found:
            notify("Images not found.")
            return
        
        if self.field.section_layer.is_zarr_file and create_new:
            notify("Images are already scaled.")
            return
        
        elif not self.field.section_layer.is_zarr_file and not create_new:
            notify(
                "Images are not in zarr format.\n"
                "Please convert to zarr first."
            )
            return
        
        if create_new:
            zarr_fp = FileDialog.get(
                "save",
                self,
                "Convert Images to scaled zarr",
                file_name=f"{self.series.name}_images.zarr",
                filter="Zarr Directory (*.zarr)"
            )
            if not zarr_fp: return

        python_bin = sys.executable
        zarr_converter = Path(assets_dir) / "scripts/start_process.py"

        ## Determine number of cores to use
        cores = determine_cpus(  
            self.series.getOption("cpu_max")
        )
        
        if create_new:
            
            convert_cmd = [
                python_bin,
                str(zarr_converter.absolute()),
                "convert_zarr",
                str(cores),
                f"\"{self.series.src_dir}\"",
                zarr_fp
            ]
            
        else:
            
            convert_cmd = [
                python_bin,
                str(zarr_converter.absolute()),
                "convert_zarr",
                str(cores),
                f"\"{self.series.src_dir}\""
            ]

        if os.name == 'nt':

            subprocess.Popen(
                convert_cmd, creationflags=subprocess.CREATE_NO_WINDOW
            )
            
        else:

            convert_cmd = " ".join(convert_cmd)
            subprocess.Popen(convert_cmd, shell=True, stdout=None, stderr=None)

    def editImage(self, option : str, direction : str, log_event=True):
        """Edit the brightness or contrast of the image.
        
            Params:
                option (str): brightness or contrast
                direction (str): up or down
        """
        if option == "brightness" and direction == "up":
            self.field.changeBrightness(1)
        elif option == "brightness" and direction == "down":
            self.field.changeBrightness(-1)
        elif option == "contrast" and direction == "up":
            self.field.changeContrast(2)
        elif option == "contrast" and direction == "down":
            self.field.changeContrast(-2)
        self.mouse_palette.updateBC()
    
    def flickerSections(self):
        """Switch between the current and b sections."""
        if self.field.b_section:
            self.changeSection(self.field.b_section.n, save=False)

    def translate(self, direction : str, amount : str):
        """Translate the current transform.
        
            Params:
                direction (str): left, right, up, or down
                amount (str): small, med, or big
        """
        if amount == "small":
            num = self.series.getOption("small_dist")
        elif amount == "med":
            num = self.series.getOption("med_dist")
        elif amount == "big":
            num = self.series.getOption("big_dist")
        if direction == "left":
            x, y = -num, 0
        elif direction == "right":
            x, y = num, 0
        elif direction == "up":
            x, y = 0, num
        elif direction == "down":
            x, y = 0, -num
        self.field.translate(x, y)
    
    def changeTform(self, new_tform_list : list = None):
        """Open dialog to edit section transform."""        

        ## Ensure not in no-alignment
        if self.series.alignment == "no-alignment":
            notify(
                "Cannot edit section transform in alignment:\n\n\"no-alignment\"\n\n"
                "Change to another alignment by opening the alignment panel (ctrl + shift + A)."
            )
            return

        ## Check section lock status
        if self.field.section.align_locked:
            notify(
                "Unlock the section to adjust its transformation.\n\n"
                "(You can do this in the section list or "
                "you can unlock the current section with ctrl + shift + U)"
            )
            return
        
        if new_tform_list is None:
            current_tform = " ".join(
                [str(round(n, 5)) for n in self.field.section.tform.getList()]
            )
            new_tform_list, confirmed = QInputDialog.getText(
                self, "New Transform", "Edit section transform:", text=current_tform)
            if not confirmed:
                return
            try:
                new_tform_list = [float(n) for n in new_tform_list.split()]
                if len(new_tform_list) != 6:
                    return
            except ValueError:
                return

        self.field.changeTform(
            Transform(new_tform_list)
        )
    
    def newAlignment(self, new_alignment_name : str):
        """Add a new alignment (based on existing alignment).
        
            Params:
                new_alignment_name (str): the name of the new alignment
        """
        if new_alignment_name in self.field.section.tforms:
            QMessageBox.information(
                self,
                " ",
                "This alignment already exists.",
                QMessageBox.Ok
            )
            return
        self.series.newAlignment(
            new_alignment_name,
            self.series.alignment
        )
    
    def modifyAlignments(self):
        """Open dialog to modify alignments."""
        self.saveAllData()
        
        alignments = list(
            self.field.section.tforms.keys()
        )

        response, confirmed = AlignmentDialog(
            self,
            alignments,
            self.series.alignment
        ).exec()
        if not confirmed:
            return
        
        alignment_name, alignment_dict = response

        modified = False
        if alignment_dict:
            for k, v in alignment_dict.items():
                if k != v:
                    modified = True
                    break
            if modified:
                self.series.modifyAlignments(alignment_dict, self.field.series_states)
                self.createContextMenus()
        
        if alignment_name:
            self.changeAlignment(alignment_name, overwrite=True)
        else:
            self.changeAlignment(self.series.alignment, overwrite=True)

    def changeAlignment(self, new_alignment : str, overwrite=False):
        """Change the current series alignment.
        
            Params:
                alignment (str): the alignment to switch to
                overwrite (bool): change the alignment even if the name is the same
        """
        attr = getattr(self, f"{new_alignment}_alignment_act")
        attr.setChecked(True)

        current_alignment = self.series.alignment
        if overwrite or new_alignment != current_alignment:
            attr = getattr(self, f"{current_alignment}_alignment_act")  # generated from createContextMenu
            attr.setChecked(False)
            self.field.changeAlignment(new_alignment)
    
    def changeBCProfiles(self):
        """Open dialog to modify and change brightness/contrast profiles."""
        self.saveAllData()
        
        bc_profiles = list(
            self.field.section.bc_profiles.keys()
        )

        response, confirmed = BCProfilesDialog(
            self,
            bc_profiles,
            self.series.bc_profile
        ).exec()
        if not confirmed:
            return
        
        profile_name, profiles_dict = response

        modified = False
        if profiles_dict:
            for k, v in profiles_dict.items():
                if k != v:
                    modified = True
                    break
            if modified:
                self.series.modifyBCProfiles(profiles_dict, self.field.series_states)
                self.field.reload()
        
        if profile_name:
            self.field.changeBCProfile(profile_name)
        elif modified:
            self.field.changeBCProfile(self.series.bc_profile)
            
    def calibrateMag(self, trace_lengths : dict = None):
        """Calibrate the pixel size for the series.
        
            Params:
                trace_lengths (dict): the lengths of traces to calibrate
        """
        self.saveAllData()
        
        if trace_lengths is None:
            # gather trace names
            names = []
            for trace in self.field.section.selected_traces:
                if trace.name not in names:
                    names.append(trace.name)
            
            if len(names) == 0:
                notify("Please select traces for calibration.")
            
            # prompt user for length of each trace name
            trace_lengths = {}
            for name in names:
                d, confirmed = QInputDialog.getText(
                    self,
                    "Trace Length",
                    f'Length of "{name}" in microns:'
                )
                if not confirmed:
                    return
                try:
                    d = float(d)
                except ValueError:
                    return
                trace_lengths[name] = d
        
        self.field.calibrateMag(trace_lengths)
    
    def setSeriesMag(self):
        """Manually set (or view) the series magnification."""
        response, confirmed = QInputDialog.getDouble(
            self, 
            "Set Magnification", 
            "Series magnification (microns per image pixel):",
            self.series.avg_mag,
            decimals=8,
            step = 0.001
        )
        if not confirmed:
            return
        if response <= 0:
            notify("Magnification cannot be less than or equal to zero.")
        
        self.saveAllData()
        
        self.field.setMag(response)
    
    def optimizeBC(self, sections : list = None):
        """Optimize the brightness and contrast of the series.
        
            Params:
                sections (list): the list of section numbers
        """
        structure = [
            ["Mean (0-255):", ("int", 128, range(256))],
            ["Standard Devation:", ("float", 60)],
            [("radio", ("Use full image", True), ("Use current window view only", False))],
        ]
        response, confirmed = QuickDialog.get(self, structure, "Optimize Images")
        if not confirmed:
            return
        
        mean = response[0]
        std = response[1]
        full_image = response[2][0][1]
        
        if not noUndoWarning():
            return
        
        if sections is None:
            sections = list(self.series.sections.keys())
        
        optimizeSeriesBC(
            self.series, 
            mean,
            std,
            sections,
            None if full_image else self.series.window.copy()
        )
        self.field.reload()
        self.field.table_manager.updateSections(sections)
    
    
