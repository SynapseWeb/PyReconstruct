import vedo

from modules.gui.utils import notify
from modules.backend.volume import generateVolumes
from modules.backend.threading import ThreadPoolProgBar

class CustomPlotter(vedo.Plotter):

    def __init__(self, mainwindow, *args, **kwargs):
        self.mainwindow = mainwindow
        self.series = self.mainwindow.series
        super().__init__(*args, **kwargs)
        self.is_closed = False

        self.window.ShowWindowOff()
        self.is_showing = False

        self.pbar = None
        self.threadpool = None
        self.extremes = None
        self.sc = None

        self.selected_text = vedo.Text2D(pos="top-left", font="Courier", s=1.5)
        self.add(self.selected_text)
        self.selected_names = []

        self.pos_text = vedo.Text2D(pos="bottom-left", font="Courier", s=1.5)
        self.add(self.pos_text)
        self.add_callback("MouseMove", self.mouseMoveEvent)

        self.add_callback("LeftButtonClick", self.leftButtonClickEvent)
        self.click_time = None

    def getSectionFromZ(self, z):
        """Get the section number from a z coordinate."""
        snum = round(z / self.mainwindow.field.section.thickness)  # probably change this

        # if the section is not in the seris, find closest section
        all_sections = list(self.series.sections.keys())
        if snum not in all_sections:
            diffs = [abs(s - snum) for s in all_sections]
            snum = all_sections[diffs.index(min(diffs))]
        
        return snum

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
        txt = f"{name} | section {section} | x={x:.3f} y={y:.3f}"
        self.pos_text.text(txt)                    # update text message

        self.render()
    
    def updateSelectedText(self):
        """Update the selected names text."""
        if not self.selected_names:
            self.selected_text.text("")
            return
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
        
        self.updateSelectedText()
    
    def _keypress(self, iren, event):
        """Called when a key is pressed."""
        key = iren.GetKeySym()

        if "_L" in key or "_R" in key:
            return

        if iren.GetShiftKey():
            key = "Shift+" + key

        if iren.GetControlKey():
            key = "Ctrl+" + key

        if iren.GetAltKey():
            key = "Alt+" + key
        
        overwrite = False

        if key in ("Left", "Right", "Up", "Down", "Ctrl+Up", "Ctrl+Down"):
            overwrite = True

        if key == "c":
            if self.sc is None:
                pos = []
                for i in (1, 3, 5):
                    pos.append((self.extremes[i] + self.extremes[i-1]) / 2)
                self.sc = vedo.Cube(tuple(pos), c="gray5")
                self.sc.metadata["name"] = "Scale Cube"
                self.add(self.sc)
                # self.render()
            else:
                self.remove(self.sc)
                self.sc = None

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
        elif key == "bracketleft" or key == "bracketright":
            for actor in self.getMeshes():
                name = actor.metadata["name"][0]
                if name in self.selected_names:
                    new_opacity = actor.alpha() + 0.05 * (-1 if key == "bracketleft" else 1)
                    actor.alpha(new_opacity)
                    # set the opacity in series 3D options
                    if name in self.series.object_3D_modes:
                        type_3D = self.series.object_3D_modes[name][0]
                    else:
                        type_3D = "surface"
                    self.series.object_3D_modes[name] = type_3D, new_opacity
        
        # select/deselect all
        elif key == "Ctrl+d":
            self.selected_names = []
            self.updateSelectedText()
        elif key == "Ctrl+a":
            self.selected_names = []
            for actor in self.getMeshes():
                name = actor.metadata["name"][0]
                if name is not None:
                    self.selected_names.append(name)
            self.updateSelectedText()

        if not overwrite:
            super()._keypress(iren, event)
    
    def addObjects(self, obj_names):
        """Add objects to the scene."""
        # check for existing progress bar (aka generating in progress)
        if self.pbar is not None:
            notify("Please wait for existing process to finish.")
            return
        
        # remove existing object from scene
        self.removeObjects(obj_names)

        # create threadpool
        self.threadpool = ThreadPoolProgBar()
        worker = self.threadpool.createWorker(generateVolumes, self.series, obj_names)
        worker.signals.result.connect(self.placeInScene)
        self.threadpool.startAll(text="Generating 3D...", status_bar=self.mainwindow.statusbar)
        self.checkShowing()
    
    def placeInScene(self, result):
        """Called by addObjects after thread is completed"""
        # add object to scene
        mesh_data_list, extremes = result
        if self.extremes is None:
            self.extremes = extremes
        for md in mesh_data_list:
            vm = vedo.Mesh([md["vertices"], md["faces"]], md["color"], md["alpha"])
            vm.metadata["name"] = md["name"]
            self.add(vm)
    
    def checkShowing(self):
        """Check if the window is showing."""
        if not self.is_showing:
            self.is_showing = True
            self.window.ShowWindowOn()
            self.show(*self.actors).close()
        else:
            self.render()
    
    def removeObjects(self, obj_names):
        """Remove objects from the scene."""
        # check for existing progress bar (aka generating in progress)
        if self.pbar is not None:
            notify("Please wait for existing process to finish.")
            return
        
        for actor in self.getMeshes().copy():
            try:
                if actor.metadata["name"] is not None and actor.metadata["name"][0] in obj_names:
                    self.remove(actor)
            except AttributeError or TypeError:
                pass
        
        self.render()
    
    def close_window(self):
        self.is_closed = True
        return super().close_window()