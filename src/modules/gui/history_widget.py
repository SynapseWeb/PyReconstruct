from PySide6.QtWidgets import QDockWidget, QPlainTextEdit
from PySide6.QtCore import Qt

class HistoryWidget(QDockWidget):

    def __init__(self, parent, output_str : str):
        super().__init__(parent)
        self.setWindowTitle("History")
        self.setFloating(True)
        self.setAllowedAreas(Qt.NoDockWidgetArea)

        output = QPlainTextEdit(self)
        output.setWindowTitle("Trace Log")
        output.setPlainText(output_str)

        self.setWidget(output)
        self.show()