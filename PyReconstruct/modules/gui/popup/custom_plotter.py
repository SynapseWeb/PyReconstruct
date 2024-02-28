import vedo

from PyReconstruct.modules.gui.dialog import QuickDialog
from PyReconstruct.modules.gui.utils import notify
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

        self.sc = None
        self.sc_color = (150, 150, 150)
        self.sc_side = 1

        self.selected_text = vedo.Text2D(pos="top-left", font="Courier")
        self.add(self.selected_text)
        self.selected_names = []

        self.pos_text = vedo.Text2D(pos="bottom-left", font="Courier")
        self.add(self.pos_text)
        self.add_callback("MouseMove", self.mouseMoveEvent)

        self.add_callback("LeftButtonClick", self.leftButtonClickEvent)
        self.click_time = None

        self.help_widget = None

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
            for i in (1, 3, 5):
                pos.append((self.extremes[i] + self.extremes[i-1]) / 2)
        else:
            pos = self.sc.pos()
            self.remove(self.sc)
        self.sc = vedo.Cube(tuple(pos), self.sc_side, c=self.sc_color)
        self.sc.metadata["name"] = "Scale Cube"
        self.sc.metadata["type"] = "scale_cube"
        self.sc.lw(5)
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
        if not self.selected_names:
            self.selected_text.text("")
        else:
            name_str = "\n".join(self.selected_names[:5])
            if len(self.selected_names) > 5:
                name_str += "\n..."
            self.selected_text.text(f"Selected:\n{name_str}")

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
        name = msh.metadata["name"][0]
        if name in self.selected_names:
            self.selected_names.remove(name)
        else:
            self.selected_names.append(name)
        
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
            if self.sc is None:
                self.createScaleCube()
            else:
                self.remove(self.sc)
                self.sc = None
        elif key == "Shift+C":
            if self.sc is None:
                return
            
            structure = [
                ["Side length:", ("float", self.sc_side)],
                ["Color:", ("color", self.sc_color)]
            ]
            response, confirmed = QuickDialog.get(None, structure, "Scale Cube")
            if not confirmed:
                return
            self.sc_side, self.sc_color = response
            self.createScaleCube()
            self.render()

        elif key == "Left" and self.sc is not None:
            x, y, z = self.sc.pos()
            self.sc.x(x - 0.1)
        elif key == "Right" and self.sc is not None:
            x, y, z = self.sc.pos()
            self.sc.x(x + 0.1)
        elif key == "Up" and self.sc is not None:
            x, y, z = self.sc.pos()
            self.sc.y(y + 0.1)
        elif key == "Down" and self.sc is not None:
            x, y, z = self.sc.pos()
            self.sc.y(y - 0.1)
        elif key == "Ctrl+Up" and self.sc is not None:
            x, y, z = self.sc.pos()
            self.sc.z(z + 0.1)
        elif key == "Ctrl+Down" and self.sc is not None:
            x, y, z = self.sc.pos()
            self.sc.z(z - 0.1)
        
        # custom opacity changer
        elif key == "Bracketleft" or key == "Bracketright":
            for actor in self.get_meshes():
                name = actor.metadata["name"][0]
                t = actor.metadata["type"][0]
                if name in self.selected_names:
                    new_opacity = actor.alpha() + 0.05 * (-1 if key == "Bracketleft" else 1)
                    actor.alpha(new_opacity)
                    # set the opacity in series 3D options
                    if t == "object":
                        self.series.setAttr(name, "3D_opacity", new_opacity)
                        self.mainwindow.seriesModified(True)
        
        # select/deselect all
        elif key == "Ctrl+D":
            self.selected_names = []
            self.updateSelected()
        elif key == "Ctrl+A":
            self.selected_names = []
            for actor in self.get_meshes():
                name = actor.metadata["name"][0]
                if name is not None:
                    self.selected_names.append(name)
            self.updateSelected()
        
        # help menu
        if key == "Shift+Question":
            overwrite = True
            if not self.help_widget or self.help_widget.closed:
                self.help_widget = Help3DWidget()

        if not overwrite:
            super()._keypress(iren, event)
        else:
            self.render()
    
    def removeObjects(self, obj_names):
        """Remove objects from the scene."""
        for actor in self.getObjects():
            name = actor.metadata["name"][0]
            if name in obj_names:
                self.remove(actor)
                if name in self.selected_names:
                    self.selected_names.remove(name)
        
        self.updateSelected()
        self.render()
    
    def addObjects(self, obj_names, remove_first=True):
        """Add objects to the scene."""
        # remove existing object from scene
        if remove_first:
            self.removeObjects(obj_names)

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
            self.add(vm)
        self.render()
    
    def removeZtraces(self, ztrace_names):
        """Remove ztraces from the scene."""
        for actor in self.getZtraces():
            name = actor.metadata["name"][0]
            if name in ztrace_names:
                self.remove(actor)
                if name in self.selected_names:
                    self.selected_names.remove(name)
        
        self.updateSelected()
        self.render()
    
    def addZtraces(self, ztrace_names, remove_first=True):
        """Add ztraces to the scene."""
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
            curve = vedo.Mesh(vedo.Tube(pts, r=(d/1000)), c=ztrace.color, alpha=1)
            curve.metadata["name"] = name
            curve.metadata["type"] = "ztrace"
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

    def getSelected(self, objects=True, ztraces=True):
        """Return all of the selected meshes."""
        selected_meshes = []
        for msh in self.getObjects() + self.getZtraces():
            if msh.metadata["name"][0] in self.selected_names:
                selected_meshes.append(msh)
        return selected_meshes


class CustomPlotter(QVTKRenderWindowInteractor):

    def __init__(self, mainwindow, obj_names, ztraces=False):
        super().__init__()
        self.mainwindow = mainwindow
        self.series = self.mainwindow.series

        self.extremes = None
        self.is_closed = False
        self.help_widget = None
        self.mouse_x = 0
        self.mouse_y = 0

        # Create vedo renderer
        self.plt = VPlotter(self, qt_widget=self)

        # connect functions
        self.addObjects = self.plt.addObjects
        self.removeObjects = self.plt.removeObjects
        self.addZtraces = self.plt.addZtraces
        self.removeZtraces = self.plt.removeZtraces

        # gerenate objects and display
        if ztraces:
            self.addZtraces(obj_names, remove_first=False)
        else:
            self.addObjects(obj_names, remove_first=False)
        
        self.plt.show(*self.plt.actors)
        self.show()
    
    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        self.plt._keypress(self, event)
    
    def closeEvent(self, event):
        self.plt.close()
        self.is_closed = True
        super().closeEvent(event)