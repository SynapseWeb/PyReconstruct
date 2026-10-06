"""Pure-data tests for Contour and the headless helpers of Section.

Contour (modules/datatypes/contour.py) is a thin, name-keyed container of
Trace objects with a handful of container dunders, bounds aggregation, and a
duplicate-merging importer. None of it needs Qt or a Series, so we exercise it
end-to-end with hand-built traces and hand-derived expectations.

Section (modules/datatypes/section.py) cannot be *constructed* without real
series files: ``Section.__init__`` joins ``series.getwdir()`` with
``series.sections[n]`` and immediately reads/parses that file from disk. So we
only cover its genuinely pure pieces:

  * ``getEmptyDict`` / ``updateJSON`` -- static, dict-in/dict-out (or in-place).
  * ``addTrace`` / ``removeTrace`` / ``tracesAsList`` -- instance methods whose
    logic touches only ``self.contours`` and the tracking lists. We drive them
    on a bare ``Section.__new__`` instance with ``log_event=False`` (the only
    branch that reaches ``self.series`` is the log call), which is the smallest
    faithful way to test the real method bodies without I/O.

Expected values below are derived by hand, not echoed from the code.  See the
module-level ``flags`` note returned by the harness for Section limitations.
"""
import math

import pytest

from PyReconstruct.modules.datatypes.contour import Contour
from PyReconstruct.modules.datatypes.trace import Trace
from PyReconstruct.modules.datatypes.section import Section
from PyReconstruct.modules.datatypes.transform import Transform


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def mk(name, points, color=(0, 0, 0), closed=True):
    """Build a Trace with explicit points (bypassing the GUI add path)."""
    t = Trace(name, color, closed)
    t.points = list(points)
    return t


# A unit-ish square used in several import tests.
SQUARE = [(0, 0), (10, 0), (10, 10), (0, 10)]


# --------------------------------------------------------------------------- #
# Contour construction
# --------------------------------------------------------------------------- #
def test_empty_contour_construction():
    c = Contour("axon")
    assert c.name == "axon"
    assert c.getTraces() == []
    assert len(c) == 0
    assert c.isEmpty() is True


def test_construction_with_matching_traces():
    traces = [mk("axon", [(0, 0), (1, 0), (1, 1)]),
              mk("axon", [(5, 5), (6, 5), (6, 6)])]
    c = Contour("axon", traces)
    assert len(c) == 2
    assert c.isEmpty() is False
    # The stored list is the very list passed in (no defensive copy in ctor).
    assert c.getTraces() == traces


def test_construction_name_mismatch_raises():
    with pytest.raises(Exception):
        Contour("axon", [mk("dendrite", [(0, 0), (1, 1)])])


def test_construction_with_empty_list_is_empty():
    # falsy traces arg -> fresh empty list
    c = Contour("axon", [])
    assert len(c) == 0
    assert c.isEmpty() is True


# --------------------------------------------------------------------------- #
# append / remove / index
# --------------------------------------------------------------------------- #
def test_append_matching_name():
    c = Contour("axon")
    t = mk("axon", [(0, 0), (1, 1)])
    c.append(t)
    assert len(c) == 1
    assert c[0] is t
    assert c.isEmpty() is False


def test_append_name_mismatch_raises():
    c = Contour("axon")
    with pytest.raises(Exception):
        c.append(mk("dendrite", [(0, 0), (1, 1)]))


def test_append_uses_normalized_trace_name():
    # Trace normalizes "a b" -> "a_b"; the contour must carry the same name.
    c = Contour("a_b")
    t = mk("a b", [(0, 0), (1, 1)])           # Trace() turns this into "a_b"
    assert t.name == "a_b"
    c.append(t)                                # must not raise
    assert len(c) == 1


def test_remove_trace():
    t1 = mk("axon", [(0, 0), (1, 1)])
    t2 = mk("axon", [(2, 2), (3, 3)])
    c = Contour("axon", [t1, t2])
    c.remove(t1)
    assert len(c) == 1
    assert c[0] is t2


def test_index_returns_position():
    t1 = mk("axon", [(0, 0), (1, 1)])
    t2 = mk("axon", [(2, 2), (3, 3)])
    t3 = mk("axon", [(4, 4), (5, 5)])
    c = Contour("axon", [t1, t2, t3])
    assert c.index(t1) == 0
    assert c.index(t2) == 1
    assert c.index(t3) == 2


