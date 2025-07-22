"""Application 3D operations."""

from typing import Union, List

from PyReconstruct.modules.gui.dialog import FileDialog
from PyReconstruct.modules.gui.utils import notify
from PyReconstruct.modules.gui.popup import CustomPlotter
from PyReconstruct.modules.backend.volume import export3DObjects, export3DData


class ThreeDimensionalOperations:

    def addTo3D(self, names, ztraces=False):
        """Generate the 3D view for a list of objects.
        
            Params:
                obj_names (list): a list of object names
        """
        self.saveAllData()
        
        if not self.viewer or self.viewer.is_closed:
            
            self.viewer = CustomPlotter(self, names, ztraces)
            
        else:
            
            if ztraces:
                self.viewer.addToScene([], names)
            else:
                self.viewer.addToScene(names, [])
        
        self.viewer.activateWindow()
        
    def removeFrom3D(self, obj_names: list, ztraces: Union[List, None]=None):
        """Remove objects from 3D viewer.
        
            Params:
                obj_names (list): a list of object names
        """
        self.saveAllData()
        
        if not self.viewer or self.viewer.is_closed:
            return
        
        if ztraces:
            
            self.viewer.removeObjects(None, ztraces)
            
        else:
            
            self.viewer.removeObjects(obj_names, None)

        self.viewer.activateWindow()

    def exportAs3D(self, obj_names, export_type, ztraces=False):
        """Export 3D objects."""
        self.saveAllData()
        export_dir = FileDialog.get(
                "dir",
                self,
                "Select folder to export objects to",
            )
        if not export_dir: return
        export3DObjects(self.series, obj_names, export_dir, export_type)

    def export3DData(self, obj_names):
        """Export quantitative data from meshes."""
        
        notify(
            f"3D surface area and volume measurements depend on the meshing algorithm "
            f"implemented in PyReconstruct. We recommend verifying proper mesh quality by "
            f"inspecting objects in the 3D scene before analyzing quantitative data.\n\n"
            f"Click OK to specificy where to save this data."
        )
        
        self.saveAllData()
        
        output_fp = FileDialog.get(
            "save", self, "Save data as CSV file", "*.csv", "mesh_data.csv"
        )
        if not output_fp: return

        export3DData(self.series, obj_names, output_fp)
    
    def load3DScene(self):
        """Load a 3D scene."""
        load_fp = FileDialog.get(
            "file",
            self,
            "Load 3D Scene",
            "JSON file (*.json)"
        )
        if not load_fp:
            return
        
        if not self.viewer or self.viewer.is_closed:
            self.viewer = CustomPlotter(self, load_fp=load_fp)
        else:
            self.viewer.loadScene(load_fp)
        
        self.viewer.setFocus()
        
