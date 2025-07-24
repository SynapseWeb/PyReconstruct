"""The main window."""

from PySide6.QtWidgets import QMainWindow

## Core functions
from .ops import Initialization, HandlingOperations, FileOperations                

## UI components
from .ops import MenuOperations, UIOperations, ViewOperations                      

## Content manipulation
from .ops import ImageOperations, NavigationOperations, ImportExportOperations     

## Advanced features
from .ops import HistoryOperations, ThreeDimensionalOperations, ProjectOperations  


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
