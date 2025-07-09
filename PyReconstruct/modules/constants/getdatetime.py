from datetime import datetime, timedelta

from PySide6.QtCore import QSettings


def utc_p() -> bool:
    """Determine if user using UTC."""

    settings = QSettings("KHLab", "PyReconstruct")
    utc = settings.value("utc", False)

    return False if utc == "false" else True


def get_now() -> datetime:
    """Return now's datetime object."""

    return datetime.utcnow() if utc_p() else datetime.now()


def remove_days_from_today(delta_days: int):
    """Remove days from now."""

    return get_now().date() - timedelta(days=delta_days)


def getDateTime(date_str="%y-%m-%d", time_str="%H:%M"):
    
    dt = get_now()
    
    d = dt.strftime(date_str)
    t = dt.strftime(time_str)
    
    return d, t
