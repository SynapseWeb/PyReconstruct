"""The autoseg color options must be declared so the options dialog and the
converter can read/write them (seed = the re-roll escape hatch)."""

from PyReconstruct.modules.datatypes.default_settings import default_settings


def test_autoseg_color_seed_is_declared_as_int():
    assert "autoseg_color_seed" in default_settings
    assert isinstance(default_settings["autoseg_color_seed"], int)


def test_autoseg_color_palette_is_declared_as_list():
    # empty by default -> converter falls back to the built-in curated palette
    assert "autoseg_color_palette" in default_settings
    assert isinstance(default_settings["autoseg_color_palette"], list)
    assert default_settings["autoseg_color_palette"] == []
