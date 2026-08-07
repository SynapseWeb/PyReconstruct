"""Behavior tests for smoothing and grid/polygon ops in modules.calc.

Two source modules are exercised here, with expected values derived by hand
(shoelace areas, linear-interpolation identities, convex-hull geometry) rather
than echoed from the functions themselves:

  * quantification.py -- rolling_average() / get_window_points() (the z-trace
    smoother and its windowing helper, for all three edge_mode values) and
    interpolate_points() on valid multi-point paths.
  * grid.py -- reducePoints() (Douglas-Peucker via cv2.approxPolyDP),
    getExterior(), mergeTraces(), and cutTraces() on a valid 2-point cut.
  * feret.py -- feret() min/max diameters (a pure-math convex-hull routine).

Grid ops rasterize onto an integer pixel grid, so the few raster-dependent
assertions use loose-but-meaningful geometric bounds (a merged union must be a
single trace whose area lies strictly between the larger input and the sum of
inputs, etc.) rather than exact equality.

Notes for the reader:
  * reducePoints feeds the points straight to cv2.approxPolyDP, which only
    accepts CV_32S/CV_32F. Integer point lists work as-is; float coordinates
    are only valid via the ``mag`` path (which casts to int32 and back). Plain
    float64 with no ``mag`` raises cv2.error and is therefore not a supported
    input, so it is not tested here.
  * feret() sorts its argument in place (Points.sort()), so it is NOT pure --
    see test_feret_mutates_input_documented and the flag in the report. Every
    other feret test passes a throwaway copy.
"""

import math

import numpy as np
import pytest

from PyReconstruct.modules.calc.quantification import (
    rolling_average,
    get_window_points,
    interpolate_points,
    area,
    euclidean_distance,
)
from PyReconstruct.modules.calc.grid import (
    reducePoints,
    getExterior,
    mergeTraces,
    cutTraces,
)
from PyReconstruct.modules.calc.feret import feret


# Points are [x, y, snum] triples for the smoother (it indexes p[0], p[1]).
def _ramp(n, mx=1.0, my=2.0, snum=0):
    """A straight ramp: point i = (i*mx, i*my). Linear in the index."""
    return [(float(i * mx), float(i * my), snum) for i in range(n)]


# ---------------------------------------------------------------------------
# get_window_points -- window selection per edge_mode
# ---------------------------------------------------------------------------

def test_window_padded_clamps_at_left_edge():
    """padded: indices outside the array clamp to the nearest endpoint.

    window=10 -> half=5 -> offsets -5..+5 (11 indices). At idx 0 the five
    negative offsets all clamp to point 0, so point[0] appears 6 times, then
    points 1..5 follow.
    """
    pts = _ramp(11, mx=1.0, my=10.0)
    wx, wy = get_window_points(pts, 0, 10, "padded")
    assert len(wx) == 11
    assert wx == [0.0] * 6 + [1.0, 2.0, 3.0, 4.0, 5.0]
    assert wy == [0.0] * 6 + [10.0, 20.0, 30.0, 40.0, 50.0]


def test_window_padded_interior_is_symmetric():
    """An interior index sees the full symmetric window with no clamping."""
    pts = _ramp(11)
    wx, _ = get_window_points(pts, 5, 10, "padded")
    assert wx == [float(i) for i in range(11)]


def test_window_circular_wraps_around():
    """circular: out-of-range offsets wrap modulo len(points)."""
    pts = _ramp(11, mx=1.0, my=10.0)
    wx, _ = get_window_points(pts, 0, 10, "circular")
    # offsets -5..-1 wrap to indices 6,7,8,9,10; then 0..5
    assert len(wx) == 11
    assert wx == [6.0, 7.0, 8.0, 9.0, 10.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0]


@pytest.mark.parametrize(
    "idx,expected_len",
    [(0, 1), (1, 3), (2, 5), (3, 7), (5, 11)],
)
def test_window_shrinking_grows_from_edges(idx, expected_len):
    """shrinking: window size is min(1 + 2*dist_from_edge, max_size).

    So it is 1 at an endpoint and grows by 2 each step inward until it
    saturates at max_size (here 10 -> capped at the symmetric 11 in the
    middle of an 11-point list).
    """
    pts = _ramp(11)
    wx, _ = get_window_points(pts, idx, 10, "shrinking")
    assert len(wx) == expected_len
    # window is centered on idx
    half = expected_len // 2
    assert wx == [float(i) for i in range(idx - half, idx + half + 1)]


