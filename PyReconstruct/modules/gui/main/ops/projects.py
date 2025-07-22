"""Application project methods."""

from pathlib import Path

from PyReconstruct.modules.gui.dialog import FileDialog
from PyReconstruct.modules.gui.utils import notify, notifyConfirm
from PyReconstruct.modules.backend.imports import modules_available
from PyReconstruct.modules.backend.remote import download_vol_as_tifs
from PyReconstruct.modules.constants import kharris2015
from PyReconstruct.assets.scripts.projects import randomize_project, derandomize_project


class ProjectOperations:
    """Project operations for MainWindow."""

    def downloadExample(self):
        """Download example kharris2015 images to local machine."""
                
        if not modules_available(["cloudvolume", "tifffile"], notify=True):
            return

        confirm = notifyConfirm(
            "Harris2015 is a published volume (~2 nm/px, ~50 nm section thickness) from the "
            "middle of stratum radiatum in hippocampal area CA1 of an adult rat (p77). It is "
            "stored remotely at neurodata.io and a small subvolume of 10 sections can be "
            "downloaded here.\n\n"
            "See the publication:\n\n"
            "Harris et al. (2015) A resource from 3D electron microscopy of hippocampal "
            "neuropil for user training and tool development. Sci Data Sep 1;2:150046. PMID:"
            "26347348\n\n"
            "Click OK to select a location to store example images."
        )

        if not confirm: return

        download_dir = FileDialog.get(
                "dir",
                self,
                "Select folder to store images",
            )
        
        if not download_dir: return

        success = download_vol_as_tifs(
            kharris2015,
            [[2560, 4560], [2072, 4072], [48, 58]],
            output_dir=download_dir,
            output_prefix="harris2015"
        )

        if success:

            notify(
                "harris2015 example images downloaded successfully to:\n\n"
                f"{download_dir}\n\n"
                "Start a new series by going to File > New from images and selecting "
                "the downloaded images."
            )

        if not success:

            notify(
                "Something went wrong. Please try downloading example images again."
            )

    def randomizeProject(self):

        response = notifyConfirm(
            (
                "This feature randomizes images from multiple series, codes the images, "
                "and produces a single jser. You must provide a project directory that "
                "contains one to many subdirectories, each containing images for a "
                "series.<br><br>Something like this:"
                "<p style='font-family: monospace;'>&nbsp;&nbsp;project_dir<br>"
                "&nbsp;&nbsp;├── series_1<br>"
                "&nbsp;&nbsp;│   ├── 1.tif<br>"
                "&nbsp;&nbsp;│   └── 2.tif<br>"
                "&nbsp;&nbsp;└── series_2<br>"
                "&nbsp;&nbsp;&nbsp;&nbsp;    ├── 1.tif<br>"
                "&nbsp;&nbsp;&nbsp;&nbsp;    └── 2.tif</p>"
                "Would you like to continue to select a project directory?"
            )
        )
        if response == False:
            return

        project_dir = FileDialog.get(
            "dir",
            self,
            "Select a project directory",
        )
        if not project_dir: return

        response = notifyConfirm(
            (
                "You are about to randomize images for the following project:\n\n"
                f"{project_dir}\n\n"
                "Are you sure you want to proceed?"
            )
        )
        if response == False:
            return

        jser_coded = randomize_project(project_dir)
        
        notify(
            "Project randomized and ready in:\n\n"
            f"{jser_coded}\n\n"
            "Note: A file with decoding information (decode.txt) is available in "
            "the project dir. Do not lose that file -- you will need it later to "
            "de-randomize your images."
        )

    def derandomizeProject(self):

        response = notifyConfirm(
            "You are about to de-randomize and decode a project. "
            "Are you sure you want to continue to select a coded jser?"
        )

        if response == False:
            return

        coded_jser = FileDialog.get(
            "file",
            self,
            "Select coded jser",
            filter="*.jser"
        )

        if not coded_jser:
            return

        if self.series.jser_fp == coded_jser:

            notify(
                "You have this series open right now. Please save and close it "
                "before proceeding."
            )

            return

        decode_info = Path(coded_jser).parent / "decode.txt"

        if not decode_info.exists():
            
            notify(
                f"No decoding information available at:\n\n{decode_info}"
                "\n\nPlease make sure this file exists in the proper format. "
                "(This file was created when the project was randomized.)"
            )

            return

        response = notifyConfirm(
            (
                "You are about to de-randomize and decode the following project:\n\n"
                f"{coded_jser}\n\n"
                "Are you sure you want to proceed?"
            )
        )

        if response == False:
            return

        project_dir = derandomize_project(coded_jser)

        notify(
            "Project decoded and ready in:\n\n"
            f"{project_dir}"
        )


