"""Unit tests for Ztrace (datatypes/ztrace.py) and Log/LogSet/LogSetPair
(datatypes/log.py).

Expected values are derived by hand from the source, not echoed back from the
functions under test:

  * Ztrace.overlaps uses a strict ``> 1e-6`` tolerance on x/y and an exact match
    on the section index; a length mismatch short-circuits to False. Color is
    never consulted.
  * Ztrace.copy does ``self.points.copy()`` -- a *new* list (so append/in-place
    magScale on the copy must not touch the original) holding the same immutable
    point tuples.
  * Ztrace.getDistance sums distance3D over consecutive transformed points, with
    z taken from series.getZValues(); with an identity transform the geometry is
    a plain 3D Euclidean sum we compute directly.
  * Ztrace.smooth maps points to field space, applies rolling_average(..,
    edge_mode="padded"), then maps back with the inverted transform. Because the
    transform is linear and invertible, an identity and a uniform-scale transform
    must yield the *same* base-coordinate result -- a real round-trip check, not
    a tautology. The padded moving-average values are computed by hand.
  * Ztrace.magScale multiplies x,y by new_mag/prev_mag for points on the named
    section only.
  * Log.__str__/fromStr round-trip; ints, lists and None for ``section``; ranges
    rendered "a" when a==b else "a-b"; events containing ", " are rejoined.
  * Log.containsSection is inclusive on both ends (range(n1, n2+1)) and False for
    a None range.
  * LogSet.addLog dynamic merging, the Create/Delete special cases, plus
    addExistingLog / fromList round-trip / removeCuration / getLastIndex.
  * LogSetPair divergence index and getModifiedSinceDiverge.

trimSectionRange is covered elsewhere and is intentionally not retested here.

Headless: Transform is a real dependency (QTransform under the hood) and works
under QT_QPA_PLATFORM=offscreen; Log uses getDateTime (QSettings), also headless
safe. No network or file I/O (LogSet.exportLogHistory, which needs real CSV
files, is not exercised).
"""
import math
import types

import pytest

from PyReconstruct.modules.datatypes.ztrace import Ztrace
from PyReconstruct.modules.datatypes.transform import Transform
from PyReconstruct.modules.datatypes.log import Log, LogSet, LogSetPair


# --------------------------------------------------------------------------- #
# Ztrace
# --------------------------------------------------------------------------- #

IDENTITY = [1, 0, 0, 0, 1, 0]
SCALE2 = [2, 0, 0, 0, 2, 0]  # uniform scale-by-2 about the origin


def _make_series(tform_list, zvals, align="align", ztrace_align="align"):
    """Duck-typed Series stub sufficient for getDistance and smooth.

    ``zvals`` maps section number -> z value; every section gets the same
    Transform under key ``align``. ``getAttr`` returns ``ztrace_align`` for the
    per-ztrace alignment lookup (set to None to exercise getDistance's fallback
    to ``series.alignment``).
    """
    tform = Transform(tform_list)
    sections = {s: {"tforms": {align: tform}} for s in zvals}
    stub = types.SimpleNamespace(data={"sections": sections}, alignment=align)
    stub.getZValues = lambda: dict(zvals)
    stub.getAttr = lambda name, key, ztrace=False: ztrace_align
    return stub


def test_copy_returns_new_list_with_equal_contents():
    zt = Ztrace("z", [255, 0, 0], [(0.0, 0.0, 0), (1.0, 1.0, 1)])
    c = zt.copy()

    assert c is not zt
    assert c.name == zt.name
    assert c.color == zt.color
    assert c.points == zt.points
    # the list itself must be a distinct object (shallow copy)
    assert c.points is not zt.points


def test_copy_append_does_not_affect_original():
    zt = Ztrace("z", [1, 2, 3], [(0.0, 0.0, 0), (1.0, 1.0, 1)])
    c = zt.copy()

    c.points.append((2.0, 2.0, 2))

    assert zt.points == [(0.0, 0.0, 0), (1.0, 1.0, 1)]
    assert c.points == [(0.0, 0.0, 0), (1.0, 1.0, 1), (2.0, 2.0, 2)]


