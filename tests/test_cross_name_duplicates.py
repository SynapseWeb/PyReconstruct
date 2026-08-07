"""``Series.findDifferentlyNamedDuplicates``: one shape traced under two names.

``Series.deleteDuplicateTraces`` draws both traces of a candidate pair out of a
single ``section.contours[cname]``, and contours are keyed by trace name, so two
people tracing the same structure under two names produce a duplicate it never
compares. Nothing in the comparison itself reads a name: ``Trace.overlaps`` is
purely geometric. This is therefore a new scan across names rather than a change
to the overlap test, and the tests below hold both halves of that: the new scan
finds cross-name pairs, and the existing same-name operation still behaves
exactly as it did.

The scan reports and never modifies. Which of two names is the right one is a
question about the data rather than about geometry, so the operation does not
choose.

``_duplicatePairs`` is where the cost lives, since comparing across names means
comparing every trace on a section against every other. Two filters keep the
number of measured overlap ratios proportional to the trace count rather than to
its square, and ``test_the_filtered_scan_agrees_with_brute_force`` is the test
that matters most here: the filters are only allowed to be faster, never to
change an answer.
"""

import pytest

from PyReconstruct.modules.datatypes.trace import Trace


def _trace(points, closed=True, name="t"):
    t = Trace(name, (255, 0, 0), closed=closed)
    t.points = list(points)
    return t


def _template(section):
    for cname in section.contours:
        for trace in section.contours[cname]:
            if trace.closed and len(trace.points) >= 3:
                return trace
    pytest.skip("no closed trace in the fixture section")


def _add(series, snum, name, points, closed=True):
    section = series.loadSection(snum)
    template = _template(section)
    trace = Trace(name, template.color, closed=closed)
    trace.points = list(points)
    section.addTrace(trace, log_event=False)
    section.save()


def _square(cx, cy, half):
    return [
        (cx - half, cy - half),
        (cx + half, cy - half),
        (cx + half, cy + half),
        (cx - half, cy + half),
    ]


def _first_section(series):
    return sorted(series.sections.keys())[0]


def _pairs(records):
    """The reported pairs as name sets, so row order never matters."""
    return {frozenset((r["name"], r["other_name"])) for r in records}


# --------------------------------------------------------------------------
# what the scan finds
# --------------------------------------------------------------------------

def test_one_shape_under_two_names_is_found(real_series):
    snum = _first_section(real_series)
    shape = _square(20, 20, 1.0)
    _add(real_series, snum, "dendrite", shape)
    _add(real_series, snum, "d01", shape)

    found = real_series.findDifferentlyNamedDuplicates(0.95)

    assert frozenset(("dendrite", "d01")) in _pairs(found)


def test_a_point_for_point_match_is_reported_as_such(real_series):
    snum = _first_section(real_series)
    shape = _square(20, 20, 1.0)
    _add(real_series, snum, "dendrite", shape)
    _add(real_series, snum, "d01", shape)

    record = real_series.findDifferentlyNamedDuplicates(0.95)[0]

    assert record["ratio"] == 1.0
    assert "Point-for-point match" in record["reason"]


def test_nearly_identical_shapes_are_found_by_their_overlap_ratio(real_series):
    """Not the same points, so the ratio has to do the work.

    The offset has to clear ``POINTS_MATCH_TOLERANCE``, or ``pointsMatch``
    settles the pair first and the ratio is never measured.
    """
    snum = _first_section(real_series)
    offset = Trace.POINTS_MATCH_TOLERANCE * 2
    _add(real_series, snum, "dendrite", _square(20, 20, 1.0))
    _add(real_series, snum, "d01", _square(20 + offset, 20 + offset, 1.0))

    found = real_series.findDifferentlyNamedDuplicates(0.95)
    record = [
        r for r in found
        if {r["name"], r["other_name"]} == {"dendrite", "d01"}
    ]

    assert len(record) == 1
    assert record[0]["ratio"] < 1.0
    assert "Overlap" in record[0]["reason"]


def test_different_shapes_are_not_reported(real_series):
    snum = _first_section(real_series)
    _add(real_series, snum, "one", _square(20, 20, 1.0))
    _add(real_series, snum, "two", _square(40, 40, 1.0))

    found = _pairs(real_series.findDifferentlyNamedDuplicates(0.95))

    assert frozenset(("one", "two")) not in found


def test_merely_touching_neighbors_are_not_reported(real_series):
    """Two autosegmented neighbors share a boundary without being duplicates."""
    snum = _first_section(real_series)
    _add(real_series, snum, "left", _square(20, 20, 1.0))
    _add(real_series, snum, "right", _square(21.9, 20, 1.0))

    found = _pairs(real_series.findDifferentlyNamedDuplicates(0.95))

    assert frozenset(("left", "right")) not in found


