"""Tests for editing part of an existing tag.

Tags are edited on three surfaces and each had its own reason a partial edit did
not survive:

* ``Trace ▸ Edit trace attributes...`` gives every tag its own line edit
  (``MultiInput``), but "-" popped the last row wherever the caret was, so
  correcting the first of several tags meant deleting the rows after it and
  typing them again. The rows also came straight out of a set, so a tag moved
  between openings.
* The trace palette's Tags column is one comma-separated cell. It was parsed
  with ``text.split(", ")``, which turns the "axon, " left behind by deleting
  "spine" into two tags, the second of them empty, and turns an untagged trace's
  empty cell into a single empty tag.
* The object list's ``Edit attributes...`` prefills the Tags field and then adds
  the set it gets back instead of assigning it, so an edited set can add a tag
  but never drop one.

None of this covers the click itself. What it covers is what the widgets and the
series do when driven through their real slots and methods.
"""

import pytest

from PyReconstruct.modules.datatypes import Trace
from PyReconstruct.modules.gui.dialog import trace as trace_dialog_module
from PyReconstruct.modules.gui.dialog.helper import MultiInput
from PyReconstruct.modules.gui.dialog.quick_dialog import QuickTabDialog
from PyReconstruct.modules.gui.dialog.trace import TraceDialog
from PyReconstruct.modules.gui.dialog.trace_palette import (
    TracePaletteDialog,
    parseTags,
)


def _trace(tags):
    """A minimal closed trace carrying the given tags."""
    t = Trace("axon", (255, 0, 0))
    t.points = [(0, 0), (1, 0), (1, 1)]
    t.tags = set(tags)
    return t


def _shown(widget):
    """Show and activate a widget so that setFocus() actually takes effect.

    Offscreen Qt hands out no focus at all until a window is active, so a test
    that drives focus has to ask for it explicitly.
    """
    from PySide6.QtWidgets import QApplication

    widget.show()
    widget.activateWindow()
    QApplication.instance().processEvents()
    return widget


# --- parseTags (pure) -------------------------------------------------------


@pytest.mark.parametrize("text, expected", [
    ("", []),                                   # an untagged trace's cell
    ("   ", []),
    ("axon", ["axon"]),
    ("axon, spine", ["axon", "spine"]),
    ("axon, ", ["axon"]),                       # "spine" deleted off the end
    (", spine", ["spine"]),                     # "axon" deleted off the front
    ("axon,,spine", ["axon", "spine"]),         # a tag deleted from the middle
    ("axon,spine", ["axon", "spine"]),          # separator typed without a space
    ("  axon ,  spine  ", ["axon", "spine"]),
])
def test_parse_tags(text, expected):
    assert parseTags(text) == expected


# --- the palette's Tags column ---------------------------------------------


@pytest.fixture
def palette_dialog(qapp, real_series, monkeypatch):
    """A real TracePaletteDialog whose exec() does not block.

    ``TracePaletteDialog.exec`` calls up to ``QuickDialog.exec``, which spins a
    modal loop that offscreen Qt has nobody to dismiss. Replacing the inherited
    exec with the responses the widgets already produced leaves the part under
    test, the palette write-back, running for real.
    """
    from PySide6.QtWidgets import QWidget

    monkeypatch.setattr(
        QuickTabDialog, "exec", lambda self: (self.responses, True)
    )
    parent = QWidget()
    dialog = TracePaletteDialog(parent, real_series)
    yield dialog
    dialog.deleteLater()
    parent.deleteLater()


def _tags_field(dialog, palette_name, row):
    """The Tags line edit for one palette row (7 fields per trace)."""
    return dialog.inputs[palette_name][row * 7 + 3].widget


def _all_palette_tags(series):
    return [
        t.tags
        for traces in series.palette_traces.values()
        for t in traces
    ]


def test_palette_untagged_trace_stays_untagged(palette_dialog, real_series):
    # every palette trace in the fixture series starts untagged, so accepting
    # the dialog untouched used to give every one of them a single empty tag
    assert all(tags == set() for tags in _all_palette_tags(real_series))

    palette_dialog.accept()
    palette_dialog.exec()

    assert all(tags == set() for tags in _all_palette_tags(real_series))


def test_palette_partial_delete_leaves_the_remaining_tag(
    palette_dialog, real_series
):
    name = next(iter(palette_dialog.inputs))
    _tags_field(palette_dialog, name, 0).setText("axon, spine")
    _tags_field(palette_dialog, name, 1).setText("axon, ")

    palette_dialog.accept()
    palette_dialog.exec()

    traces = real_series.palette_traces[name]
    assert traces[0].tags == {"axon", "spine"}
    assert traces[1].tags == {"axon"}
    assert not any("" in tags for tags in _all_palette_tags(real_series))


