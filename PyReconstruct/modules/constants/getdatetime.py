from datetime import datetime

from PySide6.QtCore import QSettings

def getDateTime(date_str="%y-%m-%d", time_str="%H:%M"):
    settings = QSettings("KHLab", "PyReconstruct")
    utc = settings.value("utc", False)
    dt = datetime.utcnow() if utc else datetime.now()
    d = dt.strftime(date_str)
    t = dt.strftime(time_str)
    return d, t