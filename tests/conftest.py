"""Shared setup for the test suite.

Two things have to happen before any test module imports the application:

* Qt has to run without a display, so the widget tests work over ssh and in CI.

* QSettings has to be redirected. The application reads and writes real user
  settings through ``QSettings("KHLab", "PyReconstruct")``, and
  ``Series.getOption`` writes a default back whenever a key is missing, so a
  test that touched an option would edit the settings of whoever ran it. Every
  call site constructs ``QSettings(organization, application)``, which resolves
  to the native backend: a plist through ``cfprefsd`` on macOS, the registry on
  Windows. Neither ``setPath`` nor ``setDefaultFormat`` moves that (``setPath``
  documents no effect on the native backends, and a native default is what the
  two-argument constructor resolves to regardless), and redirecting ``$HOME``
  does not either, because ``cfprefsd`` resolves the real user's domain. What
  does work is binding the name the application imports to a subclass that
  hands every instance an explicit INI file under a temporary directory.
"""

import os
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

import PySide6.QtCore

_RealQSettings = PySide6.QtCore.QSettings
_SETTINGS_DIR = tempfile.mkdtemp(prefix="pyrecon-test-settings-")


class _TempQSettings(_RealQSettings):
    """QSettings backed by a throwaway INI file, keyed by organization/app."""

    def __init__(self, *args, **kwargs):
        organization = args[0] if args else "test"
        application = args[1] if len(args) > 1 else "test"
        super().__init__(
            os.path.join(_SETTINGS_DIR, f"{organization}.{application}.ini"),
            _RealQSettings.Format.IniFormat,
        )


PySide6.QtCore.QSettings = _TempQSettings

# for the test that guards the redirect
SETTINGS_DIR = _SETTINGS_DIR
REAL_QSETTINGS = _RealQSettings


@pytest.fixture(scope="session")
def qapp():
    """The one QApplication the widget tests share."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(["pytest"])
    yield app


@pytest.fixture
def real_series(qapp, tmp_path):
    """A real series opened from the checker fixture, on a copy.

    Nothing is stubbed: the palette, the sections and the object data are the
    ones the application would load.
    """
    import shutil

    from PyReconstruct.modules.datatypes.series import Series
    from PyReconstruct.modules.datatypes.series_data import SeriesData

    src = os.path.join(
        os.path.dirname(__file__), "..", "PyReconstruct", "assets",
        "checker", "files", "shapes1.jser",
    )
    assert os.path.exists(src), f"missing test fixture: {src}"

    fp = str(tmp_path / "shapes1.jser")
    shutil.copyfile(src, fp)

    series = Series.openJser(fp)
    data = SeriesData(series)
    data.refresh()
    series.data = data

    yield series

    series.close()
