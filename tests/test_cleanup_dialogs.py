"""The two clean-up review lists, driven as real widgets.

``MalformedContoursDialog`` grew a column spec, a default sort column and a
subclass button hook so the two clean-up lists could reuse its selection,
navigation, deletion and export behavior instead of restating it.

The property worth pinning is that ``DifferentlyNamedDuplicatesDialog`` reports
and does not delete, and that this is a property of the class rather than a
keyword each call site chooses: it takes no ``delete`` parameter at all, so
adding deletion has to be a deliberate change here.
"""

import inspect

import pytest

from PyReconstruct.modules.gui.dialog import (
    MalformedContoursDialog,
    PixelDustDialog,
    DifferentlyNamedDuplicatesDialog,
)


@pytest.fixture
def parent(qapp):
    from PySide6.QtWidgets import QWidget

    widget = QWidget()
    yield widget
    widget.deleteLater()


def _dust_record(name="dust", snum=3, area=0.004):
    return {
        "name": name,
        "section": snum,
        "index": 0,
        "points": 4,
        "location": (20.0, 20.0),
        "reason": f"Area {area} um^2",
        "area": area,
        "match": {"color": (255, 0, 0), "points": [(20.0, 20.0)]},
    }


def _pair_record(name="dendrite", other="d01", snum=3, ratio=0.98):
    return {
        "name": name,
        "section": snum,
        "index": 0,
        "points": 4,
        "location": (20.0, 20.0),
        "reason": f"Overlap {ratio} with '{other}'",
        "area": 1.5,
        "ratio": ratio,
        "other_name": other,
        "other_index": 1,
        "other_points": 4,
        "other_location": (20.1, 20.1),
        "other_area": 1.4,
        "other_match": {"color": (0, 255, 0), "points": [(20.1, 20.1)]},
        "match": {"color": (255, 0, 0), "points": [(20.0, 20.0)]},
    }


# --------------------------------------------------------------------------
# the pairs list reports and does not delete
# --------------------------------------------------------------------------

def test_report_only_is_a_property_of_the_class():
    """No delete parameter, so no call site can turn deletion on."""
    params = inspect.signature(DifferentlyNamedDuplicatesDialog.__init__).parameters

    assert "delete" not in params


def test_the_pairs_list_shows_no_delete_buttons(parent):
    dialog = DifferentlyNamedDuplicatesDialog(parent, [_pair_record()])

    assert dialog.delete is None
    assert dialog.delete_selected_button is None
    assert dialog.delete_all_button is None


def test_the_heading_says_nothing_was_changed(parent):
    dialog = DifferentlyNamedDuplicatesDialog(parent, [_pair_record()])

    assert "Nothing in the series has been changed" in dialog.heading.text()


def test_the_row_names_both_objects_and_shows_the_overlap(parent):
    dialog = DifferentlyNamedDuplicatesDialog(
        parent, [_pair_record(name="dendrite", other="d01", ratio=0.98)]
    )

    assert dialog.COLUMNS[:4] == ["Object", "Duplicate of", "Section", "Overlap"]
    texts = [
        dialog.table.item(0, col).text()
        for col in range(dialog.table.columnCount())
    ]
    assert "dendrite" in texts
    assert "d01" in texts
    assert any("0.98" in t for t in texts)


def test_both_traces_of_a_pair_are_reachable(parent):
    """Two navigation buttons, each framing its own side of the pair."""
    visited = []
    dialog = DifferentlyNamedDuplicatesDialog(
        parent,
        [_pair_record(name="dendrite", other="d01")],
        navigate=lambda snum, name, index: visited.append((snum, name, index)),
    )
    dialog.table.selectRow(0)

    dialog.goToSelectedContour()
    dialog.goToSelectedOtherContour()

    assert visited == [(3, "dendrite", 0), (3, "d01", 1)]


def test_the_go_to_buttons_are_off_until_a_row_is_selected(parent):
    dialog = DifferentlyNamedDuplicatesDialog(
        parent, [_pair_record()], navigate=lambda *a: None
    )

    assert dialog.goto_button.isEnabled() is False
    assert dialog.goto_other_button.isEnabled() is False

    dialog.table.selectRow(0)

    assert dialog.goto_button.isEnabled() is True
    assert dialog.goto_other_button.isEnabled() is True


def test_the_pairs_table_opens_sorted_by_section(parent):
    """Section moved to column 2 here, so the inherited sort index would be wrong.

    The names run opposite to the section numbers on purpose: sorting by either
    of the two name columns would put the rows in the reverse order, so a
    hardcoded sort column cannot pass this by coincidence.
    """
    records = [
        _pair_record(name="a", other="a2", snum=9),
        _pair_record(name="c", other="c2", snum=1),
        _pair_record(name="b", other="b2", snum=5),
    ]
    dialog = DifferentlyNamedDuplicatesDialog(parent, records)

    section_col = dialog.COLUMNS.index("Section")
    assert section_col == dialog.DEFAULT_SORT_COLUMN
    shown = [
        int(dialog.table.item(row, section_col).text())
        for row in range(dialog.table.rowCount())
    ]
    assert shown == [1, 5, 9]


# --------------------------------------------------------------------------
# the pixel-dust list still deletes, and the base class is unchanged
# --------------------------------------------------------------------------

def test_the_pixel_dust_list_deletes_what_was_reviewed(parent, monkeypatch):
    # the confirmation prompt falls back to reading stdin without a GUI
    monkeypatch.setattr(
        "PyReconstruct.modules.gui.dialog.malformed_contours.notifyConfirm",
        lambda *args, **kwargs: True,
    )
    handed = []
    records = [_dust_record("dust"), _dust_record("other")]
    dialog = PixelDustDialog(
        parent, records, delete=lambda recs: (handed.extend(recs), recs)[1]
    )

    assert dialog.delete_all_button is not None
    dialog._deleteRecords([records[0]])

    assert [r["name"] for r in handed] == ["dust"]


def test_a_declined_confirmation_deletes_nothing(parent, monkeypatch):
    monkeypatch.setattr(
        "PyReconstruct.modules.gui.dialog.malformed_contours.notifyConfirm",
        lambda *args, **kwargs: False,
    )
    handed = []
    records = [_dust_record("dust")]
    dialog = PixelDustDialog(
        parent, records, delete=lambda recs: (handed.extend(recs), recs)[1]
    )

    dialog._deleteRecords(records)

    assert handed == []


def test_the_pixel_dust_list_shows_an_area_column(parent):
    dialog = PixelDustDialog(parent, [_dust_record(area=0.004)])

    assert "Area (um^2)" in dialog.COLUMNS
    col = dialog.COLUMNS.index("Area (um^2)")
    assert "0.004" in dialog.table.item(0, col).text()


def test_neither_list_grows_a_button_the_base_class_did_not_ask_for(parent):
    """The hook is opt-in, so the smoothing report is unaffected by it."""
    base = MalformedContoursDialog(parent, [_dust_record()])
    dust = PixelDustDialog(parent, [_dust_record()])

    assert base.extra_buttons == []
    assert dust.extra_buttons == []


def test_the_base_class_still_sorts_by_section_and_titles_itself(parent):
    base = MalformedContoursDialog(parent, [_dust_record()])

    assert base.DEFAULT_SORT_COLUMN == 1
    assert base.COLUMNS[1] == "Section"
    assert base.windowTitle() == "Traces skipped during smoothing"
