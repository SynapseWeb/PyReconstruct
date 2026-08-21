"""One selected row is one item, however many of its cells are selected.

The lists select cells, not rows -- nothing calls setSelectionBehavior -- so
``selectedIndexes()`` reports one index per selected cell. Building the selection
from those indexes counted a row once per cell, and every list did it.

For the trace list that was destructive rather than merely wrong. A row selected
across its columns handed the same trace to ``editTraceAttributes`` several
times; the first pass replaces the trace, so the second raises out of the
command, past the decorator that saves the state and refreshes the lists: the
edit half applied, no error surfaced to the user, and the tag they had just added
missing from the list they were looking at.

Driven through the real widgets over the real fixture series -- what the test
supplies is the selection, which is otherwise the user's mouse.
"""

import types

import pytest

from PyReconstruct.modules.datatypes.contour import Contour
from PyReconstruct.modules.datatypes.section import Section
from PyReconstruct.modules.datatypes.trace import Trace
from PyReconstruct.modules.datatypes.transform import Transform


@pytest.fixture
def trace_list(qapp, real_series):
    """A real TraceTableWidget on the fixture series' current section."""
    from PySide6.QtWidgets import QMainWindow

    from PyReconstruct.modules.backend.table.manager import TableManager

    series = real_series
    section = series.loadSection(series.current_section)

    mainwindow = QMainWindow()
    mainwindow.field = types.SimpleNamespace(
        getTraceMenu=lambda is_in_field=True: []
    )
    mainwindow.addDockWidget = lambda *args, **kwargs: None

    manager = TableManager(series, section, None, mainwindow)
    manager.newTable("trace", section)
    table = manager.tables["trace"][0]

    yield table, section, series

    table.deleteLater()
    mainwindow.deleteLater()


def _rows_for(table, name):
    return [
        r for r in range(table.table.rowCount())
        if table.table.item(r, 0).text() == name
    ]


def _select_whole_rows(table, rows):
    """What dragging across the columns, or ctrl+A, leaves selected."""
    table.table.clearSelection()
    for r in rows:
        table.table.selectRow(r)


def _select_one_cell(table, rows):
    """What a plain click leaves selected."""
    table.table.clearSelection()
    for r in rows:
        table.table.item(r, 0).setSelected(True)


def test_whole_row_selection_yields_one_entry_per_row(trace_list):
    table, section, _ = trace_list
    name = sorted(section.contours.keys())[0]
    rows = _rows_for(table, name)

    _select_whole_rows(table, rows)

    assert len(table.table.selectedIndexes()) > len(rows), (
        "premise: selecting a row selects each of its cells"
    )
    assert len(table.getSelected()) == len(rows)
    assert len(table.getTraces(table.getSelected())) == len(rows)


def test_one_cell_selection_is_unchanged(trace_list):
    table, section, _ = trace_list
    name = sorted(section.contours.keys())[0]
    rows = _rows_for(table, name)

    _select_one_cell(table, rows)

    assert len(table.getSelected()) == len(rows)


def test_single_selection_accepts_a_fully_selected_row(trace_list):
    """``single=True`` rejected one row selected across its columns."""
    table, section, _ = trace_list
    name = sorted(section.contours.keys())[0]
    row = _rows_for(table, name)[:1]

    _select_whole_rows(table, row)

    assert table.getSelected(single=True) is not None, (
        "one row is one trace, so a single-selection option has to accept it"
    )


def _section_with_one_trace(tags):
    class _Series:
        alignment = "default"

        def getAttr(self, name, attr):
            return False

        def addLog(self, *args):
            pass

    section = Section.__new__(Section)
    section.n = 0
    section.series = _Series()
    section.contours = {}
    section.selected_traces = []
    section.added_traces = []
    section.removed_traces = []
    section.modified_contours = set()
    section.tforms = {"default": Transform([1, 0, 0, 0, 1, 0])}
    section.mag = 1.0

    trace = Trace("axon", (255, 0, 0))
    trace.points = [(0, 0), (1, 0), (1, 1)]
    trace.tags = set(tags)
    section.contours["axon"] = Contour("axon", [trace])
    return section, trace


def test_edit_attributes_survives_a_repeated_trace():
    """The same defence one layer down, where the damage was done."""
    section, trace = _section_with_one_trace(set())

    section.editTraceAttributes(
        [trace, trace, trace], None, None, {"mytag"}, None, log_event=False
    )

    traces = section.contours["axon"].getTraces()
    assert len(traces) == 1, "the trace must not be duplicated or dropped"
    assert traces[0].tags == {"mytag"}


def test_edit_attributes_keeps_a_repeated_trace_selected_once():
    section, trace = _section_with_one_trace(set())
    section.selected_traces = [trace]

    section.editTraceAttributes(
        [trace, trace], None, None, {"mytag"}, None, log_event=False
    )

    assert len(section.selected_traces) == 1
    assert section.selected_traces[0].tags == {"mytag"}