# --------------------------------------------------------------------------- #
# container protocol: __iter__ / __len__ / __getitem__
# --------------------------------------------------------------------------- #
def test_iteration_yields_traces_in_order():
    traces = [mk("axon", [(i, i), (i + 1, i + 1)]) for i in range(3)]
    c = Contour("axon", traces)
    assert list(iter(c)) == traces
    # iterating again restarts from the beginning (fresh iterator each time)
    assert [t for t in c] == traces


def test_len_matches_trace_count():
    c = Contour("axon")
    assert len(c) == 0
    c.append(mk("axon", [(0, 0), (1, 1)]))
    assert len(c) == 1
    c.append(mk("axon", [(2, 2), (3, 3)]))
    assert len(c) == 2


def test_getitem_index_and_slice():
    traces = [mk("axon", [(i, i), (i + 1, i + 1)]) for i in range(4)]
    c = Contour("axon", traces)
    assert c[0] is traces[0]
    assert c[-1] is traces[-1]
    # slicing delegates to list slicing and returns a plain list
    sl = c[1:3]
    assert sl == traces[1:3]
    assert isinstance(sl, list)


# --------------------------------------------------------------------------- #
# getTraces / copy
# --------------------------------------------------------------------------- #
def test_get_traces_returns_independent_list():
    t = mk("axon", [(0, 0), (1, 1)])
    c = Contour("axon", [t])
    g = c.getTraces()
    assert g[0] is t                 # same trace objects (shallow copy)
    g.append("junk")                 # mutating the returned list ...
    assert len(c) == 1               # ... must not touch the contour


def test_copy_produces_distinct_traces_with_equal_points():
    orig = Contour("axon", [mk("axon", [(0, 0), (2, 0), (2, 2)])])
    cp = orig.copy()
    assert cp.name == "axon"
    assert len(cp) == 1
    assert cp[0] is not orig[0]                     # trace objects are copied
    assert cp[0].points == orig[0].points           # but values are equal
    # mutating the copy's points does not affect the original
    cp[0].points.append((9, 9))
    assert orig[0].points == [(0, 0), (2, 0), (2, 2)]


# --------------------------------------------------------------------------- #
# getBounds / getMidpoint
# --------------------------------------------------------------------------- #
def test_get_bounds_single_trace():
    c = Contour("axon", [mk("axon", [(0, 0), (4, 0), (4, 3), (0, 3)])])
    assert c.getBounds() == (0, 0, 4, 3)


def test_get_bounds_spans_multiple_traces():
    c = Contour("axon")
    c.append(mk("axon", [(0, 0), (2, 0), (2, 2), (0, 2)]))
    c.append(mk("axon", [(10, 10), (11, 10), (11, 12), (10, 12)]))
    # xmin/ymin from the first square, xmax/ymax from the second
    assert c.getBounds() == (0, 0, 11, 12)


def test_get_bounds_with_negative_coords():
    c = Contour("axon", [mk("axon", [(-5, -2), (3, -2), (3, 7), (-5, 7)])])
    assert c.getBounds() == (-5, -2, 3, 7)


def test_get_bounds_applies_translation_transform():
    # pure translation: x += 5, y -= 3  (tform list = [a,b,tx,c,d,ty])
    tform = Transform([1, 0, 5, 0, 1, -3])
    c = Contour("axon", [mk("axon", [(0, 0), (2, 0), (2, 2), (0, 2)])])
    xmin, ymin, xmax, ymax = c.getBounds(tform)
    assert xmin == pytest.approx(5.0)
    assert ymin == pytest.approx(-3.0)
    assert xmax == pytest.approx(7.0)
    assert ymax == pytest.approx(-1.0)


def test_get_midpoint_is_average_of_extremes():
    c = Contour("axon")
    c.append(mk("axon", [(0, 0), (2, 0), (2, 2), (0, 2)]))
    c.append(mk("axon", [(10, 10), (11, 10), (11, 12), (10, 12)]))
    # bounds (0,0,11,12) -> midpoint ((0+11)/2, (0+12)/2)
    mx, my = c.getMidpoint()
    assert mx == pytest.approx(5.5)
    assert my == pytest.approx(6.0)


def test_get_bounds_empty_contour_raises():
    # min()/max() over empty extreme lists -> ValueError
    with pytest.raises(ValueError):
        Contour("empty").getBounds()


