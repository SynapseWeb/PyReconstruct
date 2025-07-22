"""Application setup methods."""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap

from PyReconstruct.modules.gui.utils import setMainWindow, customExcepthook, get_screen_info
from PyReconstruct.modules.constants import icon_path


class Initialization:
    """Initialization methods for MainWindow."""
    
    def _initialize(self, filename):
        """Initialize the main window."""
        # Setup exception handling
        sys.excepthook = customExcepthook
        
        # Set window properties
        self.setWindowTitle("PyReconstruct")
        self.setWindowIcon(QPixmap(icon_path))
        
        # Setup window size
        screen = QApplication.primaryScreen()
        self.screen_info = get_screen_info(screen)
        self.setGeometry(
            50, 80,
            self.screen_info["width"] - 100,
            self.screen_info["height"] - 160
        )
        
        # Initialize instance variables
        self._init_instance_variables()
        
        # Set mouse tracking
        self.setMouseTracking(True)
        
        # Create status bar
        self.statusbar = self.statusBar()
        
        # Open series
        if filename and Path(filename).exists():
            self.openSeries(jser_fp=filename)
        else:
            self.openWelcomeSeries()
            
        # Set main window as parent of progress bar
        setMainWindow(self)
        
        # Set theme
        self.setTheme(self.series.getOption("theme"))
        
        self.show()
        
        # Prompt for username
        self.changeUsername()
        
    def _init_instance_variables(self):
        """Initialize instance variables."""
        self.series = None
        self.series_data = None
        self.field = None
        self.menubar = None
        self.mouse_palette = None
        self.zarr_palette = None
        self.viewer = None
        self.shortcuts_widget = None
        self.is_zooming = False
        self.restart_mainwindow = False
        self.check_actions_enabled = False
        self.actions_initialized = False
