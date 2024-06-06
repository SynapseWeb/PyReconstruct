import os
import re
import random
import vedo
import json
import numpy as np

from PySide6.QtWidgets import QMainWindow

from PyReconstruct.modules.gui.dialog import QuickDialog, FileDialog
from PyReconstruct.modules.gui.utils import populateMenuBar, notify, notifyConfirm
from PyReconstruct.modules.gui.table import Help3DWidget
from PyReconstruct.modules.backend.volume import generateVolumes
from PyReconstruct.modules.backend.threading import ThreadPoolProgBar
from PyReconstruct.modules.datatypes import Series

from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtk import vtkTransform

class VPlotter(vedo.Plotter):

    def __init__(self, qt_parent, *args, **kwargs):
        self.qt_parent = qt_parent
        self.mainwindow = qt_parent.mainwindow
        self.series = self.mainwindow.series
        super().__init__(*args, **kwargs)

        self.objs = SceneObjectList()

        self.selected_text = vedo.Text2D(pos="top-left", font="Courier")
        self.add(self.selected_text)
        self.selected = []

        self.pos_text = vedo.Text2D(pos="bottom-left", font="Courier")
        self.add(self.pos_text)
        self.add_callback("MouseMove", self.mouseMoveEvent)

        self.add_callback("LeftButtonClick", self.leftButtonClickEvent)
        self.click_time = None

        self.help_widget = None
        self.flash_on = False
        
    def getSectionFromZ(self, z):
        """Get the section number from a z coordinate."""
        snum = round(z / self.mainwindow.field.section.thickness)  # probably change this

        # if the section is not in the seris, find closest section
        all_sections = list(self.series.sections.keys())
        if snum not in all_sections:
            diffs = [abs(s - snum) for s in all_sections]
            snum = all_sections[diffs.index(min(diffs))]
        
        return snum
    
    def createScaleCube(self, attrs_dict=None):
        """Create the scale cube in the 3D scene."""
        sc_mesh = vedo.Cube(side=1, c=(150, 150, 150))
        sc_mesh.lw(5)
        name = attrs_dict["name"] if attrs_dict else "Scale Cube"
        sc_scene_obj = self.objs.add(sc_mesh, self.series, name, "scale_cube", (150, 150, 150), 1)
        if attrs_dict:
            sc_scene_obj.setColor(attrs_dict["color"])
            sc_scene_obj.setAlpha(attrs_dict["alpha"])
            sc_scene_obj.applyTform(attrs_dict["tform"])
        else:
            pos = self.camera.GetFocalPoint()  # get the approx center of the scene
            sc_scene_obj.translate(*pos)
        
        return sc_scene_obj

    def mouseMoveEvent(self, event):
        """Called when mouse is moved -- display coordinates."""
        msh = event.actor
        if not msh:
            self.pos_text.text("")
            self.render()
            return                       # mouse hits nothing, return.
        
        obj = self.objs[msh]
        name = obj.name
        if obj.series_fp != self.series.jser_fp:
            name += f" ({os.path.basename(obj.series_fp)[:-5]})"

        pt = event.picked3d                # 3d coords of point under mouse
        x, y, s = self.getFieldCoords(msh, pt)
        txt = f"{name}\nsection {s}\nx={x:.3f} y={y:.3f}"
        self.pos_text.text(txt)                    # update text message

        self.render()
    
    def updateSelected(self):
        """Update the selected names text."""
        # update the text
        if not self.selected:
            self.selected_text.text("")
        else:
            names = []
            for o in self.selected:
                name = o.name
                if o.series_fp != self.series.jser_fp:
                    name += f" ({os.path.basename(o.series_fp)[:-5]})"
                names.append(name)
            name_str = "\n".join(names[:5])
            if len(self.selected) > 5:
                name_str += "\n..."
            self.selected_text.text(f"Selected:\n{name_str}")

        # update the object highlight(s)
        for scene_obj in self.objs.values():
            if scene_obj in self.selected:
                if scene_obj.type == "scale_cube":
                    scene_obj.msh.color((64, 64, 64))
                else:
                    scene_obj.msh.lw(1)
            else:
                if scene_obj.type == "scale_cube":
                    scene_obj.msh.color(scene_obj.color)
                else:
                    scene_obj.msh.lw(0)
        
        self.render()
    
    def leftButtonClickEvent(self, event):
        """Called when left mouse button is clicked."""
        # record the time of click
        prev_click_time = self.click_time
        self.click_time = event.time
        # check for double clicks
        if prev_click_time is not None and self.click_time - prev_click_time < 0.25:
            msh = event.actor
            # check that mesh is in the current series
            if not msh or self.objs[msh].series_fp != self.series.jser_fp:
                return
            pt = event.picked3d                # 3d coords of point under mouse
            x, y, s = self.getFieldCoords(msh, pt)
            
            self.mainwindow.field.moveTo(s, x, y)
            self.mainwindow.activateWindow()
        
        msh = event.actor
        if not msh:
            return
        
        scene_obj = self.objs[msh]
        if scene_obj in self.selected:
            self.selected.remove(scene_obj)
        else:
            self.selected.append(scene_obj)

        self.updateSelected()

    def _keypress(self, iren, event):
        """Called when a key is pressed."""
        key = iren.GetKeySym()

        if "_L" in key or "_R" in key:
            return
        
        key = key.capitalize()

        if iren.GetShiftKey():
            key = "Shift+" + key

        if iren.GetControlKey():
            key = "Ctrl+" + key

        if iren.GetAltKey():
            key = "Alt+" + key
        
        overwrite = False

        if key in ("Left", "Right", "Up", "Down", "Ctrl+Up", "Ctrl+Down",
                   "Shift+S", "Shift+E", "Shift+F"):
            overwrite = True

        if key == "C":
            self.toggleScaleCube(not bool(self.objs.getType("scale_cube")))

        # direction key pressed
        elif any((direction in key) for direction in ("Left", "Right", "Up", "Down")):
            split_key = key.split("+")

            if "Shift" in split_key:
                fn = self.rotateSelected
                step = 10
            else:
                fn = self.translateSelected
                step = 0.1
            
            xyz = (0, 0, 0)

            if "Left" in key and "Ctrl" not in key:
                xyz = (-step, 0, 0)
            elif "Right" in key and "Ctrl" not in key:
                xyz = (step, 0, 0)
            elif "Up" in key:
                if "Ctrl" in key:
                    xyz = (0, 0, step)
                else:
                    xyz = (0, step, 0)
            elif "Down" in key:
                if "Ctrl" in key:
                    xyz = (0, 0, -step)
                else:
                    xyz = (0, -step, 0)
            
            fn(*xyz)
        
        # # custom opacity changer
        # elif key == "Bracketleft" or key == "Bracketright":
        #     self.incAlpha(0.05 * (-1 if key == "Bracketleft" else 1))
        
        # # select/deselect all
        # elif key == "Ctrl+D":
        #     self.selected = []
        #     self.updateSelected()
        # elif key == "Ctrl+A":
        #     self.selected = list(self.objs.values())
        #     self.updateSelected()
        
        # remove selected object from scene
        if key in ("Backspace", "Delete"):
            self.removeSelected()
        
        # # help menu
        # if key == "Shift+Question":
        #     overwrite = True
        #     self.showHelp()
        
        # # select all in host group
        # if key == "Shift+H":
        #     self.selectHostGroup()
        
        if set(("Ctrl", "Shift", "H")) == set(key.split("+")):
            self.organizeHostGroups()

        if not overwrite:
            super()._keypress(iren, event)
        else:
            self.render()
    
    def toggleScaleCube(self, show : bool = None, attrs=None):
        """Toggle the scale cube display in the scene.
        
            Params:
                show (bool): True if scale cube should be displayed
        """
        if show is None:
            show = not bool(self.objs.getType("scale_cube"))
        if show:
            sc_obj = self.createScaleCube(attrs)
            self.add(sc_obj.msh)
        else:
            for sc_obj in self.objs.getType("scale_cube"):
                self.objs.remove(sc_obj)
                self.remove(sc_obj.msh)
                if sc_obj in self.selected:
                    self.selected.remove(sc_obj)
                    self.updateSelected()
        # update the menubar display
        self.qt_parent.togglesc_act.setChecked(show)
    
    def modifySelected(self):
        """Modify the size and color of the scale cube."""
        if not self.selected:
            return
        
        only_scale_cubes = all((obj.type == "scale_cube") for obj in self.selected)
        
        # if only scale cubes being modified
        if only_scale_cubes:
            # get defaults
            if len(self.selected) == 1:
                sc_obj = self.selected[0]
                side_len = sc_obj.getSideLength()
                color = sc_obj.color
                alpha = sc_obj.alpha
                lw = sc_obj.msh.lw()
            else:
                side_len, color, alpha, lw = None, None, None, None
            
            structure = [
                ["Side length:", ("float", round(side_len, 4))],
                ["Color:", ("color", color)],
                ["Opacity (0-1):", ("float", alpha)],
                ["Outline width:", ("float", lw)]
            ]
            response, confirmed = QuickDialog.get(None, structure, "Scale Cube")
            if not confirmed:
                return
            
            side_len, color, alpha, lw = tuple(response)
            for sc_obj in self.selected:
                sc_obj : SceneObject
                if side_len:
                    sc_obj.msh.scale(side_len / sc_obj.getSideLength())
                if color:
                    sc_obj.setColor(color)
                if alpha:
                    sc_obj.setAlpha(alpha)
                if lw:
                    sc_obj.msh.lw(lw)

        # mixed objects being modified
        else:
            # get defaults
            if len(self.selected) == 1:
                obj = self.selected[0]
                color = obj.color
            else:
                color = None
            
            structure = [
                ["Color:", ("color", color)],
                ["Opacity (0-1):", ("float", alpha)],
            ]
            response, confirmed = QuickDialog.get(None, structure, "Scale Cube")
            if not confirmed:
                return
            
            color = response[0]
            alpha = response[1]
            for obj in self.selected:
                if color: obj.setColor(color)
                if alpha: obj.setAlpha(alpha)
        
        self.updateSelected()
        self.render()
    
    def incAlpha(self, i : float):
        """Increment the transparency of the selected meshes.
        
        Params:
            i (float): the value to increment the transparency
        """
        for scene_obj in self.selected:
            new_alpha = scene_obj.alpha + i
            scene_obj.setAlpha(new_alpha)
            if scene_obj.type == "object" and scene_obj.series_fp == self.series.jser_fp:
                self.series.setAttr(scene_obj.name, "3D_opacity", new_alpha)
        self.render()

        
    def translateSelected(self, dx : float, dy : float, dz : float):
        """Translate the selected meshes.
        
            Params:
                dx (float): the x translate
                dy (float): the y translate
                dz (float): the z translate
        """
        for scene_obj in self.selected:
            scene_obj.translate(dx, dy, dz)
    
    def rotateSelected(self, rx : float, ry : float, rz : float):
        """Rotate the selected meshes.
        
            Params:
                rx (float): the x rotate angle
                ry (float): the y rotate angle
                rz (float): the z rotate angle
        """
        if not self.selected:
            return
        
        # get the total cetner
        centers = [np.array(obj.center) for obj in self.selected]
        avg_center = tuple(sum(centers) / len(centers))

        # rotate the objs
        for scene_obj in self.selected:
            scene_obj.rotate(rx, ry, rz, avg_center)
            
    def removeFromScene(self, obj_names : list, ztrace_names : list, series_fp=None):
        """Remove objects and ztraces from the scene.
        
            Params:
                obj_names (list): the names of the objects to remove
                ztrace_names (list): the names of the ztraces to remove
        """
        if series_fp is None:
            series_fp = self.series.jser_fp
        
        scene_objs = []
        for name in obj_names:
            scene_obj = self.objs.search(name, "object", series_fp)
            if scene_obj: scene_objs.append(scene_obj)
        for name in ztrace_names:
            scene_obj = self.objs.search(name, "ztrace", series_fp)
            if scene_obj: scene_objs.append(scene_obj)
        for scene_obj in scene_objs:
            self.remove(scene_obj.msh)
            self.objs.remove(scene_obj)
            if scene_obj in self.selected:
                self.selected.remove(scene_obj)
        
        self.updateSelected()
        self.render()
    
    def placeInScene(self, result):
        """Called by addToScene after thread is completed"""
        # add objects and ztraces to scene
        mesh_data_list, series = result
        
        for md in mesh_data_list:
            vm = vedo.Mesh([md["vertices"], md["faces"]], md["color"], md["alpha"])
            obj = self.objs.add(vm, series, md["name"], md["type"], md["color"], md["alpha"])
            if md["tform"]:
                obj.applyTform(md["tform"])
            self.add(vm)
        self.render()
    
    def addToScene(self, objs : list, ztraces : list, remove_first=True, series=None):
        """Add objects to the scene.
        
            Params:
                objs (list): list of dictionaries containing object name, color, alpha, and tform (only names can also be provided)
                ztraces (list): list of dictionaries containing ztrace name, color, alpha, and tform (only names can also be provided)
                remove_first (bool): True if objects should be removed from scene first
                series (Series or str): the series or the filepath for the series containing the objects
        """
        if not (objs or ztraces):
            return
        
        # check if only names were provided and standardize the format
        if objs and type(objs[0]) is str:
            obj_names = objs
            objs = [{"name": s} for s in objs]
        else:
            obj_names = [o["name"] for o in objs]
        if ztraces and type(ztraces[0]) is str:
            ztrace_names = ztraces
            ztraces = [{"name": s} for s in ztraces]
        else:
            ztrace_names = [z["name"] for z in ztraces]
        
        # parse through the provided series
        if series is None:
            series = self.series
            series_fp = series.jser_fp
        elif type(series) is str:
            series_fp = series
            series = None
        elif type(series) is Series:
            series_fp = series.jser_fp

        # remove existing objects from scene
        if remove_first:
            self.removeFromScene(obj_names, ztrace_names, series_fp)
        
        # check for objects/ztraces that don't exist in the current series
        if series == self.series:  # operating from opened series
            # copy the lists
            obj_names = obj_names.copy()
            ztrace_names = ztrace_names.copy()

            # run check on both objects and ztraces
            for s, names, check_in in [
                ("object", obj_names, series.data["objects"]), 
                ("ztrace", ztrace_names, series.ztraces)
            ]:
                # check for objects that don't exist in the series
                removed = []
                for i, name in enumerate(names.copy()):
                    if name not in check_in:
                        removed.append(names.pop(i))
                if removed:
                    if not names:
                        notify(f"None of the requested {s}s exist in this series.")
                        return
                    else:
                        confirm = notifyConfirm(
                            f"The {s}(s) {', '.join(removed)} do not exist in this series.\n" +
                            f"Would you like to continue with the other {s}s?",
                            yn=True
                        )
                        if not confirm:
                            return

        # create threadpool
        self.threadpool = ThreadPoolProgBar()
        worker = self.threadpool.createWorker(
            generateVolumes,
            series if series else series_fp, 
            objs,
            ztraces
        )
        worker.signals.result.connect(self.placeInScene)
        self.threadpool.startAll(text="Generating 3D...", status_bar=self.mainwindow.statusbar)

    def showHelp(self):
        """Show the keyboard shortcuts available to the user."""
        if not self.help_widget or self.help_widget.closed:
            self.help_widget = Help3DWidget()
    
    def clear(self):
        """Clear the scene."""
        for scene_obj in list(self.objs.values()):
            self.objs.remove(scene_obj)
            self.remove(scene_obj.msh)
            self.selected = []
            self.updateSelected()
    
    def selectHostGroup(self):
        """Select the full host group for every selected object."""
        for scene_obj in self.selected.copy():
            scene_obj : SceneObject
            # skip if not an object
            if scene_obj.type != "object":
                continue
            # get the host group names
            host_group = self.objs.getHostGroup(scene_obj)
            # add the objects to selected
            for so in host_group:
                if so not in self.selected:
                    self.selected.append(so)
        self.updateSelected()
    
    def organizeScene(self, group_by_host=True, axis=0, spacing=0):
        """Space groups of scene objects.
        
            Params:
                group_by_host (True): organize objects by host groups if checked
                axis (int): the index of the axis to organize on
                spacing (float): the spacing to add between scene object groups
        """
        if group_by_host:
            # organize the objects into their host groups
            groups = []
            for scene_obj in self.objs.getType("object"):
                if not any([scene_obj in hg for hg in groups]):  # if obj group has not been found yet
                    groups.append(self.objs.getHostGroup(scene_obj))
        else:
            groups = []
            for scene_obj in self.objs.getType("object"):
                groups.append([scene_obj])
        
        # add the remaining ztraces to the groups (this should probnably be fixed somehow)
        for scene_obj in self.objs.getType("ztrace"):
            groups.append([scene_obj])
        
        # # clear the transform for each object
        # for group in groups:
        #     for obj in group:
        #         obj.clearTform()
        
        # get the bounds for each host group
        group_bounds = []
        for host_group in groups:
            bounds = host_group[0].bounds
            for scene_obj in host_group[1:]:
                bounds = combineBounds(bounds, scene_obj.bounds)
            group_bounds.append(bounds)
        
        # move each host group
        spacer = [0, 0, 0]  # space the objects from each other
        for host_group, bounds in zip(groups, group_bounds):
            size = tuple((b[1] - b[0]) for b in bounds) # x, y, z
            center = tuple(((b[1] + b[0]) / 2) for b in bounds)
            spacer[axis] += size[axis] / 2  # space along axis
            for scene_obj in host_group:
                x, y, z = center
                scene_obj.translate(
                    -x + spacer[0],
                    -y + spacer[1],
                    -z + spacer[2],
                )
            spacer[axis] += size[axis] / 2 + spacing
        
        # move the scale cube to origin if applicable
        for sc_obj in self.objs.getType("scale_cube"):
            sc_obj.msh.pos(0, 0, 0)
        
        self.show()

    def organizeHostGroups(self, spacing=0):
        """michael you better be wildly impressed by this"""
        # organize the objects into their host groups
        host_groups = []
        for scene_obj in self.objs.getType("object"):
            if not any([scene_obj in hg for hg in host_groups]):  # if obj group has not been found yet
                host_groups.append(self.objs.getHostGroup(scene_obj))
        
        self.spaceGroups(host_groups, spacing)
    
    def getFieldCoords(self, msh : vedo.Mesh, pt : tuple):
        """Get the coordinates for a point on a mesh."""
        # get the transform and apply its inverse to a point
        x, y, z = msh.get_transform().GetInverse().TransformFloatPoint(*pt)

        # get the section
        s = self.getSectionFromZ(z)

        return round(x, 3), round(y, 3), s

    def selectAll(self, select=True):
        """Select or deselect all the objects.
        
            Params:
                select (bool): True if all should be selected
        """
        self.selected = list(self.objs.values()) if select else []
        self.updateSelected()
    
    def removeSelected(self):
        """Remove the selected objects from the scene."""
        # check for scale_cube
        for scene_obj in self.selected.copy():
            if scene_obj.type == "scale_cube":
                self.toggleScaleCube()
                break
        # remove regular objects and ztraces
        for scene_obj in self.selected.copy():
            self.objs.remove(scene_obj)
            self.remove(scene_obj.msh)
            self.selected.remove(scene_obj)
        self.updateSelected()
    
    def clearTforms(self):
        """Clear the transforms for all of the objects."""
        for obj in self.objs.values():
            obj.clearTform()