def test_palette_tags_cell_is_ordered():
    """The cell text is sorted, so a tag does not move between openings."""
    structure = TracePaletteDialog.getStructure(
        None, [_trace({"zeta", "alpha", "mu"})]
    )
    assert structure[1][3] == ("text", "alpha, mu, zeta")


# --- MultiInput, the trace attributes dialog's tag rows --------------------


def test_remove_takes_the_row_being_edited(qapp):
    from PySide6.QtWidgets import QVBoxLayout, QWidget

    host = QWidget()
    field = MultiInput(host, ["axon", "spine", "dendrite"])
    layout = QVBoxLayout()
    layout.addWidget(field)
    host.setLayout(layout)
    _shown(host)

    field.inputs[0].setFocus()
    qapp.processEvents()
    assert field.currentIndex() == 0

    field.remove()
    assert field.getEntries() == ["spine", "dendrite"]

    host.deleteLater()


def test_remove_falls_back_to_the_last_row(qapp):
    """With the caret nowhere in the field, "-" keeps its old meaning."""
    from PySide6.QtWidgets import QWidget

    host = QWidget()
    field = MultiInput(host, ["axon", "spine", "dendrite"])

    field.remove()
    assert field.getEntries() == ["axon", "spine"]

    host.deleteLater()


def test_removing_the_only_row_clears_it_instead(qapp):
    from PySide6.QtWidgets import QWidget

    host = QWidget()
    field = MultiInput(host, ["axon"])

    field.remove()
    assert field.getEntries() == []
    assert len(field.inputs) == 1  # still a line edit to type into

    field.remove()
    assert len(field.inputs) == 1

    host.deleteLater()


def test_remove_takes_the_focused_row_of_a_combo_field(qapp):
    """A combobox row is focused through its own internal line edit.

    ``MultiInput`` also backs the group and host fields, which are comboboxes, so
    the row lookup has to walk up from the focused widget rather than expect it
    to be the row itself.
    """
    from PySide6.QtWidgets import QVBoxLayout, QWidget

    host = QWidget()
    field = MultiInput(
        host, ["axon", "spine"], combo=True, combo_items=["axon", "spine"]
    )
    layout = QVBoxLayout()
    layout.addWidget(field)
    host.setLayout(layout)
    _shown(host)

    field.inputs[0].lineEdit().setFocus()
    qapp.processEvents()
    assert field.currentIndex() == 0

    field.remove()
    assert field.getEntries() == ["spine"]

    host.deleteLater()


def test_removing_the_only_combo_row_clears_it_instead(qapp):
    from PySide6.QtWidgets import QWidget

    host = QWidget()
    field = MultiInput(host, ["axon"], combo=True, combo_items=["axon"])

    field.remove()
    assert field.getEntries() == []
    assert len(field.inputs) == 1

    host.deleteLater()


def test_add_remove_buttons_do_not_steal_focus(qapp):
    """The premise of the fix: "-" can only know which row the caret is in if
    pressing it leaves the caret alone."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QPushButton, QWidget

    host = QWidget()
    field = MultiInput(host, ["axon"])
    buttons = field.findChildren(QPushButton)

    assert [b.text() for b in buttons] == ["-", "+"]
    assert all(b.focusPolicy() == Qt.NoFocus for b in buttons)

    host.deleteLater()


# --- the trace attributes dialog ------------------------------------------


def test_trace_dialog_lists_tags_in_a_stable_order(qapp, monkeypatch):
    """The dialog hands MultiInput an ordered sequence, not the raw set."""
    captured = []
    real_multi_input = trace_dialog_module.MultiInput

    def recording(parent, entries=None, *args, **kwargs):
        captured.append(entries)
        return real_multi_input(parent, entries, *args, **kwargs)

    monkeypatch.setattr(trace_dialog_module, "MultiInput", recording)

    dialog = TraceDialog(None, traces=[_trace({"zeta", "alpha", "mu"})])

    assert captured == [["alpha", "mu", "zeta"]]
    assert [w.text() for w in dialog.tags_input.inputs] == [
        "alpha", "mu", "zeta"
    ]

    dialog.deleteLater()


def test_trace_dialog_drops_a_tag_cleared_in_place(qapp):
    """Clearing a tag's text is how a single tag is deleted; the dialog must not
    return it as an empty tag."""
    dialog = TraceDialog(None, traces=[_trace({"axon", "spine"})])

    rows = {w.text(): w for w in dialog.tags_input.inputs}
    rows["axon"].setText("")
    assert dialog.tags_input.getEntries() == ["spine"]

    dialog.deleteLater()


# --- the object list's Edit attributes... ----------------------------------


def _all_sections(series):
    return list(series.sections.keys())


def _tags_on_disk(series, obj_name):
    """Every stored trace's tags for one object, read back per section."""
    out = []
    for snum, section in series.enumerateSections(show_progress=False):
        if obj_name in section.contours:
            for trace in section.contours[obj_name].getTraces():
                out.append(set(trace.tags))
    assert out, f"object {obj_name} had no traces to check"
    return out


