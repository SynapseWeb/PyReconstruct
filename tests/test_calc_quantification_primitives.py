"""Unit tests for the geometry primitives in modules/calc/quantification.py.

Covers the scalar/elementary helpers that the rest of the app (and the
vectorized traceGeometry hot path) is built on: shoelace area, polygon
centroid, 2D/3D Euclidean distance, polyline length, significant-figure
rounding, segment orientation/intersection, contour intersection, ellipse
sampling, the deterministic colorize palette, and the OpenCV-backed
point-in-polygon / distance-from-trace helpers.

Expected values are hand-derived from known geometry (shoelace, geometric
centroids, Pythagorean triples, perimeters) and mathematical identities
(orientation independence of area magnitude and centroid, symmetry), not
echoed back from the functions under test. traceGeometry and the
interpolate_points empty/single guard are covered elsewhere and not retested.
"""
import math

import pytest

from PyReconstruct.modules.calc.quantification import (
    area,
    centroid,
    distance,
    distance3D,
    euclidean_distance,
    lineDistance,
    sigfigRound,
    ccw,
    linesIntersect,
    lineIntersectsContour,
    colorize,
    ellipseFromPair,
    pointInPoly,
    getDistanceFromTrace,
)


# A unit/known square reused across several tests.
SQUARE = [(0, 0), (10, 0), (10, 10), (0, 10)]          # CCW, area 100, perim 40
SQUARE_CW = [(0, 0), (0, 10), (10, 10), (10, 0)]       # same square, reversed
SQUARE_100 = [(0, 0), (100, 0), (100, 100), (0, 100)]  # for OpenCV int tests


# --------------------------------------------------------------------------- #
# area() -- shoelace, unsigned                                                #
# --------------------------------------------------------------------------- #

def test_area_square():
    assert area(SQUARE) == pytest.approx(100.0)


def test_area_triangle():
    # base 4, height 3 -> 1/2 * 4 * 3 = 6
    assert area([(0, 0), (4, 0), (2, 3)]) == pytest.approx(6.0)


@pytest.mark.parametrize("pts", [[], [(0, 0)], [(0, 0), (1, 1)]])
def test_area_two_or_fewer_points_is_zero(pts):
    assert area(pts) == 0


def test_area_auto_closes_open_ring():
    # An explicitly-closed square (first == last) must give the same area
    # as the open form; the function appends the first point if needed.
    closed = SQUARE + SQUARE[:1]
    assert area(closed) == pytest.approx(area(SQUARE))


def test_area_is_unsigned_orientation_independent():
    # Shoelace is signed by winding; area() takes abs, so CW == CCW magnitude.
    assert area(SQUARE_CW) == pytest.approx(area(SQUARE))


def test_area_collinear_points_zero():
    assert area([(0, 0), (1, 1), (2, 2), (3, 3)]) == pytest.approx(0.0)


# --------------------------------------------------------------------------- #
# centroid() -- area-weighted, mean fallback for degenerate shapes            #
# --------------------------------------------------------------------------- #

def test_centroid_unit_square():
    assert centroid([(0, 0), (1, 0), (1, 1), (0, 1)]) == (0.5, 0.5)


def test_centroid_triangle_equals_vertex_mean():
    # The centroid of a triangle is the mean of its vertices: (0+6+0)/3 = 2.
    assert centroid([(0, 0), (6, 0), (0, 6)]) == (2.0, 2.0)


def test_centroid_offset_square_translates():
    # Centroid of a square translated to (100,200): center is (101,201).
    pts = [(100, 200), (102, 200), (102, 202), (100, 202)]
    assert centroid(pts) == (101.0, 201.0)


def test_centroid_orientation_independent():
    # Reversing the winding must not move the centroid.
    assert centroid(SQUARE_CW) == centroid(SQUARE)


def test_centroid_degenerate_falls_back_to_mean_of_points():
    # Collinear -> zero area -> mean of the supplied points: (0+1+2+3)/4 = 1.5.
    assert centroid([(0, 0), (1, 1), (2, 2), (3, 3)]) == (1.5, 1.5)


def test_centroid_two_points_mean():
    # <=2 pts has zero area; result is the mean: ((0+2)/2, (0+4)/2).
    assert centroid([(0, 0), (2, 4)]) == (1.0, 2.0)


def test_centroid_rounded_to_six_places():
    cx, cy = centroid([(0, 0), (3, 0), (3, 7), (0, 7)])
    # Each coordinate is round(_, 6): no more than 6 decimal places.
    assert cx == round(cx, 6)
    assert cy == round(cy, 6)
    assert (cx, cy) == (1.5, 3.5)


# --------------------------------------------------------------------------- #
# distance(), distance3D(), euclidean_distance()                              #
# --------------------------------------------------------------------------- #