class Container(QMainWindow):

    def closeEvent(self, event):
        self.centralWidget().close()
        super().closeEvent(event)


class CustomPlotter(QVTKRenderWindowInteractor):

    def __init__(self, mainwindow, names=[], ztraces=False, load_fp=None):
        # use container to create menubar
        self.container = Container()
        super().__init__(self.container)
        self.container.setCentralWidget(self)

        self.mainwindow = mainwindow
        self.series = self.mainwindow.series

        self.is_closed = False
        self.help_widget = None
        self.mouse_x = 0
        self.mouse_y = 0

        # Create vedo renderer
        self.plt = VPlotter(self, qt_widget=self)

        # create the menu bar
        menubar_list = [
            {
                "attr_name": "filemenu",
                "text": "File",
                "opts":
                [
                    ("savescene_act", "Save scene...", "", self.saveScene),
                    ("loadscene_act", "Load scene...", "", self.loadScene),
                    None,
                    {
                        "attr_name": "addtoscenemenu",
                        "text": "Add to scene",
                        "opts":
                        [
                            ("addtoscenefromsave_act", "From save file...", "", lambda : self.loadScene(add_only=True)),
                            ("addtoscenefromseries_act", "From other series...", "", self.addFromOtherSeries),
                        ]
                    }
                ]
            },
            {
                "attr_name": "editmenu",
                "text": "Edit",
                "opts":
                [
                    ("edit_act", "Edit attributes...", "Ctrl+E", self.plt.modifySelected),
                    None,
                    ("incalpha_act", "Increase opacity", "]", lambda : self.plt.incAlpha(0.1)),
                    ("decalpha_act", "Decrease opacity", "[", lambda : self.plt.incAlpha(-0.1)),
                    None,
                    ("clearmovements_act", "Clear movements", "", self.plt.clearTforms),
                ]
            },
            {
                "attr_name": "scenemenu",
                "text": "Scene",
                "opts":
                [
                    {
                        "attr_name": "selectmenu",
                        "text": "Select",
                        "opts":
                        [
                            ("selectall_act", "Select all", "Ctrl+A", self.plt.selectAll),
                            ("deselect_act", "Deselect all", "Ctrl+D", lambda : self.plt.selectAll(False)),
                            None,
                            ("selecthost_act", "Select object's host group", "Shift+H", self.plt.selectHostGroup)
                        ]
                    },
                    ("focusobjs_act", "Focus on objects", "Home", self.plt.show),
                    ("organize_act", "Organize scene", "Ctrl+Shift+H", self.organizeScene),
                ]
            },
            {
                "attr_name": "scmenu",
                "text": "Scale Cube",
                "opts":
                [
                    ("togglesc_act", "Display in scene", "checkbox", self.toggleScaleCube),
                ]
            },
            {
                "attr_name": "helpmenu",
                "text": "Help",
                "opts":
                [
                    ("shortcuts_act", "Shortcuts", "?", self.plt.showHelp)
                ]
            }
        ]
        self.menubar_widget = self.container.menuBar()
        self.menubar_widget.setNativeMenuBar(False)
        populateMenuBar(self, self.menubar_widget, menubar_list)

        # gerenate objects and display
        if load_fp:
            self.loadScene(load_fp)
        elif names:
            if ztraces:
                self.addZtraces(names, remove_first=False)
            else:
                self.addObjects(names, remove_first=False)
        
        self.plt.show(*self.plt.actors, resetcam=(False if load_fp else None))
        self.show()
        self.container.show()
    
    # CONVENIENCE FUNCTIONS (connect to add/remove scene functions)
    def addObjects(self, obj_names, remove_first=True):
        self.plt.addToScene(obj_names, [], remove_first)
    def removeObjects(self, obj_names):
        self.plt.removeFromScene(obj_names, [])
    def addZtraces(self, ztrace_names, remove_first=True):
        self.plt.addToScene([], ztrace_names, remove_first)
    def removeZtraces(self, ztrace_names):
        self.plt.removeFromScene([], ztrace_names)
    
    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        self.plt._keypress(self, event)
    
    def toggleScaleCube(self):
        """Toggle the scale cube."""
        self.plt.toggleScaleCube(
            self.togglesc_act.isChecked()
        )
    
    def moveScaleCubeHelp(self):
        """Inform the user of how to move the scale cube."""
        notify(sc_help_message)
    
    def clearScene(self):
        """Clear the scene."""
        self.plt.clear()

    def saveScene(self):
        """Save the 3D scene to be opened later."""
        save_fp = FileDialog.get(
            "save",
            self,
            "Save 3D Scene",
            "JSON File (*.json)",
            "scene.json"
        )
        if not save_fp:
            return

        # get the object information
        d = {"scene_objects": self.plt.objs.getExportDict()}
        
        # get the camera attributes
        d["camera"] = {}
        d["camera"]["position"] = self.plt.camera.GetPosition()
        d["camera"]["focal_point"] = self.plt.camera.GetFocalPoint()
        d["camera"]["view_up"] = self.plt.camera.GetViewUp()
        d["camera"]["distance"] = self.plt.camera.GetDistance()

        with open(save_fp, "w") as f:
            json.dump(d, f)
    
    def loadScene(self, load_fp : str = None, add_only=False):
        """Load a scene.
        
            Params:
                load_fp (str): the filepath to the saved scene.
        """
        if not load_fp:
            load_fp = FileDialog.get(
                "file",
                self,
                "Load 3D Scene",
                "JSON file (*.json)"
            )
            if not load_fp:
                return
        
        # load the JSON file
        with open(load_fp, "r") as f:
            d = json.load(f)
        
        # clear the plot if not adding to the scene
        if not add_only:
            self.clearScene()
        
        # add the objects to the scene and match attributes
        for fp, scene_objs in d["scene_objects"]["series_fps"].items():
            series = self.series if fp == self.series.jser_fp else fp
            objs = scene_objs["objects"]
            ztraces = scene_objs["ztraces"]
            self.plt.addToScene(objs, ztraces, series=series)
        
        # add scale cube if making from new
        if not add_only:
            for sc_dict in d["scene_objects"]["scale_cubes"]:
                self.plt.toggleScaleCube(True, sc_dict)

        # move the camera if making from new
        if not add_only:
            self.plt.camera.SetPosition(d["camera"]["position"])
            self.plt.camera.SetFocalPoint(d["camera"]["focal_point"])
            self.plt.camera.SetViewUp(d["camera"]["view_up"])
            self.plt.camera.SetDistance(d["camera"]["distance"])
            self.plt.show(resetcam=False)
    
    def addFromOtherSeries(self):
        """Add objects or ztrace from another series."""
        # prompt the user for the series
        jser_fp = FileDialog.get(
            "file",
            self,
            "Find Series",
            "*.jser"
        )
        if not jser_fp:
            return

        # open the series
        series = Series.openJser(jser_fp)

        # get the possible traces and ztraces from the other series
        obj_names = list(series.data["objects"].keys())
        ztrace_names = list(series.ztraces.keys())

        # prompt the user to select the object and ztraces (include regex)
        structure = [
            ["Objects (regex accepted):"],
            [("multicombo", obj_names, [], False)],
            ["Ztraces (regex accepted):"],
            [("multicombo", ztrace_names, [], False)],
        ]
        response, confirmed = QuickDialog.get(self, structure, "Add to Scene")
        if not confirmed:
            return

        # get the object and ztrace names
        included_objs = []
        included_ztraces = []
        for requested, name_pool, included in (
            (response[0], obj_names, included_objs),
            (response[1], ztrace_names, included_ztraces)
        ):
            for pattern in requested:
                for name in name_pool:
                    if bool(re.fullmatch(pattern, name)):
                        included.append(name)

        # add to the scene
        self.plt.addToScene(included_objs, included_ztraces, series=series)
    
    def organizeScene(self):
        """Organize the scene by arranging objects in a row."""
        structure = [
            ["This action will line up the objects in the scene side-by-side."],
            [" "],
            ["Line up objects:"],
            [("radio", ("by host group", True), ("individually", False))],
            ["Along the:"],
            [("radio", ("x-axis", True), ("y-axis", False), ("z-axis", False))],
            ["Space between objects:", (True, "float", 0), " "],
        ]
        response, confirmed = QuickDialog.get(self, structure, "Organize Scene")
        if not confirmed:
            return
        
        group_by_host = response[0][0][1]
        for i in range(3):
            if response[1][i][1]: axis = i
        spacing = response[2]

        self.plt.organizeScene(group_by_host, axis, spacing)
    
    def closeEvent(self, event):
        self.plt.close()
        self.is_closed = True
        self.container = None
        super().closeEvent(event)


