"""Regression test for upstream issue #51.

"Right-click deletes trace when using the scissors tool and all other traces
are hidden."

Root cause: the scissors tool picks a trace up by DELETING it in
``scissorsPress`` (a raw ``section.deleteTraces`` call, not guarded by
``@field_interaction``) and relies on the right-click completion in
``lineRelease`` to recreate it via ``newTrace``. But ``newTrace`` is wrapped by
``@field_interaction``, which is a no-op while the trace layer is hidden
(``self.hide_trace_layer``). So a scissors pickup + right-click completion with
the trace layer hidden deleted the trace with nothing put back -- destroying
the user's work.

The per-trace ``hidden`` flag ("hide all OTHER traces") does NOT trigger this:
the edited trace is not itself hidden, and ``newTrace`` only gates on
``hide_trace_layer``. The reproducing state is the trace layer being hidden.

The fix restores the picked-up trace in ``lineRelease`` whenever the
replacement was not actually created. Sibling tools (knife ``cutTrace``,
``mergeTraces``) delete and recreate inside a single ``@field_interaction``
method, so they are skipped atomically when hidden and never lose data.

Driven headlessly against the real ``FieldWidgetMouse.scissorsPress`` /
``lineRelease`` and the real ``FieldWidgetTrace.newTrace`` bound to a duck-typed
stub, over a real ``Section`` -- no Qt event loop.
"""
import types

import pytest

from PyReconstruct.modules.datatypes.trace import Trace
from PyReconstruct.modules.datatypes.contour import Contour
from PyReconstruct.modules.datatypes.section import Section
from PyReconstruct.modules.datatypes.transform import Transform
from PyReconstruct.modules.gui.main.field_widget_5_mouse import (
    FieldWidgetMouse,
    SCISSORS,
)
from PyReconstruct.modules.gui.main.field_widget_2_trace import FieldWidgetTrace


# a picked-up trace maps to these pixel coords (traceToPix is stubbed);
# window/pixmap/mag below make the field mapping non-degenerate so newTrace
# keeps >= 2 points when it does run.
PIX = [(100, 900), (300, 900), (300, 700), (100, 700)]


class _Series:
    def __init__(self):
        self.alignment = "default"
        self.window = [0, 0, 1000, 1000]
        self.log = []
        self.palette_traces = [[Trace("pal", (0, 255, 0), True)]]
        self.palette_index = (0, 0)

    def getAttr(self, name, attr):
        return False

    def addLog(self, *a):
        self.log.append(a)

    def getOption(self, k):
        return False


def _mk_trace(name, closed):
    t = Trace(name, (255, 0, 0), closed)
    t.points = [(100, 100), (300, 100), (300, 300), (100, 300)]
    return t


def _build_section(edit_trace, other_hidden):
    s = Section.__new__(Section)
    s.n = 0
    s.series = _Series()
    s.contours = {}
    other = _mk_trace("other", True)
    other.hidden = other_hidden
    for t in (edit_trace, other):
        s.contours.setdefault(t.name, Contour(t.name)).append(t)
    s.selected_traces = [edit_trace]
    s.selected_ztraces = []
    s.selected_flags = []
    s.modified_contours = set()
    s.added_traces = []
    s.removed_traces = []
    s.tforms = {"default": Transform([1, 0, 0, 0, 1, 0])}
    s.mag = 1.0
    return s


def _count(section, name):
    contour = section.contours.get(name)
    return len(contour.getTraces()) if contour else 0


def _run_scissors_cycle(hide_trace_layer, other_hidden, closed):
    """Simulate: left-click pickup (scissorsPress) then right-click completion
    (lineRelease). Returns (present_after_pickup, present_after_complete)."""
    edit = _mk_trace("mytrace", closed)
    sec = _build_section(edit, other_hidden=other_hidden)

    stub = types.SimpleNamespace()
    stub.lclick = True
    stub.rclick = False
    stub.clicked_x, stub.clicked_y = 100, 900
    stub.section = sec
    stub.series = sec.series
    stub.hide_trace_layer = hide_trace_layer
    stub.pixmap_dim = (1000, 1000)
    stub.mouse_mode = SCISSORS
    stub.is_scissoring = False
    stub.is_line_tracing = False
    stub.current_trace = []
    stub.selected_trace = None
    stub.selected_type = None
    stub.tracing_trace = None
    stub.section_layer = types.SimpleNamespace(
        getTrace=lambda x, y: (edit, "trace"),
        traceToPix=lambda t: list(PIX),
    )
    stub.mainwindow = types.SimpleNamespace(
        checkActions=lambda *a, **k: None,
        mouse_palette=types.SimpleNamespace(incrementButton=lambda: None),
    )
    for attr in (
        "deselectAllTraces", "generateView", "activateMouseBoundaryTimer",
        "deactivateMouseBoundaryTimer", "update", "saveState",
        "setMouseMode", "setTracingTrace", "autoMerge",
    ):
        setattr(stub, attr, (lambda *a, **k: None))
    stub.newTrace = types.MethodType(FieldWidgetTrace.newTrace, stub)

    FieldWidgetMouse.scissorsPress(stub, None)
    after_pickup = _count(sec, "mytrace")

    stub.lclick = False
    stub.rclick = True
    FieldWidgetMouse.lineRelease(stub, None)
    after_complete = _count(sec, "mytrace")

    return after_pickup, after_complete


@pytest.mark.parametrize("closed", [False, True])
@pytest.mark.parametrize("other_hidden", [False, True])
def test_scissors_rightclick_preserves_trace_when_layer_hidden(closed, other_hidden):
    """The reproduced bug: trace layer hidden -> scissors pickup + right-click
    used to leave the trace deleted. It must now survive."""
    after_pickup, after_complete = _run_scissors_cycle(
        hide_trace_layer=True, other_hidden=other_hidden, closed=closed
    )
    # pickup deletes the original (that part is unchanged)...
    assert after_pickup == 0
    # ...and the completion must put it back rather than destroy it
    assert after_complete == 1, "scissors right-click destroyed the trace"


@pytest.mark.parametrize("closed", [False, True])
@pytest.mark.parametrize("other_hidden", [False, True])
def test_scissors_rightclick_still_creates_replacement_when_visible(closed, other_hidden):
    """Guardrail: the normal (layer visible) scissors flow must be unchanged --
    the completion creates the (re)traced replacement."""
    after_pickup, after_complete = _run_scissors_cycle(
        hide_trace_layer=False, other_hidden=other_hidden, closed=closed
    )
    assert after_pickup == 0
    assert after_complete == 1
