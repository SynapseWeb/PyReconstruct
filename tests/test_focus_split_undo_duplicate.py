"""Regression test for issue #99.

"Trace Duplication from Undoing an Erroneous Merge":

    When I am in Focus mode and accidentally add a trace to an object
    incorrectly, I then shift-click the trace again to make it an <obj>_split.
    If I then try to undo this change, it creates a duplicate trace --
    resulting in two traces, one with the original name and one with the
    <obj>_split name.

Root cause: the focus-mode split branch of ``FieldWidgetMouse.pointerRelease``
mutates the section (``section.editTraceAttributes(..., name=f"{name}_split")``)
and then only calls ``generateView()``. It never calls ``saveState()``, so no
``SectionStates.addState`` is pushed for the split. It is the *only*
``editTraceAttributes`` caller in the GUI that is neither decorated with
``@field_interaction`` nor followed by an explicit ``saveState()`` -- the sibling
branch three lines below it (the "incorporate into obj" merge, via
``pasteAttributes``) is decorated and does save.

Why that produces a *duplicate* rather than merely an un-undoable split.
``SectionStates.undoState`` restores only the contours named in
``current_state.getModifiedContours()``. Because the split was never recorded,
``current_state`` is still the one written by the *previous* edit, whose modified
set names that edit's contours -- and not ``<obj>_split``, which did not exist
yet. So undo faithfully restores the trace under its original name while the
``<obj>_split`` contour, which nothing knows about, is left holding its own copy.
One trace becomes two.

Note on why the reproduction needs a recorded edit *before* the merge: with
exactly one undo state, ``undoState`` takes its single-state branch and
wholesale-replaces ``section.contours`` with the baseline, which happens to
discard the orphaned ``<obj>_split`` contour and hides the bug. The duplication
needs the multi-state branch, which restores contours one by one. Two or more
prior edits is the normal state of any real editing session.

Driven headlessly against the real ``FieldWidgetMouse.pointerRelease``, the real
``FieldWidgetTrace.selectTrace``/``pasteAttributes`` bound to a duck-typed stub,
a real ``Series``/``Section`` built in a temporary directory, and a real
``SeriesStates``. No ``MainWindow`` and no Qt event loop.
"""
import types

import pytest
from PySide6.QtCore import Qt

from PyReconstruct.modules.datatypes import Series
from PyReconstruct.modules.datatypes.trace import Trace
from PyReconstruct.modules.backend.func.state_manager import SeriesStates
from PyReconstruct.modules.gui.main.field_widget_2_trace import FieldWidgetTrace
from PyReconstruct.modules.gui.main.field_widget_5_mouse import FieldWidgetMouse

SNUM = 0
FOCUS_OBJ = "d03"        # the object the user is focused on
VICTIM_OBJ = "d03p13"    # the object whose trace is merged in by accident
BYSTANDER = "d03sp12"    # unrelated object, used for the prior recorded edit
BYSTANDER_2 = "d03sp13"  # unrelated object, touched by nothing
SPLIT_OBJ = f"{FOCUS_OBJ}_split"

# Four disjoint unit squares, so no two objects share a point and a mis-restored
# contour cannot be mistaken for a correctly restored one.
SHAPES = {
    FOCUS_OBJ: [(0, 0), (1, 0), (1, 1), (0, 1)],
    VICTIM_OBJ: [(3, 0), (4, 0), (4, 1), (3, 1)],
    BYSTANDER: [(0, 3), (1, 3), (1, 4), (0, 4)],
    BYSTANDER_2: [(3, 3), (4, 3), (4, 4), (3, 4)],
}


def _counts(section):
    """name -> number of traces, omitting emptied contours."""
    return {
        name: len(contour.getTraces())
        for name, contour in section.contours.items()
        if len(contour.getTraces())
    }


def _one_trace(section, name):
    traces = section.contours[name].getTraces()
    assert len(traces) == 1, f"fixture changed: {name} has {len(traces)} traces"
    return traces[0]