# ---------------------------------------------------------------------------
# rolling_average -- smoothing for all three edge modes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mode", ["padded", "shrinking", "circular"])
def test_rolling_average_constant_is_unchanged(mode):
    """The mean of a constant window is that constant -- smoothing a constant
    sequence must return it unchanged, for every edge mode."""
    const = [(7.0, 3.0, 0)] * 11
    out = rolling_average(const, window=10, edge_mode=mode)
    assert out == [(7.0, 3.0)] * 11


@pytest.mark.parametrize("mode", ["padded", "shrinking", "circular"])
def test_rolling_average_ramp_interior_is_local_mean(mode):
    """On a straight ramp, an interior window's mean equals the centre point.

    For window=3 each interior point i averages i-1, i, i+1; on a linear
    sequence that mean is exactly point i. This holds identically for all three
    edge modes because edge handling only affects the endpoints. We assert on
    the strictly-interior indices common to all modes (here index 3 of 7).
    """
    ramp = _ramp(7, mx=1.0, my=2.0)  # point i = (i, 2i)
    out = rolling_average(ramp, window=3, edge_mode=mode)
    # interior index 3 -> mean of (2,4),(3,6),(4,8) = (3, 6) = point 3
    assert out[3] == pytest.approx((3.0, 6.0))
    # spot-check another interior index
    assert out[4] == pytest.approx((4.0, 8.0))


def test_rolling_average_shrinking_preserves_linear_endpoints():
    """For shrinking mode every window is symmetric about its centre, so a
    linear ramp is reproduced exactly end to end (endpoints map to themselves
    because their window is a single point)."""
    ramp = _ramp(7, mx=1.0, my=2.0)
    out = rolling_average(ramp, window=3, edge_mode="shrinking")
    expected = [(float(i), float(2 * i)) for i in range(7)]
    assert out == [pytest.approx(p) for p in expected]


def test_rolling_average_padded_left_edge_value():
    """Hand-computed padded edge value at idx 0, window=3 (half=1).

    Window indices clamp to {0,0,1}: points (0,0),(0,0),(1,2). Mean =
    (1/3, 2/3) -> rounded to 4 dp.
    """
    ramp = _ramp(7, mx=1.0, my=2.0)
    out = rolling_average(ramp, window=3, edge_mode="padded")
    assert out[0] == pytest.approx((round(1 / 3, 4), round(2 / 3, 4)))


def test_rolling_average_rounds_to_four_dp():
    """Output is rounded to 4 decimal places."""
    # three points whose mean has a long decimal: (0,0),(1,0),(0,0) over a
    # window=3 at idx 1 gives x-mean 1/3 = 0.3333...
    pts = [(0.0, 0.0, 0), (1.0, 0.0, 0), (0.0, 0.0, 0)]
    out = rolling_average(pts, window=3, edge_mode="padded")
    # every coordinate must have at most 4 decimal places
    for x, y in out:
        assert x == round(x, 4)
        assert y == round(y, 4)


def test_rolling_average_invalid_edge_mode_raises():
    pts = _ramp(5)
    with pytest.raises(ValueError):
        rolling_average(pts, window=4, edge_mode="bogus")
    with pytest.raises(ValueError):
        rolling_average(pts, window=4, edge_mode="")


# ---------------------------------------------------------------------------
# interpolate_points -- valid multi-point paths
# ---------------------------------------------------------------------------

def test_interpolate_count_equals_int_total_over_spacing():
    """Point count is int(total_length / spacing)."""
    path = [(0.0, 0.0), (10.0, 0.0)]  # total length 10
    for spacing, expected in [(1.0, 10), (2.0, 5), (4.0, 2), (3.0, 3)]:
        res = interpolate_points(path, spacing=spacing)
        assert len(res) == int(10.0 / spacing) == expected


