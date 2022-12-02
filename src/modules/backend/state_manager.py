from modules.pyrecon.section import Section
from modules.pyrecon.contour import Contour

class FieldState():

    def __init__(self, contours : dict, tforms : dict, updated_contours=None):
        """Create a field state with traces and the transform.
        
            Params:
                contours (dict): all the contours on a section
                tforms (dict): the tforms for the section state
                updated_contours: the names of the modified contours
        """
        self.contours = {}
        # first state made for a section (or copy)
        if updated_contours is None:
            for contour_name in contours:
                self.contours[contour_name] = contours[contour_name].copy()
        # added another state
        else:
            for contour_name in updated_contours:
                self.contours[contour_name] = contours[contour_name].copy()
        # save tforms
        self.tforms = {}
        for alignment_name in tforms:
            self.tforms[alignment_name] = tforms[alignment_name].copy()
    
    def copy(self):
        return FieldState(self.contours, self.tforms)
    
    def getContours(self):
        contours = {}
        for cname in self.contours:
            contours[cname] = self.contours[cname].copy()
        return contours
    
    def getModifiedContours(self):
        return set(self.contours.keys())
    
    def getTforms(self):
        return self.tforms.copy()

class SectionStates():

    def __init__(self, section : Section):
        """Create the section state manager.
        
            Params:
                section (Section): the sectin object to store states for
        """
        self.current_state = FieldState(section.contours, section.tforms)
        self.undo_states = []
        self.redo_states = []
    
    def addState(self, section : Section):
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
                set([trace.name for trace in section.removed_traces])
            )
        )
        # set the new current state
        self.current_state = FieldState(
            section.contours,
            section.tforms,
            updated_contours
        )
        
    def undoState(self, section : Section) -> set:
        """Restore an undo state on the section.
        
            Params:
                section (Section): the section to restore
            Returns:
                (set): the names of modified contours
        """
        # if there are not undo states
        if len(self.undo_states) == 0:
            return
        # if only one undo state exists
        elif len(self.undo_states) == 1:
            modified_contours = self.current_state.getModifiedContours()
            section.contours = self.undo_states[0].getContours()
        # if there are multiple undo states
        else:
            # iterate backwards and find the last ieration of the recently changed contours
            last_changed = self.current_state.getModifiedContours()
            modified_contours = last_changed.copy()
            for state in reversed(self.undo_states):
                state_contours = state.getContours()
                for contour in last_changed.copy():
                    if contour in state_contours:
                        section.contours[contour] = state_contours[contour]
                        last_changed.remove(contour)
                if not last_changed:
                    break
            # if the contour was not found (aka it was just created)
            if last_changed:
                for contour in last_changed:
                    section.contours[contour] = Contour(contour)

        # restore the transforms
        restored_tforms = self.undo_states[-1].getTforms()
        section.tforms = restored_tforms

        # edit the undo/redo stacks and the current state
        self.redo_states.append(self.current_state)
        self.current_state = self.undo_states.pop().copy()

        # return the modified contours
        return modified_contours
    
    def redoState(self, section : Section) -> set:
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
        # restore the transforms
        section.tforms = redo_state.getTforms()

        # edit the undo/redo stacks and the current state
        self.undo_states.append(self.current_state)
        self.current_state = self.redo_states.pop()

        # return the modified contours
        return modified_contours