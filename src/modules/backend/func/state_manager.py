from modules.pyrecon import (
    Series,
    Section,
    Contour,
    Ztrace
)

class FieldState():

    def __init__(self, contours : dict, ztraces : dict, tforms : dict, updated_contours=None, updated_ztraces=None):
        """Create a field state with traces and the transform.
        
            Params:
                contours (dict): all the contours on a section
                tforms (dict): the tforms for the section state
                updated_contours: the names of the modified contours
        """
        self.contours = {}
        self.ztraces = {}
        # first state made for a section (or copy)
        if updated_contours is None:
            for contour_name in contours:
                self.contours[contour_name] = contours[contour_name].copy()
        # added another state
        else:
            for contour_name in updated_contours:
                self.contours[contour_name] = contours[contour_name].copy()
        
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
    
    def copy(self):
        return FieldState(self.contours, self.ztraces, self.tforms)
    
    def getContours(self):
        contours = {}
        for cname in self.contours:
            contours[cname] = self.contours[cname].copy()
        return contours
    
    def getZtraces(self):
        ztraces = {}
        for zname in self.ztraces:
            ztraces[zname] = self.ztraces[zname].copy()
        return ztraces
    
    def getModifiedContours(self):
        return set(self.contours.keys())
    
    def getModifiedZtraces(self):
        return set(self.ztraces.keys())
    
    def getTforms(self):
        return self.tforms.copy()

class SectionStates():

    def __init__(self, section : Section, series : Series):
        """Create the section state manager.
        
            Params:
                section (Section): the sectin object to store states for
        """
        self.current_state = FieldState(section.contours, series.ztraces, section.tforms)
        self.undo_states = []
        self.redo_states = []
    
    def addState(self, section : Section, series : Series):
        """Add a new undo state (called when an action is performed.
        
            Params:
                section (Section): the section object
        """
        # clear redo states
        self.redo_states = []
        # push current state to undo states
        self.undo_states.append(self.current_state)
        # get the names of the updated contours
        updated_contours = (
            set([trace.name for trace in section.added_traces]).union(
                set([trace.name for trace in section.removed_traces]).union(
                    set([trace.name for trace in section.modified_traces])
                )
            )
        )
        # get the updated ztraces
        updated_ztraces = series.modified_ztraces.copy()
        # set the new current state
        self.current_state = FieldState(
            section.contours,
            series.ztraces,
            section.tforms,
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
        elif len(self.undo_states) == 1:
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

        # restore the transforms
        restored_tforms = self.undo_states[-1].getTforms()
        section.tforms = restored_tforms

        # edit the undo/redo stacks and the current state
        self.redo_states.append(self.current_state)
        self.current_state = self.undo_states.pop().copy()

        # return the modified contours and ztraces
        return modified_contours, modified_ztraces
    
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
        
        # restore the transforms
        section.tforms = redo_state.getTforms()

        # edit the undo/redo stacks and the current state
        self.undo_states.append(self.current_state)
        self.current_state = self.redo_states.pop()

        # return the modified contours
        return modified_contours, modified_ztraces

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



