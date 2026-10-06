import csv
import html

from PySide6.QtWidgets import (
    QWidget,
    QDialog,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QToolButton,
    QToolTip,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QDialogButtonBox,
    QHeaderView,
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QComboBox,
    QStyledItemDelegate,
)
from PySide6.QtCore import Qt

from PyReconstruct.modules.gui.utils import notifyConfirm


# the Keep cell of the duplicates list stores the row's names here
NAMES_ROLE = Qt.UserRole + 1


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

        # one line above the list; the full explanation is the tooltip of
        # the "?" beside it
        self.heading = QLabel(self)
        # a button, not a label, so the keyboard can reach it too: Tab to
        # it and press Space to show the same tooltip a hover shows
        self.help_icon = QToolButton(self)
        self.help_icon.setText("?")
        self.help_icon.setAccessibleName("Explanation")
        self.help_icon.setFocusPolicy(Qt.StrongFocus)
        self.help_icon.setFixedSize(18, 18)
        self.help_icon.setCursor(Qt.WhatsThisCursor)
        self.help_icon.setStyleSheet(
            "QToolButton { border: 1px solid palette(mid); border-radius: 9px;"
            " font-weight: bold; padding: 0; }"
        )
        self.help_icon.clicked.connect(self._showExplanation)
        self._refreshHeading()

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

        heading_row = QHBoxLayout()
        heading_row.addWidget(self.heading)
        heading_row.addWidget(self.help_icon)
        heading_row.addStretch(1)

        layout = QVBoxLayout()
        layout.addLayout(heading_row)
        layout.addWidget(self.table)
        layout.addWidget(buttonbox)
        self.setLayout(layout)

    def _refreshHeading(self):
        """Set the one-line heading and the "?" tooltip from the records."""
        self.heading.setText(self._summaryText())
        explanation = self._explanationText()
        # rich text, so Qt wraps the tooltip instead of drawing one long line
        self.help_icon.setToolTip("".join(
            f"<p>{html.escape(paragraph, quote=False)}</p>"
            for paragraph in explanation.split("\n\n")
        ))
        self.help_icon.setAccessibleDescription(explanation)

    def _showExplanation(self):
        """Show the "?" tooltip under the icon, for a click or a key."""
        QToolTip.showText(
            self.help_icon.mapToGlobal(self.help_icon.rect().bottomLeft()),
            self.help_icon.toolTip(),
            self.help_icon,
        )

    def _summaryText(self):
        """One short line that says what the list holds."""
        num_traces = len(self.records)
        if not num_traces:
            return "All listed traces have been deleted."
        trace_word = "trace" if num_traces == 1 else "traces"
        return f"{num_traces} {trace_word} could not be smoothed."

    def _explanationText(self):
        """Build the full explanation (the "?" tooltip) from the records."""
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
        self._refreshHeading()
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

    def _summaryText(self):
        num_traces = len(self.records)
        if not num_traces:
            return "All listed traces have been deleted."
        trace_word = "trace" if num_traces == 1 else "traces"
        return f"{num_traces} {trace_word} at or below the area threshold."

    def _explanationText(self):
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


class _KeepNameCombo(QComboBox):
    """A drop-down that ignores the mouse wheel.

    Several styles change a combo box's value on a wheel turn over it, so
    scrolling the list would change the picks it passed over. The wheel
    scrolls the table instead.
    """

    def wheelEvent(self, event):
        event.ignore()


class _KeepNameDelegate(QStyledItemDelegate):
    """The drop-down in a duplicates row's Keep cell.

    The pick is stored as the cell's own text, so it travels with its row
    through a column sort and reaches the copied table as it is; the
    drop-down is only the editor over it, kept open on every row.
    """

    PLACEHOLDER = "Pick a name"

    def createEditor(self, parent, option, index):
        combo = _KeepNameCombo(parent)
        combo.addItems(index.data(NAMES_ROLE) or [])
        combo.setPlaceholderText(self.PLACEHOLDER)
        combo.setCurrentIndex(-1)
        combo.currentIndexChanged.connect(
            lambda _i, c=combo: self.commitData.emit(c)
        )
        return combo

    def setEditorData(self, editor, index):
        name = index.data(Qt.DisplayRole) or ""
        editor.blockSignals(True)
        editor.setCurrentIndex(editor.findText(name) if name else -1)
        editor.blockSignals(False)

    def setModelData(self, editor, model, index):
        name = editor.currentText() if editor.currentIndex() >= 0 else ""
        model.setData(index, name, Qt.EditRole)


