"""The Series ▸ Clean up operations: pixel dust, empty traces, duplicates.

Three scans and one guard, all against the real ``shapes1.jser`` fixture with
synthetic traces layered on top of it:

* ``Series.findPixelDustTraces`` reports small closed traces at or below an area
  threshold (um^2, measured the way the object and trace tables measure it).
* ``Series.findEmptyTraces`` reports traces with no geometry at all: no points, a
  closed trace enclosing zero area, an open trace of zero length.
* ``Series.deleteDuplicateTraces`` is the pre-existing same-name operation. It is
  covered here because ``Trace.getOverlapRatio`` used to divide by zero on
  degenerate traces and take the whole pass down with it.

Neither scan modifies anything: removal goes through
``Series.deleteMalformedTraces``, which re-finds each trace by a color plus
rounded-points signature, so one confirmation removes exactly the reviewed
traces and one undo puts them back.
"""

import pytest

from PyReconstruct.modules.datatypes.trace import Trace


def _template(section):
    """A real closed trace from the section, to copy display attributes from."""
    for cname in section.contours:
        for trace in section.contours[cname]:
            if trace.closed and len(trace.points) >= 3:
                return trace
    pytest.skip("no closed trace in the fixture section")


def _add(series, snum, name, points, closed=True):
    """Add a synthetic trace to a section and save it.

    Returns nothing: every assertion below re-reads the section through the
    scans, so a trace that did not survive ``addTrace`` shows up as a scan that
    finds nothing rather than as a stale object that looks fine.
    """
    section = series.loadSection(snum)
    template = _template(section)
    trace = Trace(name, template.color, closed=closed)
    trace.points = list(points)
    section.addTrace(trace, log_event=False)
    section.save()


def _square(cx, cy, half):
    """A closed square centered on (cx, cy)."""
    return [
        (cx - half, cy - half),
        (cx + half, cy - half),
        (cx + half, cy + half),
        (cx - half, cy + half),
    ]


def _first_section(series):
    return sorted(series.sections.keys())[0]


# --------------------------------------------------------------------------
# pixel dust
# --------------------------------------------------------------------------

def test_a_small_closed_trace_is_reported_as_pixel_dust(real_series):
    snum = _first_section(real_series)
    _add(real_series, snum, "dust", _square(20, 20, 0.01))

    found = real_series.findPixelDustTraces(0.01)

    assert [r["name"] for r in found] == ["dust"]
    assert found[0]["section"] == snum
    assert found[0]["area"] > 0


def test_a_large_trace_is_not_pixel_dust(real_series):
    snum = _first_section(real_series)
    _add(real_series, snum, "big", _square(20, 20, 2.0))

    found = real_series.findPixelDustTraces(0.01)

    assert "big" not in {r["name"] for r in found}


def test_the_area_threshold_includes_its_own_edge(real_series):
    """At or below, not below: a trace whose area equals the threshold goes."""
    snum = _first_section(real_series)
    _add(real_series, snum, "edge", _square(20, 20, 0.05))

    section = real_series.loadSection(snum)
    trace = section.contours["edge"][0]
    exact = real_series._traceArea(trace, section.tform)

    assert "edge" in {r["name"] for r in real_series.findPixelDustTraces(exact)}
    assert "edge" not in {
        r["name"] for r in real_series.findPixelDustTraces(exact * 0.99)
    }


def test_open_traces_are_never_pixel_dust(real_series):
    """An open trace encloses no area, so an area threshold cannot judge it."""
    snum = _first_section(real_series)
    _add(real_series, snum, "line", [(30, 30), (30.001, 30), (30.002, 30)],
         closed=False)

    found = real_series.findPixelDustTraces(1.0)

    assert "line" not in {r["name"] for r in found}


def test_zero_area_traces_are_left_to_the_empty_scan(real_series):
    """The two scans stay disjoint, so nothing is reported by both."""
    snum = _first_section(real_series)
    _add(real_series, snum, "flat", [(40, 40), (41, 40), (42, 40)])

    dust = {r["name"] for r in real_series.findPixelDustTraces(1.0)}
    empty = {r["name"] for r in real_series.findEmptyTraces()}

    assert "flat" not in dust
    assert "flat" in empty
    assert not (dust & empty)


def test_locked_objects_are_skipped_by_the_pixel_dust_scan(real_series):
    snum = _first_section(real_series)
    _add(real_series, snum, "dust", _square(20, 20, 0.01))
    real_series.setAttr("dust", "locked", True)

    assert real_series.findPixelDustTraces(0.01) == []
    assert "dust" in {
        r["name"] for r in real_series.findPixelDustTraces(
            0.01, include_locked=True
        )
    }


