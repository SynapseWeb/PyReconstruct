import os
import json
import time
from copy import deepcopy

from PyReconstruct.modules.datatypes import (
    Series,
    Section,
    Contour,
    Ztrace,
    Trace
)

class FieldState():

    def __init__(
            self, 
            contours : dict, 
            ztraces : dict, 
            tforms : dict, 
            flags : list,
            contours_fp : str = None,
            updated_contours=None, 
            updated_ztraces=None
        ):
        """Create a field state with traces and the transform.
        
            Params:
                contours (dict): all the contours on a section
                tforms (dict): the tforms for the section state
                flags (list): the flags for the section state
                contours_fp (str): the filepath to store the contours
                updated_contours: the names of the modified contours
                updated_ztraces: the names of the modified ztraces
        """
        self.contours = {}
        self.contours_fp = contours_fp
        if updated_contours is None:
            if contours is None:
                updated_contours = []
            else:
                updated_contours = contours.keys()

        # store contours in memory if no fp provided
        if not self.contours_fp:  
            for contour_name in updated_contours:
                if contour_name in contours:
                    self.contours[contour_name] = contours[contour_name].copy()
                else:  # empty Contour
                    self.contours[contour_name] = Contour(contour_name)
        # store contours in json
        elif contours is None:  # assume stored in JSON already
            self.contours = None
        else:  # store contours if provided with both fp and contours
            for contour_name in updated_contours:
                self.contours[contour_name] = [trace.getList() for trace in contours[contour_name]]
            with open(self.contours_fp, "w") as f:
                json.dump(self.contours, f)
            self.contours = None
        
        self.ztraces = {}
        # first state made for a section (or copy)
        if updated_ztraces is None:
            for ztrace_name in ztraces:
                self.ztraces[ztrace_name] = ztraces[ztrace_name].copy()
        # added another state
        else:
            for ztrace_name in updated_ztraces:
                self.ztraces[ztrace_name] = ztraces[ztrace_name].copy()
        
        # save tforms
        self.tforms = {}
        for alignment_name in tforms:
            self.tforms[alignment_name] = tforms[alignment_name].copy()
        
        # save flags
        self.flags = []
        for flag in flags:
            self.flags.append(flag.copy())
    
    def copy(self):
        return FieldState(self.contours, self.ztraces, self.tforms, self.flags, self.contours_fp)
    
    def getContours(self):
        contours = {}
        if self.contours_fp:
            with open(self.contours_fp, "r") as f:
                contours = json.load(f)
                for cname, contour in contours.items():
                    contours[cname] = Contour(cname, [Trace.fromList(trace) for trace in contour])
            return contours
        else:
            for cname in self.contours:
                contours[cname] = self.contours[cname].copy()
            return contours
    
    def getZtraces(self):
        ztraces = {}
        for zname in self.ztraces:
            ztraces[zname] = self.ztraces[zname].copy()
        return ztraces
    
    def getModifiedContours(self):
        if self.contours_fp:
            with open(self.contours_fp, "r") as f:
                contours = json.load(f)
            return set(contours.keys())
        else:
            return set(self.contours.keys())
    
    def getModifiedZtraces(self):
        return set(self.ztraces.keys())
    
    def getTforms(self):
        return self.tforms.copy()

    def getFlags(self):
        return self.flags.copy()
    
    def updateTime(self):
        self.time = round(time.time()*10)  # keep track of time when added to state list