class _Field:
    """The FieldWidget surface that ``pointerRelease`` actually touches.

    Deliberately not a real FieldWidget: constructing one drags in MainWindow,
    which blocks indefinitely under the offscreen platform. The real methods
    under test are bound onto this instead.
    """

    def __init__(self, series, section, series_states, focus_obj):
        self.series = series
        self.section = section
        self.series_states = series_states
        self.focus_mode = focus_obj
        self.hide_trace_layer = False

        # single-click, left button, on a trace
        self.lclick = True
        self.single_click = True
        self.click_time = 0.0
        self.max_click_time = 1.0
        self.zarr_layer = None
        self.selected_trace = None
        self.selected_type = "trace"
        self.is_moving_trace = False
        self.is_selecting_traces = False
        self.current_trace = []

        # toggleFocusMode copies the focused object's traces to the clipboard;
        # pasteAttributes reads clipboard[0] for the name to apply.
        self.clipboard = [_one_trace(section, focus_obj).copy()]

        self.save_state_calls = 0

        self.isSingleClicking = types.MethodType(
            FieldWidgetMouse.isSingleClicking, self
        )
        self.selectTrace = types.MethodType(FieldWidgetTrace.selectTrace, self)
        self.pasteAttributes = types.MethodType(
            FieldWidgetTrace.pasteAttributes, self
        )

    # --- the real FieldWidget.saveState, minus the tables and the main window.
    # field_widget_1_base.saveState is addState + updateData; updateData ends in
    # TableManager.updateAll, which is what calls section.clearTracking().
    def saveState(self):
        self.save_state_calls += 1
        self.series_states[self.section].addState(self.section, self.series)
        self.series_states.checkOverwrite(self.section.n)
        self.section.clearTracking()

    def undo(self):
        self.section.selected_traces = []
        self.section.selected_ztraces = []
        self.section.selected_flags = []
        self.series_states.undoSection(self.section)

    def generateView(self, *args, **kwargs):
        pass

    def update(self, *args, **kwargs):
        pass


def _shift_click(field, trace):
    """Shift-click ``trace`` in the field, in pointer mode."""
    field.selected_trace = trace
    field.selected_type = "trace"
    event = types.SimpleNamespace(modifiers=lambda: Qt.ShiftModifier)
    FieldWidgetMouse.pointerRelease(field, event)


@pytest.fixture
def series(tmp_path):
    """A real, writable, three-section series with four single-trace objects.

    Built rather than checked in: the test needs a real ``Series`` because
    ``SeriesStates`` reads the series' hidden directory, log and object
    attributes, and building one keeps the fixture visible in this file rather
    than hidden in a binary asset.
    """
    images = []
    for i in range(3):
        image = tmp_path / f"section{i}.tif"
        image.write_bytes(b"")  # never decoded; the field is stubbed out
        images.append(str(image))

    s = Series.new(images, "focus_split", 0.01, 0.05)

    section = s.loadSection(SNUM)
    for name, points in SHAPES.items():
        trace = Trace(name, (255, 0, 0))
        trace.points = list(points)
        section.addTrace(trace, log_event=False)
    section.save()
    s.data.updateSection(section, all_traces=True)

    yield s
    s.close()


@pytest.fixture
def field(series):
    """A stub field over the fixture series, focused on FOCUS_OBJ, with one edit
    already recorded so that undo takes its multi-state path."""
    series.current_section = SNUM
    section = series.loadSection(SNUM)

    states = SeriesStates(series)
    states[section]  # initialize the baseline state for this section

    f = _Field(series, section, states, FOCUS_OBJ)

    # A prior, ordinary, *recorded* edit on an unrelated object -- i.e. the user
    # has done something earlier in the session. Recoloring is the smallest
    # such edit that goes through the normal editTraceAttributes + saveState
    # path.
    bystander = _one_trace(section, BYSTANDER)
    section.editTraceAttributes(
        traces=[bystander], name=None, color=(1, 2, 3), tags=None, mode=None
    )
    f.saveState()
    assert len(states[SNUM].undo_states) == 1

    # Focus mode selects every trace of the focused object (toggleFocusMode).
    section.selected_traces = [
        t for t in section.tracesAsList() if t.name == FOCUS_OBJ
    ]
    return f


