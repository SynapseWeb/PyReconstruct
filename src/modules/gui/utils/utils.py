import os

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QMenuBar,
    QMenu,
    QProgressDialog,
    QMessageBox,
    QFileDialog
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt

from modules.constants import fd_dir

mainwindow = None

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

def setMainWindow(mw):
    """Set the main window for the gui functions."""
    global mainwindow
    mainwindow = mw

def notify(message):
    """Notify the user."""
    QMessageBox.information(
        mainwindow,
        "Notify",
        message,
        QMessageBox.Ok
    )

def notifyConfirm(message):
    """Notify the user and give option to OK or cancel."""
    response = QMessageBox.warning(
        mainwindow,
        " ",
        message,
        QMessageBox.Ok,
        QMessageBox.Cancel
    )
    return response == QMessageBox.Ok

def noUndoWarning():
    """Inform the user of an action that can't be undone."""
    return notifyConfirm("WARNING: This action cannot be undone.")

def saveNotify():
    response = QMessageBox.question(
        mainwindow,
        "Exit",
        "This series has been modified.\nWould you like save before exiting?",
        buttons=(
            QMessageBox.Yes |
            QMessageBox.No |
            QMessageBox.Cancel
        )
    )
    
    if response == QMessageBox.Yes:
        return "yes"
    elif response == QMessageBox.No:
        return "no"
    else:
        return "cancel"

def unsavedNotify():
    response = QMessageBox.question(
        mainwindow,
        "Unsaved Series",
        "An unsaved version of this series has been found.\nWould you like to open it?",
        QMessageBox.Yes,
        QMessageBox.No
    )

    return response == QMessageBox.Yes

def getSaveLocation(series):
    # prompt user to pick a location to save the jser file
    global fd_dir
    file_path, ext = QFileDialog.getSaveFileName(
        mainwindow,
        "Save Series",
        os.path.join(fd_dir.get(), f"{series.name}.jser"),
        filter="JSON Series (*.jser)"
    )
    if not file_path:
        return None, False
    else:
        fd_dir.set(os.path.dirname(file_path))
        return file_path, True


# PROGRESS BAR

class BasicProgbar():
    def __init__(self, text : str, maximum=100):
        """Create a 'vanilla' progress indicator.
        
        Params:
            text (str): the text to display by the indicator
        """
        self.text = text
        self.max = maximum
        if self.max == 0:
            print(f"{text} | Loading...", end="\r")
        else:
            print(f"{text} | 0.0%", end="\r")
    
    def setValue(self, n):
        """Update the progress indicator.
        
            Params:
                p (float): the percentage of progress made
        """
        if self.max == 0:
            return
        print(f"{self.text} | {n / self.max * 100 :.1f}%", end="\r")
        if n == self.max:
            self.close()
    
    def wasCanceled(self):
        """Dummy function -- do nothing!"""
        return False
    
    def close(self):
        """Force finish the progbar."""
        print()

def getProgbar(text, cancel=True, maximum=100):
    """Create a progress bar (either for pyqt or in cmd text).
    
        Params:
            text (str): the text for the progress bar
            cancel (bool): True if progress bar is cancelable
            maximum (int): the max value for the progress bar
    """
    use_basic = False

     # check if PySide6 has benn initialized
    if not QApplication.instance():
        use_basic = True
    else:
        try:
            progbar = QProgressDialog(
                    text,
                    "Cancel",
                    0, maximum,
                    mainwindow
                )
            progbar.setMinimumDuration(1500)
            progbar.setWindowTitle(" ")
            progbar.setWindowModality(Qt.WindowModal)
            if not cancel:
                progbar.setCancelButton(None)
        except:
            use_basic = True

    if use_basic:
        progbar = BasicProgbar(text, maximum)
    
    return progbar