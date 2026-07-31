import csv

from PySide6.QtWidgets import (
    QWidget,
    QDialog,
    QLabel,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QDialogButtonBox,
    QHeaderView,
    QAbstractItemView,
    QApplication,
    QFileDialog,
)
from PySide6.QtCore import Qt

from PyReconstruct.modules.gui.utils import notifyConfirm


class MalformedContoursDialog(QDialog):
    """Report traces skipped during object smoothing.

    Each row is one trace that could not be smoothed (typically too few
    points to interpolate a curve). The dialog shows enough context to track
    each one down: the object, the section, how many points the trace had,
    where it sits, and why it was skipped. Selecting a row and clicking
    "Go to trace" (or double-clicking the row) focuses the field on it, and
    the list can be copied or exported for triage.
    """

    COLUMNS = ["Object", "Section", "Point count", "Location (x, y)", "Reason"]
    WINDOW_TITLE = "Traces skipped during smoothing"
    # column the table is sorted by when it opens; subclasses that put a
    # different column at index 1 override it to keep the sort meaningful
    DEFAULT_SORT_COLUMN = 1

    def _columnSpecs(self):
        """Return (record-key, kind) pairs, one per column in COLUMNS.

        kind is one of "str", "int", "float", "loc" and controls how the cell
        value is stored (numeric kinds sort numerically). Subclasses override
        this together with COLUMNS to show different fields.
        """
        return [
            ("name", "str"),
            ("section", "int"),
            ("points", "int"),
            ("location", "loc"),
            ("reason", "str"),
        ]

    def __init__(self, mainwindow: QWidget, records: list, navigate=None,
                 delete=None):
        """Create the skipped-traces dialog.

            Params:
                mainwindow (QWidget): the parent window
                records (list): list of dicts, each with keys "name",
                    "section", "points", "location" ((x, y) or None), "reason"
                    and "trace" (the Trace object, used for deletion)
                navigate (callable): optional navigate(section_num, obj_name,
                    index) callback used to focus the field on a
                    double-clicked row
                delete (callable): optional delete(records) callback that
                    removes the given records from the series and returns the
                    records actually deleted; the Delete buttons are only shown
                    when it is provided
        """
        super().__init__(mainwindow)
        # destroy (don't merely hide) on close so repeated runs don't leave
        # hidden dialog children parented to the main window
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.mainwindow = mainwindow
        self.records = records
        self.navigate = navigate
        self.delete = delete

        self.setWindowTitle(self.WINDOW_TITLE)
        self.resize(660, 420)

        self.heading = QLabel(self._headingText(), self)
        self.heading.setWordWrap(True)

        self.table = QTableWidget(len(self.records), len(self.COLUMNS), self)
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(False)
        self._populate()
        self.table.setSortingEnabled(True)
        self.table.sortItems(self.DEFAULT_SORT_COLUMN)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.cellDoubleClicked.connect(self._onDoubleClick)

        self.goto_button = QPushButton("Go to trace", self)
        self.goto_button.setToolTip(
            "Focus the field on the selected trace"
        )
        self.goto_button.setEnabled(False)
        self.goto_button.clicked.connect(self.goToSelectedContour)

        copy_button = QPushButton("Copy table list", self)
        copy_button.setToolTip(
            "Copy the table of skipped traces above to the clipboard "
            "(tab-separated, including the column headers)"
        )
        copy_button.clicked.connect(self.copyToClipboard)

        save_button = QPushButton("Save table as CSV…", self)
        save_button.setToolTip(
            "Save the table of skipped traces above to a CSV file"
        )
        save_button.clicked.connect(self.saveCSV)

        # destructive actions, only when a delete callback is provided
        self.delete_selected_button = None
        self.delete_all_button = None
        if self.delete:
            self.delete_selected_button = QPushButton("Delete selected", self)
            self.delete_selected_button.setToolTip(
                "Delete the selected trace(s) from the series (can be undone)"
            )
            self.delete_selected_button.setEnabled(False)
            self.delete_selected_button.clicked.connect(
                self.deleteSelectedContours
            )

            self.delete_all_button = QPushButton("Delete all", self)
            self.delete_all_button.setToolTip(
                "Delete every trace listed above from the series "
                "(can be undone)"
            )
            self.delete_all_button.setEnabled(bool(self.records))
            self.delete_all_button.clicked.connect(self.deleteAllContours)

        # subclass hook, run before the selection signal is connected so
        # anything it adds is already there the first time the slot fires
        self.extra_buttons = []  # (button, needs_a_selected_row)
        self._addExtraButtons()

        # connected after the buttons exist so the slot can safely touch them
        self.table.itemSelectionChanged.connect(self._updateRowActionButtons)

        buttonbox = QDialogButtonBox(QDialogButtonBox.Close, self)
        buttonbox.rejected.connect(self.reject)
        buttonbox.addButton(self.goto_button, QDialogButtonBox.ActionRole)
        for button, _ in self.extra_buttons:
            buttonbox.addButton(button, QDialogButtonBox.ActionRole)
        buttonbox.addButton(copy_button, QDialogButtonBox.ActionRole)
        buttonbox.addButton(save_button, QDialogButtonBox.ActionRole)
        if self.delete:
            buttonbox.addButton(
                self.delete_selected_button, QDialogButtonBox.ActionRole
            )
            buttonbox.addButton(
                self.delete_all_button, QDialogButtonBox.ActionRole
            )

        layout = QVBoxLayout()
        layout.addWidget(self.heading)
        layout.addWidget(self.table)
        layout.addWidget(buttonbox)
        self.setLayout(layout)

    def _headingText(self):
        """Build the heading text from the current records."""
        num_traces = len(self.records)
        if not num_traces:
            return (
                "All listed traces have been deleted.\n\n"
                "You can close this window."
            )

        num_objs = len({r["name"] for r in self.records})
        trace_word = "trace" if num_traces == 1 else "traces"
        obj_word = "object" if num_objs == 1 else "objects"
        was_were = "was" if num_traces == 1 else "were"

        action = (
            "Select one or more rows, then use “Go to trace” to focus the "
            "field, or “Delete selected” / “Delete all” to remove them."
            if self.delete
            else "Select a row and click “Go to trace” to focus the field "
            "on that trace."
        )

        return (
            f"{num_traces} {trace_word} across {num_objs} {obj_word} "
            f"{was_were} skipped during smoothing.\n\n"
            "A trace is skipped when it cannot be smoothed — usually "
            "because it has too few points to interpolate a curve (fewer "
            "than 3). These traces were left unchanged; the Reason column "
            "explains why each one was skipped.\n\n"
            f"{action}"
        )

    def _populate(self):
        """Fill the table from the records."""
        # Qt may hand back a *copy* of a stored Python object, so identity
        # through item data is unreliable. Stash a stable int key per row and
        # resolve it back to the real record via this map; the key travels with
        # the row through re-sorting.
        self._records_by_key = {}
        specs = self._columnSpecs()
        for row, r in enumerate(self.records):

            self._records_by_key[row] = r

            for col, (key, kind) in enumerate(specs):
                if kind == "int":
                    item = QTableWidgetItem()
                    item.setData(Qt.DisplayRole, int(r[key]))
                elif kind == "float":
                    # store as a float so the column sorts numerically
                    item = QTableWidgetItem()
                    item.setData(Qt.DisplayRole, round(float(r[key]), 8))
                elif kind == "loc":
                    item = QTableWidgetItem(self._format_location(r.get(key)))
                else:  # "str"
                    item = QTableWidgetItem(str(r[key]))
                # a stable per-row key on the first column, resolved back to the
                # real record by _recordAtRow; it travels with the row on sort
                if col == 0:
                    item.setData(Qt.UserRole, row)
                item.setTextAlignment(Qt.AlignCenter)
                # show the full cell value on hover; columns are stretched to
                # fit the window, so wider values (e.g. the Reason) truncate
                item.setToolTip(item.text())
                self.table.setItem(row, col, item)

    @staticmethod
    def _format_location(loc):
        """Render a location tuple for display ('—' when there are no points)."""
        if not loc:
            return "—"
        return f"({loc[0]}, {loc[1]})"

    def _addExtraButtons(self):
        """Subclass hook: append (button, needs_selection) to extra_buttons.

        Nothing here by default. A button appended with needs_selection True is
        disabled while no row is selected, exactly like "Go to trace".
        """
        return

    def _updateRowActionButtons(self):
        """Enable selection-dependent buttons only while a row is selected."""
        has_selection = self.table.selectionModel().hasSelection()
        self.goto_button.setEnabled(has_selection)
        if self.delete_selected_button is not None:
            self.delete_selected_button.setEnabled(has_selection)
        for button, needs_selection in self.extra_buttons:
            if needs_selection:
                button.setEnabled(has_selection)

    def _recordAtRow(self, row):
        """Return the record for the given table row (or None)."""
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        return self._records_by_key.get(item.data(Qt.UserRole))

    def _navigateToRow(self, row):
        """Focus the field on the trace in the given table row."""
        if not self.navigate:
            return
        record = self._recordAtRow(row)
        if record is None:
            return
        self.navigate(record["section"], record["name"], record["index"])

    def goToSelectedContour(self):
        """Focus the field on the currently selected trace."""
        rows = self.table.selectionModel().selectedRows()
        if rows:
            self._navigateToRow(rows[0].row())

    def _onDoubleClick(self, row, _col):
        """Focus the field on the double-clicked trace."""
        self._navigateToRow(row)

    def _selectedRecords(self):
        """Return the records for the currently selected rows."""
        records = []
        for index in self.table.selectionModel().selectedRows():
            record = self._recordAtRow(index.row())
            if record is not None:
                records.append(record)
        return records

    def deleteSelectedContours(self):
        """Delete the traces for the currently selected rows."""
        self._deleteRecords(self._selectedRecords())

    def deleteAllContours(self):
        """Delete every trace listed in the dialog."""
        self._deleteRecords(list(self.records))

    def _deleteRecords(self, records):
        """Confirm, delete the given records, and prune the rows that went."""
        if not self.delete or not records:
            return
        count = len(records)
        noun = "trace" if count == 1 else "traces"
        if not notifyConfirm(
            f"Delete {count} {noun} from the series?\n\n"
            "This can be undone (Ctrl+Z).",
            yn=True,
        ):
            return
        deleted = self.delete(records)
        self._pruneRecords(deleted or [])

    def _pruneRecords(self, deleted):
        """Remove the rows/records that were actually deleted."""
        if not deleted:
            return
        deleted_ids = {id(r) for r in deleted}
        # remove bottom-up so earlier row indices stay valid
        for row in range(self.table.rowCount() - 1, -1, -1):
            item = self.table.item(row, 0)
            if item is None:
                continue
            key = item.data(Qt.UserRole)
            record = self._records_by_key.get(key)
            if record is not None and id(record) in deleted_ids:
                self.table.removeRow(row)
                del self._records_by_key[key]
        self.records = list(self._records_by_key.values())
        self.heading.setText(self._headingText())
        if self.delete_all_button is not None:
            self.delete_all_button.setEnabled(bool(self.records))
        self._updateRowActionButtons()

    def _rows_for_export(self):
        """Return the report as a list of rows (header first).

        Reads the table in its current visual order so the export matches what
        the user sees, including any column sort they have applied.
        """
        rows = [list(self.COLUMNS)]
        for row in range(self.table.rowCount()):
            cells = []
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                cells.append("" if item is None else item.text())
            rows.append(cells)
        return rows

    def copyToClipboard(self):
        """Copy the report to the clipboard as tab-separated text."""
        rows = self._rows_for_export()
        text = "\n".join("\t".join(cell for cell in row) for row in rows)
        QApplication.clipboard().setText(text)

    def saveCSV(self):
        """Save the report to a CSV file the user chooses."""
        fp, _ = QFileDialog.getSaveFileName(
            self,
            "Save skipped traces",
            "skipped_traces.csv",
            "CSV files (*.csv);;All files (*)",
        )
        if not fp:
            return
        with open(fp, "w", newline="") as f:
            csv.writer(f).writerows(self._rows_for_export())