def _merge_then_split(field):
    """The reported sequence: accidental merge into the focused object, then a
    second shift-click that splits it back out under a `_split` name."""
    section = field.section

    # 1. accidental merge: shift-click a trace of another object while focused
    #    on FOCUS_OBJ -> pointerRelease takes the "incorporate into obj" branch.
    _shift_click(field, _one_trace(section, VICTIM_OBJ))
    assert VICTIM_OBJ not in _counts(section), "merge did not move the trace"
    after_merge = _counts(section)

    # 2. the correction: shift-click the same trace again. It now belongs to the
    #    focused object, so pointerRelease takes the split branch.
    split_me = [
        t for t in section.contours[FOCUS_OBJ].getTraces()
        if t in section.selected_traces
    ][-1]
    _shift_click(field, split_me)
    assert SPLIT_OBJ in _counts(section), "split branch did not run"

    return after_merge


def test_undo_after_focus_mode_split_does_not_duplicate_trace(field):
    """Issue #99: undoing the split must not leave the trace in two places."""
    section = field.section
    after_merge = _merge_then_split(field)

    field.undo()
    after_undo = _counts(section)

    # The reported symptom, stated as a count: the trace must not exist twice,
    # once under its original name and once as <obj>_split.
    assert after_undo.get(SPLIT_OBJ, 0) == 0, (
        f"undo left an orphaned {SPLIT_OBJ} contour behind: {after_undo}"
    )
    assert not (after_undo.get(VICTIM_OBJ, 0) and after_undo.get(SPLIT_OBJ, 0)), (
        "trace duplicated across its original name and the _split name: "
        f"{after_undo}"
    )

    # Undoing the split must land exactly on the state before the split, which
    # is the state right after the merge -- no traces gained, none lost.
    assert sum(after_undo.values()) == sum(after_merge.values()), (
        f"trace count changed across undo: {after_merge} -> {after_undo}"
    )
    assert after_undo == after_merge, (
        f"undo did not restore the pre-split state: {after_merge} -> {after_undo}"
    )


def test_focus_mode_split_records_an_undo_state(field):
    """The defect itself: the split branch must push exactly one undo state, as
    every other trace-editing field interaction does."""
    section = field.section
    states = field.series_states[SNUM]

    _shift_click(field, _one_trace(section, VICTIM_OBJ))  # merge
    undos_after_merge = len(states.undo_states)
    calls_after_merge = field.save_state_calls

    split_me = [
        t for t in section.contours[FOCUS_OBJ].getTraces()
        if t in section.selected_traces
    ][-1]
    _shift_click(field, split_me)  # split

    assert field.save_state_calls == calls_after_merge + 1, (
        "focus-mode split did not save an undo state"
    )
    assert len(states.undo_states) == undos_after_merge + 1


def test_focus_mode_split_state_names_both_contours(field):
    """The recorded state must name *both* sides of the split, so that undo
    knows to empty the new <obj>_split contour as well as restore the old one.
    Recording only one side is what turns one trace into two."""
    _merge_then_split(field)

    modified = field.series_states[SNUM].current_state.getModifiedContours()
    assert FOCUS_OBJ in modified
    assert SPLIT_OBJ in modified, (
        f"split state does not name {SPLIT_OBJ}; undo cannot clean it up: "
        f"{sorted(modified)}"
    )


def test_focus_mode_merge_branch_still_saves_one_state(field):
    """Guardrail: the sibling 'incorporate into obj' branch is unchanged -- one
    state per merge, via @field_interaction."""
    section = field.section
    before = field.save_state_calls

    _shift_click(field, _one_trace(section, VICTIM_OBJ))

    assert field.save_state_calls == before + 1
    assert VICTIM_OBJ not in _counts(section)


def test_bystanders_untouched_by_split_and_undo(field):
    """Guardrail: the split and its undo must not disturb unrelated objects."""
    section = field.section
    before = _counts(section)
    _merge_then_split(field)
    field.undo()
    after = _counts(section)

    assert after[BYSTANDER] == before[BYSTANDER]
    assert after[BYSTANDER_2] == before[BYSTANDER_2]