def test_copy_isolates_in_place_magscale():
    # magScale mutates the points list in place; the original must be untouched.
    zt = Ztrace("z", [1, 2, 3], [(3.0, 4.0, 0), (5.0, 6.0, 1)])
    c = zt.copy()

    c.magScale(0, prev_mag=1.0, new_mag=2.0)

    assert c.points == [(6.0, 8.0, 0), (5.0, 6.0, 1)]
    assert zt.points == [(3.0, 4.0, 0), (5.0, 6.0, 1)]


def test_overlaps_identical_points_true():
    a = Ztrace("a", [1, 1, 1], [(0.0, 0.0, 0), (1.5, -2.5, 3)])
    b = Ztrace("b", [9, 9, 9], [(0.0, 0.0, 0), (1.5, -2.5, 3)])
    # color differs but is ignored
    assert a.overlaps(b) is True
    assert b.overlaps(a) is True


def test_overlaps_within_tolerance_true():
    # 5e-7 difference is below the strict > 1e-6 threshold -> still overlapping
    a = Ztrace("a", [1, 1, 1], [(0.0, 0.0, 0), (1.0, 1.0, 1)])
    b = Ztrace("b", [1, 1, 1], [(0.0000005, -0.0000005, 0), (1.0, 1.0, 1)])
    assert a.overlaps(b) is True


def test_overlaps_outside_tolerance_false():
    # 2e-6 difference exceeds the threshold
    a = Ztrace("a", [1, 1, 1], [(0.0, 0.0, 0)])
    b = Ztrace("b", [1, 1, 1], [(0.000002, 0.0, 0)])
    assert a.overlaps(b) is False


def test_overlaps_section_mismatch_false():
    a = Ztrace("a", [1, 1, 1], [(0.0, 0.0, 0), (1.0, 1.0, 1)])
    b = Ztrace("b", [1, 1, 1], [(0.0, 0.0, 0), (1.0, 1.0, 2)])
    assert a.overlaps(b) is False


def test_overlaps_length_mismatch_false():
    a = Ztrace("a", [1, 1, 1], [(0.0, 0.0, 0), (1.0, 1.0, 1)])
    b = Ztrace("b", [1, 1, 1], [(0.0, 0.0, 0)])
    assert a.overlaps(b) is False
    assert b.overlaps(a) is False


def test_get_start_and_end():
    zt = Ztrace("z", [1, 1, 1], [(0.0, 0.0, 5), (1.0, 1.0, 2), (2.0, 2.0, 9)])
    assert zt.getStart() == 2
    assert zt.getEnd() == 9


@pytest.mark.parametrize(
    "section, prev_mag, new_mag, expected",
    [
        # scale section 0 up by 2x; section 1 untouched
        (0, 1.0, 2.0, [(6.0, 8.0, 0), (5.0, 6.0, 1)]),
        # scale section 1 down by half; section 0 untouched
        (1, 2.0, 1.0, [(3.0, 4.0, 0), (2.5, 3.0, 1)]),
        # a section not present in the trace -> no change at all
        (7, 1.0, 10.0, [(3.0, 4.0, 0), (5.0, 6.0, 1)]),
    ],
)
def test_magscale_scales_only_matching_section(section, prev_mag, new_mag, expected):
    zt = Ztrace("z", [1, 1, 1], [(3.0, 4.0, 0), (5.0, 6.0, 1)])
    zt.magScale(section, prev_mag=prev_mag, new_mag=new_mag)
    assert zt.points == pytest.approx(expected)


def test_get_distance_identity_transform():
    # points (0,0) @z0 and (3,4) @z50 with identity tform -> 3D distance
    zt = Ztrace("z", [1, 1, 1], [(0.0, 0.0, 0), (3.0, 4.0, 1)])
    series = _make_series(IDENTITY, {0: 0.0, 1: 50.0})

    expected = math.sqrt(3 ** 2 + 4 ** 2 + 50 ** 2)
    assert zt.getDistance(series) == pytest.approx(expected)