def _set_tags(series, obj_name, tags):
    """Put a known set of tags on an object, using the replacement path."""
    series.editObjectAttributes(
        [obj_name],
        tags=set(tags),
        sections=_all_sections(series),
        add_tags=False,
        log_event=False,
    )


def _two_objects(series):
    names = sorted(series.data["objects"].keys())
    assert len(names) >= 2, "fixture has fewer than two objects"
    return names[0], names[1]


def test_object_edit_can_drop_one_tag(real_series):
    """The reported symptom at the layer that caused it: one tag of two goes."""
    obj, _ = _two_objects(real_series)
    _set_tags(real_series, obj, {"alpha", "beta"})
    assert all(t == {"alpha", "beta"} for t in _tags_on_disk(real_series, obj))

    real_series.editObjectAttributes(
        [obj],
        tags={"alpha"},
        sections=_all_sections(real_series),
        add_tags=False,
        log_event=False,
    )

    assert all(t == {"alpha"} for t in _tags_on_disk(real_series, obj)), (
        "an edited tag set must be able to drop a tag; when the set is added "
        "rather than assigned, the missing tag simply survives"
    )


def test_object_edit_can_clear_every_tag(real_series):
    """Emptying the field. An empty set has to mean "no tags"."""
    obj, _ = _two_objects(real_series)
    _set_tags(real_series, obj, {"alpha", "beta"})

    real_series.editObjectAttributes(
        [obj],
        tags=set(),
        sections=_all_sections(real_series),
        add_tags=False,
        log_event=False,
    )

    assert all(t == set() for t in _tags_on_disk(real_series, obj)), (
        "an empty set is the only way to say 'clear'; added rather than "
        "assigned it is an empty loop and nothing happens"
    )


def test_add_tags_defaults_to_the_existing_behavior(real_series):
    """A caller that does not pass ``add_tags`` still adds.

    ``Object.name``'s setter calls ``editObjectAttributes`` without it.
    """
    obj, _ = _two_objects(real_series)
    _set_tags(real_series, obj, {"alpha"})

    real_series.editObjectAttributes(
        [obj],
        tags={"beta"},
        sections=_all_sections(real_series),
        log_event=False,
    )

    assert all(t == {"alpha", "beta"} for t in _tags_on_disk(real_series, obj))


def test_additive_preserves_divergent_tags_across_objects(real_series):
    """The property the multi-object path depends on.

    Two objects with different tags, one shared tag added: neither loses what it
    had. This is what makes it safe to leave a multi-object edit additive.
    """
    obj_a, obj_b = _two_objects(real_series)
    _set_tags(real_series, obj_a, {"only_a"})
    _set_tags(real_series, obj_b, {"only_b"})

    real_series.editObjectAttributes(
        [obj_a, obj_b],
        tags={"shared"},
        sections=_all_sections(real_series),
        add_tags=True,
        log_event=False,
    )

    assert all(
        t == {"only_a", "shared"} for t in _tags_on_disk(real_series, obj_a)
    )
    assert all(
        t == {"only_b", "shared"} for t in _tags_on_disk(real_series, obj_b)
    )


def test_none_leaves_tags_alone_under_either_flag(real_series):
    """None means "no value chosen" for tags exactly as it does for name/color.

    The trace dialog reports no single tag set for a selection whose tags
    disagree, so this has to hold on the replacement path too.
    """
    obj, _ = _two_objects(real_series)
    _set_tags(real_series, obj, {"alpha"})

    real_series.editObjectAttributes(
        [obj],
        color=(9, 9, 9),
        tags=None,
        sections=_all_sections(real_series),
        add_tags=False,
        log_event=False,
    )
    assert all(t == {"alpha"} for t in _tags_on_disk(real_series, obj))

    real_series.editObjectAttributes(
        [obj],
        color=(8, 8, 8),
        tags=None,
        sections=_all_sections(real_series),
        add_tags=True,
        log_event=False,
    )
    assert all(t == {"alpha"} for t in _tags_on_disk(real_series, obj))


class _FakeTraceDialog:
    """Stands in for ``TraceDialog``, recording what it was shown.

    The real dialog needs a modal event loop and a QWidget parent. What matters
    here is the contract either side of it: which tags the object list hands the
    dialog, and what it does with the set the dialog hands back.
    """

    seen = None      # kwargs the object list constructed it with
    returns = None   # (tags, sections) to report as the user's input

    def __init__(self, parent, **kwargs):
        type(self).seen = kwargs

    def exec(self):
        tags, sections = type(self).returns
        trace = Trace(None, None)
        trace.color = None
        trace.tags = tags
        trace.fill_mode = (None, None)
        return (trace, sections), True


