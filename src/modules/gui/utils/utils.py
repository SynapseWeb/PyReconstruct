import os

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QMenuBar,
    QMenu,
    QProgressDialog,
    QMessageBox,
    QFileDialog,
    QLabel
)
from PySide6.QtGui import (
    QAction,
    QPainter,
    QPainterPath,
    QPen,
    QBrush,
    QColor,
    QFont
)
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

def progbar(title : str, text : str, cancel=True):
    """Create an easy progress dialog."""
    # check if PySide6 has benn initialized
    if not QApplication.instance():
        return None, None
    else:
        progbar = QProgressDialog(
                text,
                "Cancel",
                0, 100,
                mainwindow
            )
        progbar.setMinimumDuration(1500)
        progbar.setWindowTitle(title)
        progbar.setWindowModality(Qt.WindowModal)
        if not cancel:
            progbar.setCancelButton(None)
        return progbar.setValue, progbar.wasCanceled

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

def drawOutlinedText(painter : QPainter, x : int, y : int, text : str, c1 : tuple, c2 : tuple, size : int, right_justify=False):
    """Draw outlined text using a QPainter object.
    
        Params:
            painter (QPainter): the QPainter object to use
            x (int): the x-pos of the text
            y (int): the y-pos of the text
            text (str): the text to write to the screen
            c1 (tuple): the primary color of the text
            c2 (tuple): the outline color of the text
            size (int): the size of the text
    """
    font = QFont("Courier New", size, QFont.Bold)

    if right_justify:
        l = QLabel(text=text)
        l.setFont(font)
        l.adjustSize()
        x -= l.width()
        l.close()
    
    w = 1  # outline thickness
    path = QPainterPath()
    path.addText(x, y, font, text)

    pen = QPen(QColor(*c2), w * 2)
    brush = QBrush(QColor(*c1))
    painter.strokePath(path, pen)
    painter.fillPath(path, brush)