def test_get_distance_sums_multiple_segments():
    # three collinear-in-z points: (0,0,z0)->(0,0,z3)->(0,0,z7): dz=3 then dz=4
    zt = Ztrace("z", [1, 1, 1], [(0.0, 0.0, 0), (0.0, 0.0, 1), (0.0, 0.0, 2)])
    series = _make_series(IDENTITY, {0: 0.0, 1: 3.0, 2: 7.0})

    assert zt.getDistance(series) == pytest.approx(3.0 + 4.0)


def test_get_distance_alignment_fallback_to_series_alignment():
    # getAttr returns None -> code falls back to series.alignment ("align").
    zt = Ztrace("z", [1, 1, 1], [(0.0, 0.0, 0), (6.0, 8.0, 1)])
    series = _make_series(IDENTITY, {0: 0.0, 1: 0.0}, ztrace_align=None)

    # purely planar (same z): distance is sqrt(6^2 + 8^2) = 10
    assert zt.getDistance(series) == pytest.approx(10.0)


def test_smooth_padded_moving_average_identity():
    # window=2 -> half=1, taps at i-1,i,i+1 clamped to [0, n-1].
    # field pts == base pts (identity). Hand-computed averages:
    #   i0: idx 0,0,1 -> x=(0+0+3)/3=1,   y=(0+0+9)/3=3
    #   i1: idx 0,1,2 -> x=(0+3+6)/3=3,   y=(0+9+0)/3=3
    #   i2: idx 1,2,2 -> x=(3+6+6)/3=5,   y=(9+0+0)/3=3
    zt = Ztrace("z", [1, 1, 1], [(0.0, 0.0, 0), (3.0, 9.0, 1), (6.0, 0.0, 2)])
    series = _make_series(IDENTITY, {0: 0.0, 1: 1.0, 2: 2.0})

    zt.smooth(series, smooth=2)

    assert zt.points == [(1.0, 3.0, 0), (3.0, 3.0, 1), (5.0, 3.0, 2)]


def test_smooth_window_one_is_identity():
    # window=1 -> half=0, single tap per index -> points unchanged (and section
    # numbers preserved in order).
    pts = [(0.5, -1.5, 4), (2.25, 3.75, 5)]
    zt = Ztrace("z", [1, 1, 1], list(pts))
    series = _make_series(IDENTITY, {4: 0.0, 5: 1.0})

    zt.smooth(series, smooth=1)

    assert zt.points == pytest.approx(pts)


def test_smooth_is_transform_invariant_for_uniform_scale():
    # The map -> average -> inverse-map pipeline is linear, so a uniform-scale
    # transform must produce the SAME base coordinates as identity. This proves
    # smooth genuinely de-transforms (a stub that forgot the inverse would not
    # match the identity result).
    base = [(0.0, 0.0, 0), (3.0, 9.0, 1), (6.0, 0.0, 2)]

    zt_id = Ztrace("z", [1, 1, 1], list(base))
    zt_id.smooth(_make_series(IDENTITY, {0: 0.0, 1: 1.0, 2: 2.0}), smooth=2)

    zt_sc = Ztrace("z", [1, 1, 1], list(base))
    zt_sc.smooth(_make_series(SCALE2, {0: 0.0, 1: 1.0, 2: 2.0}), smooth=2)

    assert zt_sc.points == pytest.approx(zt_id.points)


# --------------------------------------------------------------------------- #
# Log
# --------------------------------------------------------------------------- #

def _log(section, event="Modified", obj_name="obj1", user="alice",
         date="26-06-29", time="1200"):
    return Log(date, time, user, obj_name, section, event)


def test_log_init_int_section_becomes_single_range():
    assert _log(5).section_ranges == [(5, 5)]


def test_log_init_list_section_kept():
    assert _log([(1, 3), (7, 9)]).section_ranges == [(1, 3), (7, 9)]


def test_log_init_none_section():
    assert _log(None).section_ranges is None


def test_log_str_single_int_section():
    s = str(_log(5))
    assert s == "26-06-29, 1200, alice, obj1, 5, Modified"


def test_log_str_collapses_equal_range_endpoints():
    # a single-element range (5,5) renders as "5", not "5-5"
    assert str(_log([(5, 5)])) == "26-06-29, 1200, alice, obj1, 5, Modified"


def test_log_str_multi_range_space_joined():
    s = str(_log([(1, 3), (7, 9)]))
    assert s == "26-06-29, 1200, alice, obj1, 1-3 7-9, Modified"


