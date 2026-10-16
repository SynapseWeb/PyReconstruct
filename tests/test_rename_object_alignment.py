"""Renaming an object keeps the alignment it is measured in.

The data is a new series of eight sections with one circular object, traced
under a "default" alignment that rotates and scales each section, plus an
"alt" alignment rotated and scaled against it.
"""

import math

import pytest

from PyReconstruct.modules.datatypes.transform import Transform


OBJ = "dend"


@pytest.fixture
def series(qapp, tmp_path):
    from PyReconstruct.modules.datatypes.series import Series
    from PyReconstruct.modules.datatypes.trace import Trace

    images = [str(tmp_path / f"img{i}.tif") for i in range(8)]
    s = Series.new(images, "rename", 0.002, 0.05)

    for snum, section in s.enumerateSections(show_progress=False):
        a = math.radians(3 + snum)
        section.tforms["default"] = Transform([
            1.05 * math.cos(a), -1.05 * math.sin(a), 0.1 * snum,
            1.05 * math.sin(a), 1.05 * math.cos(a), -0.05 * snum,
        ])
        section.tforms["alt"] = section.tforms["default"] * Transform([0.9, -0.1, 0.2, 0.1, 0.9, -0.1])
        trace = Trace(OBJ, (255, 0, 0))
        trace.points = [
            (1 + 0.02 * snum + 0.1 * math.cos(t), 1 + 0.1 * math.sin(t))
            for t in (2 * math.pi * i / 12 for i in range(12))
        ]
        section.addTrace(trace)
        section.save()

    yield s
    s.close()


def centroids(data, name):
    return {s: [t.getCentroid() for t in traces] for s, traces in data["objects"][name].traces.items()}


def test_renaming_keeps_the_object_alignment(series):
    from PyReconstruct.modules.datatypes.series_data import SeriesData

    series.setAttr(OBJ, "alignment", "alt")
    series.data.refresh()
    before = centroids(series.data, OBJ)

    series.editObjectAttributes([OBJ], name="axon", sections=list(series.sections))

    assert series.getAttr("axon", "alignment") == "alt"
    # every section, the first included, is measured in the kept alignment
    fresh = SeriesData(series)
    fresh.refresh()
    assert centroids(series.data, "axon") == centroids(fresh, "axon") == before


def test_a_new_object_takes_the_series_alignment(series):
    from PyReconstruct.modules.datatypes.trace import Trace

    section = series.loadSection(0)
    trace = Trace("spine", (0, 255, 0))
    trace.points = [(2, 2), (2.2, 2), (2.2, 2.2)]
    section.addTrace(trace)
    section.save()

    assert series.getAttr("spine", "alignment") == series.alignment
