
from PySide6.QtWidgets import QTableWidget, QApplication
from PySide6.QtCore import Qt

class CopyTableWidget(QTableWidget):

    def keyPressEvent(self, event):
        ret = super().keyPressEvent(event)
        # override the table copy function
        if event.key() == Qt.Key_C and (event.modifiers() & Qt.ControlModifier):
            self.copy()
        return ret

    def copy(self):
        """Copy table data onto the clipboard."""
        indexes = sorted(self.selectedIndexes())
        if indexes:
            clipboard_str = ""
            row = indexes[0].row()
            row_list = []
            for index in indexes:
                if index.row() > row:
                    clipboard_str += "\t".join(row_list) + "\n"
                    row_list = []
                    row = index.row()
                row_list.append(self.itemFromIndex(index).text())
            clipboard_str += "\t".join(row_list) + "\n"
            QApplication.clipboard().setText(clipboard_str)
