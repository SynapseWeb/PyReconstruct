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
        """Construct skeleton for an empty main window."""
        super().__init__()
        self._initialize(filename)

    def restart(self):
        """Restart the application and clear console."""
        self.restart_mainwindow = True

        # Clear console
        if os.name == 'nt': _ = os.system('cls')
        else: _ = os.system('clear')
        
        self.close()

    def closeEvent(self, event):
        """Save all data to hidden files when user exits."""
        response = self.saveToJser(notify=True, close=True)
        
        if response == "cancel":
            event.ignore()
            return
        
        if self.viewer and not self.viewer.is_closed:
            self.viewer.close()
            
        event.accept()


qdark_addon = """
QPushButton {border: 1px solid transparent}
QComboBox {padding-right: 40px}
"""
