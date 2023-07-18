from PySide6.QtWidgets import QDockWidget, QPlainTextEdit
from PySide6.QtCore import Qt

from .text_widget import TextWidget

class HistoryWidget(TextWidget):

    def __init__(self, parent, output_str : str):
        """Create a text widget to display history"""
        super().__init__(parent, output_str)
        self.setWindowTitle("History")
        self.output.setWindowTitle("Trace Log")