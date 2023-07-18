from PySide6.QtWidgets import QDockWidget, QPlainTextEdit
from PySide6.QtCore import Qt

class TextWidget(QDockWidget):

    def __init__(self, parent, output_str : str, title=" "):
        """Create a text widget to display history"""
        super().__init__(parent)
        self.setFloating(True)
        self.setAllowedAreas(Qt.NoDockWidgetArea)
        self.setWindowTitle(title)

        self.output = QPlainTextEdit(self)
        self.output.setPlainText(output_str)

        self.setWidget(self.output)
        self.show()