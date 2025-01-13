import os
import sys
import re
import time
import webbrowser
from datetime import datetime
import json
import subprocess
from typing import List, Union
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QInputDialog, 
    QApplication,
    QMessageBox, 
    QMenu
)

from PySide6.QtGui import (
    QKeySequence,
    QShortcut,
    QPixmap,
    QAction,
    QImage,
    QPainter,
    QRegion
)

from PySide6.QtCore import (
    Qt,
    QPoint,
    QSettings
)

from .field_widget import FieldWidget

from PyReconstruct.modules.gui.palette import (
    MousePalette,
    ZarrPalette
)

from PyReconstruct.modules.gui.dialog import (
    AlignmentDialog,
    GridDialog,
    CreateZarrDialog,
    TrainDialog,
    SegmentDialog,
    PredictDialog,
    QuickDialog,
    FileDialog,
    AllOptionsDialog,
    BCProfilesDialog,
    BackupDialog,
    ShortcutsDialog,
    BackupCommentDialog,
    ImportSeriesDialog,
)

from PyReconstruct.modules.gui.popup import (
    TextWidget,
    CustomPlotter,
    AboutWidget
)

from PyReconstruct.modules.gui.utils import (
    populateMenuBar,
    populateMenu,
    notify,
    notifyConfirm,
    saveNotify,
    unsavedNotify,
    setMainWindow,
    noUndoWarning,
    checkMag,
    getUserColsMenu,
    getAlignmentsMenu,
    getOpenRecentMenu,
    customExcepthook,
    get_screen_info,
    get_welcome_setup,
    get_center_pixel
)

from PyReconstruct.modules.backend.func import determine_cpus

from PyReconstruct.modules.gui.table import (
    HistoryTableWidget,
    CopyTableWidget,
    ObjectTableWidget
)

from PyReconstruct.modules.backend.func import (
    xmlToJSON,
    jsonToXML,
    importTransforms,
    importSwiftTransforms
)

from PyReconstruct.modules.backend.view import (
    optimizeSeriesBC
)

from PyReconstruct.modules.backend.autoseg import (
    zarrToNewSeries,
    labelsToObjects
)

from PyReconstruct.modules.backend.volume import (
    export3DObjects
)

from PyReconstruct.modules.backend.imports import (
    modules_available
)

from PyReconstruct.modules.backend.remote import (
    download_vol_as_tifs
)

from PyReconstruct.modules.datatypes import (
    Series,
    Trace,
    Transform,
    Flag
)

from PyReconstruct.modules.constants import (
    welcome_series_dir,
    assets_dir,
    img_dir,
    icon_path,
    kh_web,
    kh_wiki,
    kh_atlas,
    gh_repo,
    gh_issues,
    gh_submit,
    developers_mailto_str,
    repo_info,
    repo_string,
    kharris2015
)

from PyReconstruct.assets.scripts.projects import (
    randomize_project,
    derandomize_project
)

from .menubar import return_menubar

from .context_menu_list import get_field_menu_list