# --------------------------------------------------------------------------- #
# __add__
# --------------------------------------------------------------------------- #
def test_add_concatenates_traces_into_new_contour():
    a = Contour("z", [mk("z", [(0, 0), (1, 1)], closed=False)])
    b = Contour("z", [mk("z", [(2, 2), (3, 3)], closed=False)])
    c = a + b
    assert c is not a and c is not b          # a fresh contour
    assert len(c) == 2
    assert c.name == "z"
    # operands are untouched
    assert len(a) == 1 and len(b) == 1
    # order preserved: self's traces then other's
    assert c[0] is a[0]
    assert c[1] is b[0]


def test_add_name_mismatch_raises():
    with pytest.raises(Exception):
        Contour("a") + Contour("b")


# --------------------------------------------------------------------------- #
# importTraces (pure-data merge logic)
# --------------------------------------------------------------------------- #
def test_import_identical_leading_traces_keep_self_merges_tags():
    s = Contour("o", [mk("o", SQUARE)])
    other_t = mk("o", SQUARE)
    other_t.addTag("from_other")
    other = Contour("o", [other_t])

    rem_s, rem_o = s.importTraces(other, threshold=0.95, keep_above="self")

    # the two leading traces overlap exactly -> treated as a duplicate
    assert len(s) == 1
    assert s[0] is not other_t                 # kept "self" trace
    assert "from_other" in s[0].tags           # but absorbed other's tag
    # an exact-duplicate match leaves no leftover conflict pool
    assert rem_s == []
    assert rem_o == []


def test_import_identical_keep_other_uses_other_trace():
    self_t = mk("o", SQUARE)
    self_t.addTag("from_self")
    s = Contour("o", [self_t])
    other = Contour("o", [mk("o", SQUARE)])

    s.importTraces(other, threshold=0.95, keep_above="other")

    assert len(s) == 1
    assert s[0] is not self_t                  # now holds "other"'s trace
    assert "from_self" in s[0].tags            # with self's tag merged in


def test_import_identical_keep_blank_retains_both():
    s = Contour("o", [mk("o", SQUARE)])
    other = Contour("o", [mk("o", SQUARE)])
    s.importTraces(other, threshold=0.95, keep_above="")
    assert len(s) == 2


def test_import_disjoint_traces_are_all_retained_as_conflicts():
    s = Contour("o", [mk("o", [(0, 0), (1, 0), (1, 1), (0, 1)])])
    other = Contour("o", [mk("o", [(100, 100), (101, 100), (101, 101), (100, 101)])])

    rem_s, rem_o = s.importTraces(other, threshold=0.95, keep_above="self")

    # nothing overlaps, so both survive and both are reported as conflicts
    assert len(s) == 2
    assert len(rem_s) == 1
    assert len(rem_o) == 1


def test_import_into_empty_self_takes_all_other_traces():
    s = Contour("o", [])
    other = Contour("o", [mk("o", SQUARE), mk("o", [(1, 1), (2, 2)], closed=False)])
    rem_s, rem_o = s.importTraces(other, threshold=0.95, keep_above="self")
    # self had nothing, so every other trace ends up in self
    assert len(s) == 2
    assert rem_s == []          # self contributed no leftover traces
    assert len(rem_o) == 2      # all of other's traces are "remaining"


def test_import_invalid_keep_above_raises_when_duplicate_found():
    # The bad-key check only fires inside addDuplicate, i.e. when an actual
    # overlapping pair is encountered.
    s = Contour("o", [mk("o", SQUARE)])
    other = Contour("o", [mk("o", SQUARE)])
    with pytest.raises(Exception):
        s.importTraces(other, threshold=0.95, keep_above="bogus")


# --------------------------------------------------------------------------- #
# Section.getEmptyDict  (pure static)
# --------------------------------------------------------------------------- #
def test_get_empty_dict_keys_and_values():
    d = Section.getEmptyDict()
    assert set(d.keys()) == {
        "src", "brightness_contrast_profiles", "mag", "align_locked",
        "thickness", "tforms", "contours", "flags", "calgrid",
    }
    assert d["src"] == ""
    assert d["brightness_contrast_profiles"] == {"default": (0, 0)}
    assert d["mag"] == pytest.approx(0.00254)
    assert d["align_locked"] is True
    assert d["thickness"] == pytest.approx(0.05)
    assert d["contours"] == {}
    assert d["flags"] == []
    assert d["calgrid"] is False
    # the only tform is an identity "default"
    assert set(d["tforms"].keys()) == {"default"}
    assert d["tforms"]["default"] == [1, 0, 0, 0, 1, 0]


