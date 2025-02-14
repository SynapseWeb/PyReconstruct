import os
import re
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QMenuBar,
    QMenu,
    QProgressDialog,
    QMessageBox,
    QLabel,
    QTableWidget
)
from PySide6.QtGui import (
    QAction,
    QPainter,
    QPainterPath,
    QPen,
    QBrush,
    QColor,
    QFont,
    QScreen
)
from PySide6.QtCore import Qt

from PyReconstruct.modules.constants import welcome_series_dir


mainwindow = None
qt_offscreen = os.getenv("QT_QPA_PLATFORM") == "offscreen"


def get_screen_info(screen: QScreen) -> dict:
    """Return screen information."""

    screen_rect = screen.size()

    screen_info = {
        "width"  : screen_rect.width(),
        "height" : screen_rect.height(),
        "dpi"    : round(screen.physicalDotsPerInch())
    }

    return screen_info


def get_window_size(window) -> tuple:
    """Return width and height of the mainwindow."""
    
    return (
        window.size().width(),
        window.size().height()
    )


def get_center_pixel(window) -> tuple:
    """Return the center pixel of the mainwindow."""

    width, height = get_window_size(window)

    return width // 2, height // 2


def get_clicked(event) -> tuple:
    """Return L, M, and R mouse clicks."""

    buttons = event.buttons()
    
    return (
        Qt.LeftButton in buttons,
        Qt.MiddleButton in buttons,
        Qt.RightButton in buttons
    )


def get_welcome_setup() -> tuple:
    """Return welcome series setup."""

    welcome_dir = Path(welcome_series_dir)
    welcome_ser = welcome_dir  / "welcome.ser"

    date = datetime.now().strftime("%m%d")
    welcome_src_today = welcome_dir.parent / f"dates/{date}"

    ## Check if date specific splash image exists
    if welcome_src_today.exists():

        welcome_src = str(welcome_src_today)

    else:

        welcome_src = str(welcome_dir.parent)

    welcome_setup = (
        str(welcome_ser),        # .ser
        {0: "welcome.0"},        # secs
        welcome_src              # src
    )

    return welcome_setup


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
        if "checkbox" in kbd:
            action.setCheckable(True)
            if "True" in kbd:
                action.setChecked(True)
        else:
            action.setShortcut(kbd)
    else:  # assume series was passed in
        action.setShortcut(kbd.getOption(act_name))

    # remove previous action
    if act_name in dir(widget):
        widget.removeAction(getattr(widget, act_name))
    
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

    if QApplication.instance() and not qt_offscreen:
        
        QMessageBox.information(
            mainwindow,
            "Message",
            message,
            QMessageBox.Ok
        )

        mainwindow.activateWindow()  # focus on mainwindow

    else:

        print(message)
        input("Press any key to continue...")


def notifyConfirm(message, yn=False):
    """Notify the user and give option to OK or cancel."""

    if yn:

        if QApplication.instance() and not qt_offscreen:
            
            response = QMessageBox.question(
                mainwindow,
                " ",
                message,
                QMessageBox.Yes,
                QMessageBox.No
            )
            
            return response == QMessageBox.Yes

        else:

            print(message)
            return ask_yes_no()
        
    else:

        if QApplication.instance() and not qt_offscreen:
        
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

def drawOutlinedText(
        painter : QPainter, 
        x : int, y : int, 
        text : str, 
        c1 : tuple = (255, 255, 255), 
        c2 : tuple = (0, 0, 0),
        size : int = 0, 
        right_justify=False
    ):
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
    # create the font
    if not size: size = painter.font().pixelSize()
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


def get_menu_dict(attr_name: str, title: str, options: list):
    """Return a menu dictionary."""

    return {
        "attr_name": attr_name,
        "text": title,
        "opts": options
    }


def getUserColsMenu(series, newUserCol, setUserCol, editUserCol):
    """Create submenu for editing categorical columns."""
    
    def getSetCall(col_name, opt):
        return (lambda : setUserCol(col_name=col_name, opt=opt))
    
    def getEditCall(col_name):
        return (lambda : editUserCol(col_name=col_name))
    
    custom_categories = []
    menu_i = 0  # keep track of numbers for unique attribute
    opts_i = 0

    for col_name, opts in series.user_columns.items():

        d = get_menu_dict(
            f"user_col_{menu_i}_menu",
            col_name,
            [
                (f"edit_user_col_{menu_i}_act", "Edit...", "", getEditCall(col_name)),
                (f"user_col_{opts_i}_act", "(blank)", "", getSetCall(col_name, "")),
            ]
        )
        
        menu_i += 1
        opts_i += 1

        for opt in opts:

            d["opts"].append(
                (f"user_col_{opts_i}_act", opt, "", getSetCall(col_name, opt))
            )

            opts_i += 1

        custom_categories.append(d)

    opts_list = [("newusercol_act", "New...", "", newUserCol)] + custom_categories
        
    return get_menu_dict(
        "customcategoriesmenu", "Custom categories", opts_list
    )


def getAlignmentsMenu(series, setAlignment):
    """Create submenu for switching alignments."""

    def getCall(alignment):
        return (lambda : setAlignment(alignment))
    
    opts_list = []

    for alignment in sorted(series.alignments):
        opts_list.append(
            (f"{alignment}_alignment_act", alignment, "checkbox", getCall(alignment))
        )
    
    return get_menu_dict("alignmentsmenu", "Series alignment", opts_list)


def getGroupsMenu(self):
    """Create submenu for group visibility."""

    group_viz = self.series.groups_visibility

    
    def getCall(group):
        return lambda: self.toggleGroupViz(group)
    
    opts_list = []

    obj_groups = self.series.groups_visibility

    for group in sorted(obj_groups.keys()):

        opts_list.append(
            (f"{group}_viz_act", group, "checkbox", getCall(group))
        )
    
    return get_menu_dict("groupsvizmenu", "Groups", opts_list)


def getOpenRecentMenu(series, openSeries):
    # create the submenu for opening a recent series
    def getCall(fp):
        return (lambda : openSeries(jser_fp=fp))

    opts_list = []
    filepaths = series.getOption("recently_opened_series")
    for fp in filepaths.copy():
        if not os.path.isfile(fp):  # remove if not a file
            filepaths.remove(fp)
        elif fp != series.jser_fp:
            opts_list.append(
                (f"openrecent{len(opts_list)}_act", fp, "", getCall(fp))
            )
    series.setOption("recently_opened_series", filepaths)

    return {
        "attr_name": "openrecentmenu",
        "text": "Open recent",
        "opts": opts_list
    }


def ask_yes_no(prompt="Please enter y/[n]: "):
    
    valid_responses = {
        'yes' : True,
        'y'   : True,
        'no'  : False,
        'n'   : False
    }

    pattern = r'\[(.*?)\]'
    default = re.findall(pattern, prompt)
    
    if default:
        
        default = default[0]
        
    while True:
        
        response = input(prompt).strip().lower()
        
        if not response and default is not None:
            
            return valid_responses[default.lower()]
        
        elif response in valid_responses:
            
            return valid_responses[response]
        
        else:
            
            print("Please enter 'y' or 'n'.")
