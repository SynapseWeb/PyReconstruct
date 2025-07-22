"""Focus mode utilities."""

from PySide6.QtCore import Qt


def focus_edit_p(event) -> bool:
    """User requests editing in focus mode."""

    return event.modifiers() & Qt.ShiftModifier


def focus_comparison(selected_trace, focused_obj) -> bool:
    """Compare selected trace and obj that is focused_on."""

    return selected_trace.name == focused_obj  # return true if same obj

