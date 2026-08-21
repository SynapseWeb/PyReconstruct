"""Launch PyReconstruct with a running commentary on where tags go.

Scratch debugging aid, not part of the app and not committed: it wraps the
handful of methods a tag passes through and prints what each one saw, so a
session that loses a tag says where. Nothing else about the run changes.

    cd <checkout> && python dev/scripts/tagdebug.py [series.jser]

Then, with the trace list open: right-click the palette, set a tag, draw a
trace, and edit a trace's tags from the list. Every [tag] line below is one hop.
Send the output along with what you saw on screen.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def log(*args):
    print("[tag]", *args, file=sys.stderr, flush=True)


def _tags(x):
    """Readable tags for a trace, or a list/set of them."""
    if x is None:
        return "None"
    if isinstance(x, (set, frozenset)):
        return "{" + ", ".join(sorted(x)) + "}" if x else "{}"
    if isinstance(x, (list, tuple)):
        return "[" + ", ".join(_tags(i) for i in x) + "]"
    return f"{getattr(x, 'name', '?')}:{_tags(getattr(x, 'tags', None))}"


def wrap(cls, name, before=None, after=None):
    """Wrap cls.name, calling before(args)/after(result, args) around it."""
    original = getattr(cls, name)

    def wrapped(self, *args, **kwargs):
        if before:
            try:
                log(f"{cls.__name__}.{name} <-", before(self, args, kwargs))
            except Exception as e:
                log(f"{cls.__name__}.{name} <- (log failed: {e})")
        result = original(self, *args, **kwargs)
        if after:
            try:
                log(f"{cls.__name__}.{name} ->", after(self, result, args, kwargs))
            except Exception as e:
                log(f"{cls.__name__}.{name} -> (log failed: {e})")
        return result

    setattr(cls, name, wrapped)


def install():
    from PyReconstruct.modules.datatypes.section import Section
    from PyReconstruct.modules.datatypes.series_data import SeriesData
    from PyReconstruct.modules.gui.main.field_widget_1_base import FieldWidgetBase
    from PyReconstruct.modules.gui.main.field_widget_2_trace import FieldWidgetTrace
    from PyReconstruct.modules.gui.main.field_widget_7_view import FieldWidgetView
    from PyReconstruct.modules.gui.palette.buttons import PaletteButton
    from PyReconstruct.modules.gui.palette.mouse_palette import MousePalette
    from PyReconstruct.modules.gui.table.trace import TraceTableWidget

    # 1. the palette dialog writes the palette trace
    wrap(
        PaletteButton, "openDialog",
        after=lambda self, r, a, k: f"palette button trace is now {_tags(self.trace)}",
    )

    # 2. the palette decides whether the pencil follows
    wrap(
        MousePalette, "paletteButtonChanged",
        before=lambda self, a, k: (
            f"button {self.palette_buttons.index(a[0]) if a[0] in self.palette_buttons else '?'}"
            f", palette_index={self.series.palette_index}"
            f", checked={[b.isChecked() for b in self.palette_buttons]}"
        ),
    )

    # 3. the pencil
    wrap(
        FieldWidgetView, "setTracingTrace",
        after=lambda self, r, a, k: f"pencil is now {_tags(self.tracing_trace)}",
    )

    # 4. a trace is drawn
    wrap(
        FieldWidgetTrace, "newTrace",
        before=lambda self, a, k: f"base trace {_tags(a[1])}",
        after=lambda self, r, a, k: (
            f"created={r}, section now holds "
            f"{_tags([t for t in self.section.tracesAsList() if t.name == a[1].name])}"
        ),
    )

    # 5. an attribute edit, and which traces it was handed
    wrap(
        Section, "editTraceAttributes",
        before=lambda self, a, k: (
            f"traces={_tags(list(a[0]))} tags={_tags(a[3] if len(a) > 3 else k.get('tags'))}"
            f" add_tags={k.get('add_tags', False)}"
        ),
    )

    # 6. which selection the shared field methods chose
    from PyReconstruct.modules.backend.table.manager import TableManager
    wrap(
        TableManager, "activeTable",
        after=lambda self, r, a, k: (
            f"asked for {a[0].__name__}, answered "
            f"{type(r).__name__ if r is not None else 'the field'}"
            f" (context_table={type(self.context_table).__name__}, "
            f"focus={type(self.hasFocus()).__name__})"
        ),
    )

    # 7. the series data the lists read from
    wrap(
        SeriesData, "updateSection",
        before=lambda self, a, k: f"modified names={sorted(a[0].getAllModifiedNames())}",
    )

    # 8. the rows the trace list writes
    def rows(self, r, a, k):
        headers = [
            self.table.horizontalHeaderItem(c).text()
            for c in range(self.table.columnCount())
        ]
        if "Tags" not in headers:
            return "!! the trace list has no Tags column (List > Set columns...)"
        col = headers.index("Tags")
        out = []
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0)
            tags = self.table.item(row, col)
            if name and name.text() in (a[0] or []):
                out.append(f"{name.text()}:{tags.text() if tags else ''!r}")
        return f"updated {sorted(a[0] or [])} -> rows {out}"

    wrap(TraceTableWidget, "updateData", after=rows)

    # 9. and what the section actually saved
    wrap(
        FieldWidgetBase, "saveState",
        before=lambda self, a, k: (
            f"modified names={sorted(self.section.getAllModifiedNames())}"
        ),
    )

    log("instrumentation installed")


if __name__ == "__main__":
    install()

    from PyReconstruct.run import runPyReconstruct

    runPyReconstruct(sys.argv[1] if len(sys.argv) > 1 else None)
