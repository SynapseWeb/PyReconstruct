"""Editor for the autoseg-import color palette (Series > Options > View).

Autoseg import colors each imported trace from a curated whitelist, mapped
deterministically from the label id (see modules/backend/autoseg/palette.py).
The whitelist ships CVD-safe by default, but issue #96 asks that the user be
able to adjust it. This widget backs the ``autoseg_color_palette`` option: it
shows the palette as clickable color swatches, lets the user add/remove/recolor
them, and offers a one-click reset to the shipped color-blind-safe default.

It is added to the options dialog as a plain composite widget (the same pattern
as BackupDialog) because a dynamic, growable swatch grid does not fit the static
quick_dialog structure tuples. Like every options widget it exposes
``accept(close=False)`` (validate) and ``set()`` (commit), which
AllOptionsDialog calls on OK.

Note on determinism: import indexes the palette by ``hash(id) % len(palette)``,
so changing the *number* of colors reshuffles every id -> color assignment (not
just the colors that changed). That is inherent to length-based indexing and is
the same knob the color seed offers; it only affects future imports and the live
preview, never traces whose colors were already baked in at a past import.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QColorDialog,
    QApplication,
)
from PySide6.QtGui import QColor, QPixmap, QIcon, QPainter, QPalette
from PySide6.QtCore import QSize, Qt

from .helper import resizeLineEdit
from PyReconstruct.modules.backend.autoseg.palette import DEFAULT_AUTOSEG_PALETTE
from PyReconstruct.modules.gui.utils import notify

# A palette of one color makes every label id the same color and leaves the seed
# and "Shuffle colors" button with nothing to reshuffle (next_shuffle_seed no-ops
# below two colors). Two is the smallest palette for which the whole color
# machinery is still meaningful, so it is the enforced floor. Distinctness beyond
# that (avoiding near-duplicate or hard-to-see colors) is left to the user, per
# the maintainer's intent.
MIN_PALETTE_COLORS = 2

_SWATCH_SIZE = QSize(56, 28)


def normalize_palette(colors):
    """Return the value to persist for ``autoseg_color_palette``.

    Store ``[]`` (meaning "use the shipped default") when the edited list matches
    DEFAULT_AUTOSEG_PALETTE exactly, so a user who never customizes keeps
    tracking the curated default even if it changes in a future release.
    Otherwise store the explicit list of ``[R, G, B]`` integer lists -- the
    format ``palette_color`` and the preview already consume.

        Params:
            colors (list): list of (R, G, B) sequences
        Returns:
            (list): [] when equal to the default, else a list of [R, G, B] lists
    """
    as_tuples = [tuple(int(v) for v in c) for c in colors]
    if as_tuples == [tuple(c) for c in DEFAULT_AUTOSEG_PALETTE]:
        return []
    return [[int(v) for v in c] for c in as_tuples]


def _swatch_icon(rgb):
    """Build a filled color-swatch icon for a palette entry."""
    pixmap = QPixmap(_SWATCH_SIZE)
    pixmap.fill(QColor(int(rgb[0]), int(rgb[1]), int(rgb[2])))
    return QIcon(pixmap)


class AutosegColorsWidget(QWidget):

    def __init__(self, parent, series, use_defaults=False):
        """Create the autoseg import-colors editor.

            Params:
                parent (QWidget): the parent widget
                series (Series): the series whose options are edited
                use_defaults (bool): show the shipped defaults instead of the
                    stored values (Reset Defaults in the options dialog)
        """
        super().__init__(parent)
        self.series = series

        stored = series.getOption("autoseg_color_palette", use_defaults) or []
        # An empty option means "use the built-in default"; show that default so
        # the user edits a concrete starting palette rather than a blank list.
        source = stored if stored else DEFAULT_AUTOSEG_PALETTE
        self.colors = [[int(v) for v in c] for c in source]

        seed = series.getOption("autoseg_color_seed", use_defaults) or 0
        self._seed = int(seed)

        vlayout = QVBoxLayout()

        header = QLabel("Autoseg import colors", self)
        f = header.font()
        f.setBold(True)
        header.setFont(f)
        vlayout.addWidget(header)

        desc = QLabel(
            "Imported autoseg traces are colored from this palette, chosen\n"
            "deterministically per label id. The default palette is color-blind\n"
            "safe and readable on grayscale images.",
            self,
        )
        vlayout.addWidget(desc)

        # seed row
        seed_row = QHBoxLayout()
        seed_row.addWidget(QLabel("Color seed (same seed gives the same colors):", self))
        self.seed_edit = QLineEdit(str(self._seed), self)
        resizeLineEdit(self.seed_edit, "000000")
        seed_row.addWidget(self.seed_edit)
        seed_row.addStretch()
        vlayout.addLayout(seed_row)

        seed_hint = QLabel(
            'The "Shuffle colors" button on the zarr import overlay updates this '
            "seed;\nset a specific number to reproduce a past run.",
            self,
        )
        vlayout.addWidget(seed_hint)

        # swatch grid: click (or Edit) a swatch to recolor it
        self.list = QListWidget(self)
        self.list.setViewMode(QListWidget.IconMode)
        self.list.setIconSize(_SWATCH_SIZE)
        self.list.setResizeMode(QListWidget.Adjust)
        self.list.setMovement(QListWidget.Static)
        self.list.setSpacing(4)
        self.list.setSelectionMode(QListWidget.SingleSelection)
        self.list.setMaximumHeight(150)
        self.list.itemDoubleClicked.connect(self._edit_selected)
        self.list.currentRowChanged.connect(lambda _: self._update_buttons())
        vlayout.addWidget(self.list)

        # controls
        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add", self)
        add_btn.clicked.connect(self._add_color)
        self.edit_btn = QPushButton("Edit", self)
        self.edit_btn.clicked.connect(self._edit_selected)
        self.remove_btn = QPushButton("Remove", self)
        self.remove_btn.clicked.connect(self._remove_selected)
        reset_btn = QPushButton("Reset to default", self)
        reset_btn.clicked.connect(self._reset_default)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(self.edit_btn)
        btn_row.addWidget(self.remove_btn)
        btn_row.addStretch()
        btn_row.addWidget(reset_btn)
        vlayout.addLayout(btn_row)

        self.setLayout(vlayout)
        self._rebuild()

    # --- palette editing -----------------------------------------------------

    def _rebuild(self):
        """Repopulate the swatch grid from self.colors."""
        self.list.clear()
        for rgb in self.colors:
            item = QListWidgetItem(self.list)
            item.setIcon(_swatch_icon(rgb))
            item.setToolTip("rgb({}, {}, {})".format(*rgb))
        self._update_buttons()

    def _update_buttons(self):
        has_sel = self.list.currentRow() >= 0
        self.edit_btn.setEnabled(has_sel)
        # keep the palette at or above the floor
        self.remove_btn.setEnabled(has_sel and len(self.colors) > MIN_PALETTE_COLORS)

    def _pick_color(self, initial):
        """Open QColorDialog; return an [R, G, B] list or None if cancelled."""
        color = QColorDialog.getColor(QColor(*initial), self)
        if color.isValid():
            return [color.red(), color.green(), color.blue()]
        return None

    def _add_color(self):
        rgb = self._pick_color((255, 255, 255))
        if rgb is None:
            return
        self.colors.append(rgb)
        self._rebuild()
        self.list.setCurrentRow(len(self.colors) - 1)

    def _edit_selected(self, *args):
        row = self.list.currentRow()
        if row < 0:
            return
        rgb = self._pick_color(self.colors[row])
        if rgb is None:
            return
        self.colors[row] = rgb
        self._rebuild()
        self.list.setCurrentRow(row)

    def _remove_selected(self):
        row = self.list.currentRow()
        if row < 0:
            return
        if len(self.colors) <= MIN_PALETTE_COLORS:
            notify(f"The palette must keep at least {MIN_PALETTE_COLORS} colors.")
            return
        del self.colors[row]
        self._rebuild()

    def _reset_default(self):
        self.colors = [[int(v) for v in c] for c in DEFAULT_AUTOSEG_PALETTE]
        self._rebuild()

    # --- options-dialog protocol (accept -> set) -----------------------------

    def accept(self, close=True):
        """Validate the inputs. Called by AllOptionsDialog before set()."""
        text = self.seed_edit.text().strip()
        if not text:
            self._seed = 0
        else:
            try:
                self._seed = int(text)
            except ValueError:
                notify("Please enter a whole number for the color seed.")
                return False
        if len(self.colors) < MIN_PALETTE_COLORS:
            notify(f"The palette must keep at least {MIN_PALETTE_COLORS} colors.")
            return False
        return True

    def set(self):
        """Commit the seed and palette to the series options."""
        self.series.setOption("autoseg_color_seed", self._seed)
        self.series.setOption("autoseg_color_palette", normalize_palette(self.colors))

    # --- cosmetic border, matching the sibling OptionWidgets -----------------

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setPen(QApplication.palette().color(QPalette.WindowText))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
