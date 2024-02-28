from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QMenuBar,
    QMenu,
    QProgressDialog,
    QMessageBox,
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
    action : QAction = container.addAction(text, f, "")
    
    # create the shorcut or checkbox
    if type(kbd) is str:
        if kbd == "checkbox":
            action.setCheckable(True)
        else:
            action.setShortcut(kbd)
    else:  # assume series was passed in
        action.setShortcut(kbd.getOption(act_name))

    # attach to widget
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
    if "\n" in text:
        l = QLabel(text="X")
        l.setFont(font)
        l.adjustSize()
        h = l.height()
        l.close()
        split_text = text.split("\n")
        for line in split_text:
            path.addText(x, y, font, line)
            y += h + 1
    else:
        path.addText(x, y, font, text)
    
    # determine outline color if not provided
    if not c2:
        black_outline = c1[0] + 3*c1[1] + c1[2] > 400
        c2 = (0, 0, 0) if black_outline else (255, 255, 255)

    pen = QPen(QColor(*c2), w * 2)
    brush = QBrush(QColor(*c1))
    painter.strokePath(path, pen)
    painter.fillPath(path, brush)

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

def notifyLocked(obj_names, series, series_states):
    """Open a dialog when the user tries to interact with a locked object."""
    if len(obj_names) > 1:
        s = "These objects are locked.\nWould you like to unlock them?"
    else:
        s = "This object is locked.\nWould you like to unlock it?"
    
    response = QMessageBox.question(
        mainwindow,
        "Locked Object",
        s,
        QMessageBox.Yes,
        QMessageBox.No
    )

    if response == QMessageBox.Yes:
        series_states.addState()
        for obj_name in obj_names:
            series.setAttr(obj_name, "locked", False)
        return True
    else:
        return False

def checkMag(s_series, o_series):
    """Check the magnification between the two series. If different, prompt user for response."""
    if abs(o_series.avg_mag - s_series.avg_mag) > 1e-8:
        response = QMessageBox.question(
            mainwindow,
            "Calibration Mismatch",
            (
                "The series have different calibrations.\n" +
                f"Current series: {round(s_series.avg_mag, 8)}\n" +
                f"Importing series: {round(o_series.avg_mag, 8)}\n" + 
                "Would you like to continue?"
            ),
            QMessageBox.Yes,
            QMessageBox.No
        )
        if response != QMessageBox.Yes:
            return False
        
    return True
    
