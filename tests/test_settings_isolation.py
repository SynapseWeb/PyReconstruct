"""Guards the QSettings redirect that conftest.py installs.

A settings write that escaped the redirect would land in the real user domain
and stay there, and nothing else in a passing run would say so. This asserts the
seam rather than trusting it.
"""

from PySide6.QtCore import QSettings

import conftest


def test_application_settings_go_to_a_temporary_file():
    settings = QSettings("KHLab", "PyReconstruct")

    assert settings.format() == conftest.REAL_QSETTINGS.Format.IniFormat
    assert settings.fileName().startswith(conftest.SETTINGS_DIR)


def test_per_series_settings_go_to_a_temporary_file():
    """Series options use their own ``PyReconstruct-<code>`` organization."""
    settings = QSettings("KHLab", "PyReconstruct-ABCD")

    assert settings.fileName().startswith(conftest.SETTINGS_DIR)


def test_the_modules_that_read_settings_see_the_redirect():
    """The application binds the name at import time, so the patch has to be in
    place before the first import, not just before the first call."""
    from PyReconstruct.modules.constants import getdatetime
    from PyReconstruct.modules.datatypes import series

    assert getdatetime.QSettings is conftest._TempQSettings
    assert series.QSettings is conftest._TempQSettings