class PixelDustDialog(MalformedContoursDialog):
    """Review tiny "pixel-dust" traces before removing them.

    A data clean-up review list: every row is a small closed trace at or below
    the area threshold the user chose. The user inspects the candidates (and can
    "Go to trace" to confirm), then deselects any legitimate small trace before
    "Delete selected" / "Delete all". Reuses all of the selection, navigation,
    deletion (undoable), and export behavior of MalformedContoursDialog; only
    the columns (an Area column) and the explanatory heading differ.
    """

    COLUMNS = ["Object", "Section", "Area (um^2)", "Point count",
               "Location (x, y)", "Reason"]
    WINDOW_TITLE = "Remove pixel-dust traces"

    def _columnSpecs(self):
        return [
            ("name", "str"),
            ("section", "int"),
            ("area", "float"),
            ("points", "int"),
            ("location", "loc"),
            ("reason", "str"),
        ]

    def _headingText(self):
        """Explain the pixel-dust review and how to act on it."""
        num_traces = len(self.records)
        if not num_traces:
            return (
                "All listed traces have been deleted.\n\n"
                "You can close this window."
            )

        num_objs = len({r["name"] for r in self.records})
        trace_word = "trace" if num_traces == 1 else "traces"
        obj_word = "object" if num_objs == 1 else "objects"

        return (
            f"{num_traces} small (pixel-dust) {trace_word} across "
            f"{num_objs} {obj_word} at or below the area threshold.\n\n"
            "These are typically stray specks left by segmentation. Review the "
            "candidates below, select a row and click “Go to trace” to inspect "
            "one, and deselect any legitimate trace you want to keep. Then use "
            "“Delete selected” or “Delete all” to remove them (can be undone)."
            "\n\nNothing is removed until you choose to delete."
        )


