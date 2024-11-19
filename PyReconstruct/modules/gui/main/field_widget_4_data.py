import os
import time
import math

import cv2

from PySide6.QtWidgets import (
    QInputDialog,
)

from PyReconstruct.modules.calc import (
    pixmapPointToField,
    centroid,
    lineDistance,
    correlate
)
from PyReconstruct.modules.datatypes import Transform
from PyReconstruct.modules.gui.dialog import (
    QuickDialog,
)
from PyReconstruct.modules.gui.utils import (
    notify, 
    notifyLocked, 
    notifyConfirm,
)

from .field_widget_3_object import FieldWidgetObject

class FieldWidgetData(FieldWidgetObject):
    """
    SECTION AND SERIES FUNCTIONS
    ---------------
    All of the field widget functions related to editing the section and series data.
    """
    def markTime(self):
        """Keep track of the time on the series file."""
        try:
            for f in os.listdir(self.series.getwdir()):
                if "." not in f and f.isnumeric():
                    os.remove(os.path.join(self.series.getwdir(), f))
                    break
            self.time = str(round(time.time()))
            open(os.path.join(self.series.getwdir(), self.time), "w").close()
        except FileNotFoundError:
            pass
    
    def unlockSection(self):
        """Unlock the current section."""
        self.section.align_locked = False
        self.updateData()
        self.mainwindow.seriesModified()
    
    def usingLocked(self):
        """Returns true if the current tracing trace is locked."""
        return self.series.getAttr(self.tracing_trace.name, "locked")
    
    def notifyLocked(self, names):
        """Notify to the user that a trace is locked."""
        if type(names) is str:
            names = [names]
        else:
            names = set(names)

        unlocked = notifyLocked(names, self.series, self.series_states)
        
        if unlocked:
            self.table_manager.updateObjects(names)

        return unlocked
    
    def setCuration(self, cr_status : str, traces : list = None):
        """Set the curation for the selected traces.
        
            Params:
                cr_status (str): the curation status to set for the traces
                traces (list): the list of traces to set
        """
        if not traces:
            traces = self.section.selected_traces.copy()

        if cr_status == "Needs curation":
            assign_to, confirmed = QInputDialog.getText(
                self,
                "Assign to",
                "Assign curation to username:\n(press enter to leave blank)"
            )
            if not confirmed:
                return
        else:
            assign_to = ""
        
        self.series.setCuration([t.name for t in traces], cr_status, assign_to)

        # manually mark as edited
        [self.section.modified_contours.add(t.name) for t in traces]

        self.saveState()
    
    def deleteAll(self, tags=False):
        """Delete all traces in the series that match the trace name (and possibly tags).
        
            Params:
                tags (bool): True if tags should be compared
        """
        if len(self.section.selected_traces) != 1:
            notify("Please select only one trace.")
            return
        trace = self.section.selected_traces[0]

        if tags:
            self.series.deleteAllTraces(trace.name, trace.tags, self.series_states)
        else:
            self.series.deleteAllTraces(trace.name, series_states=self.series_states)
        
        self.table_manager.updateObjects([trace.name])
        self.reload()
    
    def changeTform(self, new_tform):
        # check for section locked status
        if self.section.align_locked:
            return

        # check if propagating
        if self.propagate_tform:
            current_tform = self.section_layer.section.tform
            dtform = new_tform * current_tform.inverted()
            self.stored_tform = dtform * self.stored_tform

        self.section.tform = new_tform
        self.series.addLog(None, self.section.n, "Modify transform")
        
        self.generateView()
        self.saveState()
    
    def setBrightness(self, b : int, log_event=True):
        """Set the brightness of the section."""
        self.section.brightness = b
        if self.section.brightness > 100:
            self.section.brightness = 100
        elif self.section.brightness < -100:
            self.section.brightness = -100

        # update the table
        self.series.data.updateSection(self.section)
        self.table_manager.updateSections([self.section.n])

        self.mainwindow.seriesModified(True)
        self.generateView(generate_traces=False)
        
        if log_event:
            self.series.addLog(None, self.series.current_section, "Modify brightness/contrast")
    
    def setContrast(self, c : int, log_event=True):
        """Set the contrast of the section."""
        self.section.contrast = c
        if self.section.contrast > 100:
            self.section.contrast = 100
        elif self.section.contrast < -100:
            self.section.contrast = -100

        # update the table
        self.series.data.updateSection(self.section)
        self.table_manager.updateSections([self.section.n])
        
        self.mainwindow.seriesModified(True)
        self.generateView(generate_traces=False)
        
        if log_event:
            self.series.addLog(None, self.series.current_section, "Modify brightness/contrast")
    
    def changeBrightness(self, change : int):
        """Change the brightness of the section.
        
            Params:
                change (int): the degree to which brightness is changed
        """
        self.setBrightness(self.section.brightness + change)
    
    def changeContrast(self, change : int):
        """Change the contrast of the section.
        
            Params:
                change (int): the degree to which contrast is changed"""
        self.setContrast(self.section.contrast + change)
    
    def setPropagationMode(self, propagate : bool):
        """Set the propagation mode.
        
            Params:
                propagate (bool): whether to begin or finish propagating
        """
        self.propagate_tform = propagate
        if self.propagate_tform:
            self.stored_tform = Transform([1,0,0,0,1,0])
            self.propagated_sections = set([self.series.current_section])
        self.update()
        
    def propagateTo(self, to_end : bool = True, log_event=True):
        """Propagate the stored transform to the start/end of series.
        
            Params:
                to_end (bool): True propagates to the end, False propagates to beginning
        """
        # save the current section
        self.section.save()
        
        included_sections = []
        for snum in self.series.sections:
            if snum not in self.propagated_sections:
                modify_section = (
                    (to_end and snum > self.series.current_section)
                    or
                    (not to_end and snum < self.series.current_section)
                )
                if modify_section: included_sections.append(snum)
        
        for snum in included_sections:
            section = self.series.loadSection(snum)
            if section.align_locked:
                if not notifyConfirm("Locked sections will not be modified.\nWould you still like to propagate the transform?"):
                    return
                break
        
        for snum in included_sections:
            section = self.series.loadSection(snum)
            new_tform = self.stored_tform * section.tform
            section.tform = new_tform
            section.save()
            self.propagated_sections.add(snum)
            if log_event:
                self.series.addLog(None, snum, "Modify transform")
        
        self.reload()
    
    def changeAlignment(self, new_alignment : str, refresh_data=True):
        """Change the alignment setting for the series.
        
            Params:
                new_alignment (str): the name of the new alignment
        """
        self.series.alignment = new_alignment

        # turn off propagation
        self.setPropagationMode(False)
        
        self.reload()

        # refresh data and tables
        self.table_manager.recreateTables(refresh_data)
    
    def translateTform(self, dx : float, dy : float):
        """Translate the transform for the entire section.
            Params:
                dx (float): x-translate
                dy (float): y-translate
        """
        new_tform = self.section.tform.getList()
        new_tform[2] += dx
        new_tform[5] += dy
        new_tform = Transform(new_tform)
        self.changeTform(new_tform)
    
    def rotateTform(self, cc=True):
        """Rotate the section transform."""
        tform = self.section.tform
        tform_list = tform.getList()
        x, y = pixmapPointToField(
            self.mouse_x,
            self.mouse_y,
            self.pixmap_dim,
            self.series.window,
            self.section.mag
        )
        translate_tform = Transform([1, 0, x, 0, 1, y])
        t = math.pi / 720
        t *= 1 if cc else -1
        sin = math.sin(t)
        cos = math.cos(t)
        rotate_tform = Transform([
            cos, -sin, 0,
            sin, cos, 0
        ])
        new_tform = (
            (tform * translate_tform.inverted() * rotate_tform * translate_tform)
        )
        self.changeTform(new_tform)
    
    def scaleTform(self, sx : float = 1, sy : float = 1):
        """Scale a section transform.
        
            Params:
                sx (float): scaling factor in x
                sy (float): scaling factor in y
        """
        m = self.section.tform.getList()
        m[0] *= sx
        m[4] *= sy
        new_tform = Transform(m)
        self.changeTform(new_tform)
    
    def shearTform(self, sx : float = 0, sy : float = 0):
        """Shear a section transform.
        
            Params:
                sx (float): shear delta in x
                sy (float): shear delta in y
        """
        m = self.section.tform.getList()
        m[1] += sx
        m[3] += sy
        new_tform = Transform(m)
        self.changeTform(new_tform)
    
    def translate(self, dx : float, dy : float):
        """Translate the transform OR the selected traces.
        
            Params:
                dx (float): x-translate
                dy (float): y-translate
        """
        if self.section.selected_traces or self.section.selected_ztraces:
            self.section.translateTraces(dx, dy)
            self.saveState()
            self.generateView()
        else:
            self.translateTform(dx, dy)
    
    def affineAlign(self):
        """Modify the linear transformation using points from the selected trace.
        """
        if not self.b_section or self.section.align_locked:
            return
        
        # gather traces
        a_traces = self.section.selected_traces.copy()
        b_traces = self.b_section.selected_traces.copy()

        # check number of selected traces
        alen = len(a_traces)
        blen = len(b_traces)
        if alen < 3:
            notify("Please select 3 or more traces for aligning.")
        if alen != blen:
            notify("Please select the same number of traces on each section.")
            return
        contour_name = a_traces[0].name

        # check that all traces have same name
        for trace in (a_traces + b_traces):
            if trace.name != contour_name:
                notify("Please select traces of the same name on both sections.")
                return

        # gather points from each section
        centsA = []
        for trace in a_traces:
            centsA.append(centroid(trace.points))
        centsB = []
        tformB = self.b_section.tform
        for trace in b_traces:
            pts = tformB.map(trace.points)
            centsB.append(centroid(pts))
        
        # calculate the tform
        a2b_tform = Transform.estimateTform(centsA, centsB)

        # change the transform
        self.changeTform(a2b_tform)

    def corrAlign(self):
        """Align image by correlation using FFT."""

        if not self.b_section_layer or self.section.align_locked:
            if self.section.align_locked:
                notify(
                    "Make sure to unlock section before "
                    "preforming alignment by correlation."
                )
            return

        window = self.series.window
        dim = self.pixmap_dim

        arr_prev = self.b_section_layer.generateImageArray(dim, window)
        arr_curr = self.section_layer.generateImageArray(dim, window)

        arr_prev = cv2.cvtColor(arr_prev, cv2.COLOR_RGB2BGR)
        arr_curr = cv2.cvtColor(arr_curr, cv2.COLOR_RGB2BGR)

        x, y = correlate(arr_curr, arr_prev)  # get cross correlation

        shift_x = x / self.scaling * self.section.mag
        shift_y = (y / self.scaling * self.section.mag) * -1
        
        shift_tform = Transform([1, 0, shift_x, 0, 1, shift_y])

        tform = self.section.tform
        self.section.tform = shift_tform * tform

        self.generateView()
        self.saveState()

    def calibrateMag(self, trace_lengths : dict, log_event=True):
        """Calibrate the pixel mag based on the lengths of given traces.

            Params:
                trace_lengths (dict): the lengths of the selected traces (name: length)
        """
        # get an average scaling factor across the selected traces
        sum_scaling = 0
        total = 0
        for cname in trace_lengths:
            for trace in self.section.contours[cname]:
                # get the length of the trace with the given transform
                tform = self.section.tform
                d = lineDistance(tform.map(trace.points), closed=False)
                # scaling = expected / actual
                sum_scaling += trace_lengths[trace.name] / d
                total += 1
        
        # calculate new mag
        avg_scaling = sum_scaling / total
        new_mag = self.section.mag * avg_scaling

        self.setMag(new_mag, log_event)
    
    def setMag(self, new_mag : float, log_event=True):
        """Set a new magnification for the series.
        
            Params:
                new_mag (float): the new magnification for the series
        """

        # apply new mag to every section
        for snum, section in self.series.enumerateSections(
            message="Changing series magnification..."
        ):
            section.setMag(new_mag)
            section.save()
        
        if log_event:
            self.series.addLog(None, None, "Calibrate series")
        
        # reload the field
        self.reload()
        self.table_manager.recreateTables(refresh_data=True)
    
    def quickAlign(self):
        """Do a quick translational alignment of the current secion and b section."""  
        if not self.b_section_layer or self.section.align_locked:
            return

        from skimage import registration
        
        pixmap_dim = self.section_layer.pixmap_dim
        window = self.series.window
        
        arr1 = self.b_section_layer.generateImageArray(pixmap_dim, window)
        arr2 = self.section_layer.generateImageArray(pixmap_dim, window)

        # Perform phase correlation to find translation
        model = registration.phase_cross_correlation(arr1, arr2)
        error = model[1]
        shift_x = model[0][1] / self.scaling * self.section.mag
        shift_y = model[0][0] / self.scaling * self.section.mag

        current_tform = self.section.tform
        shift_tform = Transform([
            1,
            0,
            shift_x, 
            0,
            1,
            shift_y
        ])
        self.section.tform = shift_tform * current_tform

        self.generateView()
        self.saveState()
