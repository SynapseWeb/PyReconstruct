"""Guards the QSettings redirect that conftest.py installs.

A settings write that escaped the redirect would land in the real user domain
and stay there, and nothing else in a passing run would say so. This asserts the
seam rather than trusting it.

The assertions go through the modules that actually construct QSettings, not
through a locally imported name: rebinding ``PySide6.QtCore.QSettings`` looks
like it works from the patching side while the application still resolves the
real class, so a test that only checked its own import would pass over exactly
the failure it exists to catch.
"""

import conftest

from PyReconstruct.modules.constants import getdatetime
from PyReconstruct.modules.datatypes import series


def test_application_settings_go_to_a_temporary_file():
    settings = getdatetime.QSettings("KHLab", "PyReconstruct")

    assert settings.fileName().startswith(conftest.SETTINGS_DIR)


def test_per_series_settings_go_to_a_temporary_file():
    """Series options use their own ``PyReconstruct-<code>`` organization."""
    settings = series.QSettings("KHLab", "PyReconstruct-ABCD")

    assert settings.fileName().startswith(conftest.SETTINGS_DIR)


def test_a_write_lands_in_the_temporary_directory():
    """The path is where the value ends up, not just what fileName() reports."""
    settings = series.QSettings("KHLab", "PyReconstruct")
    settings.setValue("pyrecon_test_probe", "1")
    settings.sync()

    with open(settings.fileName()) as f:
        assert "pyrecon_test_probe" in f.read()