def test_the_pixel_dust_scan_modifies_nothing(real_series):
    """A scan is a report. Running it must leave every trace where it was."""
    snum = _first_section(real_series)
    _add(real_series, snum, "dust", _square(20, 20, 0.01))

    before = {
        n: [list(t.points) for t in real_series.loadSection(n).contours[c]]
        for n in sorted(real_series.sections.keys())
        for c in real_series.loadSection(n).contours
    }

    real_series.findPixelDustTraces(0.01)
    real_series.findEmptyTraces()

    after = {
        n: [list(t.points) for t in real_series.loadSection(n).contours[c]]
        for n in sorted(real_series.sections.keys())
        for c in real_series.loadSection(n).contours
    }
    assert before == after


def test_deleting_reviewed_records_removes_exactly_those_traces(real_series):
    snum = _first_section(real_series)
    _add(real_series, snum, "dust", _square(20, 20, 0.01))
    _add(real_series, snum, "keep", _square(25, 25, 0.01))

    found = real_series.findPixelDustTraces(0.01)
    chosen = [r for r in found if r["name"] == "dust"]
    assert len(chosen) == 1

    deleted = real_series.deleteMalformedTraces(
        chosen, message="Removing pixel-dust traces..."
    )

    assert [r["name"] for r in deleted] == ["dust"]
    contours = real_series.loadSection(snum).contours
    assert "dust" not in contours or len(contours["dust"]) == 0
    assert len(contours["keep"]) == 1


def test_a_record_still_matches_its_trace_after_a_save_and_reload(real_series):
    """The signature is color plus 7-decimal points, not object identity."""
    snum = _first_section(real_series)
    _add(real_series, snum, "dust", _square(20, 20, 0.01))

    record = real_series.findPixelDustTraces(0.01)[0]
    section = real_series.loadSection(snum)
    section.save()

    reloaded = real_series.loadSection(snum).contours["dust"][0]
    assert real_series._traceMatchesSignature(reloaded, record["match"])


# --------------------------------------------------------------------------
# empty traces
# --------------------------------------------------------------------------

def test_a_closed_trace_enclosing_zero_area_is_empty(real_series):
    snum = _first_section(real_series)
    _add(real_series, snum, "collinear", [(40, 40), (41, 40), (42, 40)])

    found = {r["name"]: r for r in real_series.findEmptyTraces()}

    assert "collinear" in found
    assert found["collinear"]["reason"] == "Closed trace enclosing zero area"


def test_an_open_trace_of_zero_length_is_empty(real_series):
    snum = _first_section(real_series)
    _add(real_series, snum, "coincident", [(50, 50), (50, 50), (50, 50)],
         closed=False)

    found = {r["name"]: r for r in real_series.findEmptyTraces()}

    assert "coincident" in found
    assert found["coincident"]["reason"] == "Open trace of zero length"


def test_real_traces_are_not_reported_as_empty(real_series):
    """The fixture's own shapes all enclose area, so none of them qualify."""
    found = {r["name"] for r in real_series.findEmptyTraces()}

    section = real_series.loadSection(_first_section(real_series))
    real_names = {
        c for c in section.contours
        if any(len(t.points) >= 3 for t in section.contours[c])
    }
    assert not (found & real_names)


def test_locked_objects_are_skipped_by_the_empty_scan(real_series):
    snum = _first_section(real_series)
    _add(real_series, snum, "collinear", [(40, 40), (41, 40), (42, 40)])
    real_series.setAttr("collinear", "locked", True)

    assert "collinear" not in {r["name"] for r in real_series.findEmptyTraces()}
    assert "collinear" in {
        r["name"] for r in real_series.findEmptyTraces(include_locked=True)
    }


def test_empty_traces_are_removed_by_the_shared_delete_path(real_series):
    snum = _first_section(real_series)
    _add(real_series, snum, "collinear", [(40, 40), (41, 40), (42, 40)])

    records = [
        r for r in real_series.findEmptyTraces() if r["name"] == "collinear"
    ]
    deleted = real_series.deleteMalformedTraces(
        records, message="Removing empty traces..."
    )

    assert [r["name"] for r in deleted] == ["collinear"]
    contours = real_series.loadSection(snum).contours
    assert "collinear" not in contours or len(contours["collinear"]) == 0


# --------------------------------------------------------------------------
# the zero-area guard in getOverlapRatio
# --------------------------------------------------------------------------

def _trace(points, closed=True, name="t"):
    t = Trace(name, (255, 0, 0), closed=closed)
    t.points = list(points)
    return t


