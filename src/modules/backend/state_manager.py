from modules.pyrecon.section import Section

class FieldState():

    def __init__(self, contours : dict, tforms : dict, updated_contours=None):
        """Create a field state with traces and the transform"""
        self.contours = {}
        # first state made for a section
        if updated_contours is None:
            for contour_name in contours:
                self.contours[contour_name] = []
                for trace in contours[contour_name]:
                    self.contours[contour_name].append(trace.copy())
        # added another state
        else:
            for contour_name in updated_contours:
                self.contours[contour_name] = []
                if contour_name in contours:
                    for trace in contours[contour_name]:
                        self.contours[contour_name].append(trace.copy())
        # save tforms
        self.tforms = {}
        for alignment_name in tforms:
            self.tforms[alignment_name] = tforms[alignment_name].copy()
    
    def getContours(self):
        return self.contours.copy()
    
    def getModifiedContours(self):
        return set(self.contours.keys())
    
    def getTforms(self):
        return self.tforms.copy()

class SectionStates():

    def __init__(self, section : Section):
        self.current_state = FieldState(section.contours, section.tforms)
        self.undo_states = []
        self.redo_states = []
    
    def addState(self, section : Section):
        # clear redo states
        self.redo_states = []
        # push current state to undo states
        self.undo_states.append(self.current_state)
        # set the new current state
        self.current_state = FieldState(
            section.contours,
            section.tforms,
            section.contours_to_update
        )
    
    def undoState(self, section : Section):
        if len(self.undo_states) == 0:
            return
        # get the restored contours
        # iterate backwards through undo states and add contours
        restored_contours = {}
        for state in reversed(self.undo_states):
            state_contours = state.getContours()
            for contour_name in state_contours:
                if contour_name not in restored_contours:
                    restored_contours[contour_name] = state_contours[contour_name]
        # get the restored transforms
        restored_tforms = self.undo_states[-1].getTforms()
        # get the objects that were changed
        contours_to_update = set(self.current_state.getContours().keys())

        # restore these values in the section object
        section.contours = restored_contours
        section.tforms = restored_tforms
        section.contours_to_update = section.contours_to_update.union(contours_to_update)

        # edit the undo/redo stacks and the current state
        self.redo_states.append(self.current_state)
        self.current_state = self.undo_states.pop()
    
    def redoState(self, section : Section):
        if len(self.redo_states) == 0:
            return
        redo_state = self.redo_states[-1]
        # restore the contours on the section
        state_contours = redo_state.getContours()
        for contour_name in state_contours:
            section.contours[contour_name] = state_contours[contour_name]
        # restore the transforms
        section.tforms = redo_state.getTforms()
        # update the objects that were changed
        contours_to_update = set(state_contours.keys())
        section.contours_to_update = section.contours_to_update.union(contours_to_update)

        # edit the undo/redo stacks and the current state
        self.undo_states.append(self.current_state)
        self.current_state = self.redo_states.pop()