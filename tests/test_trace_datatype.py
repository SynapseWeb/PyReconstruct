"""Unit tests for the pure-data methods of datatypes.trace.Trace.

These cover construction and attribute defaults, the getList()/fromList()
serialization round-trip (both include_name variants), copy() independence,
the bounds/midpoint geometry (with and without an affine Transform), tag
mutation, the boolean flag setters, magScale(), getStretched(), and the
isSameTrace()/overlaps() comparisons. Expected geometry is derived by hand
from small known shapes (axis-aligned squares/rectangles) rather than echoed
back from the methods under test.

Anything requiring a live QApplication or a real Series is intentionally
skipped; only headless geometry/attribute behavior is exercised.
"""
import pytest

from PyReconstruct.modules.datatypes.trace import Trace
from PyReconstruct.modules.datatypes.transform import Transform


# A unit-ish square, counter-clockwise, anchored at the origin.
SQUARE = [(0, 0), (10, 0), (10, 10), (0, 10)]
# A 4-wide, 2-tall rectangle offset from the origin.
RECT = [(2, 3), (6, 3), (6, 5), (2, 5)]


def make_square_trace(name="square", color=(255, 0, 0), closed=True):
    t = Trace(name, color, closed=closed)
    t.points = list(SQUARE)
    return t


# ---------------------------------------------------------------------------
# Construction / defaults
# ---------------------------------------------------------------------------

def test_constructor_defaults():
    t = Trace("axon", (1, 2, 3))
    assert t.name == "axon"
    assert t.color == (1, 2, 3)
    assert t.closed is True          # default
    assert t.negative is False
    assert t.hidden is False
    assert t.points == []
    assert t.tags == set()
    assert t.fill_mode == ("none", "none")


def test_constructor_closed_false():
    t = Trace("dendrite", (0, 0, 0), closed=False)
    assert t.closed is False


def test_name_setter_normalizes_whitespace_and_commas():
    # leading/trailing whitespace stripped; internal spaces and commas -> "_"
    t = Trace("  my trace, v2 ", (0, 0, 0))
    assert t.name == "my_trace__v2"


def test_name_setter_collapses_multiple_spaces():
    # "_".join(value.split()) collapses runs of whitespace to a single "_"
    t = Trace("a   b\tc", (0, 0, 0))
    assert t.name == "a_b_c"


def test_name_setter_accepts_none():
    t = Trace("temp", (0, 0, 0))
    t.name = None
    assert t.name is None


def test_name_setter_rejects_non_string():
    with pytest.raises(AssertionError):
        Trace(123, (0, 0, 0))


# ---------------------------------------------------------------------------
# add()
# ---------------------------------------------------------------------------

def test_add_appends_point():
    t = Trace("t", (0, 0, 0))
    t.add((1, 2))
    t.add((3, 4))
    assert t.points == [(1, 2), (3, 4)]


# ---------------------------------------------------------------------------
# getList() shape and contents
# ---------------------------------------------------------------------------

def test_getlist_with_name_has_nine_elements():
    t = make_square_trace()
    t.negative = True
    t.hidden = True
    t.fill_mode = ("solid", "selected")
    t.tags = {"tagA"}
    l = t.getList(include_name=True)
    assert len(l) == 9
    name, x, y, color, closed, negative, hidden, fill_mode, tags = l
    assert name == "square"
    assert x == [0, 10, 10, 0]
    assert y == [0, 0, 10, 10]
    assert color == (255, 0, 0)
    assert closed is True
    assert negative is True
    assert hidden is True
    assert fill_mode == ("solid", "selected")
    assert sorted(tags) == ["tagA"]


def test_getlist_without_name_has_eight_elements():
    t = make_square_trace()
    l = t.getList(include_name=False)
    assert len(l) == 8
    # first element is the x-list, not a name
    assert l[0] == [0, 10, 10, 0]


def test_getlist_rounds_coordinates_to_seven_decimals():
    t = Trace("t", (0, 0, 0))
    # more than 7 decimal places of precision should be rounded
    t.points = [(1.123456789, 2.987654321)]
    l = t.getList(include_name=False)
    x_list, y_list = l[0], l[1]
    assert x_list == [round(1.123456789, 7)]
    assert y_list == [round(2.987654321, 7)]
    assert x_list == [1.1234568]
    assert y_list == [2.9876543]