def test_distance_3_4_5():
    assert distance(0, 0, 3, 4) == pytest.approx(5.0)


def test_distance_symmetric_and_zero():
    assert distance(1, 2, 4, 6) == pytest.approx(distance(4, 6, 1, 2))
    assert distance(7, 7, 7, 7) == pytest.approx(0.0)


def test_distance3D_known_triple():
    # (1,2,2) has magnitude sqrt(1+4+4) = 3.
    assert distance3D(0, 0, 0, 1, 2, 2) == pytest.approx(3.0)


def test_distance3D_z_order_symmetric():
    # Only (z2 - z1)**2 enters; swapping z endpoints can't change the result.
    assert distance3D(0, 0, 5, 0, 0, 2) == pytest.approx(distance3D(0, 0, 2, 0, 0, 5))


def test_distance3D_reduces_to_2d_when_z_equal():
    assert distance3D(0, 0, 9, 3, 4, 9) == pytest.approx(5.0)


def test_euclidean_distance_matches_distance():
    assert float(euclidean_distance((0, 0), (3, 4))) == pytest.approx(5.0)
    assert float(euclidean_distance((1, 1), (4, 5))) == pytest.approx(
        distance(1, 1, 4, 5)
    )


# --------------------------------------------------------------------------- #
# lineDistance() -- polyline length, open vs closed                           #
# --------------------------------------------------------------------------- #

def test_line_distance_closed_square_perimeter():
    # Four edges of length 10 -> 40.
    assert lineDistance(SQUARE, closed=True) == pytest.approx(40.0)


def test_line_distance_open_square_drops_closing_edge():
    # Open path omits the final return edge -> 30.
    assert lineDistance(SQUARE, closed=False) == pytest.approx(30.0)


@pytest.mark.parametrize("pts", [[], [(5, 5)]])
def test_line_distance_one_or_fewer_points_is_zero(pts):
    assert lineDistance(pts) == 0


def test_line_distance_open_triangle_vs_closed():
    tri = [(0, 0), (3, 0), (3, 4)]
    # open: 3 + 4 = 7; closed adds the hypotenuse 5 -> 12.
    assert lineDistance(tri, closed=False) == pytest.approx(7.0)
    assert lineDistance(tri, closed=True) == pytest.approx(12.0)


def test_line_distance_rounded_to_seven_places():
    val = lineDistance(SQUARE, closed=True)
    assert val == round(val, 7)


# --------------------------------------------------------------------------- #
# sigfigRound()                                                               #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "n,sf,expected",
    [
        (12345, 2, 12000),
        (12345, 1, 10000),
        (6789, 1, 7000),
        (0.012345, 2, 0.012),
        (0.0123456, 3, 0.0123),
        (-12345, 2, -12000),
        (-0.012345, 2, -0.012),
    ],
)
def test_sigfig_round_values(n, sf, expected):
    assert sigfigRound(n, sf) == pytest.approx(expected)


def test_sigfig_round_zero_returns_zero():
    assert sigfigRound(0, 3) == 0


def test_sigfig_round_keeps_count_of_significant_digits():
    # 123456 to 3 s.f. -> 123000.
    assert sigfigRound(123456, 3) == pytest.approx(123000)


# --------------------------------------------------------------------------- #
# ccw() -- orientation of an ordered triple                                   #
# --------------------------------------------------------------------------- #

def test_ccw_counterclockwise_true():
    assert ccw((0, 0), (1, 0), (0, 1)) is True


def test_ccw_clockwise_false():
    assert ccw((0, 0), (0, 1), (1, 0)) is False


def test_ccw_collinear_false():
    # Strict inequality: collinear triples are not counterclockwise.
    assert ccw((0, 0), (1, 1), (2, 2)) is False


def test_ccw_reversing_two_points_flips_orientation():
    a, b, c = (0, 0), (3, 1), (1, 4)
    assert ccw(a, b, c) != ccw(a, c, b)


# --------------------------------------------------------------------------- #
# linesIntersect() -- crossing / parallel / shared endpoint                   #
# --------------------------------------------------------------------------- #

def test_lines_intersect_crossing_x():
    # Diagonals of a square cross in the middle.
    assert linesIntersect((0, 0), (2, 2), (0, 2), (2, 0)) is True


def test_lines_intersect_parallel_false():
    assert linesIntersect((0, 0), (2, 0), (0, 1), (2, 1)) is False
    assert linesIntersect((0, 0), (0, 2), (1, 0), (1, 2)) is False


def test_lines_intersect_disjoint_collinear_false():
    assert linesIntersect((0, 0), (1, 0), (2, 0), (3, 0)) is False


def test_lines_intersect_shared_endpoint_true():
    # Two segments meeting at a common endpoint count as intersecting.
    assert linesIntersect((0, 0), (1, 0), (1, 0), (1, 1)) is True


