"""With auto merge on, a stroke is merged with what it overlaps -- and only that.

Tags belong to a trace, not to the contour it is part of: a contour is many
traces and each can carry its own. So the palette applies to the stroke being
drawn, and the traces already on the section keep what they have.

``autoMerge`` runs after every closed stroke and used to merge every selected
trace of that object, whether or not the stroke went anywhere near it. Merging is
destructive -- the traces are deleted and rebuilt from one set of attributes --
so the whole selection came back wearing one trace's tags. Worse, the selection
is a lineage that outlives each merge, because the merged trace is what stays
selected, so it lasted until the user deselected or changed section: tags set on
the palette appeared on new traces, and then removing them changed nothing,
because every later stroke was rebuilt from the tagged seed.

Driven through the real newTrace/autoMerge/mergeTraces over a real Section, with
the trace geometry mapped to pixels the way SectionLayer would.
"""

import types

import pytest

from PyReconstruct.modules.datatypes.contour import Contour
from PyReconstruct.modules.datatypes.section import Section
from PyReconstruct.modules.datatypes.trace import Trace
from PyReconstruct.modules.datatypes.transform import Transform
from PyReconstruct.modules.gui.main.field_widget_2_trace import FieldWidgetTrace
from PyReconstruct.modules.gui.main.field_widget_5_mouse import FieldWidgetMouse
from PyReconstruct.modules.gui.main.field_widget_7_view import FieldWidgetView

WINDOW = [0, 0, 1000, 1000]
PIXMAP = (1000, 1000)

# four disjoint squares in pixel coordinates: disjoint so the merge returns them
# as separate traces, which is what tracing an object in strokes looks like
SQUARES = [
    [(100, 100), (200, 100), (200, 200), (100, 200)],
    [(300, 100), (400, 100), (400, 200), (300, 200)],
    [(500, 100), (600, 100), (600, 200), (500, 200)],
    [(700, 100), (800, 100), (800, 200), (700, 200)],
]


class _Series:
    def __init__(self, auto_merge):
        self.alignment = "default"
        self.window = list(WINDOW)
        self.avg_mag = 1.0
        self._options = {"auto_merge": auto_merge}

    def getOption(self, name, *args):
        return self._options.get(name, False)

    def getAttr(self, name, attr):
        return False

    def addLog(self, *args):
        pass


def _section(series):
    section = Section.__new__(Section)
    section.n = 0
    section.series = series
    section.contours = {}
    section.selected_traces = []
    section.selected_ztraces = []
    section.selected_flags = []
    section.added_traces = []
    section.removed_traces = []
    section.modified_contours = set()
    section.tforms = {"default": Transform([1, 0, 0, 0, 1, 0])}
    section.mag = 1.0
    return section


@pytest.fixture
def field(qapp):
    """A field bound to the real drawing and merging methods."""
    series = _Series(auto_merge=True)
    section = _section(series)

    f = types.SimpleNamespace()
    f.series = series
    f.section = section
    f.hide_trace_layer = False
    f.pixmap_dim = PIXMAP
    f.tracing_trace = None
    f.series_states = None
    f.table_manager = types.SimpleNamespace(
        activeTable=lambda cls: None, updateAll=lambda *a, **k: None
    )
    f.mainwindow = types.SimpleNamespace(
        saveAllData=lambda: None,
        mouse_palette=types.SimpleNamespace(incrementButton=lambda: None),
    )
    for name in ("saveState", "generateView", "update", "updateData",
                 "endPendingEvents"):
        setattr(f, name, lambda *a, **k: None)

    def to_pix(trace):
        return [
            (round((x - WINDOW[0]) / WINDOW[2] * PIXMAP[0]),
             round(PIXMAP[1] - (y - WINDOW[1]) / WINDOW[3] * PIXMAP[1]))
            for x, y in trace.points
        ]

    f.section_layer = types.SimpleNamespace(traceToPix=to_pix)
    f.newTrace = types.MethodType(FieldWidgetTrace.newTrace, f)
    f.mergeTraces = types.MethodType(FieldWidgetTrace.mergeTraces, f)
    f.autoMerge = types.MethodType(FieldWidgetMouse.autoMerge, f)
    f.setTracingTrace = types.MethodType(FieldWidgetView.setTracingTrace, f)
    return f


def _palette_trace(tags=(), color=(0, 255, 0), fill=("none", "none")):
    t = Trace("newobj", color)
    t.points = [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)]
    t.tags = set(tags)
    t.fill_mode = fill
    return t


def _draw(field, square):
    """One closed stroke, as traceRelease performs it."""
    field.newTrace(list(square), field.tracing_trace)
    field.autoMerge()


def _tags(field):
    return [t.tags for t in field.section.contours["newobj"].getTraces()]


OVERLAPPING = [(150, 150), (250, 150), (250, 250), (150, 250)]  # runs into SQUARES[0]


