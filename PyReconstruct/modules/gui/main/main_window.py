"""The main window."""

from PySide6.QtWidgets import QMainWindow

from .ops import (
    Initialization, HandlingOperations, FileOperations,                # core funcs
    MenuOperations, UIOperations, ViewOperations,                      # ui components        
    ImageOperations, NavigationOperations, ImportExportOperations,     # content manipulation
    HistoryOperations, ThreeDimensionalOperations, ProjectOperations,  # advanced features
)


class MainWindow(
        QMainWindow, Initialization, HandlingOperations, FileOperations,
        MenuOperations, ImageOperations, UIOperations, NavigationOperations,
        ViewOperations, ImportExportOperations, HistoryOperations,
        ThreeDimensionalOperations, ProjectOperations
):

    def __init__(self, filename):
        super().__init__()
        self._initialize(filename)

    def wheelEvent(self, event):
        self.handleWheelEvent(event)

    def closeEvent(self, event):
        self.handleCloseEvent(event)


qdark_addon = """
QPushButton {border: 1px solid transparent}
QComboBox {padding-right: 40px}
"""