class SceneObject():

    def __init__(self, msh : vedo.Mesh, series : Series, name : str, type : str, color : tuple, alpha : float):
        """Create the 3D scene object.
        
            Params:
                msh (vedo.Mesh): the mesh object
                series (Series): the series containing this object
                name (str): the name of the object
                type (str): object, ztrace, or scale_cube
                color (tuple): the color of the object
                alpha (float): the 0-1 transparency of the object
        """
        self.msh = msh
        self.series_fp = series.jser_fp
        self.name = name
        self.type = type
        self.color = color
        self.alpha = alpha
        self.id = None
    
    def setID(self, new_id : str):
        """Set the ID of the scene object."""
        self.id = new_id
        self.msh.metadata["id"] = new_id
    
    def setColor(self, new_color : tuple):
        """Set the color of the object."""
        self.msh.color(new_color)
        self.color = new_color
    
    def setAlpha(self, new_alpha : float):
        """Set the transparency of the object."""
        self.msh.alpha(new_alpha)
        self.alpha = new_alpha
    
    @property
    def center(self):
        return self.msh.center_of_mass()
    
    def translate(self, dx=0, dy=0, dz=0):
        """Translate the mesh in space."""
        self.msh.shift(dx, dy, dz)
    
    def rotate(self, rx=0, ry=0, rz=0, c=None):
        """Rotate the mesh."""
        if c is None:
            c = self.msh.center_of_mass()
        if rx: self.msh.rotate_x(rx, around=c)
        if ry: self.msh.rotate_y(ry, around=c)
        if rz: self.msh.rotate_z(rz, around=c)
    
    @property
    def tform(self):
        fn = self.msh.get_transform().GetMatrix().GetElement
        m = [[fn(i, j) for j in range(4)] for i in range(4)]
        return m
    
    def clearTform(self):
        """Clear the transform for the object."""
        self.applyTform([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ])
    
    def applyTform(self, tform : list, concatenate=False):
        """Apply a transform to the object.
        
            Params:
                tform (list): the transform
                concatenate (bool): True if transform should be multiplied with current transform
        """
        self.msh.apply_transform(tform, concatenate=concatenate)
        self.msh.transform = None  # long story, I'm pretty sure this is a bug with the module
    
    def getSideLength(self):
        """Returns the side length of the object ONLY if it is of type scale_cube."""
        if self.type == "scale_cube":
            self.msh : vedo.Cube
            return self.msh.GetScale()[0]
    
    def getExportDict(self):
        """Get the export dictionary describing the object."""
        return {
            "name": self.name,
            # "series_fp": self.series_fp,
            # "type": self.type,
            "color": self.color,
            "alpha": self.alpha,
            "tform": self.tform,
        }
    
    @property
    def bounds(self):
        b = self.msh.bounds()
        return [(b[i], b[i+1]) for i in range(0, len(b), 2)]


