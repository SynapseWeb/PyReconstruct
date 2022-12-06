from PySide6.QtWidgets import (
    QWidget,
    QMenuBar,
    QMenu,
    QProgressDialog,
    QMessageBox
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt

def newMenu(widget : QWidget, container, menu_dict : dict):
    """Create a menu.
    
        Params:
            widget (QWidget): the widget the menu is connected to
            container (QMenu or QMenuBar): the menu containing the new menu
            menu_dict (dict): the dictionary describing the menu
    """
    # create the menu attribute
    menu = container.addMenu(menu_dict["text"])
    setattr(widget, menu_dict["attr_name"], menu)
    # populate the menu
    for item in menu_dict["opts"]:
        addItem(widget, menu, item)

def newAction(widget : QWidget, container : QMenu, action_tuple : tuple):
    """Create an action within a menu.
    
        Params:
            widget (QWidget): the widget the action is connected to
            container (QMenu): the menu that contains the action
            action_tuple (tuple): the tuple describing the action (name, text, keyboard shortcut, function)
    """
    act_name, text, kbd, f = action_tuple
    # create the action attribute
    action = container.addAction(text, f, kbd)
    if kbd == "checkbox":
        action.setCheckable(True)
    widget.addAction(action)
    setattr(widget, act_name, action)

def newQAction(widget : QWidget, container : QMenu, action : QAction):
    """Add an existing action to the menu.
    
        Params:
            widget (QWidget): the widget the action is connected to
            container (QMenu): the menu that contains the action
            action (QAction): the action to add to the menu
    """
    container.addAction(action)

def addItem(widget : QWidget, container, item):
    """Add an item to an existing menu or menubar
    
        Params:
            widget (QWidget): the widget to contain the attributes
            container: the menu or menubar
            item: the item to add
    """
    if type(item) is tuple:
        newAction(widget, container, item)
    elif type(item) is dict:
        newMenu(widget, container, item)
    elif type(item) is QAction:
        newQAction(widget, container, item)
    elif item is None:
        container.addSeparator()

def populateMenu(widget : QWidget, menu : QMenu, menu_list : list):
    """Create a menu.
    
        Params:
            widget (QWidget): the widget the menu belongs to
            menu (QMenu): the menu object to contain the list objects
            menu_list (list): formatted list describing the menu
    """
    for item in menu_list:
        addItem(widget, menu, item)

def populateMenuBar(widget : QWidget, menu : QMenuBar, menubar_list : list):
    """Create a menubar for a widget.
    
        Params:
            widget (QWidget): the widget containing the menu bar
            menubar (QMenuBar): the menubar object to add menus to
            menubar_list (list): the list of menus on the menubar
    """
    # populate menubar
    for menu_dict in menubar_list:
        newMenu(widget, menu, menu_dict)

def progbar(title : str, text : str):
    """Create an easy progress dialog."""
    progbar = QProgressDialog(
            text,
            "Cancel",
            0, 100
        )
    progbar.setWindowTitle(title)
    progbar.setWindowModality(Qt.WindowModal)
    return progbar.setValue, progbar.wasCanceled

def noUndoWarning(parent):
    """Inform the user of an action that can't be undone."""
    response = QMessageBox.warning(
        parent,
        "",
        "WARNING: This action cannot be undone.",
        QMessageBox.Ok,
        QMessageBox.Cancel
    )
    return response == QMessageBox.Ok