def test_log_str_none_obj_and_section_render_dash():
    s = str(Log("26-06-29", "1200", "alice", None, None, "static event"))
    assert s == "26-06-29, 1200, alice, -, -, static event"


@pytest.mark.parametrize(
    "section",
    [
        5,                      # int -> single range
        [(1, 3), (7, 9)],       # multi-range list
        [(2, 2)],               # single collapsed range
        None,                   # no section
    ],
)
def test_log_str_fromstr_roundtrip(section):
    original = _log(section)
    rebuilt = Log.fromStr(str(original))

    assert str(rebuilt) == str(original)
    assert rebuilt == original
    # field-level checks
    assert rebuilt.date == original.date
    assert rebuilt.time == original.time
    assert rebuilt.user == original.user
    assert rebuilt.obj_name == original.obj_name
    assert rebuilt.section_ranges == original.section_ranges
    assert rebuilt.event == original.event


def test_log_fromstr_dash_obj_becomes_none():
    log = Log.fromStr("26-06-29, 1200, alice, -, 5, Modified")
    assert log.obj_name is None
    assert log.section_ranges == [(5, 5)]


def test_log_fromstr_dash_section_becomes_none():
    log = Log.fromStr("26-06-29, 1200, alice, obj1, -, Modified")
    assert log.section_ranges is None
    assert log.obj_name == "obj1"


def test_log_roundtrip_event_with_commas():
    # event itself contains ", " separators; fromStr must rejoin them.
    original = _log(5, event="merged a, b, and c")
    rebuilt = Log.fromStr(str(original))

    assert rebuilt.event == "merged a, b, and c"
    assert rebuilt == original


def test_log_eq_same_fields_equal():
    assert _log(5) == _log(5)


def test_log_eq_int_and_single_range_equal():
    # int 5 and [(5,5)] stringify identically -> __eq__ True
    assert _log(5) == _log([(5, 5)])


def test_log_eq_differing_event_not_equal():
    assert _log(5, event="A") != _log(5, event="B")


def test_log_eq_differing_section_not_equal():
    assert _log(5) != _log(6)


@pytest.mark.parametrize(
    "snum, expected",
    [
        (4, False),   # just below lower bound
        (5, True),    # lower bound inclusive
        (7, True),    # interior
        (10, True),   # upper bound inclusive
        (11, False),  # just above upper bound
    ],
)
def test_contains_section_single_range_inclusive(snum, expected):
    assert _log([(5, 10)]).containsSection(snum) is expected


@pytest.mark.parametrize(
    "snum, expected",
    [
        (1, True),    # in first range
        (3, True),    # upper bound of first range
        (5, False),   # gap between ranges
        (7, True),    # lower bound of second range
        (9, True),    # upper bound of second range
        (10, False),  # past second range
    ],
)
def test_contains_section_multi_range(snum, expected):
    assert _log([(1, 3), (7, 9)]).containsSection(snum) is expected


def test_contains_section_none_range_false():
    assert _log(None).containsSection(5) is False


# --------------------------------------------------------------------------- #
# LogSet
# --------------------------------------------------------------------------- #

def test_logset_adddynamic_merges_adjacent_sections():
    # same user/obj/event on consecutive sections -> one log, ranges merged.
    ls = LogSet()
    ls.addLog("u", "A", 1, "E")
    ls.addLog("u", "A", 2, "E")

    assert len(ls.all_logs) == 1
    assert ls.all_logs[0].section_ranges == [(1, 2)]


def test_logset_adddynamic_gap_then_fill():
    # 1, then 3 (gap -> two ranges), then 2 (bridges -> single merged range).
    ls = LogSet()
    ls.addLog("u", "A", 1, "E")
    ls.addLog("u", "A", 3, "E")
    assert ls.all_logs[0].section_ranges == [(1, 1), (3, 3)]

    ls.addLog("u", "A", 2, "E")
    assert ls.all_logs[0].section_ranges == [(1, 3)]
    assert len(ls.all_logs) == 1


