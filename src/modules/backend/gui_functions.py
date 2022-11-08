from PySide6.QtWidgets import QWidget, QMenuBar, QMenu
from PySide6.QtCore import Qt

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

def newMenu(widget : QWidget, container, menu_dict : dict):
    """Create a menu.
    
        Params:
            widget (QWidget): the widget the menu is connected to
            container (QMenu or QMenuBar): the menu containing the new menu
            menu_dict (dict): the dictionary describing the menu
    """
    # create the menu attribute
    setattr(widget, menu_dict["attr_name"], container.addMenu(menu_dict["text"]))
    # get the menu attribute
    menu = getattr(widget, menu_dict["attr_name"])
    # populate the menu
    for item in menu_dict["opts"]:
        if type(item) is tuple:  # create new action
            newAction(widget, menu, item)
        elif type(item) is dict:  # create new menu
            newMenu(widget, menu, item)

def newAction(widget : QWidget, container : QMenu, action_tuple : tuple):
    """Create an action within a menu.
    
        Params:
            widget (QWidget): the widget the action is connected to
            container (QMenu): the menu that contains the action
            action_tuple (tuple): the tuple describing the action (name, text, keyboard shortcut, function)
    """
    act_name, text, kbd, f = action_tuple
    # create the action attribute
    setattr(widget, act_name, container.addAction(text))
    # get the action attribute
    action = getattr(widget, act_name)
    # set the shortcut and function
    action.setShortcut(kbd)
    action.triggered.connect(f)

def populateMenu(widget : QWidget, menu : QMenu, menu_list : list):
    """Create a menu.
    
        Params:
            widget (QWidget): the widget the menu belongs to
            menu (QMenu): the menu object to contain the list objects
            menu_list (list): formatted list describing the menu
    """
    for item in menu_list:
        if type(item) is tuple:
            newAction(widget, menu, item)
        if type(item) is dict:
            newMenu(widget, menu, item)