@pytest.mark.parametrize("a, b", [
    # both traces confined to one horizontal line
    ([(0, 0), (1, 0), (2, 0)], [(0, 0), (3, 0), (4, 0)]),
    # both confined to one vertical line
    ([(0, 0), (0, 1), (0, 2)], [(0, 0), (0, 3), (0, 4)]),
    # a single point and a run passing through it
    ([(5, 5)], [(5, 5), (5, 6), (5, 7)]),
])
def test_a_collapsed_bounding_box_answers_zero_rather_than_raising(a, b):
    """The combined box has no area, so there is no area to compare.

    ``getOverlapRatio`` picks its raster scale from the combined bounding box
    area. Two traces on one line collapse that box, and the scale factor used to
    divide by it.
    """
    assert _trace(a).getOverlapRatio(_trace(b)) == 0
    assert _trace(b).getOverlapRatio(_trace(a)) == 0


@pytest.mark.parametrize("threshold", [0, 0.5, 0.95, 1])
def test_overlaps_answers_for_collinear_traces_at_every_threshold(threshold):
    a = _trace([(0, 0), (1, 0), (2, 0)])
    b = _trace([(0, 0), (3, 0), (4, 0)])

    assert a.overlaps(b, threshold=threshold) is False


def test_identical_degenerate_traces_are_still_duplicates():
    """Settled on points before a ratio is ever asked for, so the guard is safe."""
    a = _trace([(0, 0), (1, 0), (2, 0)])
    b = _trace([(0, 0), (1, 0), (2, 0)])

    assert a.overlaps(b, threshold=0.95) is True


def test_the_duplicate_pass_survives_a_degenerate_trace(real_series):
    """The crash this guards: one such pair ended the whole pass.

    Two collinear traces under one name used to raise ``ZeroDivisionError`` out
    of ``getOverlapRatio``, through ``overlaps``, and out of
    ``deleteDuplicateTraces``, so no section after the first offender was
    scanned and nothing was cleaned up.
    """
    snum = _first_section(real_series)
    _add(real_series, snum, "flat", [(60, 60), (61, 60), (62, 60)])
    _add(real_series, snum, "flat", [(60, 60), (63, 60), (64, 60)])

    real_series.deleteDuplicateTraces(0.95, include_locked=True)

    # both survive: they are not duplicates of each other
    assert len(real_series.loadSection(snum).contours["flat"]) == 2


def test_identical_degenerate_duplicates_are_still_collapsed(real_series):
    snum = _first_section(real_series)
    _add(real_series, snum, "flat", [(60, 60), (61, 60), (62, 60)])
    _add(real_series, snum, "flat", [(60, 60), (61, 60), (62, 60)])

    real_series.deleteDuplicateTraces(0.95, include_locked=True)

    assert len(real_series.loadSection(snum).contours["flat"]) == 1


# --------------------------------------------------------------------------
# the menu
# --------------------------------------------------------------------------

class _Stub:
    """Answers any attribute with another stub, so the menu tree can be built.

    ``return_series_menu`` reads a handler off the window for every row. The
    tree is data, so building it against a stub is enough to assert what rows
    exist and which attribute name each one points at.
    """

    def __getattr__(self, name):
        child = _Stub()
        object.__setattr__(self, name, child)
        return child

    def __call__(self, *args, **kwargs):
        return None


def _menu_rows(tree, path=()):
    if isinstance(tree, dict):
        for opt in tree.get("opts", []):
            yield from _menu_rows(opt, path + (tree.get("text", ""),))
    elif isinstance(tree, tuple):
        yield path, tree


@pytest.fixture
def series_menu(qapp):
    from PyReconstruct.modules.gui.main.menubar import return_series_menu

    return list(_menu_rows(return_series_menu(_Stub())))


def test_the_clean_up_submenu_holds_the_four_operations(series_menu):
    rows = [r for p, r in series_menu if "Clean up" in p]

    assert [r[0] for r in rows] == [
        "removeduplicates_act",
        "finddiffnamedduplicates_act",
        "removepixeldust_act",
        "removeempty_act",
    ]


def test_each_clean_up_row_is_wired_to_its_own_handler(series_menu):
    """The rows must not share a slot, which a copy-paste error would produce."""
    from PyReconstruct.modules.gui.main.main_window import MainWindow

    expected = {
        "removeduplicates_act": "deleteDuplicateTraces",
        "finddiffnamedduplicates_act": "findDifferentlyNamedDuplicates",
        "removepixeldust_act": "removePixelDustTraces",
        "removeempty_act": "removeEmptyTraces",
    }
    rows = {r[0]: r for p, r in series_menu if "Clean up" in p}

    for act, handler in expected.items():
        assert act in rows
        assert hasattr(MainWindow, handler), f"{handler} missing on MainWindow"


def test_removing_duplicates_is_reachable_only_from_the_clean_up_submenu(
    series_menu
):
    """It moved into the submenu rather than being duplicated into it."""
    rows = [(p, r) for p, r in series_menu if r[0] == "removeduplicates_act"]

    assert len(rows) == 1
    assert "Clean up" in rows[0][0]