def test_interpolate_preserves_endpoints():
    """linspace includes both ends, so first/last points are the path ends."""
    path = [(2.0, -3.0), (12.0, -3.0)]
    res = interpolate_points(path, spacing=1.0)
    assert res[0] == pytest.approx((2.0, -3.0))
    assert res[-1] == pytest.approx((12.0, -3.0))


def test_interpolate_points_lie_on_straight_segment():
    """All interpolated points of a single straight segment lie on its line.

    Segment from (0,0) to (10,0): every interpolated y must be 0, and x must
    be monotonically non-decreasing within [0, 10].
    """
    res = interpolate_points([(0.0, 0.0), (10.0, 0.0)], spacing=1.0)
    xs = [p[0] for p in res]
    for x, y in res:
        assert y == pytest.approx(0.0)
        assert 0.0 <= x <= 10.0
    assert xs == sorted(xs)


def test_interpolate_multi_segment_lie_on_line():
    """A 3-point path that is itself collinear (slope 4/3) -- every
    interpolated point must satisfy y == (4/3) x, endpoints preserved, and the
    count matches int(total_length / spacing).
    """
    path = [(0.0, 0.0), (3.0, 4.0), (6.0, 8.0)]  # all on y = 4/3 x
    total = euclidean_distance(path[0], path[1]) + euclidean_distance(path[1], path[2])
    res = interpolate_points(path, spacing=1.0)
    assert len(res) == int(total / 1.0)
    assert res[0] == pytest.approx((0.0, 0.0))
    assert res[-1] == pytest.approx((6.0, 8.0))
    for x, y in res:
        assert y == pytest.approx((4.0 / 3.0) * x, abs=1e-3)


def test_interpolate_spacing_is_uniform_arc_length():
    """linspace spaces samples uniformly in arc length across the whole path,
    so consecutive Euclidean gaps are equal (a straight segment makes arc
    length == Euclidean distance)."""
    res = interpolate_points([(0.0, 0.0), (9.0, 0.0)], spacing=1.0)  # 9 points
    gaps = [res[i + 1][0] - res[i][0] for i in range(len(res) - 1)]
    assert all(g == pytest.approx(gaps[0], abs=1e-3) for g in gaps)


# ---------------------------------------------------------------------------
# reducePoints -- Douglas-Peucker simplification
# ---------------------------------------------------------------------------

def test_reduce_points_drops_collinear_midpoints():
    """Extra points lying exactly on the edges of a square are removed,
    leaving the four corners; area is preserved exactly (shoelace = 100)."""
    square_with_mids = [
        [0, 0], [5, 0], [10, 0], [10, 5],
        [10, 10], [5, 10], [0, 10], [0, 5],
    ]
    reduced = reducePoints(square_with_mids, ep=0.80, closed=True)
    assert len(reduced) == 4
    assert set(map(tuple, reduced)) == {(0, 0), (10, 0), (10, 10), (0, 10)}
    assert area(reduced) == pytest.approx(100.0)


def test_reduce_points_returns_plain_list():
    reduced = reducePoints([[0, 0], [5, 0], [10, 0], [10, 10], [0, 10]],
                           ep=0.80, closed=True)
    assert isinstance(reduced, list)
    assert isinstance(reduced[0], list)


def test_reduce_points_array_flag_returns_ndarray():
    reduced = reducePoints([[0, 0], [10, 0], [10, 10], [0, 10]],
                           ep=0.80, closed=True, array=True)
    assert isinstance(reduced, np.ndarray)
    assert reduced.shape[1] == 2


def test_reduce_points_keeps_real_corner():
    """A genuine, non-collinear vertex (a tall bump) must be kept: the input
    pentagon keeps all five vertices and its area (shoelace = 600) is
    preserved."""
    pentagon = [[0, 0], [20, 0], [20, 20], [10, 40], [0, 20]]
    reduced = reducePoints(pentagon, ep=0.80, closed=True)
    assert len(reduced) == 5
    assert area(reduced) == pytest.approx(600.0)