def test_the_threshold_is_honored(real_series):
    snum = _first_section(real_series)
    _add(real_series, snum, "a", _square(20, 20, 1.0))
    _add(real_series, snum, "b", _square(20.5, 20, 1.0))

    pair = frozenset(("a", "b"))
    strict = _pairs(real_series.findDifferentlyNamedDuplicates(0.95))
    loose = _pairs(real_series.findDifferentlyNamedDuplicates(0.1))

    assert pair not in strict
    assert pair in loose


def test_open_and_closed_traces_never_pair(real_series):
    """As in Trace.overlaps, which refuses the comparison outright."""
    snum = _first_section(real_series)
    shape = _square(20, 20, 1.0)
    _add(real_series, snum, "closed_one", shape, closed=True)
    _add(real_series, snum, "open_one", shape, closed=False)

    found = _pairs(real_series.findDifferentlyNamedDuplicates(0.1))

    assert frozenset(("closed_one", "open_one")) not in found


def test_same_name_duplicates_are_not_this_operations_business(real_series):
    """They are unambiguous, and deleteDuplicateTraces already collapses them."""
    snum = _first_section(real_series)
    shape = _square(20, 20, 1.0)
    _add(real_series, snum, "twice", shape)
    _add(real_series, snum, "twice", shape)

    found = real_series.findDifferentlyNamedDuplicates(0.95)

    assert all(r["name"] != r["other_name"] for r in found)
    assert frozenset(("twice",)) not in _pairs(found)


def test_the_same_name_operation_still_leaves_cross_name_pairs_alone(real_series):
    """The existing path is untouched, which is what makes the new one needed."""
    snum = _first_section(real_series)
    shape = _square(20, 20, 1.0)
    _add(real_series, snum, "dendrite", shape)
    _add(real_series, snum, "d01", shape)

    real_series.deleteDuplicateTraces(0.95, include_locked=True)

    contours = real_series.loadSection(snum).contours
    assert len(contours["dendrite"]) == 1
    assert len(contours["d01"]) == 1


def test_locked_objects_are_left_out(real_series):
    snum = _first_section(real_series)
    shape = _square(20, 20, 1.0)
    _add(real_series, snum, "dendrite", shape)
    _add(real_series, snum, "d01", shape)
    real_series.setAttr("d01", "locked", True)

    pair = frozenset(("dendrite", "d01"))
    assert pair not in _pairs(real_series.findDifferentlyNamedDuplicates(0.95))
    assert pair in _pairs(
        real_series.findDifferentlyNamedDuplicates(0.95, include_locked=True)
    )


def test_zero_area_traces_are_settled_on_points_and_do_not_raise(real_series):
    """Both filters reason about area, so a shape with none must bypass them."""
    snum = _first_section(real_series)
    line = [(60, 60), (61, 60), (62, 60)]
    _add(real_series, snum, "flat_a", line)
    _add(real_series, snum, "flat_b", line)

    found = _pairs(real_series.findDifferentlyNamedDuplicates(0.95))

    assert frozenset(("flat_a", "flat_b")) in found


# --------------------------------------------------------------------------
# the record, and that nothing is modified
# --------------------------------------------------------------------------

def test_the_record_describes_both_traces_of_the_pair(real_series):
    snum = _first_section(real_series)
    shape = _square(20, 20, 1.0)
    _add(real_series, snum, "dendrite", shape)
    _add(real_series, snum, "d01", shape)

    record = real_series.findDifferentlyNamedDuplicates(0.95)[0]

    for key in (
        "name", "other_name", "section", "ratio", "area", "other_area",
        "points", "location", "other_location", "other_index", "other_match",
    ):
        assert key in record, f"record is missing {key}"
    assert record["area"] > 0
    assert record["other_area"] > 0


@pytest.mark.parametrize("threshold", [0, 0.1, 0.5, 0.95, 1])
def test_the_scan_modifies_nothing_at_any_threshold(real_series, threshold):
    snum = _first_section(real_series)
    shape = _square(20, 20, 1.0)
    _add(real_series, snum, "dendrite", shape)
    _add(real_series, snum, "d01", shape)

    def snapshot():
        out = {}
        for n in sorted(real_series.sections.keys()):
            section = real_series.loadSection(n)
            out[n] = {
                c: [list(t.points) for t in section.contours[c]]
                for c in section.contours
            }
        return out

    before = snapshot()
    real_series.findDifferentlyNamedDuplicates(threshold)

    assert snapshot() == before


def test_the_pair_order_does_not_depend_on_contour_walk_order(real_series):
    """A stable (name, index) order, so the report is reproducible."""
    snum = _first_section(real_series)
    shape = _square(20, 20, 1.0)
    _add(real_series, snum, "zzz", shape)
    _add(real_series, snum, "aaa", shape)

    record = [
        r for r in real_series.findDifferentlyNamedDuplicates(0.95)
        if {r["name"], r["other_name"]} == {"aaa", "zzz"}
    ][0]

    assert record["name"] == "aaa"
    assert record["other_name"] == "zzz"