class SectionStates():

    def __init__(self, section : Section = None, series : Series = None):
        """Create the section state manager.
        
            Params:
                section (Section): the section object to store states for
                series (Series): the series that contains the sections
        """
        self.initialized = False
        self.current_state = None
        self.undo_states = []
        self.redo_states = []
        if section and series:
            self.initialize(section, series)
    
    def initialize(self, section : Section, series : Series):
        """Create the section state manager.
        
            Params:
                section (Section): the section object to store states for
                series (Series): the series that contains the sections
        """
        contours_fp = os.path.join(series.hidden_dir, f"{series.sections[section.n]}.s0")
        self.current_state = FieldState(
            section.contours, 
            series.ztraces, 
            section.tforms, 
            section.flags,
            contours_fp
        )
        self.initialized = True
    
    def addState(self, section : Section, series : Series):
        """Add a new undo state (called when an action is performed).
        
            Params:
                section (Section): the section object
        """
        # clear redo states
        self.redo_states = []
        # push current state to undo states
        self.current_state.updateTime()  # keep track of when added to undos
        self.undo_states.append(self.current_state)
        # get the names of the updated contours
        updated_contours = section.getAllModifiedNames()
        # get the updated ztraces
        updated_ztraces = series.modified_ztraces.copy()
        # set the new current state
        self.current_state = FieldState(
            section.contours,
            series.ztraces,
            section.tforms,
            section.flags,
            None,
            updated_contours,
            updated_ztraces
        )
        
    def undoState(self, section : Section, series : Series) -> set:
        """Restore an undo state on the section.
        
            Params:
                section (Section): the section to restore
                series (Series): the series with ztraces to restore
            Returns:
                (set): the names of modified contours
        """
        # if there are not undo states
        if len(self.undo_states) == 0:
            return
        
        # if only one undo state exists
        if len(self.undo_states) == 1:
            state = self.undo_states[0]
            # restore contours
            modified_contours = self.current_state.getModifiedContours()
            section.contours = state.getContours()
            # restore ztraces
            modified_ztraces = self.current_state.getModifiedZtraces()
            for zname in modified_ztraces:
                series.ztraces[zname] = restoreZtraceOnSection(
                    series.ztraces[zname],
                    state.ztraces[zname],
                    section.n
                )

        # if there are multiple undo states
        else:
            # iterate backwards and find the last ieration of the recently changed contours
            last_changed_contours = self.current_state.getModifiedContours().copy()
            last_changed_ztraces = self.current_state.getModifiedZtraces().copy()
            modified_contours = last_changed_contours.copy()
            modified_ztraces = last_changed_ztraces.copy()
            for state in reversed(self.undo_states):
                state_contours = state.getContours()
                state_ztraces = state.getZtraces()
                for contour in last_changed_contours.copy():
                    if contour in state_contours:
                        section.contours[contour] = state_contours[contour]
                        last_changed_contours.remove(contour)
                for ztrace in last_changed_ztraces.copy():
                    if ztrace in state_ztraces:
                        series.ztraces[ztrace] = restoreZtraceOnSection(
                            series.ztraces[ztrace],
                            state_ztraces[ztrace],
                            section.n
                        )
                        last_changed_ztraces.remove(ztrace)
                if not last_changed_contours and not last_changed_ztraces:
                    break
            # if the contour was not found (aka it was just created)
            if last_changed_contours:
                for contour in last_changed_contours:
                    section.contours[contour] = Contour(contour)
            
        # update the series log
        for cname in modified_contours:
            series.addLog(cname, section.n, "Modify trace(s)")
        for zname in modified_ztraces:
            series.addLog(zname, section.n, "Modify ztrace")

        # restore the transforms
        restored_tforms = self.undo_states[-1].getTforms()
        section.tforms = restored_tforms
        if section.tformsModified():
            series.addLog(None, section.n, "Modify transform")

        # restore the flags
        restored_flags = self.undo_states[-1].getFlags()
        # check if flag changes should be logged
        flist_1 = [len(f.comments) for f in section.flags]
        flist_2 = [len(f.comments) for f in restored_flags]
        if flist_1 != flist_2:
            series.addLog(None, section.n, "Modify flag(s)")
        section.flags = restored_flags

        # edit the undo/redo stacks and the current state
        self.redo_states.append(self.current_state)
        self.current_state = self.undo_states.pop().copy()

        # add the modified contours to the section object
        section.modified_contours = section.modified_contours.union(modified_contours)
        # add modified ztrace names to the series object
        series.modified_ztraces = series.modified_ztraces.union(modified_ztraces)
    
    def redoState(self, section : Section, series : Series) -> set:
        """Restore a redo state on the section.
        
            Params:
                section (Section): the section to restore
            Returns:
                (set): the names of modified contours
        """
        if len(self.redo_states) == 0:
            return
        redo_state = self.redo_states[-1]
        # restore the contours on the section
        state_contours = redo_state.getContours()
        modified_contours = redo_state.getModifiedContours()
        for contour_name in state_contours:
            section.contours[contour_name] = state_contours[contour_name]
        # restore the ztraces
        state_ztraces = redo_state.getZtraces()
        modified_ztraces = redo_state.getModifiedZtraces()
        for zname in state_ztraces:
            series.ztraces[zname] = restoreZtraceOnSection(
                series.ztraces[zname],
                state_ztraces[zname],
                section.n
            )
        
        # update the series log
        for cname in modified_contours:
            series.addLog(cname, section.n, "Modify trace(s)")
        for zname in modified_ztraces:
            series.addLog(zname, section.n, "Modify ztrace")
        
        # restore the transforms
        section.tforms = redo_state.getTforms()
        if section.tformsModified():
            series.addLog(None, section.n, "Modify transform")

        # restore the flags
        restored_flags = redo_state.getFlags()
        # check if flag changes should be logged
        flist_1 = [len(f.comments) for f in section.flags]
        flist_2 = [len(f.comments) for f in restored_flags]
        if flist_1 != flist_2:
            series.addLog(None, section.n, "Modify flag(s)")
        section.flags = restored_flags

        # edit the undo/redo stacks and the current state
        self.undo_states.append(self.current_state)
        self.current_state = self.redo_states.pop()

        # add the modified contours to the section object
        section.modified_contours = section.modified_contours.union(modified_contours)
        # add modified ztrace names to the series object
        series.modified_ztraces = series.modified_ztraces.union(modified_ztraces)

