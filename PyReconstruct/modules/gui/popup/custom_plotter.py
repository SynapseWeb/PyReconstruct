import os
import vedo
import json
import numpy as np

from PySide6.QtWidgets import QMainWindow

from PyReconstruct.modules.gui.dialog import QuickDialog, FileDialog
from PyReconstruct.modules.gui.utils import populateMenuBar, notify, notifyConfirm
from PyReconstruct.modules.gui.table import Help3DWidget
from PyReconstruct.modules.backend.volume import generateVolumes
from PyReconstruct.modules.backend.threading import ThreadPoolProgBar

from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

class VPlotter(vedo.Plotter):

    def __init__(self, qt_parent, *args, **kwargs):
        self.qt_parent = qt_parent
        self.mainwindow = qt_parent.mainwindow
        self.series = self.mainwindow.series
        super().__init__(*args, **kwargs)

        self.extremes = None
        self.translations = {
            "object": {},
            "ztrace": {},
            "scale_cube": {}
        }
        self.rotations = {
            "object": {},
            "ztrace": {},
            "scale_cube": {}
        }

        self.sc = None
        self.sc_color = (150, 150, 150)
        self.sc_side = 1

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
    
    def createScaleCube(self):
        """Create the scale cube in the 3D scene."""
        if self.sc is None:
            pos = []
            rot = (0, 0, 0)
            for i in (1, 3, 5):
                pos.append((self.extremes[i] + self.extremes[i-1]) / 2)
        else:
            # get the current position and rotation of the scale cube
            pos = self.sc.pos()
            if "Scale Cube" in self.rotations["scale_cube"]:
                rot = self.rotations["scale_cube"]["Scale Cube"]
            else:
                rot = (0, 0, 0)
            self.toggleScaleCube(False)
        self.sc = vedo.Cube(tuple(pos), self.sc_side, c=self.sc_color)
        self.sc.metadata["name"] = "Scale Cube"
        self.sc.metadata["type"] = "scale_cube"
        self.sc.metadata["color"] = self.sc_color
        self.sc.lw(5)
        self.rotate(self.sc, *rot, save=False)
        self.add(self.sc)

    def mouseMoveEvent(self, event):
        """Called when mouse is moved -- display coordinates."""
        msh = event.actor
        if not msh or msh.metadata["name"] is None:
            self.pos_text.text("")
            self.render()
            return                       # mouse hits nothing, return.
        
        name = msh.metadata["name"][0]  # not sure why it returns as a list?

        pt = event.picked3d                # 3d coords of point under mouse
        x = round(pt[0], 3)
        y = round(pt[1], 3)
        section = self.getSectionFromZ(pt[2])
        txt = f"{name}\nsection {section}\nx={x:.3f} y={y:.3f}"
        self.pos_text.text(txt)                    # update text message

        self.render()
    
    def updateSelected(self):
        """Update the selected names text."""
        # update the text
        if not self.selected:
            self.selected_text.text("")
        else:
            names = [msh.metadata["name"][0] for msh in self.selected]
            name_str = "\n".join(names[:5])
            if len(self.selected) > 5:
                name_str += "\n..."
            self.selected_text.text(f"Selected:\n{name_str}")

        # update the object highlight
        for actor in self.actors:
            if isinstance(actor, vedo.Mesh):
                if actor in self.selected:
                    if actor is self.sc:
                        actor.color((64, 64, 64))
                    else:
                        actor.lw(1)
                else:
                    if actor is self.sc:
                        actor.color(self.sc_color)
                    else:
                        actor.lw(0)
        
        self.render()
    
    def leftButtonClickEvent(self, event):
        """Called when left mouse button is clicked."""
        # record the time of click
        prev_click_time = self.click_time
        self.click_time = event.time
        # check for double clicks
        if prev_click_time is not None and self.click_time - prev_click_time < 0.25:
            msh = event.actor
            if not msh:
                return                       # mouse hits nothing, return.
            pt = event.picked3d                # 3d coords of point under mouse
            x = round(pt[0], 3)
            y = round(pt[1], 3)
            section = self.getSectionFromZ(pt[2])
            
            self.mainwindow.field.moveTo(section, x, y)
            self.mainwindow.activateWindow()
        
        msh = event.actor
        if not msh or msh.metadata["name"] is None:
            return
        if msh in self.selected:
            self.selected.remove(msh)
        else:
            self.selected.append(msh)
        
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
            self.toggleScaleCube(bool(self.sc is None))
        
        elif key == "Shift+C":
            self.modifyScaleCube()

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
        
        # custom opacity changer
        elif key == "Bracketleft" or key == "Bracketright":
            for actor in self.get_meshes():
                name = actor.metadata["name"][0]
                t = actor.metadata["type"][0]
                if actor in self.selected:
                    new_opacity = actor.alpha() + 0.05 * (-1 if key == "Bracketleft" else 1)
                    actor.alpha(new_opacity)
                    # set the opacity in series 3D options
                    if t == "object":
                        self.series.setAttr(name, "3D_opacity", new_opacity)
                        self.mainwindow.seriesModified(True)
        
        # select/deselect all
        elif key == "Ctrl+D":
            self.selected = []
            self.updateSelected()
        elif key == "Ctrl+A":
            self.selected = []
            for actor in self.get_meshes():
                name = actor.metadata["name"][0]
                if name is not None:
                    self.selected.append(actor)
            self.updateSelected()
        
        # remove selected object from scene
        if key in ("Delete", "Backspace"):
            obj_names = []
            ztrace_names = []
            for msh in self.selected:
                n = msh.metadata["name"][0]
                t = msh.metadata["type"][0]
                if t == "object":
                    obj_names.append(n)
                elif t == "ztrace":
                    ztrace_names.append(n)
                elif t == "scale_cube":
                    self.toggleScaleCube(False)
            
            self.removeObjects(obj_names)
            self.removeZtraces(ztrace_names)
        
        # help menu
        if key == "Shift+Question":
            overwrite = True
            self.showHelp()

        if not overwrite:
            super()._keypress(iren, event)
        else:
            self.render()
    
    def toggleScaleCube(self, show : bool):
        """Toggle the scale cube display in the scene.
        
            Params:
                show (bool): True if scale cube should be displayed
        """
        if show:
            self.createScaleCube()
        else:
            self.remove(self.sc)
            if self.sc in self.selected:
                self.selected.remove(self.sc)
                self.updateSelected()
            self.sc = None
        # update the menubar display
        self.qt_parent.togglesc_act.setChecked(show)
    
    def modifyScaleCube(self):
        """Modify the size and color of the scale cube."""
        structure = [
            ["Side length:", ("float", self.sc_side)],
            ["Color:", ("color", self.sc_color)]
        ]
        response, confirmed = QuickDialog.get(None, structure, "Scale Cube")
        if not confirmed:
            return
        self.sc_side, self.sc_color = response

        if self.sc is not None:
            self.createScaleCube()
            self.render()
    
    def translate(self, msh, dx : float, dy : float, dz : float, save=True):
        """Translate a meshe.
        
            Params:
                msh: the mesh to translate
                dx (float): the x translate
                dy (float): the y translate
                dz (float): the z translate
        """
        x, y, z = msh.pos()
        msh.pos(x + dx, y + dy, z + dz)
        # store translation data in case of saving
        if save:
            n = msh.metadata["name"][0]
            t = msh.metadata["type"][0]
            if n in self.translations[t]:
                x, y, z = self.translations[t][n]
            else:
                x, y, z = 0, 0, 0
            self.translations[t][n] = (x + dx, y + dy, z + dz)
    
    def rotate(self, msh, rx : float, ry : float, rz : float, save=True):
        """Rotate the selected meshes.
        
            Params:
                msh: the mesh to rotate
                rx (float): the x rotate angle
                ry (float): the y rotate angle
                rz (float): the z rotate angle
        """
        cm = tuple(msh.center_of_mass())
        if rx: msh.rotate_x(rx, around=cm)
        if ry: msh.rotate_y(ry, around=cm)
        if rz: msh.rotate_z(rz, around=cm)
        # store rotation data in case of saving
        if save:
            n = msh.metadata["name"][0]
            t = msh.metadata["type"][0]
            if n in self.rotations[t]:
                x, y, z = self.rotations[t][n]
            else:
                x, y, z = 0, 0, 0
            self.rotations[t][n] = (x + rx, y + ry, z + rz)
        
    def translateSelected(self, dx : float, dy : float, dz : float):
        """Translate the selected meshes.
        
            Params:
                dx (float): the x translate
                dy (float): the y translate
                dz (float): the z translate
        """
        for msh in self.selected:
            self.translate(msh, dx, dy, dz)
    
    def rotateSelected(self, rx : float, ry : float, rz : float):
        """Rotate the selected meshes.
        
            Params:
                rx (float): the x rotate angle
                ry (float): the y rotate angle
                rz (float): the z rotate angle
        """
        for msh in self.selected:
            self.rotate(msh, rx, ry, rz)
            
    def removeObjects(self, obj_names):
        """Remove objects from the scene."""
        for actor in self.getObjects():
            name = actor.metadata["name"][0]
            if name in obj_names:
                self.remove(actor)
                # remove from selected
                if actor in self.selected:
                    self.selected.remove(actor)
                # remove from rotations and translations
                if name in self.rotations["object"]:
                    del(self.rotations["object"][name])
                if name in self.translations["object"]:
                    del(self.translations["object"][name]) 
        
        self.updateSelected()
        self.render()
    
    def addObjects(self, obj_names, remove_first=True):
        """Add objects to the scene."""
        if not obj_names:
            return
        
        # remove existing object from scene
        if remove_first:
            self.removeObjects(obj_names)

        # check for objects that don't exist in the series
        obj_names = obj_names.copy()
        removed = []
        for i, name in enumerate(obj_names):
            if name not in self.series.data["objects"]:
                removed.append(obj_names.pop(i))
        
        if removed:
            if not obj_names:
                notify("None of the requested objects exist in this series.")
                return
            else:
                confirm = notifyConfirm(
                    f"The object(s) {', '.join(removed)} do not exist in this series.\n" +
                    "Would you like to continue with the other objects?",
                    yn=True
                )
                if not confirm:
                    return

        # create threadpool
        self.threadpool = ThreadPoolProgBar()
        worker = self.threadpool.createWorker(generateVolumes, self.series, obj_names)
        worker.signals.result.connect(self.placeInScene)
        self.threadpool.startAll(text="Generating 3D...", status_bar=self.mainwindow.statusbar)
    
    def placeInScene(self, result):
        """Called by addObjects after thread is completed"""
        # add object to scene
        mesh_data_list, extremes = result
        if self.extremes is None:
            self.extremes = extremes
        for md in mesh_data_list:
            vm = vedo.Mesh([md["vertices"], md["faces"]], md["color"], md["alpha"])
            vm.metadata["name"] = md["name"]
            vm.metadata["type"] = "object"
            vm.metadata["color"] = md["color"]
            self.add(vm)
        self.render()
    
    def removeZtraces(self, ztrace_names):
        """Remove ztraces from the scene."""
        for actor in self.getZtraces():
            name = actor.metadata["name"][0]
            if name in ztrace_names:
                self.remove(actor)
                if actor in self.selected:
                    self.selected.remove(actor)
                # remove from rotations and translations
                if name in self.rotations["ztrace"]:
                    del(self.rotations["ztrace"][name])
                if name in self.translations["ztrace"]:
                    del(self.translations["ztrace"][name])
        
        self.updateSelected()
        self.render()
    
    def addZtraces(self, ztrace_names, remove_first=True):
        """Add ztraces to the scene."""
        if not ztrace_names:
            return
        
        # remove existing ztraces from the scene
        if remove_first:
            self.removeZtraces(ztrace_names)

        extremes = []
        for name in ztrace_names:
            ztrace = self.series.ztraces[name]
            pts = []
            for pt in ztrace.points:
                x, y, s = pt
                tform = self.series.data["sections"][s]["tforms"][self.series.alignment]
                x, y = tform.map(x, y)
                z = s * self.series.data["sections"][s]["thickness"]  # ASSUME UNIFORM SECTION THICKNESS
                pts.append((x, y, z))

                # keep track of extremes
                if not extremes:
                    extremes = [x, x, y, y, z, z]
                else:
                    for val, i in zip((x, x, y, y, z, z), range(6)):
                        if i % 2 == 0:  # is minimum
                            if val < extremes[i]:
                                extremes[i] = val
                        else:
                            if val > extremes[i]:
                                extremes[i] = val
            
            d = ztrace.getDistance(self.series)
            color = [c/255 for c in ztrace.color]
            curve = vedo.Mesh(vedo.Tube(pts, r=(d/1000)), c=color, alpha=1)
            curve.metadata["name"] = name
            curve.metadata["type"] = "ztrace"
            curve.metadata["color"] = color
            self.add(curve)
        self.render()
        
        if not self.extremes:
            self.extremes = extremes
    
    def getObjects(self):
        """Return all mesh objects in the scene."""
        objs = []
        for msh in self.get_meshes():
            if msh.metadata["type"][0] == "object":
                objs.append(msh)
        return objs
    
    def getZtraces(self):
        """Return all ztraces in the scene."""
        ztraces = []
        for msh in self.get_meshes():
            if msh.metadata["type"][0] == "ztrace":
                ztraces.append(msh)
        return ztraces

    def showHelp(self):
        """Show the keyboard shortcuts available to the user."""
        if not self.help_widget or self.help_widget.closed:
            self.help_widget = Help3DWidget()