# ---------------------------------------------------------------------------
# getList() / fromList() round-trip
# ---------------------------------------------------------------------------

def test_round_trip_with_name():
    orig = make_square_trace(name="myelin", color=(10, 20, 30), closed=True)
    orig.negative = True
    orig.hidden = False
    orig.fill_mode = ("transparent", "unselected")
    orig.tags = {"x", "y"}

    # include_name=True -> 9-element list, fromList pops the name off the front
    rebuilt = Trace.fromList(orig.getList(include_name=True))

    assert rebuilt.name == "myelin"
    assert rebuilt.color == (10, 20, 30)
    assert rebuilt.closed is True
    assert rebuilt.negative is True
    assert rebuilt.hidden is False
    assert rebuilt.fill_mode == ("transparent", "unselected")
    assert rebuilt.tags == {"x", "y"}
    # points come back as (x, y) tuples in the same order
    assert rebuilt.points == [(0, 0), (10, 0), (10, 10), (0, 10)]


def test_round_trip_without_name_supplies_name():
    orig = make_square_trace(name="ignored", color=(5, 5, 5))
    # 8-element list (no name embedded); fromList must use the supplied name
    rebuilt = Trace.fromList(orig.getList(include_name=False), name="given")
    assert rebuilt.name == "given"
    assert rebuilt.points == [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert rebuilt.color == (5, 5, 5)


def test_round_trip_idempotent_second_pass():
    # getList(fromList(getList(t))) should be stable
    orig = make_square_trace(name="obj", color=(7, 8, 9))
    orig.tags = {"only"}
    first = orig.getList(include_name=True)
    rebuilt = Trace.fromList(list(first))  # copy: fromList mutates via pop
    second = rebuilt.getList(include_name=True)
    assert first == second


def test_fromlist_points_are_tuples():
    orig = make_square_trace()
    rebuilt = Trace.fromList(orig.getList(include_name=True))
    assert all(isinstance(p, tuple) for p in rebuilt.points)


def test_fromlist_strips_name_whitespace():
    t = Trace("t", (0, 0, 0))
    t.points = [(0, 0)]
    l = t.getList(include_name=False)
    rebuilt = Trace.fromList(l, name="  spaced  ")
    # fromList calls name.strip() AND the name setter normalizes
    assert rebuilt.name == "spaced"


# ---------------------------------------------------------------------------
# copy()
# ---------------------------------------------------------------------------

def test_copy_equal_but_distinct():
    orig = make_square_trace(name="orig", color=(1, 2, 3))
    orig.tags = {"a", "b"}
    c = orig.copy()
    assert c is not orig
    assert c.name == orig.name
    assert c.color == orig.color
    assert c.closed == orig.closed
    assert c.points == orig.points
    assert c.tags == orig.tags


def test_copy_points_list_is_independent():
    orig = make_square_trace()
    c = orig.copy()
    # the points lists are separate objects
    assert c.points is not orig.points
    c.points.append((99, 99))
    assert (99, 99) not in orig.points
    assert len(orig.points) == 4
    assert len(c.points) == 5


def test_copy_points_removal_does_not_affect_original():
    orig = make_square_trace()
    c = orig.copy()
    c.points.pop()
    assert len(orig.points) == 4
    assert len(c.points) == 3


def test_copy_tags_set_is_independent():
    orig = make_square_trace()
    orig.tags = {"keep"}
    c = orig.copy()
    assert c.tags is not orig.tags
    c.addTag("extra")
    assert "extra" in c.tags
    assert "extra" not in orig.tags


def test_copy_scalar_flag_reassignment_is_independent():
    orig = make_square_trace()
    orig.hidden = False
    c = orig.copy()
    c.setHidden(True)
    # reassigning an attribute on the copy must not bleed back
    assert c.hidden is True
    assert orig.hidden is False


# ---------------------------------------------------------------------------
# getBounds()  (hand-derived expected values)
# ---------------------------------------------------------------------------

def test_bounds_square():
    t = make_square_trace()
    assert t.getBounds() == (0, 0, 10, 10)


def test_bounds_offset_rectangle():
    t = Trace("r", (0, 0, 0))
    t.points = list(RECT)  # x in [2,6], y in [3,5]
    assert t.getBounds() == (2, 3, 6, 5)


def test_bounds_negative_coordinates():
    t = Trace("n", (0, 0, 0))
    t.points = [(-5, -2), (3, -2), (3, 4), (-5, 4)]
    assert t.getBounds() == (-5, -2, 3, 4)


def test_bounds_single_point():
    t = Trace("p", (0, 0, 0))
    t.points = [(7, -3)]
    assert t.getBounds() == (7, -3, 7, -3)


def test_bounds_unsorted_points():
    # points given out of any nice order; min/max must still be exact
    t = Trace("u", (0, 0, 0))
    t.points = [(3, 9), (-1, 2), (8, -4), (0, 0)]
    assert t.getBounds() == (-1, -4, 8, 9)


def test_bounds_identity_transform_unchanged():
    t = make_square_trace()
    ident = Transform([1, 0, 0, 0, 1, 0])
    untransformed = t.getBounds()
    transformed = t.getBounds(ident)
    assert transformed[0] == pytest.approx(untransformed[0])
    assert transformed[1] == pytest.approx(untransformed[1])
    assert transformed[2] == pytest.approx(untransformed[2])
    assert transformed[3] == pytest.approx(untransformed[3])


def test_bounds_translation_transform():
    # tform_list = [m11, m12, dx, m21, m22, dy] per Transform.getQTransform:
    #   QTransform(t0, t3, t1, t4, t2, t5) -> nx = t0*x + t1*y + t2
    # so a pure translation by (+5, -3) is [1,0,5, 0,1,-3].
    t = make_square_trace()  # bounds (0,0,10,10)
    tform = Transform([1, 0, 5, 0, 1, -3])
    xmin, ymin, xmax, ymax = t.getBounds(tform)
    assert xmin == pytest.approx(5)
    assert ymin == pytest.approx(-3)
    assert xmax == pytest.approx(15)
    assert ymax == pytest.approx(7)


def test_bounds_scale_transform():
    # scale x by 2, y by 0.5: [2,0,0, 0,0.5,0]
    t = make_square_trace()  # bounds (0,0,10,10)
    tform = Transform([2, 0, 0, 0, 0.5, 0])
    xmin, ymin, xmax, ymax = t.getBounds(tform)
    assert xmin == pytest.approx(0)
    assert ymin == pytest.approx(0)
    assert xmax == pytest.approx(20)
    assert ymax == pytest.approx(5)


def test_bounds_does_not_mutate_points():
    t = make_square_trace()
    before = list(t.points)
    t.getBounds()
    t.getBounds(Transform([1, 0, 0, 0, 1, 0]))
    assert t.points == before


# ---------------------------------------------------------------------------
# getMidpoint()  (avg of bounds extremes)
# ---------------------------------------------------------------------------

def test_midpoint_square():
    t = make_square_trace()
    mx, my = t.getMidpoint()
    assert mx == pytest.approx(5.0)
    assert my == pytest.approx(5.0)


def test_midpoint_offset_rectangle():
    t = Trace("r", (0, 0, 0))
    t.points = list(RECT)  # bounds (2,3,6,5)
    mx, my = t.getMidpoint()
    assert mx == pytest.approx(4.0)   # (2+6)/2
    assert my == pytest.approx(4.0)   # (3+5)/2


def test_midpoint_with_translation_transform():
    t = make_square_trace()  # midpoint (5,5) untransformed
    tform = Transform([1, 0, 5, 0, 1, -3])
    mx, my = t.getMidpoint(tform)
    assert mx == pytest.approx(10.0)  # 5 + 5
    assert my == pytest.approx(2.0)   # 5 - 3


def test_midpoint_matches_bounds_definition():
    # independent re-derivation from the public bounds
    t = Trace("u", (0, 0, 0))
    t.points = [(3, 9), (-1, 2), (8, -4), (0, 0)]
    xmin, ymin, xmax, ymax = t.getBounds()
    mx, my = t.getMidpoint()
    assert mx == pytest.approx((xmin + xmax) / 2)
    assert my == pytest.approx((ymin + ymax) / 2)


# ---------------------------------------------------------------------------
# Tags: addTag / mergeTags
# ---------------------------------------------------------------------------

def test_add_tag():
    t = Trace("t", (0, 0, 0))
    t.addTag("foo")
    t.addTag("bar")
    t.addTag("foo")  # duplicate is a no-op (set semantics)
    assert t.tags == {"foo", "bar"}


def test_merge_tags_union():
    a = Trace("a", (0, 0, 0))
    a.tags = {"x", "y"}
    b = Trace("b", (0, 0, 0))
    b.tags = {"y", "z"}
    a.mergeTags(b)
    assert a.tags == {"x", "y", "z"}
    # the other trace is left untouched
    assert b.tags == {"y", "z"}


def test_merge_tags_with_empty():
    a = Trace("a", (0, 0, 0))
    a.tags = {"only"}
    b = Trace("b", (0, 0, 0))
    a.mergeTags(b)
    assert a.tags == {"only"}


# ---------------------------------------------------------------------------
# Boolean flag setters / direct attributes
# ---------------------------------------------------------------------------

def test_set_hidden_default_true():
    t = Trace("t", (0, 0, 0))
    assert t.hidden is False
    t.setHidden()
    assert t.hidden is True


def test_set_hidden_explicit_false():
    t = Trace("t", (0, 0, 0))
    t.setHidden(True)
    t.setHidden(False)
    assert t.hidden is False


def test_closed_and_negative_flags_assignable():
    t = Trace("t", (0, 0, 0))
    t.closed = False
    t.negative = True
    assert t.closed is False
    assert t.negative is True


# ---------------------------------------------------------------------------
# magScale()
# ---------------------------------------------------------------------------

def test_mag_scale_doubles_coordinates():
    # new_mag/prev_mag = 2.0 -> every coordinate doubles
    t = make_square_trace()
    t.magScale(prev_mag=1.0, new_mag=2.0)
    assert t.points == [(0.0, 0.0), (20.0, 0.0), (20.0, 20.0), (0.0, 20.0)]


def test_mag_scale_identity_ratio():
    t = Trace("t", (0, 0, 0))
    t.points = [(1.5, -2.5), (3.0, 4.0)]
    t.magScale(prev_mag=0.7, new_mag=0.7)
    for (x, y), (ox, oy) in zip(t.points, [(1.5, -2.5), (3.0, 4.0)]):
        assert x == pytest.approx(ox)
        assert y == pytest.approx(oy)


def test_mag_scale_halves_coordinates():
    t = Trace("t", (0, 0, 0))
    t.points = [(4.0, 8.0), (-2.0, 6.0)]
    t.magScale(prev_mag=2.0, new_mag=1.0)  # ratio 0.5
    assert t.points[0] == pytest.approx((2.0, 4.0))
    assert t.points[1] == pytest.approx((-1.0, 3.0))


def test_mag_scale_scales_bounds_consistently():
    # bounds should scale by the same factor as the points
    t = make_square_trace()  # bounds (0,0,10,10)
    t.magScale(prev_mag=2.0, new_mag=6.0)  # ratio 3
    assert t.getBounds() == pytest.approx((0, 0, 30, 30))


# ---------------------------------------------------------------------------
# getStretched()  (scaling about the polygon centroid)
# ---------------------------------------------------------------------------

def test_get_stretched_square_to_wide_rectangle():
    # square centroid is (5,5); bounds span 10x10.
    # stretch to w=20, h=10 -> scale_x=2, scale_y=1 about (5,5):
    #   (0,0)  -> (2*(0-5)+5, 1*(0-5)+5) = (-5, 0)
    #   (10,0) -> (15, 0)
    #   (10,10)-> (15, 10)
    #   (0,10) -> (-5, 10)
    t = make_square_trace()
    stretched = t.getStretched(20, 10)
    assert stretched.points == [(-5.0, 0.0), (15.0, 0.0),
                                (15.0, 10.0), (-5.0, 10.0)]
    # resulting bounds match the requested dimensions
    xmin, ymin, xmax, ymax = stretched.getBounds()
    assert (xmax - xmin) == pytest.approx(20)
    assert (ymax - ymin) == pytest.approx(10)


def test_get_stretched_returns_copy():
    t = make_square_trace()
    stretched = t.getStretched(20, 10)
    assert stretched is not t
    # original is untouched
    assert t.points == list(SQUARE)


def test_get_stretched_preserves_midpoint():
    # scaling about the centroid leaves the bounds-midpoint of a symmetric
    # shape unchanged at the centroid.
    t = make_square_trace()
    stretched = t.getStretched(4, 30)
    mx, my = stretched.getMidpoint()
    assert mx == pytest.approx(5.0)
    assert my == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# isSameTrace()
# ---------------------------------------------------------------------------

def test_is_same_trace_true_for_copy():
    a = make_square_trace()
    b = a.copy()
    assert a.isSameTrace(b) is True


def test_is_same_trace_false_on_name():
    a = make_square_trace(name="a")
    b = make_square_trace(name="b")
    assert a.isSameTrace(b) is False


def test_is_same_trace_false_on_color():
    a = make_square_trace(color=(1, 1, 1))
    b = make_square_trace(color=(2, 2, 2))
    assert a.isSameTrace(b) is False


def test_is_same_trace_false_on_points():
    a = make_square_trace()
    b = make_square_trace()
    b.points = b.points + [(5, 5)]
    assert a.isSameTrace(b) is False


def test_is_same_trace_ignores_tags_and_hidden():
    # isSameTrace only inspects name, color, points
    a = make_square_trace()
    b = make_square_trace()
    b.tags = {"different"}
    b.hidden = True
    b.negative = True
    assert a.isSameTrace(b) is True


# ---------------------------------------------------------------------------
# overlaps()
# ---------------------------------------------------------------------------

def test_overlaps_identical_traces():
    a = make_square_trace()
    b = make_square_trace()
    assert a.overlaps(b) is True


def test_overlaps_within_tolerance():
    # points within 1e-2 in both coords count as matching -> True
    a = make_square_trace()
    b = make_square_trace()
    b.points = [(x + 0.005, y - 0.005) for (x, y) in b.points]
    assert a.overlaps(b) is True


def test_overlaps_false_when_closedness_differs():
    a = make_square_trace(closed=True)
    b = make_square_trace(closed=False)
    assert a.overlaps(b) is False


def test_overlaps_disjoint_traces():
    a = make_square_trace()  # x,y in [0,10]
    b = make_square_trace()
    b.points = [(100, 100), (110, 100), (110, 110), (100, 110)]
    assert a.overlaps(b) is False


def test_overlaps_partial_below_threshold():
    # two identical-size squares sharing only a quarter of their area;
    # overlap ratio (intersection/union) is well under the default 0.99.
    a = make_square_trace()  # [0,10] x [0,10]
    b = make_square_trace()
    b.points = [(5, 5), (15, 5), (15, 15), (5, 15)]
    assert a.overlaps(b) is False


def test_overlaps_high_threshold_for_mostly_overlapping():
    # nearly-coincident squares (1-unit shift on a 10-unit square) exceed a
    # modest threshold but the point-lists are not within tolerance.
    a = make_square_trace()
    b = make_square_trace()
    b.points = [(1, 0), (11, 0), (11, 10), (1, 10)]
    # large shift, low threshold -> overlaps; identical shape so ratio ~ 9/11
    assert a.overlaps(b, threshold=0.5) is True


# ---------------------------------------------------------------------------
# getOverlapRatio()  (bounded in [0, 1]; hand-reasoned extremes)
# ---------------------------------------------------------------------------

def test_overlap_ratio_identical_is_one():
    a = make_square_trace()
    b = make_square_trace()
    assert a.getOverlapRatio(b) == pytest.approx(1.0, abs=1e-6)


def test_overlap_ratio_disjoint_is_zero():
    a = make_square_trace()
    b = make_square_trace()
    b.points = [(100, 100), (110, 100), (110, 110), (100, 110)]
    assert a.getOverlapRatio(b) == 0


def test_overlap_ratio_quarter_overlap():
    # b is the same square shifted by (5,5): the intersection is a 5x5 block,
    # the union is two 10x10 squares minus that block = 100 + 100 - 25 = 175.
    # ratio = 25/175 = 1/7 ~= 0.142857 (rasterized, so approximate).
    a = make_square_trace()
    b = make_square_trace()
    b.points = [(5, 5), (15, 5), (15, 15), (5, 15)]
    r = a.getOverlapRatio(b)
    assert r == pytest.approx(1.0 / 7.0, abs=0.02)
    assert 0 < r < 1