def test_reduce_points_triangle_unchanged():
    """A triangle has no redundant points, so it survives intact (area 40)."""
    tri = [[0, 0], [10, 0], [5, 8]]
    reduced = reducePoints(tri, ep=0.80, closed=True)
    assert len(reduced) == 3
    assert area(reduced) == pytest.approx(40.0)


def test_reduce_points_mag_path_with_floats():
    """Float coordinates are only valid through the ``mag`` path (which scales
    to int32 and back). A magnified square-with-midpoints reduces to its four
    float corners with area preserved."""
    square = [
        [0.0, 0.0], [5.0, 0.0], [10.0, 0.0],
        [10.0, 10.0], [5.0, 10.0], [0.0, 10.0],
    ]
    reduced = reducePoints(square, ep=0.80, closed=True, mag=100)
    assert len(reduced) == 4
    assert area(reduced) == pytest.approx(100.0)
    assert set(map(tuple, reduced)) == {(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)}


# ---------------------------------------------------------------------------
# getExterior -- outer contour of a single trace
# ---------------------------------------------------------------------------

def test_get_exterior_of_square_is_the_four_corners():
    """The exterior of a filled 20x20 square is its four corners (order /
    orientation may differ from the input). Area is preserved (400)."""
    square = [[0, 0], [20, 0], [20, 20], [0, 20]]
    ext = getExterior(square)
    assert isinstance(ext, list)
    assert len(ext) == 4
    assert set(map(tuple, ext)) == {(0, 0), (20, 0), (20, 20), (0, 20)}
    assert area(ext) == pytest.approx(400.0)


def test_get_exterior_l_shape_preserves_area():
    """An L-shaped (concave) trace: the exterior bounds the same region, so its
    shoelace area matches the original L. Computed by hand below.

    L outline (8 vertices):
        (0,0)-(30,0)-(30,10)-(10,10)-(10,30)-(0,30)
    Area = full 30x30 (900) minus the missing 20x20 top-right block (400) = 500.
    """
    L = [[0, 0], [30, 0], [30, 10], [10, 10], [10, 30], [0, 30]]
    assert area(L) == pytest.approx(500.0)  # sanity on our hand value
    ext = getExterior(L)
    # raster + reduction may add/drop a pixel here and there, so allow a small
    # tolerance, but the area must clearly be the L (500), not the bounding box.
    assert area(ext) == pytest.approx(500.0, abs=20.0)
    assert 4 <= len(ext) <= 8


# ---------------------------------------------------------------------------
# mergeTraces -- union of overlapping traces / passthrough of disjoint ones
# ---------------------------------------------------------------------------

def test_merge_overlapping_squares_into_one():
    """Two overlapping 20x20 squares merge into a single trace whose area is
    the union. Exact union = 400 + 400 - 100 (overlap) = 700; the rasterized
    result must be a single trace whose area lies strictly between the larger
    input (400) and the sum (800), and close to 700.
    """
    a = [[0, 0], [20, 0], [20, 20], [0, 20]]
    b = [[10, 10], [30, 10], [30, 30], [10, 30]]
    merged = mergeTraces([a, b])
    assert len(merged) == 1
    merged_area = area(merged[0])
    assert area(a) < merged_area < area(a) + area(b)  # strict union bounds
    assert merged_area == pytest.approx(700.0, abs=25.0)


def test_merge_disjoint_squares_stay_separate():
    """Two far-apart squares are not merged -- two traces come back, each the
    original ~100 area."""
    c = [[0, 0], [10, 0], [10, 10], [0, 10]]
    d = [[50, 50], [60, 50], [60, 60], [50, 60]]
    merged = mergeTraces([c, d])
    assert len(merged) == 2
    for t in merged:
        assert area(t) == pytest.approx(100.0, abs=10.0)


def test_merge_single_trace_roundtrips_area():
    """Merging a lone square returns one trace of the same area."""
    sq = [[0, 0], [20, 0], [20, 20], [0, 20]]
    merged = mergeTraces([sq])
    assert len(merged) == 1
    assert area(merged[0]) == pytest.approx(400.0, abs=15.0)


# ---------------------------------------------------------------------------
# cutTraces -- a valid 2-point cut bisects a square
# ---------------------------------------------------------------------------

