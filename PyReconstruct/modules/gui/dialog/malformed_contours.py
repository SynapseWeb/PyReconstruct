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


class MalformedContoursDialog(QDialog):
    """Report contours skipped during object smoothing for being malformed.

    Each row is one trace that could not be smoothed (too few points to
    interpolate -- often "pixel dust" left over from preprocessing the
    .jser). The dialog shows enough context to track each one down: the
    object, the section, how many points the trace had, where it sits, and
    why it was skipped. Double-clicking a row focuses the field on it, and
    the list can be copied or exported for triage.
    """

    COLUMNS = ["Object", "Section", "Point count", "Location (x, y)", "Reason"]

    def __init__(self, mainwindow: QWidget, records: list, navigate=None):
        """Create the malformed-contours dialog.

            Params:
                mainwindow (QWidget): the parent window
                records (list): list of dicts, each with keys "name",
                    "section", "points", "location" ((x, y) or None) and
                    "reason"
                navigate (callable): optional navigate(section_num, obj_name)
                    callback used to focus the field on a double-clicked row
        """
        super().__init__(mainwindow)
        # destroy (don't merely hide) on close so repeated runs don't leave
        # hidden dialog children parented to the main window
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.mainwindow = mainwindow
        self.records = records
        self.navigate = navigate

        self.setWindowTitle("Malformed contours skipped while smoothing")
        self.resize(660, 420)

        num_traces = len(records)
        num_objs = len({r["name"] for r in records})
        trace_word = "trace" if num_traces == 1 else "traces"
        obj_word = "object" if num_objs == 1 else "objects"
        was_were = "was" if num_traces == 1 else "were"
        they = "it" if num_traces == 1 else "they"
        heading = QLabel(
            f"{num_traces} contour {trace_word} across {num_objs} {obj_word} "
            f"{was_were} skipped while smoothing because {they} could not be "
            "smoothed. These are often \"pixel dust\" artifacts introduced "
            "when the .jser was preprocessed; see the Reason column for each "
            "trace. The malformed traces were left untouched.\n\n"
            "Double-click a row to focus the field on it.",
            self,
        )
        heading.setWordWrap(True)

        self.table = QTableWidget(num_traces, len(self.COLUMNS), self)
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(False)
        self._populate()
        self.table.setSortingEnabled(True)
        self.table.sortItems(1)  # default sort by section number
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.cellDoubleClicked.connect(self._onDoubleClick)

        copy_button = QPushButton("Copy to clipboard", self)
        copy_button.clicked.connect(self.copyToClipboard)

        save_button = QPushButton("Save as CSV…", self)
        save_button.clicked.connect(self.saveCSV)

        buttonbox = QDialogButtonBox(QDialogButtonBox.Close, self)
        buttonbox.rejected.connect(self.reject)
        buttonbox.addButton(copy_button, QDialogButtonBox.ActionRole)
        buttonbox.addButton(save_button, QDialogButtonBox.ActionRole)

        layout = QVBoxLayout()
        layout.addWidget(heading)
        layout.addWidget(self.table)
        layout.addWidget(buttonbox)
        self.setLayout(layout)

    def _populate(self):
        """Fill the table from the records."""
        for row, r in enumerate(self.records):

            name_item = QTableWidgetItem(str(r["name"]))
            # stash navigation target on the row so it survives re-sorting
            name_item.setData(Qt.UserRole, (int(r["section"]), str(r["name"])))

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
                self.table.setItem(row, col, item)

    @staticmethod
    def _format_location(loc):
        """Render a location tuple for display ('—' when there are no points)."""
        if not loc:
            return "—"
        return f"({loc[0]}, {loc[1]})"

    def _onDoubleClick(self, row, _col):
        """Focus the field on the double-clicked contour."""
        if not self.navigate:
            return
        item = self.table.item(row, 0)
        if item is None:
            return
        section_num, obj_name = item.data(Qt.UserRole)
        self.navigate(section_num, obj_name)

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
            "Save malformed contours",
            "malformed_contours.csv",
            "CSV files (*.csv);;All files (*)",
        )
        if not fp:
            return
        with open(fp, "w", newline="") as f:
            csv.writer(f).writerows(self._rows_for_export())
