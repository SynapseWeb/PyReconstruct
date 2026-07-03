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

    def __init__(self, mainwindow: QWidget, records: list, navigate=None,
                 delete=None):
        """Create the skipped-traces dialog.

            Params:
                mainwindow (QWidget): the parent window
                records (list): list of dicts, each with keys "name",
                    "section", "points", "location" ((x, y) or None), "reason"
                    and "trace" (the Trace object, used for deletion)
                navigate (callable): optional navigate(section_num, obj_name)
                    callback used to focus the field on a double-clicked row
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

        self.setWindowTitle("Traces skipped during smoothing")
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
        self.table.sortItems(1)  # default sort by section number
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

        # connected after the buttons exist so the slot can safely touch them
        self.table.itemSelectionChanged.connect(self._updateRowActionButtons)

        buttonbox = QDialogButtonBox(QDialogButtonBox.Close, self)
        buttonbox.rejected.connect(self.reject)
        buttonbox.addButton(self.goto_button, QDialogButtonBox.ActionRole)
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
        for row, r in enumerate(self.records):

            self._records_by_key[row] = r

            name_item = QTableWidgetItem(str(r["name"]))
            name_item.setData(Qt.UserRole, row)

            section_item = QTableWidgetItem()
            section_item.setData(Qt.DisplayRole, int(r["section"]))

            points_item = QTableWidgetItem()
            points_item.setData(Qt.DisplayRole, int(r["points"]))

            loc = r.get("location")
            loc_item = QTableWidgetItem(self._format_location(loc))

            reason_item = QTableWidgetItem(str(r["reason"]))

            for col, item in enumerate(
                (name_item, section_item, points_item, loc_item, reason_item)
            ):
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

    def _updateRowActionButtons(self):
        """Enable selection-dependent buttons only while a row is selected."""
        has_selection = self.table.selectionModel().hasSelection()
        self.goto_button.setEnabled(has_selection)
        if self.delete_selected_button is not None:
            self.delete_selected_button.setEnabled(has_selection)

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
        self.navigate(record["section"], record["name"])

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
