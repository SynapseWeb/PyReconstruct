"""The autoseg *import* path must take its trace colors from the palette.

``tests/test_autoseg_palette.py`` proves the palette itself is legible against
grayscale, CVD-safe, and deterministic. It does not prove that autoseg import
actually *uses* it -- which is the whole point of the feature. This module
covers that seam: it drives ``conversions.importSection`` over a small real
zarr and asserts every trace it creates is colored from the approved list, at
exactly the color ``palette_color`` specifies.

Without this, reverting the one line in ``importSection`` back to the old
random ``colorize(id)`` leaves the rest of the suite green.
"""
import numpy as np
import pytest

zarr = pytest.importorskip("zarr")

from PyReconstruct.modules.backend.autoseg import conversions
from PyReconstruct.modules.backend.autoseg.palette import (
    DEFAULT_AUTOSEG_PALETTE,
    palette_color,
)


SNUM = 0
LABEL_GROUP = "labels_test"
# Ids placed in the label plane. Small distinct blobs, none of them 0
# (background), chosen to land on more than one palette entry.
LABEL_IDS = (1, 2, 3, 4, 5, 7, 11, 13)


class _SectionStub:
    """Collects the traces import would have added; no disk, no Qt."""

    def __init__(self):
        self.added = []
        self.saved = 0
        self.n = SNUM
        self.contours = {}

    def addTrace(self, trace, *args, **kwargs):
        self.added.append(trace)

    def save(self):
        self.saved += 1


class _GroupsStub:
    def __init__(self):
        self.adds = []

    def add(self, group, name):
        self.adds.append((group, name))


class _SeriesStub:
    """Minimal series: the two color options, a section, and object groups."""

    def __init__(self, palette=None, seed=0):
        self._palette = [] if palette is None else palette
        self._seed = seed
        self.section = _SectionStub()
        self.object_groups = _GroupsStub()

    def getOption(self, name, *args, **kwargs):
        if name == "autoseg_color_palette":
            return self._palette
        if name == "autoseg_color_seed":
            return self._seed
        raise KeyError(name)

    def loadSection(self, snum):
        return self.section


def _make_zarr(tmp_path):
    """A minimal neuroglancer-style zarr importSection can actually read."""
    root = zarr.open(str(tmp_path / "test.zarr"), mode="w")

    # One 64x64 label plane holding a small square per id.
    plane = np.zeros((1, 64, 64), dtype=np.uint32)
    for i, label_id in enumerate(LABEL_IDS):
        r = (i // 4) * 16 + 2
        c = (i % 4) * 16 + 2
        plane[0, r:r + 10, c:c + 10] = label_id

    labels = root.create_dataset(LABEL_GROUP, data=plane, overwrite=True)
    labels.attrs["resolution"] = [50, 4, 4]
    labels.attrs["offset"] = [0, 0, 0]

    raw = root.create_dataset(
        "raw", data=np.zeros((1, 64, 64), dtype=np.uint8), overwrite=True
    )
    raw.attrs["resolution"] = [50, 4, 4]
    raw.attrs["offset"] = [0, 0, 0]
    raw.attrs["window"] = [0.0, 0.0, 1.0, 1.0]
    raw.attrs["sections"] = [SNUM]
    raw.attrs["true_mag"] = 0.004
    # identity transform for the one section
    raw.attrs["alignment"] = {str(SNUM): [1, 0, 0, 0, 1, 0]}

    return root


def _run_import(tmp_path, series):
    data_zg = _make_zarr(tmp_path)
    conversions.importSection(data_zg, LABEL_GROUP, SNUM, series)
    assert series.section.added, "import produced no traces"
    return series.section.added


def test_import_colors_come_from_the_approved_list(tmp_path):
    """Every imported trace is colored from the whitelist -- the #96 ask."""
    series = _SeriesStub()
    traces = _run_import(tmp_path, series)

    whitelist = {tuple(c) for c in DEFAULT_AUTOSEG_PALETTE}
    for trace in traces:
        assert tuple(trace.color) in whitelist, (
            f"{trace.name} got off-palette color {tuple(trace.color)}"
        )


def test_import_color_matches_palette_color_for_the_label_id(tmp_path):
    """Import must assign exactly what palette_color specifies for that id."""
    series = _SeriesStub()
    traces = _run_import(tmp_path, series)

    seen = set()
    for trace in traces:
        label_id = int(trace.name.removeprefix("autoseg_"))
        seen.add(label_id)
        assert tuple(trace.color) == palette_color(label_id)
    assert seen, "no autoseg-named traces were created"


def test_import_never_assigns_a_near_gray_or_dark_color(tmp_path):
    """The legibility guarantee, asserted on real import output.

    A grayscale EM background camouflages exactly the achromatic and near-black
    colors, which is what the issue reported. Mirrors the palette-level bound.
    """
    series = _SeriesStub()
    traces = _run_import(tmp_path, series)

    for trace in traces:
        r, g, b = (int(c) for c in trace.color)
        assert max(r, g, b) - min(r, g, b) >= 60, (
            f"{trace.name} color {(r, g, b)} is too close to gray"
        )
        assert max(r, g, b) >= 100, (
            f"{trace.name} color {(r, g, b)} is too dark"
        )


def test_import_honors_a_custom_palette(tmp_path):
    """A user-adjusted palette (series option) drives import colors."""
    custom = [(11, 22, 33), (200, 100, 50)]
    series = _SeriesStub(palette=custom)
    traces = _run_import(tmp_path, series)

    custom_set = {tuple(c) for c in custom}
    for trace in traces:
        label_id = int(trace.name.removeprefix("autoseg_"))
        assert tuple(trace.color) in custom_set
        assert tuple(trace.color) == palette_color(label_id, custom, 0)


def test_import_honors_the_color_seed(tmp_path):
    """Changing the seed (what Shuffle colors does) changes import colors."""
    traces_a = _run_import(tmp_path / "a", _SeriesStub(seed=0))
    traces_b = _run_import(tmp_path / "b", _SeriesStub(seed=12345))

    by_id_a = {t.name: tuple(t.color) for t in traces_a}
    by_id_b = {t.name: tuple(t.color) for t in traces_b}
    assert by_id_a.keys() == by_id_b.keys()
    assert by_id_a != by_id_b, "seed change did not affect import colors"


def test_import_is_deterministic_across_runs(tmp_path):
    """Same ids + same seed -> same colors, so an object is one color
    on every section it appears on."""
    a = {t.name: tuple(t.color) for t in _run_import(tmp_path / "a", _SeriesStub())}
    b = {t.name: tuple(t.color) for t in _run_import(tmp_path / "b", _SeriesStub())}
    assert a == b