def test_logset_adddynamic_distinct_events_distinct_logs():
    ls = LogSet()
    ls.addLog("u", "A", 1, "E1")
    ls.addLog("u", "A", 1, "E2")

    assert len(ls.all_logs) == 2
    events = {l.event for l in ls.all_logs}
    assert events == {"E1", "E2"}


def test_logset_new_user_clears_dynamic_tracking():
    # a different user resets dyn_logs, so the same obj/event/section produces a
    # separate log instead of merging.
    ls = LogSet()
    ls.addLog("u", "A", 1, "E")
    ls.addLog("v", "A", 2, "E")

    assert len(ls.all_logs) == 2
    assert [l.user for l in ls.all_logs] == ["u", "v"]
    assert ls.all_logs[0].section_ranges == [(1, 1)]
    assert ls.all_logs[1].section_ranges == [(2, 2)]


def test_logset_delete_object_removes_prior_non_create_logs():
    ls = LogSet()
    ls.addLog("u", "A", 1, "modified")
    ls.addLog("u", "B", 1, "modified")
    ls.addLog("u", "A", None, "Delete object")

    # A's "modified" log is gone; B's remains; the delete log is appended last.
    descrs = [(l.obj_name, l.event) for l in ls.all_logs]
    assert descrs == [("B", "modified"), ("A", "Delete object")]


def test_logset_delete_object_keeps_create_object_log():
    ls = LogSet()
    ls.addLog("u", "A", None, "Create object")
    ls.addLog("u", "A", 1, "modified")
    ls.addLog("u", "A", None, "Delete object")

    descrs = [(l.obj_name, l.event) for l in ls.all_logs]
    # the "Create object" log is preserved (its event contains "Create object");
    # only the "modified" log is purged before the delete log lands.
    assert descrs == [("A", "Create object"), ("A", "Delete object")]


def test_logset_create_object_merges_with_prior_create_traces():
    ls = LogSet()
    ls.addLog("u", "A", None, "Create trace(s)")
    ls.addLog("u", "A", None, "Create object")

    # no new log appended; prior event rewritten "trace(s)" -> "object"
    assert len(ls.all_logs) == 1
    assert ls.all_logs[0].event == "Create object"
    assert ls.all_logs[0].obj_name == "A"


def test_logset_create_object_plain_append_when_no_prior_trace_log():
    ls = LogSet()
    ls.addLog("u", "A", None, "Create object")

    assert len(ls.all_logs) == 1
    assert ls.all_logs[0].event == "Create object"


def test_add_existing_log_appends_and_optionally_tracks():
    ls = LogSet()
    log = Log("26-06-29", "1200", "u", "A", 5, "E")

    ls.addExistingLog(log, track_dyn=True)

    assert ls.all_logs == [log]
    assert "A" in ls.dyn_logs
    assert ls.dyn_logs["A"]["E"] is log


def test_add_existing_log_no_track_leaves_dyn_empty():
    ls = LogSet()
    ls.addExistingLog(Log("26-06-29", "1200", "u", "A", 5, "E"))

    assert len(ls.all_logs) == 1
    assert ls.dyn_logs == {}


def test_add_existing_log_track_none_obj_uses_dash_key():
    ls = LogSet()
    log = Log("26-06-29", "1200", "u", None, 5, "E")

    ls.addExistingLog(log, track_dyn=True)

    assert "-" in ls.dyn_logs
    assert ls.dyn_logs["-"]["E"] is log


def test_logset_getloglist_str_vs_list():
    ls = LogSet()
    log = Log("26-06-29", "1200", "u", "A", 5, "E")
    ls.addExistingLog(log)

    assert ls.getLogList() == [log]
    # the list copy is a distinct object
    assert ls.getLogList() is not ls.all_logs
    assert ls.getLogList(as_str=True) == str(log)
    assert str(ls) == str(log)


def test_logset_fromlist_roundtrip():
    ls = LogSet()
    ls.addExistingLog(
        Log("26-06-29", "1200", "u", "A", [(1, 3), (7, 9)], "event, with comma")
    )
    ls.addExistingLog(Log("26-06-29", "1201", "u", None, None, "static"))

    rebuilt = LogSet.fromList(ls.getList())

    assert rebuilt.getList() == ls.getList()