def restoreZtraceOnSection(orig_ztrace : Ztrace, new_ztrace : Ztrace, snum : int) -> Ztrace:
    """Restore the ztrace for a specific section.
    
        Params:
            orig_ztrace (Ztrace): the ztrace to be modified
            new_ztrace (Ztrace): the ztrace with data to be imported
            snum (int): the section number
        Returns:
            (Ztrace): the newly formed ztrace
    """
    orig_points = orig_ztrace.points.copy()
    new_points = new_ztrace.points.copy()
    restored_points = []
    for p0, p1 in zip(orig_points, new_points):
        if p1[2] == snum:
            restored_points.append(p1)
        else:
            restored_points.append(p0)
    return Ztrace(
        orig_ztrace.name,
        orig_ztrace.color,
        restored_points
    )

class SeriesState():

    def __init__(self, breakable=True):
        """Create a single series state."""
        self.time = round(time.time() * 10)  # keep track of time
        self.undo_lens = {}  # keep track of individial section undos (these will be populated as the enumerateSections loop progresses)
        self.series_attrs = {}
        self.breakable = breakable
    
    # STATIC METHOD
    def getSeriesAttributes(series : Series):
        """Reset the stored series attributes.
        
            Params:
                series (Series): the series to store attributes for
        """
        obj_attrs = deepcopy(series.obj_attrs)
        ztrace_attrs = deepcopy(series.ztrace_attrs)
        
        object_groups = series.object_groups.copy()
        ztrace_groups = series.ztrace_groups.copy()

        alignment = series.alignment

        ztraces = deepcopy(series.ztraces)

        user_columns = deepcopy(series.user_columns)
        object_columns = deepcopy(series.getOption("object_columns"))

        host_tree = series.host_tree.copy()
        
        return {
            "obj_attrs" : obj_attrs,
            "ztrace_attrs" : ztrace_attrs,
            "object_groups" : object_groups,
            "ztrace_groups" : ztrace_groups,
            "alignment" : alignment,
            "ztraces" : ztraces,
            "user_columns": user_columns,
            "object_columns": object_columns,
            "host_tree": host_tree
        }
    
    def resetSeriesAttributes(self, series : Series):
        """Reset the stored series attributes.
        
            Params:
                series (Series): the series to store attributes for
        """
        self.series_attrs = SeriesState.getSeriesAttributes(series)
    
    def applySeriesAttributes(self, series : Series):
        """Apply the stored series attributes to a series.
        
            Params:
                series (Series): the series to apply attributes to
        """
        pre_series_attrs = SeriesState.getSeriesAttributes(series)
        for attr, value in self.series_attrs.items():
            if attr == "object_columns":
                continue  # only replace obj columns under specific circumstances (below)
            setattr(series, attr, value)

        # specific case: no sections modified but the series data needs to be refreshed bc preferred alignments changed
        if not self.undo_lens and alignmentPreferencesChanged(pre_series_attrs, self.series_attrs):
            series.data.refresh()
        
        # specific case: switch to previous obj_columns if user_columns has been changed
        if self.series_attrs["object_columns"] != pre_series_attrs["user_columns"]:
            series.setOption("object_columns", self.series_attrs["object_columns"])

        self.series_attrs = pre_series_attrs

