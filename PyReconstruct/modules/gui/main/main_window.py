"""The main window."""

import os

from PySide6.QtWidgets import QMainWindow

from .ops import (
    Initialization,
    HandlingOperations,
    FileOperations,
    MenuOperations,
    ImageOperations,
    UIOperations,
    NavigationOperations,
    ViewOperations,
    ImportExportOperations,
    HistoryOperations,
    ThreeDimensionalOperations,
    ProjectOperations,
    #AutosegOperations
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

    def restart(self):
        """Restart application and clear console."""
        self.restart_mainwindow = True

        # Clear console
        if os.name == 'nt': _ = os.system('cls')
        else: _ = os.system('clear')
        
        self.close()    


qdark_addon = """
QPushButton {border: 1px solid transparent}
QComboBox {padding-right: 40px}
"""
