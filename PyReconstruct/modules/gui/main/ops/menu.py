"""Application menu operations."""

from PySide6.QtWidgets import QMenu

from PyReconstruct.modules.gui.utils import populateMenuBar, populateMenu

from .menubar import return_menubar

from ..field.context_menu_list import get_field_menu_list


class MenuOperations:

    def createMenuBar(self):
        """Create main window menubar."""
        menu = return_menubar(self)

        if self.menubar:
            
            self.menubar.clear()
            
        else:
            
            self.menubar = self.menuBar()
            self.menubar.setNativeMenuBar(False)

        ## Populate menu bar with menus and options
        populateMenuBar(self, self.menubar, menu)

    def createContextMenus(self):
        """Create right-click menus used in the field."""
        ## Create user columns options
        field_menu_list = get_field_menu_list(self)
        self.field_menu = QMenu(self)
        populateMenu(self, self.field_menu, field_menu_list)

        ## Organize actions
        self.trace_actions = [
            self.tracemenu,
            self.objectmenu,
            self.cut_act,
            self.copy_act,
            self.pasteattributes_act,
        ]
        self.ztrace_actions = [
            self.ztracemenu
        ]

        ## Create label menu
        label_menu_list = [
            # ("importlabels_act", "Import label(s)", "", self.importLabels),
            # ("mergelabels_act", "Merge labels", "", self.mergeLabels)
        ]
        self.label_menu = QMenu(self)
        populateMenu(self, self.label_menu, label_menu_list)

        ## Check alignment in alignment submenu
        self.changeAlignment(self.series.alignment)