class DifferentlyNamedDuplicatesDialog(MalformedContoursDialog):
    """Report traces that duplicate each other under two different names.

    Each row is a pair: one shape traced twice, once under each of two object
    names, which is what happens when two people trace the same structure. Both
    names are shown, along with the measured overlap and each trace's area, so
    the pair can be judged rather than guessed at. "Go to trace" frames the first
    of the two and "Go to other trace" frames the second, so the same field view
    can be compared against both.

    This list reports and does not delete. Two traces sharing one name are
    unambiguous and Series.deleteDuplicateTraces collapses them, but when the
    names differ, which name is the right one is a question about the data: the
    two objects may have different hosts, groups, or curation status, and the
    answer can be to rename or to merge rather than to delete. So the pairs are
    reported, and what to do about each one is left to the person reading them.
    """

    COLUMNS = ["Object", "Duplicate of", "Section", "Overlap", "Area (um^2)",
               "Other area (um^2)", "Point count", "Location (x, y)", "Reason"]
    WINDOW_TITLE = "Duplicates named differently"
    DEFAULT_SORT_COLUMN = 2  # "Section"

    def __init__(self, mainwindow: QWidget, records: list, navigate=None):
        """Create the pairs list. Takes no delete callback, on purpose.

        Report-only is a property of this dialog rather than a choice each caller
        makes, so there is no ``delete`` parameter to pass one through: adding
        deletion here has to be a deliberate change to this class.

            Params:
                mainwindow (QWidget): the parent window
                records (list): pair records from
                    Series.findDifferentlyNamedDuplicates
                navigate (callable): optional navigate(section_num, obj_name,
                    index) callback, used by both "Go to" buttons
        """
        super().__init__(mainwindow, records, navigate=navigate, delete=None)

    def _columnSpecs(self):
        return [
            ("name", "str"),
            ("other_name", "str"),
            ("section", "int"),
            ("ratio", "float"),
            ("area", "float"),
            ("other_area", "float"),
            ("points", "int"),
            ("location", "loc"),
            ("reason", "str"),
        ]

    def _addExtraButtons(self):
        """Add "Go to other trace", which frames the pair's second trace."""
        self.goto_other_button = QPushButton("Go to other trace", self)
        self.goto_other_button.setToolTip(
            "Focus the field on the other trace of the selected pair"
        )
        self.goto_other_button.setEnabled(False)
        self.goto_other_button.clicked.connect(self.goToSelectedOtherContour)
        self.extra_buttons.append((self.goto_other_button, True))

    def goToSelectedOtherContour(self):
        """Focus the field on the second trace of the selected pair."""
        if not self.navigate:
            return
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        record = self._recordAtRow(rows[0].row())
        if record is None:
            return
        self.navigate(
            record["section"], record["other_name"], record["other_index"]
        )

    def _headingText(self):
        """Explain what a row is and why nothing is deleted from here."""
        num_pairs = len(self.records)
        if not num_pairs:
            return (
                "No pairs left to report.\n\n"
                "You can close this window."
            )

        names = {r["name"] for r in self.records} | {
            r["other_name"] for r in self.records
        }
        pair_word = "pair" if num_pairs == 1 else "pairs"

        return (
            f"{num_pairs} {pair_word} of overlapping traces across "
            f"{len(names)} objects, each pair traced under two different "
            "names.\n\n"
            "Two traces of one object that sit on top of each other are "
            "duplicates without any doubt, and "
            "“Remove duplicate traces...” collapses those. When the names "
            "differ the geometry says the same thing, but which name is the "
            "right one does not follow from it: the two objects can carry "
            "different hosts, groups or curation, and the answer may be to "
            "rename or to merge rather than to delete one.\n\n"
            "So this list reports. Select a row and use “Go to trace” and "
            "“Go to other trace” to see both traces of a pair in the field, "
            "then decide. The Overlap column is the measured overlap ratio "
            "(1 means the two traces have the same points), and both areas "
            "are physical (um^2) on that trace's own section.\n\n"
            "Nothing in the series has been changed."
        )
