"""An action in a list's context menu operates on that list's selection.

The field's methods are shared by the field and the lists, and each decorator
worked out where it had been invoked from by asking Qt which table had keyboard
focus. No table has focus while its own context menu is open -- the menu is the
active window, and the action fires before focus returns -- so every context-menu
action in a list fell through to the field's selection.

For tags that meant an edit started on one row of the trace list was applied to
whatever the user had selected in the field, usually the traces they had just
drawn: the row they picked was left alone, and traces they never touched had
their tags replaced. The dialog was even prefilled from the field's traces.
"""

import types

import pytest

from PyReconstruct.modules.datatypes.trace import Trace
from PyReconstruct.modules.gui.table.object import ObjectTableWidget
from PyReconstruct.modules.gui.table.trace import TraceTableWidget


@pytest.fixture
def field_and_lists(qapp, real_series):
    """A field bound to its real methods, with a real trace list open on it."""
    from PySide6.QtWidgets import QMainWindow

    from PyReconstruct.modules.backend.func.state_manager import SeriesStates
    from PyReconstruct.modules.backend.table.manager import TableManager
    from PyReconstruct.modules.gui.main.field_widget_1_base import FieldWidgetBase
    from PyReconstruct.modules.gui.main.field_widget_2_trace import FieldWidgetTrace

    series = real_series
    section = series.loadSection(series.current_section)

    mainwindow = QMainWindow()
    mainwindow.saveAllData = lambda: None
    mainwindow.seriesModified = lambda *a: None
    mainwindow.checkActions = lambda *a: None
    mainwindow.addDockWidget = lambda *a, **k: None

    field = types.SimpleNamespace()
    field.getTraceMenu = lambda is_in_field=True: []
    mainwindow.field = field

    states = SeriesStates(series)
    states.section_states_dict[section.n].initialize(section, series)
    manager = TableManager(series, section, states, mainwindow)
    manager.newTable("trace", section)

    field.series = series
    field.section = section
    field.series_states = states
    field.table_manager = manager
    field.mainwindow = mainwindow
    field.hide_trace_layer = False
    field.generateView = lambda *a, **k: None
    field.update = lambda *a, **k: None
    field.updateData = types.MethodType(FieldWidgetBase.updateData, field)
    field.saveState = types.MethodType(FieldWidgetBase.saveState, field)
    field.traceDialog = types.MethodType(FieldWidgetTrace.traceDialog, field)

    yield field, manager, manager.tables["trace"][0], section

    mainwindow.deleteLater()


def _fake_dialog(monkeypatch, tags, shown):
    """Replace TraceDialog, recording which traces it was handed."""
    from PyReconstruct.modules.gui.main import field_widget_2_trace as mod

    class FakeTraceDialog:
        def __init__(self, parent, traces, **kwargs):
            shown.extend(sorted(t.name for t in traces))

        def exec(self):
            trace = Trace(None, None)
            trace.color = None
            trace.tags = set(tags)
            trace.fill_mode = (None, None)
            return trace, True

    monkeypatch.setattr(mod, "TraceDialog", FakeTraceDialog)


def _select_row(table, name):
    for r in range(table.table.rowCount()):
        if table.table.item(r, 0).text() == name:
            table.table.clearSelection()
            table.table.item(r, 0).setSelected(True)
            return
    raise AssertionError(f"no row for {name}")


def _tags(section, name):
    return [t.tags for t in section.contours[name].getTraces()]


def test_edit_from_the_trace_list_applies_to_that_row_only(
    field_and_lists, monkeypatch
):
    field, manager, table, section = field_and_lists
    names = sorted(section.contours.keys())
    clicked, others = names[0], names[1:3]

    _select_row(table, clicked)
    # the field still holds the traces the user drew before opening the list
    section.selected_traces = [
        section.contours[n].getTraces()[0] for n in others
    ]

    assert not table.table.hasFocus(), (
        "premise: the list does not hold keyboard focus when its menu acts"
    )

    shown = []
    _fake_dialog(monkeypatch, {"mytag"}, shown)

    manager.context_table = table  # what DataTable does while the menu is up
    try:
        field.traceDialog()
    finally:
        manager.context_table = None

    assert shown == [clicked], "the dialog must show the row that was clicked"
    assert all(t == {"mytag"} for t in _tags(section, clicked))
    for n in others:
        assert all(t == set() for t in _tags(section, n)), (
            f"{n} was selected in the field, not in the list, and must be "
            "untouched"
        )


def test_edit_from_the_field_still_uses_the_field_selection(
    field_and_lists, monkeypatch
):
    """The other half: no list menu open means the field's selection wins."""
    field, manager, table, section = field_and_lists
    names = sorted(section.contours.keys())
    listed, in_field = names[0], names[1]

    _select_row(table, listed)
    section.selected_traces = [section.contours[in_field].getTraces()[0]]

    shown = []
    _fake_dialog(monkeypatch, {"mytag"}, shown)

    field.traceDialog()  # no context_table: invoked from the field

    assert shown == [in_field]
    assert all(t == {"mytag"} for t in _tags(section, in_field))
    assert all(t == set() for t in _tags(section, listed))


def test_active_table_prefers_the_menus_list(field_and_lists):
    field, manager, table, _ = field_and_lists

    assert manager.activeTable(TraceTableWidget) is None

    manager.context_table = table
    assert manager.activeTable(TraceTableWidget) is table
    assert manager.activeTable(ObjectTableWidget) is None, (
        "a trace list must not answer for an object list action"
    )

    manager.context_table = None
    assert manager.activeTable(TraceTableWidget) is None


def test_context_menu_records_and_clears_the_source_list(
    field_and_lists, monkeypatch
):
    """Set while the menu is up, cleared when it closes.

    Left set, the next action invoked from the field would use the list's
    selection instead. exec() is intercepted rather than run: a modal menu has
    nobody to dismiss it here, and what is under test is the bookkeeping around
    it.
    """
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QContextMenuEvent

    field, manager, table, section = field_and_lists
    _select_row(table, sorted(section.contours.keys())[0])

    while_open = []
    monkeypatch.setattr(
        table.context_menu, "exec", lambda pos: while_open.append(manager.context_table)
    )

    table.contextMenuEvent(
        QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(0, 0), QPoint(0, 0))
    )

    assert while_open == [table]
    assert manager.context_table is None
