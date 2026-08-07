"""Tests for the autoseg import-colors editor (Series > Options > View).

The editor backs the ``autoseg_color_palette`` / ``autoseg_color_seed`` options.
These tests exercise its save path (accept -> set), reset-to-default, the
minimum-color floor, and that what it persists is exactly what the import
preview and shuffle consume -- without opening real Qt dialogs.
"""
import types

import pytest

from PyReconstruct.modules.backend.autoseg.palette import (
    DEFAULT_AUTOSEG_PALETTE,
    palette_color,
)
from PyReconstruct.modules.gui.dialog import autoseg_palette as ape
from PyReconstruct.modules.gui.dialog.autoseg_palette import (
    AutosegColorsWidget,
    MIN_PALETTE_COLORS,
    normalize_palette,
)


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(["test"])


class _SeriesStub:
    """Minimal series exposing just the option get/set the editor uses."""

    def __init__(self, palette=None, seed=0):
        self.store = {
            "autoseg_color_palette": [] if palette is None else palette,
            "autoseg_color_seed": seed,
        }
        self.writes = []

    def getOption(self, name, use_defaults=False):
        if use_defaults:
            return {"autoseg_color_palette": [], "autoseg_color_seed": 0}[name]
        return self.store[name]

    def setOption(self, name, value):
        self.store[name] = value
        self.writes.append((name, value))


def _widget(qapp, series, use_defaults=False):
    return AutosegColorsWidget(None, series, use_defaults)


# --- normalize_palette (pure) ----------------------------------------------


def test_normalize_default_returns_empty():
    # an unchanged default palette persists as [] so it keeps tracking the
    # shipped default instead of freezing today's colors
    assert normalize_palette([list(c) for c in DEFAULT_AUTOSEG_PALETTE]) == []
    assert normalize_palette([tuple(c) for c in DEFAULT_AUTOSEG_PALETTE]) == []


def test_normalize_custom_returns_list_of_lists():
    custom = [(1, 2, 3), (4, 5, 6)]
    assert normalize_palette(custom) == [[1, 2, 3], [4, 5, 6]]


def test_normalize_near_default_still_persists_explicitly():
    near = [list(c) for c in DEFAULT_AUTOSEG_PALETTE]
    near[0] = [0, 0, 0]  # one channel changed -> no longer the default
    out = normalize_palette(near)
    assert out != []
    assert out[0] == [0, 0, 0]


# --- construction: what the editor shows -----------------------------------


def test_empty_option_shows_default_palette(qapp):
    w = _widget(qapp, _SeriesStub(palette=[]))
    assert w.colors == [list(c) for c in DEFAULT_AUTOSEG_PALETTE]
    assert w.list.count() == len(DEFAULT_AUTOSEG_PALETTE)


def test_stored_custom_palette_is_shown(qapp):
    custom = [[10, 20, 30], [40, 50, 60], [70, 80, 90]]
    w = _widget(qapp, _SeriesStub(palette=custom, seed=7))
    assert w.colors == custom
    assert w.list.count() == 3
    assert w.seed_edit.text() == "7"


# --- save path (accept -> set) ---------------------------------------------


def test_set_round_trips_custom_palette_and_seed(qapp):
    series = _SeriesStub(palette=[], seed=0)
    w = _widget(qapp, series)
    w.colors = [[10, 20, 30], [40, 50, 60]]
    w.seed_edit.setText("12345")
    assert w.accept(close=False) is True
    w.set()
    assert series.store["autoseg_color_palette"] == [[10, 20, 30], [40, 50, 60]]
    assert series.store["autoseg_color_seed"] == 12345


def test_set_normalizes_unchanged_default_to_empty(qapp):
    # opening on the default palette and saving without edits keeps the option []
    series = _SeriesStub(palette=[], seed=3)
    w = _widget(qapp, series)
    assert w.accept(close=False) is True
    w.set()
    assert series.store["autoseg_color_palette"] == []
    assert series.store["autoseg_color_seed"] == 3


def test_saved_palette_is_consumable_by_preview_and_import(qapp):
    """What the editor writes must be exactly what palette_color reads -- the
    same option the live preview, shuffle and import all consume."""
    series = _SeriesStub(palette=[], seed=0)
    w = _widget(qapp, series)
    custom = [[10, 20, 30], [40, 50, 60], [200, 100, 0]]
    w.colors = [list(c) for c in custom]
    assert w.accept(close=False) is True
    w.set()
    saved = series.store["autoseg_color_palette"]
    seen = {palette_color(i, saved, series.store["autoseg_color_seed"])
            for i in range(1, 500)}
    assert seen  # non-empty
    assert all(list(c) in custom for c in seen)


