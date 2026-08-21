"""Shared setup for the test suite.

Two things have to happen before any test module imports the application:

* Qt has to run without a display, so the widget tests work over ssh and in CI.

* QSettings has to be redirected. The application reads and writes real user
  settings through ``QSettings("KHLab", "PyReconstruct")``, and
  ``Series.getOption`` writes a default back whenever a key is missing, so a
  test that touched an option would edit the settings of whoever ran it. Every
  call site constructs ``QSettings(organization, application)``, so the redirect
  has to move where that two-argument form resolves to.

  ``setPath`` does move it, for both the native and the INI backend. Rebinding
  the name to a subclass does not: PySide6 resolves ``from PySide6.QtCore import
  QSettings`` without consulting the patched module attribute, so the
  application keeps constructing the real class while the patch looks like it
  took. ``test_settings_isolation.py`` asserts the redirect through the
  application's own modules rather than trusting either mechanism.

  ``setPath`` is documented as having no effect on the native backend on Windows
  and macOS (the registry, and a plist through ``cfprefsd``, which resolves the
  real user's domain whatever ``$HOME`` says). The INI default below is set for
  their sake, and the guard test fails there rather than letting a run edit real
  settings quietly.
"""

import os
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from PySide6.QtCore import QSettings

_SETTINGS_DIR = tempfile.mkdtemp(prefix="pyrecon-test-settings-")

QSettings.setDefaultFormat(QSettings.Format.IniFormat)
for _format in (QSettings.Format.NativeFormat, QSettings.Format.IniFormat):
    QSettings.setPath(_format, QSettings.Scope.UserScope, _SETTINGS_DIR)
    QSettings.setPath(_format, QSettings.Scope.SystemScope, _SETTINGS_DIR)

# for the test that guards the redirect
SETTINGS_DIR = _SETTINGS_DIR


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
    assert series is not None, f"could not open test fixture: {fp}"

    data = SeriesData(series)
    data.refresh()
    series.data = data

    yield series

    series.close()