# --------------------------------------------------------------------------
# the filters are only allowed to be faster
# --------------------------------------------------------------------------

@pytest.mark.parametrize("threshold", [0.1, 0.5, 0.8, 0.95, 1])
def test_the_filtered_scan_agrees_with_brute_force(threshold):
    """Every pair the filters skip is a pair Trace.overlaps would have refused.

    Brute force is every cross-name pair straight into ``Trace.overlaps``, which
    is what a literal rewrite of the same-name loop gives. The sweep and the
    ratio ceiling must reach the same set.
    """
    from PyReconstruct.modules.datatypes.series import Series
    from PyReconstruct.modules.calc import area

    traces = []
    # a crowd with real overlaps, near misses, and plenty of disjoint pairs
    for i in range(12):
        cx = i * 1.7
        traces.append((f"obj{i}", _square(cx, 0, 1.0)))
        traces.append((f"copy{i}", _square(cx, 0, 1.0)))          # duplicate
        traces.append((f"near{i}", _square(cx + 0.3, 0, 1.0)))    # partial
        traces.append((f"far{i}", _square(cx, 40 + i, 1.0)))      # disjoint

    entries = []
    for index, (name, points) in enumerate(traces):
        t = _trace(points, name=name)
        xmin, ymin, xmax, ymax = t.getBounds()
        entries.append((xmin, ymin, xmax, ymax, abs(area(points)), name, 0, t))

    filtered = {
        frozenset((a[5], b[5]))
        for a, b, _r, _pm in Series._duplicatePairs(entries, threshold)
    }

    brute = set()
    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            a, b = entries[i], entries[j]
            if a[5] == b[5]:
                continue
            if a[7].overlaps(b[7], threshold=threshold):
                brute.add(frozenset((a[5], b[5])))

    assert filtered == brute


def test_a_pair_matching_within_tolerance_with_disjoint_boxes_is_found():
    """The bounding-box tests have to be slack by the point-match tolerance.

    ``Trace.pointsMatch`` calls two points the same within
    ``POINTS_MATCH_TOLERANCE`` per axis, so two traces can match point for point
    while their bounding boxes do not touch. A strict box test drops exactly the
    pairs the comparison would have called duplicates, and real data has them.
    """
    from PyReconstruct.modules.datatypes.series import Series
    from PyReconstruct.modules.calc import area

    offset = Trace.POINTS_MATCH_TOLERANCE * 0.6
    a_points = [(0, 0), (1, 0)]
    b_points = [(0, offset), (1, offset)]

    entries = []
    for name, points in (("a", a_points), ("b", b_points)):
        t = _trace(points, closed=False, name=name)
        xmin, ymin, xmax, ymax = t.getBounds()
        entries.append((xmin, ymin, xmax, ymax, abs(area(points)), name, 0, t))

    pairs = list(Series._duplicatePairs(entries, 0.95))

    assert len(pairs) == 1
    assert pairs[0][3] is True  # settled on points
    assert _trace(a_points, closed=False).overlaps(
        _trace(b_points, closed=False), threshold=0.95
    ) is True


# --------------------------------------------------------------------------
# the two halves extracted out of overlaps()
# --------------------------------------------------------------------------

def test_points_match_carries_the_tolerance():
    tol = Trace.POINTS_MATCH_TOLERANCE
    a = _trace([(0, 0), (1, 0), (1, 1)])

    assert a.pointsMatch(_trace([(0, tol * 0.5), (1, 0), (1, 1)])) is True
    assert a.pointsMatch(_trace([(0, tol * 2), (1, 0), (1, 1)])) is False
    assert a.pointsMatch(_trace([(0, 0), (1, 0)])) is False


@pytest.mark.parametrize("ratio, threshold, expected", [
    (0.96, 0.95, True),
    (0.95, 0.95, False),   # exclusive
    (1.0, 1, True),
    (0.999, 1, False),     # a threshold of 1 demands exactly 1
])
def test_ratio_is_overlap_matches_the_threshold_semantics(
    ratio, threshold, expected
):
    assert Trace.ratioIsOverlap(ratio, threshold) is expected


def test_overlaps_still_answers_with_a_plain_bool():
    """getOverlapRatio divides two numpy sums, so the verdict must be coerced."""
    a = _trace(_square(0, 0, 1.0))
    b = _trace(_square(0.1, 0, 1.0))

    for threshold in (0.1, 0.95, 1):
        verdict = a.overlaps(b, threshold=threshold)
        assert type(verdict) is bool, f"{threshold} gave {type(verdict)}"