def test_a_disjoint_stroke_leaves_the_traces_already_there_alone(field):
    """The reported sequence: the palette applies to the new stroke only."""
    field.setTracingTrace(_palette_trace(tags={"mytag"}))
    _draw(field, SQUARES[0])
    _draw(field, SQUARES[1])
    assert _tags(field) == [{"mytag"}, {"mytag"}], "premise: the tag arrives"

    before = field.section.contours["newobj"].getTraces()

    # the user removes the tag on the palette; the pencil follows
    field.setTracingTrace(_palette_trace(tags=set()))
    _draw(field, SQUARES[2])
    _draw(field, SQUARES[3])

    assert _tags(field) == [{"mytag"}, {"mytag"}, set(), set()], (
        "the new strokes are untagged and the older traces keep their tag"
    )
    after = field.section.contours["newobj"].getTraces()
    assert after[:2] == before, (
        "the older traces must not even be rebuilt: nothing overlapped them"
    )


def test_a_disjoint_stroke_takes_a_newly_added_tag(field):
    """The same rule the other way round: the stroke's own tags are kept."""
    field.setTracingTrace(_palette_trace(tags=set()))
    _draw(field, SQUARES[0])
    _draw(field, SQUARES[1])

    field.setTracingTrace(_palette_trace(tags={"mytag"}))
    _draw(field, SQUARES[2])

    assert _tags(field) == [set(), set(), {"mytag"}]


def test_per_trace_tags_survive_a_later_stroke(field):
    """A tag set on one trace of a contour stays on that trace."""
    field.setTracingTrace(_palette_trace())
    _draw(field, SQUARES[0])
    _draw(field, SQUARES[1])

    # as editing that one trace's attributes would leave it
    field.section.contours["newobj"].getTraces()[0].tags = {"checkme"}

    _draw(field, SQUARES[2])

    assert _tags(field) == [{"checkme"}, set(), set()]


def test_an_overlapping_stroke_merges_and_keeps_both_sets_of_tags(field):
    """A trace being extended does not lose its tag by being extended."""
    field.setTracingTrace(_palette_trace(tags={"older"}))
    _draw(field, SQUARES[0])

    field.setTracingTrace(_palette_trace(tags={"newer"}, color=(9, 9, 9),
                                        fill=("solid", "always")))
    _draw(field, OVERLAPPING)

    traces = field.section.contours["newobj"].getTraces()
    assert len(traces) == 1, "overlapping strokes still become one trace"
    assert traces[0].tags == {"older", "newer"}
    assert traces[0].color == (9, 9, 9), "the stroke's own attributes win"
    assert traces[0].fill_mode == ("solid", "always")


def test_only_what_the_stroke_runs_into_is_merged(field):
    """The disjoint trace is untouched while the overlapping one is absorbed."""
    field.setTracingTrace(_palette_trace(tags={"far"}))
    _draw(field, SQUARES[3])
    far = field.section.contours["newobj"].getTraces()[0]

    field.setTracingTrace(_palette_trace(tags={"near"}))
    _draw(field, SQUARES[0])
    _draw(field, OVERLAPPING)

    traces = field.section.contours["newobj"].getTraces()
    assert len(traces) == 2
    assert far in traces, "the far trace is not even rebuilt"
    assert far.tags == {"far"}
    assert [t.tags for t in traces if t is not far] == [{"near"}]


def test_a_chain_of_overlaps_is_merged(field):
    """The stroke runs into A, A runs into B: all three combine."""
    field.setTracingTrace(_palette_trace())
    _draw(field, [(100, 100), (200, 100), (200, 200), (100, 200)])
    _draw(field, [(180, 100), (280, 100), (280, 200), (180, 200)])
    _draw(field, [(260, 100), (360, 100), (360, 200), (260, 200)])

    assert len(field.section.contours["newobj"].getTraces()) == 1


def test_auto_merge_off_leaves_strokes_alone(field):
    """With the option off, nothing is rebuilt and each stroke keeps its own."""
    field.series._options["auto_merge"] = False

    field.setTracingTrace(_palette_trace(tags={"mytag"}))
    _draw(field, SQUARES[0])
    field.setTracingTrace(_palette_trace(tags=set()))
    _draw(field, OVERLAPPING)

    assert _tags(field) == [{"mytag"}, set()]


def test_explicit_merge_still_takes_the_first_selected_trace(field):
    """The Merge action's own rule is unchanged: the first trace selected wins."""
    field.series._options["auto_merge"] = False

    field.setTracingTrace(_palette_trace(tags={"first"}))
    _draw(field, SQUARES[0])
    field.setTracingTrace(_palette_trace(tags={"second"}))
    _draw(field, OVERLAPPING)

    traces = field.section.contours["newobj"].getTraces()
    field.mergeTraces(traces.copy())

    assert _tags(field) == [{"first"}]