def getAlignment(attrs, name):
    if name in attrs and "alignment" in attrs[name]:
        return attrs[name]["alignment"]
    else:
        return None

def alignmentPreferencesChanged(pre_series_attrs, post_series_attrs):
    """Check if the alignment preferences for objects and ztraces has changed."""
    pre_obj_attrs = pre_series_attrs["obj_attrs"]
    post_obj_attrs = post_series_attrs["obj_attrs"]
    pre_ztrace_attrs = pre_series_attrs["ztrace_attrs"]
    post_ztrace_attrs = post_series_attrs["ztrace_attrs"]

    for pre, post in (
        (pre_obj_attrs, post_obj_attrs),
        (pre_ztrace_attrs, post_ztrace_attrs)
    ):
        for name in set(pre.keys()).union(post.keys()):
            if getAlignment(pre, name) != getAlignment(post, name):
                return True
    
    return False


class SeriesStates():

    def __init__(self, series : Series):
        """Create the object to contain section states and information for series-wide states.
        
            Params:
                section_numbers (list): the list of section numbers in the series
        """
        self.series = series
        self.section_states_dict : dict[int, SectionStates] = {}
        for snum in self.series.sections:
            self.section_states_dict[snum] = SectionStates()
        self.undos : list[SeriesState] = []
        self.redos : list[SeriesState] = []
    
    def __iter__(self):
        """Return the iterator object for the series states"""
        return self.section_states_dict.__iter__()
    
    def __getitem__(self, index):
        """Allow the user to index the series states."""
        if type(index) is int:
            return self.section_states_dict[index]
        elif type(index) is Section:
            section_states = self.section_states_dict[index.n]
            if not section_states.initialized:
                section_states.initialize(index, self.series)
            return section_states
    
    def __len__(self):
        """Get the length of the series states."""
        return len(self.section_states_dict)

    def addState(self, breakable=True):
        """Create a new series undo state.
        
            Params:
                breakable (bool): True if series state can be broken (aka dissolved and left as individual section events)
        """
        new_state = SeriesState(breakable)
        new_state.resetSeriesAttributes(self.series)
        self.undos.append(new_state)
    
    def addSectionUndo(self, snum : int):
        """Flag the section's latest undo state as part of the most recent series undo.
        
            Params:
                snum (int): the section number
        """
        self.undos[-1].undo_lens[snum] = len(self[snum].undo_states)

    def clear(self):
        """Clear all state tracking."""
        for snum in self.section_states_dict:
            self.section_states_dict[snum] = SectionStates()
        self.undos = []
        self.redos = []
    
    def canUndo(self, current_section : int = None, redo=False):
        """Checks if an undo is possible.
        
            Params:
                current_section (int): the section the user is on
            Returns:
                (3D undo possible, 2D undo possible, 3D and 2D undo are linked)
        """
        if current_section is None:
            current_section = self.series.current_section
        if current_section not in self.section_states_dict:
            return (False, False, False)
        
        series_states = self.redos if redo else self.undos
        cs_undos = self[current_section].undo_states
        cs_redos = self[current_section].redo_states
        # neither section nor series undo is populated
        if not series_states and (
            redo and not cs_redos or
            not redo and not cs_undos
        ):
            return (False, False, False)
        # only section undo populated
        elif not series_states:
            return (False, True, False)
        # series undo is populated
        elif series_states:
            undo_lens = series_states[-1].undo_lens
            # check if state numbers match on all sections
            all_sections_match = True
            for snum, undo_len in undo_lens.items():
                states = self[snum]
                if not states.initialized or len(states.undo_states) != undo_len - (1 if redo else 0):
                    all_sections_match = False
                    break
            # check if state numbers match on the current section
            current_section_match = bool(
                current_section in undo_lens and 
                len(cs_undos) == undo_lens[current_section] - (1 if redo else 0)
            )
            # check if 2D undo is part of any unbreakable set
            is_in_unbreakable = False
            for state in series_states:
                if (
                    not state.breakable and
                    current_section in state.undo_lens and 
                    len(cs_undos) == state.undo_lens[current_section] - (1 if redo else 0)
                ):
                    is_in_unbreakable = True
                    break
            # check if user can perform a 2D undo only
            can_2D = bool(
                not is_in_unbreakable and
                (
                    not redo and cs_undos or
                    redo and cs_redos
                )  # no link to unbreakable set and section has undo states
            )
            return (all_sections_match, can_2D, current_section_match)
    
    def favor3D(self, current_section : int = None, redo=False):
        """If both a 2D and 3D undo are possible and they are not linked, check which one was done more recently.
        Return True if 3D is more recent (and should be favored)."""
        if current_section is None:
            current_section = self.series.current_section
        
        can_3D, can_2D, linked = self.canUndo(current_section, redo)
        if can_3D and can_2D and not linked:
            if redo:
                state_3D = self.redos[-1]
                state_2D = self[current_section].redo_states[-1]
            else:
                state_3D = self.undos[-1]
                state_2D = self[current_section].undo_states[-1]
            if state_3D.time > state_2D.time:
                return True
            else:
                return False
        else:
            return None
    
    def undoState(self, redo=False):
        """Perform a series-wide undo or redo.
        
            Params:
                redo (bool): True if redo should be performed instead of undo
        """
        can_3D, can_2D, linked = self.canUndo(redo=redo)
        
        if not can_3D:
            return
        
        state = self.redos[-1] if redo else self.undos[-1]
        
        # undo/redo the inidividual sections
        sections = state.undo_lens.keys()
        if sections:
            for snum, section in self.series.enumerateSections(
                message=("Re" if redo else "Un") + "doing action..."
            ):
                if snum not in sections:
                    continue
                states = self[snum]
                if redo:
                    states.redoState(section, self.series)
                else:
                    states.undoState(section, self.series)
                section.save()
        
        # undo/redo the series attributes
        state.applySeriesAttributes(self.series)

        # move the state accordingly
        if redo:
            self.undos.append(self.redos.pop())
        else:
            self.redos.append(self.undos.pop())
        
    def undoSection(self, section : Section, redo=False):
        """Undo/redo on a section
        
            Params:
                section (Section): the section to undo/redo on
                redo (bool): True if redo, False if undo
        """
        can_3D, can_2D, linked = self.canUndo(redo=redo)
        
        if not can_2D:
            return
        
        # check if series undo/redo should be broken
        snum = section.n
        if redo: states = self.redos
        else: states = self.undos
        for state in states.copy():
            if (
                section.n in state.undo_lens and (
                    len(self[snum].undo_states) == state.undo_lens[snum] - (1 if redo else 0)
                )
            ):
                if state.breakable:
                    states.remove(state)
                else:
                    return # do not continue if state is unbreakable
                
        if redo:
            self.section_states_dict[section.n].redoState(section, self.series)
        else:
            self.section_states_dict[section.n].undoState(section, self.series)

    def checkOverwrite(self, snum : int):
        """Check if a series undo/redo should be removed.
        
        (Called after a state has just been written to the given section)
        
            Params:
                snum (int): the section number to check
        """
        # check if a series undo has been overwritten
        if self.undos and snum in self.undos[-1].undo_lens:
            if self.undos[-1].undo_lens[snum] == len(self[snum].undo_states):
                self.undos.pop()
        # clear series redos
        for redo in self.redos.copy():
            if snum in redo.undo_lens:
                self.redos.remove(redo)

    