def test_lines_intersect_t_junction_true():
    # Endpoint of CD lands on the interior of AB.
    assert linesIntersect((0, 0), (4, 0), (2, 0), (2, 2)) is True


# --------------------------------------------------------------------------- #
# lineIntersectsContour() -- segment vs polygon, open and closed              #
# --------------------------------------------------------------------------- #

def test_segment_crosses_closed_square():
    # Horizontal line spanning across the square at y=5 crosses two edges.
    assert lineIntersectsContour(-5, 5, 15, 5, SQUARE, closed=True) is True


def test_segment_misses_square():
    # Vertical line entirely to the left of the square.
    assert lineIntersectsContour(-5, -5, -5, 15, SQUARE, closed=True) is False


def test_open_contour_skips_closing_edge():
    # The segment from (-5,5) to (5,5) only crosses the LEFT edge, which for
    # SQUARE is the closing edge (last->first). Closed sees it; open does not.
    assert lineIntersectsContour(-5, 5, 5, 5, SQUARE, closed=True) is True
    assert lineIntersectsContour(-5, 5, 5, 5, SQUARE, closed=False) is False


def test_segment_through_interior_crosses_when_reaching_an_edge():
    # A segment from inside the square out the right side crosses the right edge
    # in both open and closed modes (that edge is not the closing one).
    assert lineIntersectsContour(5, 5, 15, 5, SQUARE, closed=True) is True
    assert lineIntersectsContour(5, 5, 15, 5, SQUARE, closed=False) is True


# --------------------------------------------------------------------------- #
# ellipseFromPair()                                                           #
# --------------------------------------------------------------------------- #

def test_ellipse_point_count_matches_number():
    assert len(ellipseFromPair(0, 0, 10, 10, number=37)) == 37
    assert len(ellipseFromPair(0, 0, 10, 10)) == 100  # default


def test_ellipse_axis_aligned_bbox():
    # Diagonal corners (0,0)-(10,10): center (5,5), a=b=5 -> bbox [0,10]x[0,10].
    pts = ellipseFromPair(0, 0, 10, 10, number=200)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    assert (min(xs), max(xs)) == (0, 10)
    assert (min(ys), max(ys)) == (0, 10)


def test_ellipse_nonsymmetric_bbox_and_first_point():
    # (2,3)-(8,11): center (5,7), a=3, b=4.
    pts = ellipseFromPair(2, 3, 8, 11, number=200)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    assert (min(xs), max(xs)) == (2, 8)
    assert (min(ys), max(ys)) == (3, 11)
    # i=0: cos=1, sin=0 -> (center_x + a, center_y) = (8, 7).
    assert pts[0] == (8, 7)


# --------------------------------------------------------------------------- #
# colorize()                                                                  #
# --------------------------------------------------------------------------- #

def test_colorize_returns_three_channels_in_range():
    for n in range(0, 400):
        c = colorize(n)
        assert len(c) == 3
        assert all(100 <= v <= 255 for v in c)


def test_colorize_is_deterministic():
    assert colorize(42) == colorize(42)


def test_colorize_period_156():
    # n enters as (n % 156)**3, so inputs 156 apart collide.
    assert colorize(0) == colorize(156)
    assert colorize(3) == colorize(3 + 156)


# --------------------------------------------------------------------------- #
# pointInPoly() / getDistanceFromTrace() -- OpenCV-backed (int rounding)      #
# --------------------------------------------------------------------------- #

def test_point_in_poly_inside_true():
    assert pointInPoly(50, 50, SQUARE_100) is True


def test_point_in_poly_outside_false():
    assert pointInPoly(150, 50, SQUARE_100) is False


def test_point_in_poly_on_boundary_true():
    # OpenCV returns 0 on the boundary; pointInPoly treats >= 0 as inside.
    assert pointInPoly(0, 50, SQUARE_100) is True


def test_distance_from_trace_inside_nearest_edge():
    # (50,50) is 50 from the nearest edge of a 100x100 square.
    assert getDistanceFromTrace(50, 50, SQUARE_100) == pytest.approx(50.0)


def test_distance_from_trace_absolute_outside():
    # (150,50) is 50 outside the right edge; absolute (default) -> +50.
    assert getDistanceFromTrace(150, 50, SQUARE_100) == pytest.approx(50.0)


def test_distance_from_trace_signed_inside_positive_outside_negative():
    # Signed convention: inside positive, outside negative.
    assert getDistanceFromTrace(50, 50, SQUARE_100, absolute=False) == pytest.approx(50.0)
    assert getDistanceFromTrace(150, 50, SQUARE_100, absolute=False) == pytest.approx(-50.0)


def test_distance_from_trace_on_edge_zero():
    assert getDistanceFromTrace(0, 50, SQUARE_100) == pytest.approx(0.0)