class Container(QMainWindow):

    def closeEvent(self, event):
        self.centralWidget().close()
        super().closeEvent(event)


class CustomPlotter(QVTKRenderWindowInteractor):

    def __init__(self, mainwindow, obj_names=[], ztraces=False, load_fp=None):
        # use container to create menubar
        self.container = Container()
        super().__init__(self.container)
        self.container.setCentralWidget(self)

        self.mainwindow = mainwindow
        self.series = self.mainwindow.series

        self.extremes = None
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
                    ("addtoscene_act", "Add to scene from file...", "", lambda : self.loadScene(add_only=True))
                ]
            },
            {
                "attr_name": "scmenu",
                "text": "Scale Cube",
                "opts":
                [
                    ("togglesc_act", "Display in scene", "checkbox", self.toggleScaleCube),
                    ("modifysc_act", "Modify...", "", self.plt.modifyScaleCube),
                    ("movehelp_act", "Move scale cube...", "", self.moveScaleCubeHelp),
                ]
            },
            {
                "attr_name": "helpmenu",
                "text": "Help",
                "opts":
                [
                    ("shortcuts_act", "Shortcuts", "", self.plt.showHelp)
                ]
            }
        ]
        self.menubar_widget = self.container.menuBar()
        self.menubar_widget.setNativeMenuBar(False)
        populateMenuBar(self, self.menubar_widget, menubar_list)

        # connect functions
        self.addObjects = self.plt.addObjects
        self.removeObjects = self.plt.removeObjects
        self.addZtraces = self.plt.addZtraces
        self.removeZtraces = self.plt.removeZtraces

        # gerenate objects and display
        if load_fp:
            self.loadScene(load_fp)
        elif obj_names:
            if ztraces:
                self.addZtraces(obj_names, remove_first=False)
            else:
                self.addObjects(obj_names, remove_first=False)
        
        self.plt.show(*self.plt.actors, resetcam=(False if load_fp else None))
        self.show()
        self.container.show()
    
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
        obj_names = [a.metadata["name"][0] for a in self.plt.getObjects()]
        ztrace_names = [a.metadata["name"][0] for a in self.plt.getZtraces()]
        self.plt.removeObjects(obj_names)
        self.plt.removeZtraces(ztrace_names)
        self.plt.toggleScaleCube(False)
        self.plt.translations = {
            "object": {},
            "ztrace": {},
            "scale_cube": {}
        }
        self.plt.rotations = {
            "object": {},
            "ztrace": {},
            "scale_cube": {}
        }

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

        d = {"series_code": self.series.code}

        # get the names of the displayed objects
        d["objects"] = set()
        for actor in self.plt.getObjects():
            name = actor.metadata["name"][0]
            d["objects"].add(name)
        d["objects"] = list(d["objects"])

        # get the names of the displated ztraces
        d["ztraces"] = set()
        for actor in self.plt.getZtraces():
            name = actor.metadata["name"][0]
            d["ztraces"].add(name)
        d["ztraces"] = list(d["ztraces"])

        # store the translations and rotations
        d["translations"] = self.plt.translations
        d["rotations"] = self.plt.rotations

        # get the scale cube information
        if self.plt.sc is not None:
            d["sc"] = {}
            d["sc"]["side"] = self.plt.sc_side
            d["sc"]["color"] = self.plt.sc_color
        else:
            d["sc"] = None
        
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
        
        # check the series code
        if d["series_code"] != self.series.code:
            confirm = notifyConfirm(
                "This scene was not made from this series.\n" +
                "Would you like to continue?",
                yn=True
            )
            if not confirm:
                return
        
        # do not touch the already existing objects if adding
        if add_only:
            for obj_name in self.plt.getObjects():
                if obj_name in d["objects"]:
                    d["objects"].remove(obj_name)
            for ztrace_name in self.plt.getZtraces():
                if ztrace_name in d["ztraces"]:
                    d["ztraces"].remove(ztrace_name)
        # clear the plot otherwise
        else:
            self.clearScene()

        # add the objects
        self.plt.addObjects(d["objects"])
        # add the ztraces
        self.plt.addZtraces(d["ztraces"])

        # add the scale cube if making from new
        if d["sc"] and not add_only:
            self.plt.sc_side = d["sc"]["side"]
            self.plt.sc_color = tuple(d["sc"]["color"])
            self.plt.createScaleCube()

        # apply the rotations and translations
        for meshes, mesh_type in [
            (self.plt.getObjects(), "object"), 
            (self.plt.getZtraces(), "ztrace"),
            ([self.plt.sc] if self.plt.sc else [], "scale_cube")
        ]:
            for msh in meshes:
                name = msh.metadata["name"][0]
                # skip meshes that are not part of the loaded scene (most applicable in the case of add_only)
                if mesh_type != "scale_cube" and name not in d[f"{mesh_type}s"]:
                    continue
                # modify/save translations
                if name in d["translations"][mesh_type]:
                    dx, dy, dz = tuple(d["translations"][mesh_type][name])
                    self.plt.translate(msh, dx, dy, dz)
                # modify/save rotations
                if name in d["rotations"][mesh_type]:
                    rx, ry, rz = tuple(d["rotations"][mesh_type][name])
                    self.plt.rotate(msh, rx, ry, rz)

        # move the camera
        if not add_only:
            self.plt.camera.SetPosition(d["camera"]["position"])
            self.plt.camera.SetFocalPoint(d["camera"]["focal_point"])
            self.plt.camera.SetViewUp(d["camera"]["view_up"])
            self.plt.camera.SetDistance(d["camera"]["distance"])
            self.plt.show(resetcam=False)
                    
    def closeEvent(self, event):
        self.plt.close()
        self.is_closed = True
        self.container = None
        super().closeEvent(event)

sc_help_message = """To move the scale cube, you must first select it by left-clicking it.

Move the scale cube in XY using the arrow keys (Up/Down/Left/Right).

Move the scale cube in Z using Ctrl+Up/Down."""