class DuplicateTracesDialog(MalformedContoursDialog):
    """Review duplicate traces and combine each structure into one trace.

    Each row is one group from Series.findDuplicateTraces: a structure traced
    more than once, under one name or under several. The Keep cell is a
    drop-down of the row's names. A row with one name has it picked; a row
    with more than one starts with none, because which name is right is a
    question about the data, and a row with no name picked is never combined.

    "Combine selected" and "Combine all" hand the picked rows to the
    ``combine`` callback, after a confirmation. Combining keeps one trace
    under the picked name with the tags of the others and deletes the rest
    (Series.combineDuplicateTraces). The base class's Delete buttons never
    appear: this dialog passes no ``delete`` callback up.
    """

    COLUMNS = ["Keep", "Traced as", "Section", "Traces", "Overlap",
               "Location (x, y)"]
    WINDOW_TITLE = "Duplicates"
    DEFAULT_SORT_COLUMN = 2  # "Section"
    KEEP_COLUMN = 0

    def __init__(self, mainwindow: QWidget, records: list, navigate=None,
                 combine=None):
        """Create the duplicates list.

            Params:
                mainwindow (QWidget): the parent window
                records (list): groups from Series.findDuplicateTraces
                navigate (callable): optional navigate(section_num, obj_name,
                    index) callback for "Go to trace"
                combine (callable): optional combine(choices) callback taking
                    ``(group, keep)`` tuples as Series.combineDuplicateTraces
                    does and returning the tuples it combined. The Combine
                    buttons are only shown when it is provided.
        """
        self.combine = combine
        super().__init__(mainwindow, records, navigate=navigate, delete=None)
        self.resize(760, 440)
        self.table.setItemDelegateForColumn(
            self.KEEP_COLUMN, _KeepNameDelegate(self.table)
        )
        for row in range(self.table.rowCount()):
            self.table.openPersistentEditor(
                self.table.item(row, self.KEEP_COLUMN)
            )
        self.table.itemChanged.connect(self._updateRowActionButtons)
        self._updateRowActionButtons()

    def _populate(self):
        """Fill the table from the groups."""
        self._records_by_key = {}
        for row, group in enumerate(self.records):
            self._records_by_key[row] = group
            names = list(group["names"])
            keep = QTableWidgetItem(names[0] if len(names) == 1 else "")
            keep.setData(Qt.UserRole, row)
            keep.setData(NAMES_ROLE, names)
            section = QTableWidgetItem()
            section.setData(Qt.DisplayRole, int(group["section"]))
            count = QTableWidgetItem()
            count.setData(Qt.DisplayRole, int(group["count"]))
            ratio = QTableWidgetItem()
            ratio.setData(Qt.DisplayRole, round(float(group["ratio"]), 8))
            cells = [
                keep,
                QTableWidgetItem(", ".join(names)),
                section,
                count,
                ratio,
                QTableWidgetItem(self._format_location(group.get("location"))),
            ]
            for col, item in enumerate(cells):
                item.setTextAlignment(Qt.AlignCenter)
                if col != self.KEEP_COLUMN:
                    item.setToolTip(item.text())
                self.table.setItem(row, col, item)

    def _choicesForRows(self, rows):
        """(group, keep) for each of the rows with a name picked, and how
        many rows had none."""
        choices = []
        unpicked = 0
        for row in rows:
            group = self._recordAtRow(row)
            if group is None:
                continue
            keep = self.table.item(row, self.KEEP_COLUMN).text()
            if keep:
                choices.append((group, keep))
            else:
                unpicked += 1
        return choices, unpicked

    def _selectedRows(self):
        return sorted(
            index.row() for index in self.table.selectionModel().selectedRows()
        )

    def _addExtraButtons(self):
        """Add the two Combine buttons when there is a callback for them."""
        self.combine_selected_button = None
        self.combine_all_button = None
        if not self.combine:
            return
        self.combine_selected_button = QPushButton("Combine selected", self)
        self.combine_selected_button.setToolTip(
            "Combine each selected row into one trace under the name picked "
            "(can be undone)"
        )
        self.combine_selected_button.clicked.connect(
            lambda: self._combineRows(self._selectedRows())
        )
        self.extra_buttons.append((self.combine_selected_button, False))

        self.combine_all_button = QPushButton("Combine all", self)
        self.combine_all_button.setToolTip(
            "Combine every row with a name picked into one trace under that "
            "name (can be undone)"
        )
        self.combine_all_button.clicked.connect(
            lambda: self._combineRows(range(self.table.rowCount()))
        )
        self.extra_buttons.append((self.combine_all_button, False))

    def _updateRowActionButtons(self, *_args):
        """Also enable each Combine button only while it has a picked row."""
        super()._updateRowActionButtons()
        if self.combine_all_button is None:
            return
        all_rows = range(self.table.rowCount())
        self.combine_all_button.setEnabled(
            bool(self._choicesForRows(all_rows)[0])
        )
        self.combine_selected_button.setEnabled(
            bool(self._choicesForRows(self._selectedRows())[0])
        )

    def _combineRows(self, rows):
        """Confirm, combine the picked rows, and prune the ones combined."""
        if not self.combine:
            return
        choices, unpicked = self._choicesForRows(rows)
        if not choices:
            return
        count = len(choices)
        noun = "row" if count == 1 else "rows"
        unpicked_note = ""
        if unpicked:
            was = "row was" if unpicked == 1 else "rows were"
            unpicked_note = (
                f"\n\n{unpicked} {was} left alone because no name is picked."
            )
        if not notifyConfirm(
            f"Combine {count} {noun}?\n\n"
            "In each row, one trace is kept under the name you picked, the "
            "tags of the other traces are added to it, and the others are "
            f"deleted.{unpicked_note}\n\n"
            "This can be undone (Ctrl+Z).",
            yn=True,
        ):
            return
        applied = self.combine(choices) or []
        if not applied:
            return

        ## a combine deletes every trace of a group but the one kept, so a
        ## later trace of the same object on the same section moves up in its
        ## contour; shift the indexes of the rows left so "Go to trace" still
        ## frames the trace in its row
        from PyReconstruct.modules.datatypes.series import Series
        removed = []
        for group, keep in applied:
            kept = Series.duplicateKeptMember(group["members"], keep)
            removed.extend(
                (m["section"], m["name"], m["index"])
                for m in group["members"] if m is not kept
            )
        combined = {id(group) for group, _keep in applied}
        for group in self.records:
            if id(group) in combined:
                continue
            for member in group["members"]:
                member["index"] -= sum(
                    1 for section, name, index in removed
                    if section == member["section"]
                    and name == member["name"] and index < member["index"]
                )
        self._pruneRecords([group for group, _keep in applied])

    def _navigateToRow(self, row):
        """Focus the field on a row's trace: the one kept once a name is
        picked, and the row's first trace until then."""
        if not self.navigate:
            return
        group = self._recordAtRow(row)
        if group is None:
            return
        from PyReconstruct.modules.datatypes.series import Series
        keep = self.table.item(row, self.KEEP_COLUMN).text()
        member = (
            Series.duplicateKeptMember(group["members"], keep)
            or group["members"][0]
        )
        self.navigate(member["section"], member["name"], member["index"])

    def _summaryText(self):
        num_rows = len(self.records)
        if not num_rows:
            return "Every row has been combined."
        structures = "structure" if num_rows == 1 else "structures"
        return f"{num_rows} {structures} traced more than once."

    def _explanationText(self):
        """Explain what a row is and what combining it does."""
        num_rows = len(self.records)
        if not num_rows:
            return "Every row has been combined.\n\nYou can close this window."

        num_sections = len({g["section"] for g in self.records})
        structures = "structure" if num_rows == 1 else "structures"
        sections = "section" if num_sections == 1 else "sections"
        return (
            f"{num_rows} {structures} traced more than once, across "
            f"{num_sections} {sections}. Each row is one structure, whether "
            "its traces share a name or not.\n\n"
            "Pick the name to keep in each row. Combining a row keeps one "
            "trace under that name, adds the tags of the other traces to it, "
            "and deletes the others. A row with one name has it picked "
            "already. A row with more than one is left alone until you pick "
            "one.\n\n"
            "Select a row and click “Go to trace” to see it in the field. "
            "The Overlap column is the lowest overlap ratio between the "
            "row's traces (1 means the traces have the same points).\n\n"
            "Nothing changes until you combine, and combining can be undone "
            "(Ctrl+Z)."
        )
