"""Editing the selected palette trace has to reach the pencil.

Right-clicking a palette button edits that button's trace, and the pencil is
brought up to date afterwards -- but only for the button that is selected, and
the code asked the buttons which one that was. A button's checked state is how
the selection is drawn, not what it is: ``series.palette_index`` is what the
label and the tracing trace are set from when a series opens, and the two could
disagree, because a palette drag ends in a click on the dragged button and that
click used to toggle its checked state without touching the index.

The consequence, from the field: tags added or removed on the selected palette
trace never reached the pencil, so the next trace drawn carried the attributes
the button had before the edit.
"""

import types

import pytest

from PyReconstruct.modules.datatypes import Trace
from PyReconstruct.modules.gui.palette.mouse_palette import MousePalette


class _Button:
    """Stands in for a PaletteButton: a trace and a checked state."""

    def __init__(self, name, checked=False):
        self.trace = Trace(name, (255, 0, 0))
        self.trace.points = [(0, 0), (1, 0), (1, 1)]
        self._checked = checked

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        self._checked = checked


def _palette(selected_index, checked_index):
    """A MousePalette with only what these two methods touch.

    selected_index is what the series says is selected; checked_index is which
    button is drawn as selected, so the two can be made to disagree.
    """
    palette = MousePalette.__new__(MousePalette)
    palette.series = types.SimpleNamespace(
        palette_index=["palette1", selected_index],
        getOption=lambda name, *a: False,
    )
    palette.palette_buttons = [
        _Button(f"trace{i}", checked=(i == checked_index)) for i in range(3)
    ]
    palette.is_dragging = False

    traced = []
    palette.mainwindow = types.SimpleNamespace(
        changeTracingTrace=lambda trace: traced.append(trace)
    )
    palette.setPaletteButtonTip = lambda b, pos: None
    palette.updateLabel = lambda: None
    return palette, traced


def test_editing_the_selected_button_updates_the_pencil():
    palette, traced = _palette(selected_index=1, checked_index=1)

    MousePalette.paletteButtonChanged(palette, palette.palette_buttons[1])

    assert [t.name for t in traced] == ["trace1"]


def test_editing_the_selected_button_updates_the_pencil_when_unhighlighted():
    """The reported failure: the selection is real, its highlight is not."""
    palette, traced = _palette(selected_index=1, checked_index=None)

    MousePalette.paletteButtonChanged(palette, palette.palette_buttons[1])

    assert [t.name for t in traced] == ["trace1"], (
        "palette_index names the selected button; a lost highlight cannot mean "
        "the edit stops short of the pencil"
    )


def test_editing_another_button_leaves_the_pencil_alone():
    palette, traced = _palette(selected_index=1, checked_index=1)

    MousePalette.paletteButtonChanged(palette, palette.palette_buttons[2])

    assert traced == [], "editing an unselected button must not switch traces"


def test_a_stray_highlight_does_not_hijack_the_pencil():
    palette, traced = _palette(selected_index=1, checked_index=2)

    MousePalette.paletteButtonChanged(palette, palette.palette_buttons[2])

    assert traced == []


def test_a_drag_leaves_the_selection_and_its_highlight_alone():
    """The drift's source: the click that ends a palette drag."""
    palette, traced = _palette(selected_index=1, checked_index=1)
    palette.is_dragging = True

    MousePalette.activatePaletteButton(palette, 2)  # the button dragged

    assert palette.series.palette_index[1] == 1
    assert [b.isChecked() for b in palette.palette_buttons] == [
        False, True, False
    ], "the selected button stays highlighted, and only it"
    assert traced == []


def test_a_click_selects_the_button():
    """Guardrail: the ordinary click path is unchanged."""
    palette, traced = _palette(selected_index=1, checked_index=1)

    MousePalette.activatePaletteButton(palette, 2)

    assert palette.series.palette_index[1] == 2
    assert [b.isChecked() for b in palette.palette_buttons] == [
        False, False, True
    ]
    assert [t.name for t in traced] == ["trace2"]