class SceneObjectList():

    def __init__(self):
        """Create the scene object list."""
        self.scene_objects = {}
        self.host_trees = {}
        self.keys = self.scene_objects.keys
        self.values = self.scene_objects.values
        self.items = self.scene_objects.items
    
    def __getitem__(self, i) -> SceneObject:
        """Called when this object is indexed."""
        if isinstance(i, vedo.Mesh) and i.metadata["id"]:
            i = i.metadata["id"][0]
        if type(i) is str and i in self.scene_objects:
            return self.scene_objects[i]
        else:
            return None
    
    def add(self, msh : vedo.Mesh, series : Series, name : str, type : str, color : tuple, alpha : float) -> SceneObject:
        """Add a scene object to the list.
        
            Params:
                msh (vedo.Mesh): the mesh object
                series (Series): the series containing this object
                name (str): the name of the object
                type (str): object, ztrace, or scale_cube
                color (tuple): the color of the object
                alpha (float): the 0-1 trasnparency of the mesh
        """
        scene_object = SceneObject(
            msh, 
            series, 
            name, 
            type, 
            color,
            alpha
        )
        new_id = generateID(existing_pool=self.scene_objects)
        scene_object.setID(new_id)
        self.scene_objects[new_id] = scene_object

        # add to the host tree
        if series.jser_fp not in self.host_trees:
            self.host_trees[series.jser_fp] = series.host_tree
        
        return scene_object
    
    def remove(self, item):
        """Remove an object from the list.
        
            Params:
                item: the item to remove from the list (either an ID, mesh object, or SceneObject)
        """
        remove_id = None
        if type(item) is str:
            remove_id = item
        elif isinstance(item, vedo.Mesh) and "id" in item.metdata:
            remove_id = item.metadata["id"][0]
        elif type(item) is SceneObject:
            remove_id = item.id
        
        if remove_id in self.scene_objects:
            del(self.scene_objects[remove_id])
    
    def getExportDict(self):
        """Get the export dictionary describing the scene."""
        export_dict = {"scale_cubes": [], "series_fps": {}}
        export_series = export_dict["series_fps"]
        # organize dictionary by series_fps and then objects and ztraces
        for o in self.values():
            o : SceneObject
            if o.type in ("object", "ztrace"):
                fp = o.series_fp
                if fp not in export_series:
                    export_series[fp] = {
                        "objects": [], 
                        "ztraces": [],
                    }
                export_series[fp][f"{o.type}s"].append(o.getExportDict())
            else:
                export_dict["scale_cubes"].append(o.getExportDict())
        return export_dict
    
    def getType(self, type_str : str):
        """Return all of a certain type of object.
        
            Params:
                type_str (str): object, ztrace, or scale_cube
        """
        objs = []
        for scene_obj in self.scene_objects.values():
            if scene_obj.type == type_str:
                objs.append(scene_obj)
        return objs
    
    def search(self, name : str, type_str : str, series_fp : str):
        """Search for a specific object/ztrace in the scene.
        
            Params:
                name (str): the name of the object
                type_str (str): object or ztrace
                series_fp (str): the filepahth for the series containing the object/ztrace
        """
        for obj in self.values():
            if (
                obj.name == name and
                obj.type == type_str and
                obj.series_fp == series_fp
            ): return obj
    
    def getHostGroup(self, scene_obj : SceneObject):
        """Get the host group for an object.
        
            Params:
                scene_obj (SceneObject): the scene object
        """
        if not scene_obj.type == "object":
            return
        
        host_tree = self.host_trees[scene_obj.series_fp]
        names = host_tree.getHostGroup(
            scene_obj.name,
            [o.name for o in self.getType("object")]
        )
        host_group = [scene_obj]
        for name in names:
            so = self.search(name, "object", scene_obj.series_fp)
            if so and so not in host_group:
                host_group.append(so)
        
        return host_group


class State3D():

    def __init__(self, attrs):
        """Create the 3D state.
        
            Params:
                attrs (dict): the dictionary of objects/attributes (exactly what is exported when saving a scene)
        """
        self.attrs = attrs


possible_chars = (
    [chr(n) for n in range(65, 91)] +
    [chr(n) for n in range(97, 123)] +
    [chr(n) for n in range(48, 58)]
)
def generateID(existing_pool=None):
    """Generate an ID for a flag.
    
        Params:
            existing_pool: the existing pool of IDs
    """
    id = ""
    for _ in range(6): id += random.choice(possible_chars)
    if existing_pool and id in existing_pool:
        return generateID(existing_pool)
    else:
        return id

def combineBounds(bounds, new_bounds):
    combined = []
    for ((min1, max1), (min2, max2)) in zip(bounds, new_bounds):
        combined.append(
            (min(min1, min2), max(max1, max2))
        )
    return combined


sc_help_message = """To move the scale cube, you must first select it by left-clicking it.

Move the scale cube in XY using the arrow keys (Up/Down/Left/Right).

Move the scale cube in Z using Ctrl+Up/Down."""