class _FakeTable:
    def hasFocus(self):
        # Not an ObjectTableWidget, so object_function falls back to the
        # selected traces in the field for the selection.
        return None

    def updateObjects(self, names):
        pass


class _FakeMainWindow:
    def saveAllData(self):
        pass

    def seriesModified(self, modified):
        pass


class _FakeSection:
    def __init__(self, obj_names):
        self.selected_traces = [Trace(n, (0, 0, 0)) for n in obj_names]


class _FieldStub:
    """The minimum ``FieldWidgetObject.editAttributes`` and its decorator touch."""

    def __init__(self, series, obj_names):
        self.series = series
        self.series_states = None
        self.section = _FakeSection(obj_names)
        self.table_manager = _FakeTable()
        self.mainwindow = _FakeMainWindow()

    def reload(self):
        pass


def _run_edit_attributes(monkeypatch, series, obj_names, returns):
    """Drive the real ``editAttributes`` with the dialog faked out."""
    from PyReconstruct.modules.gui.main import field_widget_3_object as mod

    _FakeTraceDialog.seen = None
    _FakeTraceDialog.returns = returns
    monkeypatch.setattr(mod, "TraceDialog", _FakeTraceDialog)

    stub = _FieldStub(series, obj_names)
    mod.FieldWidgetObject.editAttributes(stub)
    return _FakeTraceDialog.seen


def test_single_object_edit_can_clear_tags(real_series, monkeypatch):
    """The reported symptom, driven through the real command.

    One object selected, its tags shown, the user empties the field.
    """
    obj, _ = _two_objects(real_series)
    _set_tags(real_series, obj, {"alpha", "beta"})

    seen = _run_edit_attributes(
        monkeypatch,
        real_series,
        [obj],
        returns=(set(), _all_sections(real_series)),
    )

    assert seen["tags"] == {"alpha", "beta"}, (
        "the dialog has to be prefilled with the object's tags; that is why the "
        "set it returns can be read as a replacement"
    )
    assert all(t == set() for t in _tags_on_disk(real_series, obj)), (
        "emptying the Tags field on a single-object selection has to remove the "
        "tags"
    )


def test_single_object_edit_can_drop_one_tag(real_series, monkeypatch):
    """The everyday case: delete one row of the Tags field, keep the rest."""
    obj, _ = _two_objects(real_series)
    _set_tags(real_series, obj, {"alpha", "beta"})

    _run_edit_attributes(
        monkeypatch,
        real_series,
        [obj],
        returns=({"alpha"}, _all_sections(real_series)),
    )

    assert all(t == {"alpha"} for t in _tags_on_disk(real_series, obj))


def test_multi_object_edit_adds_without_erasing(real_series, monkeypatch):
    """The other half of the fix, and the reason it is not a blanket flip.

    Two objects with different tags. The dialog shows a blank Tags field because
    there is no single value to show, the user types one tag, and both objects
    keep what they had.
    """
    obj_a, obj_b = _two_objects(real_series)
    _set_tags(real_series, obj_a, {"only_a"})
    _set_tags(real_series, obj_b, {"only_b"})

    seen = _run_edit_attributes(
        monkeypatch,
        real_series,
        [obj_a, obj_b],
        returns=({"shared"}, _all_sections(real_series)),
    )

    assert seen["tags"] is None, (
        "a multi-object selection has no single tag set to display"
    )
    assert all(
        t == {"only_a", "shared"} for t in _tags_on_disk(real_series, obj_a)
    )
    assert all(
        t == {"only_b", "shared"} for t in _tags_on_disk(real_series, obj_b)
    )


def test_multi_object_edit_with_a_blank_field_changes_nothing(
    real_series, monkeypatch
):
    """Confirming a multi-object edit without touching the Tags field.

    The dialog reports either an empty set or nothing at all here, depending on
    how it resolves an untouched blank field. Neither may remove a tag, since
    the user was never shown one.
    """
    obj_a, obj_b = _two_objects(real_series)
    _set_tags(real_series, obj_a, {"only_a"})
    _set_tags(real_series, obj_b, {"only_b"})

    for blank in (set(), None):
        _run_edit_attributes(
            monkeypatch,
            real_series,
            [obj_a, obj_b],
            returns=(blank, _all_sections(real_series)),
        )
        assert all(
            t == {"only_a"} for t in _tags_on_disk(real_series, obj_a)
        ), blank
        assert all(
            t == {"only_b"} for t in _tags_on_disk(real_series, obj_b)
        ), blank