def test_logset_fromlist_skips_blank_lines():
    rebuilt = LogSet.fromList(
        ["26-06-29, 1200, u, A, 5, E", "", "   "]
    )
    assert len(rebuilt.all_logs) == 1
    assert rebuilt.all_logs[0].obj_name == "A"


def test_logset_remove_curation():
    ls = LogSet()
    ls.addExistingLog(Log("26-06-29", "1200", "u", "A", 1, "manually curated"))
    ls.addExistingLog(Log("26-06-29", "1201", "u", "A", 1, "modified"))
    ls.addExistingLog(Log("26-06-29", "1202", "u", "B", 1, "curation removed"))

    ls.removeCuration("A")

    descrs = [(l.obj_name, l.event) for l in ls.all_logs]
    # only A's curation log is removed; A's "modified" and B's curation stay.
    assert descrs == [("A", "modified"), ("B", "curation removed")]


def test_logset_get_last_index_matches_section_and_name():
    ls = LogSet()
    ls.addExistingLog(Log("26-06-29", "1200", "u", "A", 1, "modified"))   # 0
    ls.addExistingLog(Log("26-06-29", "1201", "u", "A", 5, "modified"))   # 1
    ls.addExistingLog(Log("26-06-29", "1202", "u", "A", 9, "ztrace x"))   # 2 (skip)

    # last non-ztrace A log containing section 5 is index 1
    assert ls.getLastIndex(5, "A") == 1


def test_logset_get_last_index_no_match_returns_negative():
    ls = LogSet()
    ls.addExistingLog(Log("26-06-29", "1200", "u", "A", 1, "modified"))
    ls.addExistingLog(Log("26-06-29", "1201", "u", "A", 1, "modified"))

    # no log contains section 99, and name Z never matches -> scans to -1
    assert ls.getLastIndex(99, "A") == -1
    assert ls.getLastIndex(1, "Z") == -1


def test_logset_get_last_index_none_range_matches_any_section():
    ls = LogSet()
    ls.addExistingLog(Log("26-06-29", "1200", "u", "A", None, "Create object"))

    # section_ranges is None -> matches regardless of requested section number
    assert ls.getLastIndex(123, "A") == 0


# --------------------------------------------------------------------------- #
# LogSetPair
# --------------------------------------------------------------------------- #

def _shared_log():
    # build via fromStr on both sides so the two Log objects are independent but
    # compare equal (LogSetPair diverge detection uses __eq__).
    s = str(Log("26-06-29", "1200", "u", "A", 1, "modified"))
    return Log.fromStr(s), Log.fromStr(s)


def test_logsetpair_diverge_index_and_incomplete_match():
    a, b = LogSet(), LogSet()
    la, lb = _shared_log()
    a.addExistingLog(la)
    b.addExistingLog(lb)
    # b has one extra, divergent log
    b.addExistingLog(Log("26-06-29", "1201", "u", "B", 2, "E2"))

    pair = LogSetPair(a, b)

    assert pair.last_shared_index == 0      # first (shared) log at index 0
    assert pair.complete_match is False


def test_logsetpair_complete_match():
    a, b = LogSet(), LogSet()
    la, lb = _shared_log()
    a.addExistingLog(la)
    b.addExistingLog(lb)

    pair = LogSetPair(a, b)

    assert pair.complete_match is True
    assert pair.last_shared_index == 0


def test_logsetpair_empty_logsets_complete_match():
    pair = LogSetPair(LogSet(), LogSet())

    # no logs at all: loop never runs, i stays 0 -> last_shared_index -1,
    # and 0 == len(a)==len(b)==0 so it's a complete match.
    assert pair.last_shared_index == -1
    assert pair.complete_match is True


def test_logsetpair_modified_since_diverge():
    a, b = LogSet(), LogSet()
    la, lb = _shared_log()
    a.addExistingLog(la)
    b.addExistingLog(lb)
    # only b modifies A on section 1 after the shared point
    b.addExistingLog(Log("26-06-29", "1300", "u", "A", 1, "modified again"))

    pair = LogSetPair(a, b)

    # logset0 unchanged since diverge, logset1 changed
    assert pair.getModifiedSinceDiverge("A", 1) == (False, True)