def test_get_empty_dict_returns_independent_copies():
    a = Section.getEmptyDict()
    b = Section.getEmptyDict()
    a["contours"]["x"] = 1
    a["tforms"]["extra"] = [0, 0, 0, 0, 0, 0]
    assert "x" not in b["contours"]
    assert "extra" not in b["tforms"]


# --------------------------------------------------------------------------- #
# Section.updateJSON  (pure static, in-place)
# --------------------------------------------------------------------------- #
def test_update_json_adds_missing_keys():
    d = {"contours": {}, "tforms": {}, "flags": []}
    Section.updateJSON(d, 1)
    # every empty-dict key should now be present
    for key in Section.getEmptyDict():
        assert key in d
    assert d["mag"] == pytest.approx(0.00254)
    assert d["calgrid"] is False


def test_update_json_converts_dict_trace_to_list():
    trace_dict = {
        "x": [0, 1, 1, 0], "y": [0, 0, 1, 1],
        "color": [255, 0, 0], "closed": True, "negative": False,
        "hidden": False, "mode": ["none", "none"], "tags": [],
    }
    d = {"contours": {"c": [trace_dict]}, "tforms": {}, "flags": []}
    Section.updateJSON(d, 1)
    tr = d["contours"]["c"][0]
    assert isinstance(tr, list)
    # field order defined by updateJSON: x, y, color, closed, negative, hidden, mode, tags
    assert tr[0] == [0, 1, 1, 0]
    assert tr[1] == [0, 0, 1, 1]
    assert tr[2] == [255, 0, 0]
    assert tr[3] is True
    assert tr[6] == ["none", "none"]


def test_update_json_drops_defective_trace_and_empty_contour():
    good = [[0, 1, 1, 0], [0, 0, 1, 1], [255, 0, 0], True, False, False,
            ["none", "none"], []]
    bad = [[0], [0], [0, 0, 0], True, False, False, ["none", "none"], []]
    d = {"contours": {"good": [good], "bad": [bad]}, "tforms": {}, "flags": []}
    Section.updateJSON(d, 1)
    # the single-point trace was defective -> its only trace removed -> contour gone
    assert "bad" not in d["contours"]
    assert "good" in d["contours"]
    assert len(d["contours"]["good"]) == 1


def test_update_json_pops_history_and_normalizes_mode():
    # a length-9 trace carries a trailing history element; mode field is non-list
    nine = [[0, 1, 1, 0], [0, 0, 1, 1], [255, 0, 0], True, False, False,
            "NOT_A_LIST", [], "HISTORY"]
    d = {"contours": {"c": [nine]}, "tforms": {}, "flags": []}
    Section.updateJSON(d, 1)
    tr = d["contours"]["c"][0]
    assert len(tr) == 8                  # history popped
    assert tr[6] == ["none", "none"]     # non-list mode normalized


def test_update_json_brightness_contrast_migration():
    # |brightness| > 100 is clamped to 0; contrast is int()'d; both move to profiles
    d = {"contours": {}, "tforms": {}, "flags": [],
         "brightness": 150, "contrast": 7.9}
    Section.updateJSON(d, 1)
    assert d["brightness"] == 0
    assert d["brightness_contrast_profiles"] == {"default": (0, 7)}


def test_update_json_brightness_within_range_preserved():
    d = {"contours": {}, "tforms": {}, "flags": [],
         "brightness": -40, "contrast": 12.0}
    Section.updateJSON(d, 1)
    assert d["brightness"] == -40
    assert d["brightness_contrast_profiles"] == {"default": (-40, 12)}


def test_update_json_removes_no_alignment_tform():
    d = {"contours": {}, "flags": [],
         "tforms": {"no-alignment": [1, 0, 0, 0, 1, 0],
                    "default": [1, 0, 0, 0, 1, 0]}}
    Section.updateJSON(d, 1)
    assert "no-alignment" not in d["tforms"]
    assert "default" in d["tforms"]


def test_update_json_merges_whitespace_named_contours():
    a = [[0, 1], [0, 1], [0, 0, 0], False, False, False, ["none", "none"], []]
    b = [[2, 3], [2, 3], [0, 0, 0], False, False, False, ["none", "none"], []]
    d = {"contours": {"a b": [a], "a_b": [b]}, "tforms": {}, "flags": []}
    Section.updateJSON(d, 1)
    # "a b" normalizes to "a_b" and is merged into the existing "a_b"
    assert set(d["contours"].keys()) == {"a_b"}
    assert len(d["contours"]["a_b"]) == 2