def test_cut_traces_vertical_split():
    """A vertical cut line through the middle of a 10x10 square produces two
    pieces. The cut is a thin buffered strip (width ~0.001), so each half is
    just under 50 and they are equal."""
    square = [[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]]
    result = cutTraces(square, [(5.0, -1.0), (5.0, 11.0)], 0.0, closed=True)
    assert len(result) == 2
    areas = sorted(area(t) for t in result)
    assert areas[0] == pytest.approx(areas[1], abs=1e-3)  # halves are equal
    for ar in areas:
        assert 45.0 < ar < 50.0
    total = sum(areas)
    assert 95.0 < total < 100.0  # a sliver is removed by the cut


def test_cut_traces_horizontal_split_equal_halves():
    """Same idea with a horizontal cut -- two equal sub-50 halves."""
    square = [[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]]
    result = cutTraces(square, [(-1.0, 5.0), (11.0, 5.0)], 0.0, closed=True)
    assert len(result) == 2
    a0, a1 = (area(t) for t in result)
    assert a0 == pytest.approx(a1, abs=1e-3)


def test_cut_traces_no_intersection_keeps_original():
    """A cut line that misses the square leaves it unchanged."""
    square = [[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]]
    result = cutTraces(square, [(100.0, 100.0), (200.0, 200.0)], 0.0, closed=True)
    assert result == square


# ---------------------------------------------------------------------------
# feret -- min/max caliper diameters (pure convex-hull math)
# ---------------------------------------------------------------------------

def test_feret_square_min_is_side_max_is_diagonal():
    """For an axis-aligned 10x10 square the min Feret (narrowest caliper
    width) is the side length 10 and the max Feret is the diagonal sqrt(200)."""
    square = [[0, 0], [10, 0], [10, 10], [0, 10]]
    mn, mx = feret([list(p) for p in square])  # pass a copy: feret sorts in place
    assert mn == pytest.approx(10.0)
    assert mx == pytest.approx(math.hypot(10, 10))


def test_feret_rectangle_diameters():
    """A 6x8 rectangle: min Feret = short side 6, max Feret = diagonal 10."""
    rect = [[0, 0], [8, 0], [8, 6], [0, 6]]
    mn, mx = feret([list(p) for p in rect])
    assert mn == pytest.approx(6.0)
    assert mx == pytest.approx(10.0)


def test_feret_max_is_farthest_pair():
    """The maximum Feret diameter equals the greatest pairwise distance among
    the points. We verify against a brute-force all-pairs maximum.
    """
    pts = [[0, 0], [10, 1], [3, 9], [-2, 4], [7, -3]]
    brute_max = max(
        math.dist(p, q) for i, p in enumerate(pts) for q in pts[i + 1:]
    )
    _, mx = feret([list(p) for p in pts])
    assert mx == pytest.approx(brute_max)


def test_feret_translation_invariant():
    """Feret diameters depend only on shape, not absolute position."""
    square = [[0, 0], [10, 0], [10, 10], [0, 10]]
    shifted = [[x + 1000, y - 500] for x, y in square]
    mn0, mx0 = feret([list(p) for p in square])
    mn1, mx1 = feret([list(p) for p in shifted])
    assert mn0 == pytest.approx(mn1)
    assert mx0 == pytest.approx(mx1)


@pytest.mark.parametrize(
    "pts",
    [
        [],                       # empty
        [[1, 1]],                 # single point
        [[2, 2], [2, 2], [2, 2]], # all coincident -> degenerate hull
    ],
)
def test_feret_degenerate_is_zero(pts):
    """A degenerate point set (no extent) has Feret diameters (0, 0)."""
    assert feret([list(p) for p in pts]) == (0.0, 0.0)


def test_feret_mutates_input_documented():
    """Documenting a real wart: feret() calls Points.sort(), reordering the
    caller's list in place. This is not desired behavior, just pinned so a
    future fix is a visible, intentional change rather than a silent one.
    """
    pts = [[10, 10], [0, 0], [10, 0], [0, 10]]
    feret(pts)
    assert pts == sorted(pts)  # input was sorted in place by feret
