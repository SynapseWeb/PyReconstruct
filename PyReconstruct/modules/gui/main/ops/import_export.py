"""Application import and export operations."""

import sys
import json
import subprocess
from pathlib import Path

from PySide6.QtWidgets import QInputDialog

from PyReconstruct.modules.datatypes import Trace
from PyReconstruct.modules.gui.dialog import FileDialog, QuickDialog
from PyReconstruct.modules.gui.utils import notify
from PyReconstruct.modules.backend.imports import modules_available, Roi
from PyReconstruct.modules.backend.func import jsonToXML, importTransforms, importSwiftTransforms
from PyReconstruct.modules.constants import assets_dir


class ImportExportOperations:

    def exportToXML(self, export_fp : str = None):
        """Export the current series to XML.
        
            Params:
                export_fp (str): the filepath for the XML .ser file
        """

        ## Save current data
        self.saveAllData()

        ## Get new xml series filepath from user
        if not export_fp:
            export_fp = FileDialog.get(
                "save",
                self,
                "Export Series",
                file_name=f"{self.series.name}.ser",
                filter="XML Series (*.ser)"
            )
            if not export_fp: return False
        
        ## Convert series
        jsonToXML(self.series, os.path.dirname(export_fp))

        notify(f"Legacy series (xml) exported to:\n\n{os.path.dirname(export_fp)}")
    
    def importTransforms(self, tforms_fp : str = None):
        """Import transforms from a text file.
        
            Params:
                tforms_file (str): the filepath for the transforms file
        """
        self.saveAllData()
        # get file from user
        if tforms_fp is None:
            tforms_fp = FileDialog.get(
                "file",
                self,
                "Select file containing transforms"
            )
        if not tforms_fp: return
        
        # import the transforms
        importTransforms(self.series, tforms_fp, series_states=self.field.series_states)
        
        # reload the section
        self.field.reload()

        # refresh the data and lists
        self.field.table_manager.recreateTables()

        notify("Transforms imported successfully.")

    def importSwiftTransforms(self, swift_fp=None):
        """Import transforms from a text file.
        
            Params:
                swift_fp (str): the filepath for the transforms file
        """

        self.saveAllData()
        
        # get file from user
        if not swift_fp:
            swift_fp = FileDialog.get("file", self, "Select SWiFT project file")
            
        if not swift_fp:
            return

        # get scales from the swift project file
        with open(swift_fp, "r") as fp: swift_json = json.load(fp)

        scale_names = swift_json.get("level_data")

        if scale_names:  # new swift project file formatting
        
            scale_names = list(swift_json["level_data"].keys())
            scales_available = [int(scale[1:]) for scale in scale_names]

        else:  # old swift project file formatting

            scales_data = swift_json["data"]["scales"]
            scale_names = list(scales_data.keys())
            scales_available = [int(scale[6:]) for scale in scale_names]

        scales_available.sort()
        
        print(f'Available SWiFT project scales: {scales_available}')

        structure = [
            ["Scale:", (True, "combo", [str(s) for s in scales_available])],
            [("check", ("Includes cal grid", False))]
        ]

        response, confirmed = QuickDialog.get(self, structure, "Import SWiFT Transforms")
        if not confirmed:
            return
        scale = response[0]
        cal_grid = response[1][0][1]

        # import transforms
        print(f'Importing SWiFT transforms at scale {scale}...')
        if cal_grid: print('Cal grid included in series')
        
        importSwiftTransforms(
            self.series,
            swift_fp,
            scale,
            cal_grid,
            series_states=self.field.series_states
        )
        
        self.field.reload()

        # refresh the data and lists
        self.field.table_manager.recreateTables()

        notify("Transforms imported successfully.")
    
    def exportToZarr(self):
        """Export series as a neuroglancer-compatible zarr."""

        if not modules_available("dask"):

            notify(
                "The 'dask' module (needed to rechunk your zarr after conversion) is not "
                "available, but conversion will continue with a chunk size of (1, 256, 256)."
            )

        all_sections = sorted(list(self.series.sections.keys()))

        ## Get options from user
        
        structure = [
            ["From section", ("int", all_sections[1]),
             "to section", ("int", all_sections[-1]), " "],
            ["Group padding (px):", ("int", 50)],
            ["Groups:"],
            [("multicombo", self.series.object_groups.getGroupList(), None)],
            [("check", ("Export all tissue", True))]
        ]
        
        response, confirmed = QuickDialog.get(self, structure, "Create Neuroglancer Zarr", spacing=10)

        if not confirmed: return
        
        start, end, padding = response[0:3]
        groups = " ".join(response[3])
        max_tissue = response[4][0][1]

        ## Ask for save location

        ser_name = self.series.name

        output = FileDialog.get(
            "save",
            self,
            "Save as zarr",
            filter="*.zarr",
            file_name=f"{ser_name}-ng-export.zarr"
        )
        
        if not output: return

        if max_tissue:

            args = {
                
                "--groups"        : groups,
                "--start_section" : start,
                "--end_section"   : end,
                "--max_tissue"    : max_tissue,
                "--output"        : output
                
            }
            
        else:

            args = {
                
                "--start_section" : start,
                "--end_section"   : end,
                "--output"        : output,
                "--groups"        : groups,
                
            }

        python_bin = sys.executable
        zarr_converter = Path(assets_dir) / "scripts/start_process.py"
        
        convert_cmd = [
            python_bin,
            str(zarr_converter.absolute()),
            "create_ng_zarr",
            f"\"{self.series.jser_fp}\""
        ]

        for argname, arg in args.items():
            if arg or arg == 0:
                if type(arg) is bool:
                    convert_cmd.append(argname)
                else:
                    
                    if argname == "--output":

                        convert_cmd += [
                            "--output",
                            f"\"{arg}\""
                        ]
                        
                    else:

                        convert_cmd += [argname] + str(arg).split()

        if os.name == 'nt':

            subprocess.Popen(
                convert_cmd,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
        else:

            convert_cmd = " ".join(convert_cmd)
            subprocess.Popen(convert_cmd, shell=True, stdout=None, stderr=None)
    
    def exportSectionSVG(self):
        """Export untransformed traces as svg."""

        if not modules_available("svgwrite", notify=True):
            return

        self.saveToJser()

        s = self.series.current_section

        fp = FileDialog.get(
            "save",
            self,
            "Save section as svg",
            filter="*.svg",
            file_name=f"{self.series.name}_{s}.svg"
        )
        if not fp: return
        
        svg = self.series.loadSection(s).exportAsSVG(fp)
        
        notify(f"Traces exported to file:\n\n{svg}")

    def exportSectionPNG(self):
        """Export untransformed traces as png."""

        if not modules_available(["svgwrite", "cairosvg"], notify=True):
            return

        self.saveToJser()

        s = self.series.current_section

        fp = FileDialog.get(
            "save",
            self,
            "Save section as png",
            filter="*.png",
            file_name=f"{self.series.name}_{s}.png"
        )
        if not fp: return

        scale, confirmed = QInputDialog.getText(
            self,
            "Resolution",
            "Scale image (Full resolution = 1.0):",
            text='1.0'
        )
        if not confirmed:
            return False
        
        png = self.series.loadSection(s).exportAsPNG(fp, float(scale))
        
        notify(f"Traces exported to file:\n\n{png}")

    def importROIFiles(self):
        """Import traces from ImageJ .roi files."""

        fps = FileDialog.get("files", self, "Select .roi file(s)", filter="*.roi")

        if not fps:
            return None

        h, _ = self.field.section.img_dims
        mag = self.field.section.mag

        for fp in fps:

            print(f"Importing {fp}")

            roi = Roi(fp)
            coords = roi.get_field_coordinates(h, mag)  # px -> coords

            trace = Trace(
                Path(fp).stem,
                (255, 255, 0)
            )

            self.field.newTrace(
                coords,
                trace,
                points_as_pix=False,  # provide as coordinates
                closed=roi.closed,
                reduce_points=False,
                simplify=False
            )

        notify(".roi files imported as traces.")

    def exportROIFiles(self):
        """Export traces as ImageJ .roi files."""

        directory = FileDialog.get("dir", self, "Select directory to export .roi files.")

        if not directory:
            return

        h, _ = self.field.section.img_dims
        mag = self.field.section.mag

        contours = self.field.section.contours

        for _, contour in contours.items():
            for trace in contour.traces:
                exporter = RoiExporter(trace, mag, h)
                exporter.export_roi(directory)

        notify("Traces exported as .roi files.")

    def exportTracePaletteCSV(self):
        """Export the current trace palette as CSV file."""
        name = self.series.palette_index[0]
        fp = FileDialog.get(
            "save",
            self,
            "Export Trace Palette",
            filter="*.csv",
            file_name=f"{name}.csv"
        )
        if not fp: return

        self.series.exportTracePaletteCSV(fp)
    
    def importTracePaletteCSV(self):
        """Import a trace palette from a CSV file."""
        fp = FileDialog.get(
            "file",
            self,
            "Import Trace Palette",
            filter="*.csv"
        )
        if not fp: return

        # get the new name of the palette
        name = os.path.basename(fp)
        name = name[:name.rfind(".")]

        i = 0
        while name in self.series.palette_traces:
            i += 1
            name = f"{name}-{i}"

        self.series.importTracePaletteCSV(fp, name)
        self.series.palette_index[0] = name

        self.mouse_palette.reset()

        notify(
            f"Trace palette '{name}' successfully imported.\n" +
            f"Press {self.series.getOption('modifytracepalette_act')} to view all palettes."
        )
    