def test_update_json_flag_gets_id_and_resolved_status():
    # legacy 5-field flag: name, x, y, snum, color
    d = {"contours": {}, "tforms": {},
         "flags": [["flagname", 1.0, 2.0, 3, [255, 0, 0]]]}
    Section.updateJSON(d, 1)
    flag = d["flags"][0]
    # +False (resolved) then +generated id at front -> 7 fields
    assert len(flag) == 7
    assert flag[-1] is False           # appended resolved=False
    # the original payload is preserved, just shifted right by the inserted id
    assert flag[1:6] == ["flagname", 1.0, 2.0, 3, [255, 0, 0]]


# --------------------------------------------------------------------------- #
# Section.addTrace / removeTrace / tracesAsList
# (driven on a bare instance; log_event=False so self.series is never touched)
# --------------------------------------------------------------------------- #
def make_bare_section(n=1):
    """A Section with just the attributes addTrace/removeTrace/tracesAsList use."""
    s = Section.__new__(Section)
    s.n = n
    s.contours = {}
    s.added_traces = []
    s.removed_traces = []
    return s


def test_add_trace_creates_contour_and_tracks():
    s = make_bare_section()
    t = mk("foo", SQUARE)
    s.addTrace(t, log_event=False)
    assert "foo" in s.contours
    assert len(s.contours["foo"]) == 1
    assert s.contours["foo"][0] is t
    assert s.added_traces == [t]


def test_add_trace_appends_to_existing_contour():
    s = make_bare_section()
    t1 = mk("foo", SQUARE)
    t2 = mk("foo", [(5, 5), (6, 5), (6, 6), (5, 6)])
    s.addTrace(t1, log_event=False)
    s.addTrace(t2, log_event=False)
    assert len(s.contours["foo"]) == 2
    assert len(s.added_traces) == 2


def test_add_trace_ignores_traces_with_fewer_than_two_points():
    s = make_bare_section()
    s.addTrace(mk("dust", [(0, 0)]), log_event=False)
    assert "dust" not in s.contours
    assert s.added_traces == []


def test_add_trace_forces_two_point_trace_open():
    s = make_bare_section()
    t = mk("line", [(0, 0), (1, 1)], closed=True)   # asserts closed gets flipped
    s.addTrace(t, log_event=False)
    assert s.contours["line"][0].closed is False


def test_traces_as_list_order_and_no_copy():
    s = make_bare_section()
    a1 = mk("aaa", SQUARE)
    a2 = mk("aaa", [(5, 5), (6, 5), (6, 6), (5, 6)])
    b1 = mk("bbb", [(20, 20), (21, 20), (21, 21), (20, 21)])
    s.addTrace(a1, log_event=False)
    s.addTrace(a2, log_event=False)
    s.addTrace(b1, log_event=False)
    tl = s.tracesAsList()
    # grouped by contour (insertion order of dict), traces in append order
    assert tl == [a1, a2, b1]
    assert tl[0] is a1          # genuinely the same objects (docstring: no copy)


def test_remove_trace_updates_contour_and_tracking():
    s = make_bare_section()
    t1 = mk("foo", SQUARE)
    t2 = mk("foo", [(5, 5), (6, 5), (6, 6), (5, 6)])
    s.addTrace(t1, log_event=False)
    s.addTrace(t2, log_event=False)
    s.removeTrace(t1, log_event=False)
    assert len(s.contours["foo"]) == 1
    assert s.contours["foo"][0] is t2
    assert s.removed_traces == [t1]


def test_remove_trace_unknown_name_is_noop():
    s = make_bare_section()
    s.addTrace(mk("foo", SQUARE), log_event=False)
    # removing a trace whose name has no contour should not raise or track
    s.removeTrace(mk("ghost", SQUARE), log_event=False)
    assert s.removed_traces == []
    assert len(s.contours["foo"]) == 1


def test_add_then_remove_roundtrip_leaves_contour_present_but_empty():
    s = make_bare_section()
    t = mk("foo", SQUARE)
    s.addTrace(t, log_event=False)
    s.removeTrace(t, log_event=False)
    # removeTrace empties the contour but does not delete the (now-empty) key
    assert "foo" in s.contours
    assert len(s.contours["foo"]) == 0
    assert s.added_traces == [t]
    assert s.removed_traces == [t]