# --- reset to default -------------------------------------------------------


def test_reset_to_default_restores_cvd_palette(qapp):
    series = _SeriesStub(palette=[[1, 1, 1], [2, 2, 2]], seed=0)
    w = _widget(qapp, series)
    assert w.colors == [[1, 1, 1], [2, 2, 2]]
    w._reset_default()
    assert w.colors == [list(c) for c in DEFAULT_AUTOSEG_PALETTE]
    w.set()
    # reset + save collapses back to the "use built-in default" sentinel
    assert series.store["autoseg_color_palette"] == []


# --- minimum-color floor ----------------------------------------------------


def test_remove_refuses_below_minimum(qapp, monkeypatch):
    notes = []
    monkeypatch.setattr(ape, "notify", lambda msg: notes.append(msg))
    w = _widget(qapp, _SeriesStub(palette=[[1, 2, 3], [4, 5, 6]]))
    w.list.setCurrentRow(0)
    w._remove_selected()
    assert len(w.colors) == MIN_PALETTE_COLORS  # unchanged
    assert notes  # user was told why


def test_remove_button_disabled_at_minimum(qapp):
    w = _widget(qapp, _SeriesStub(palette=[[1, 2, 3], [4, 5, 6]]))
    w.list.setCurrentRow(0)
    assert not w.remove_btn.isEnabled()


def test_remove_allowed_above_minimum(qapp):
    w = _widget(qapp, _SeriesStub(palette=[[1, 2, 3], [4, 5, 6], [7, 8, 9]]))
    w.list.setCurrentRow(1)
    assert w.remove_btn.isEnabled()
    w._remove_selected()
    assert w.colors == [[1, 2, 3], [7, 8, 9]]


def test_accept_rejects_below_minimum(qapp, monkeypatch):
    notes = []
    monkeypatch.setattr(ape, "notify", lambda msg: notes.append(msg))
    w = _widget(qapp, _SeriesStub(palette=[[1, 2, 3], [4, 5, 6]]))
    w.colors = [[1, 2, 3]]  # forced below floor
    assert w.accept(close=False) is False
    assert notes


# --- seed validation --------------------------------------------------------


def test_accept_treats_empty_seed_as_zero(qapp):
    w = _widget(qapp, _SeriesStub(palette=[], seed=9))
    w.seed_edit.setText("")
    assert w.accept(close=False) is True
    assert w._seed == 0


def test_accept_rejects_non_integer_seed(qapp, monkeypatch):
    notes = []
    monkeypatch.setattr(ape, "notify", lambda msg: notes.append(msg))
    w = _widget(qapp, _SeriesStub(palette=[], seed=0))
    w.seed_edit.setText("not-a-number")
    assert w.accept(close=False) is False
    assert notes


# --- add / edit via the color dialog (stubbed) ------------------------------


def _stub_color(monkeypatch, rgb):
    from PySide6.QtGui import QColor

    class _C(QColor):
        def isValid(self):
            return rgb is not None

    def fake_getColor(initial=None, parent=None, *a, **k):
        return _C(*rgb) if rgb is not None else _C()

    monkeypatch.setattr(ape.QColorDialog, "getColor", staticmethod(fake_getColor))


def test_add_color_appends_picked_color(qapp, monkeypatch):
    _stub_color(monkeypatch, (11, 22, 33))
    w = _widget(qapp, _SeriesStub(palette=[[1, 2, 3], [4, 5, 6]]))
    w._add_color()
    assert w.colors[-1] == [11, 22, 33]
    assert w.list.count() == 3


def test_edit_color_replaces_selected(qapp, monkeypatch):
    _stub_color(monkeypatch, (99, 88, 77))
    w = _widget(qapp, _SeriesStub(palette=[[1, 2, 3], [4, 5, 6]]))
    w.list.setCurrentRow(1)
    w._edit_selected()
    assert w.colors == [[1, 2, 3], [99, 88, 77]]


def test_cancelled_color_dialog_leaves_palette_unchanged(qapp, monkeypatch):
    _stub_color(monkeypatch, None)  # invalid -> user cancelled
    w = _widget(qapp, _SeriesStub(palette=[[1, 2, 3], [4, 5, 6]]))
    before = [list(c) for c in w.colors]
    w._add_color()
    assert w.colors == before


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
