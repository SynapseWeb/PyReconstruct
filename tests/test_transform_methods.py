"""Tests for Transform methods not covered by test_transform.py / test_geometry.py.

Covers composition (__mul__), inverted(), imageTransform(), magScale() (which
MUTATES in place), the det property, equals() tolerance, getLinear(), identity(),
and the fromQTransform <-> getQTransform round-trip.

Expected values are independently derived: hand-computed inverses/composites,
QTransform's documented affine convention (a Transform list [t0..t5] builds
QTransform(t0, t3, t1, t4, t2, t5), i.e. m11=t0, m21=t1, m31=t2, m12=t3,
m22=t4, m32=t5), and the mathematical identities of inverse/composition.

Note on composition order: QTransform uses the row-vector convention, so for
two transforms the product (A * B) applies A first and then B; concretely
(A * B).map(p) == B.map(A.map(p)). The tests assert that real order.
"""
import math
import pytest

from PyReconstruct.modules.datatypes.transform import Transform

# Assorted transforms exercised across several tests.
TFORMS = [
    ("identity", [1, 0, 0, 0, 1, 0]),
    ("translate", [1, 0, 5.5, 0, 1, -3.25]),
    ("scale", [2.0, 0, 0, 0, 0.5, 0]),
    ("rotate", [math.cos(0.3), -math.sin(0.3), 10, math.sin(0.3), math.cos(0.3), -7]),
    ("shear", [1, 0.4, 0, 0.2, 1, 0]),
    ("affine", [1.3, 0.2, 4.0, -0.1, 0.9, 2.5]),
]
# All of the above are invertible (nonzero determinant).
INVERTIBLE = TFORMS

PTS = [(0, 0), (1, 2), (-3.5, 4.25), (100.1, -200.2)]


# ---------------------------------------------------------------------------
# getQTransform / fromQTransform component placement and round-trip
# ---------------------------------------------------------------------------

def test_getQTransform_component_placement():
    # Distinct components so each slot is unambiguous.
    q = Transform([10, 20, 30, 40, 50, 60]).getQTransform()
    assert q.m11() == 10
    assert q.m21() == 20
    assert q.m31() == 30
    assert q.m12() == 40
    assert q.m22() == 50
    assert q.m32() == 60
    # dx/dy alias the translation row.
    assert q.dx() == 30
    assert q.dy() == 60


@pytest.mark.parametrize("name,t", TFORMS, ids=[x[0] for x in TFORMS])
def test_fromQTransform_getQTransform_roundtrip(name, t):
    orig = Transform(list(t))
    rebuilt = Transform.fromQTransform(orig.getQTransform())
    for got, exp in zip(rebuilt.getList(), t):
        assert got == pytest.approx(exp, abs=1e-12)


def test_fromQTransform_returns_transform():
    out = Transform.fromQTransform(Transform([1, 0, 0, 0, 1, 0]).getQTransform())
    assert isinstance(out, Transform)


# ---------------------------------------------------------------------------
# __mul__ : composition semantics
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name_a,a", TFORMS, ids=[x[0] for x in TFORMS])
@pytest.mark.parametrize("name_b,b", TFORMS, ids=[x[0] for x in TFORMS])
def test_mul_matches_sequential_map(name_a, a, name_b, b):
    # QTransform row-vector convention: (A*B).map(p) == B.map(A.map(p)).
    A = Transform(list(a))
    B = Transform(list(b))
    C = A * B
    for p in PTS:
        cx, cy = C.map(*p)
        sx, sy = B.map(*A.map(*p))
        assert cx == pytest.approx(sx, abs=1e-9)
        assert cy == pytest.approx(sy, abs=1e-9)


def test_mul_order_is_not_symmetric_for_noncommuting():
    # A scale-then-translate composed with a translate does not commute;
    # this guards against silently swapping the composition order.
    A = Transform([2.0, 0, 1.0, 0, 3.0, -2.0])
    B = Transform([1, 0, 5.0, 0, 1, 7.0])
    p = (4.0, -1.0)
    ab = (A * B).map(*p)
    ba = (B * A).map(*p)
    # Hand-computed: A.map(p) = (2*4+1, 3*-1-2) = (9, -5); then B: (+5,+7) => (14, 2).
    assert ab == pytest.approx((14.0, 2.0), abs=1e-9)
    # The reversed product gives a different result.
    assert ba[0] != pytest.approx(ab[0], abs=1e-6) or ba[1] != pytest.approx(ab[1], abs=1e-6)


@pytest.mark.parametrize("name,t", TFORMS, ids=[x[0] for x in TFORMS])
def test_mul_identity_is_neutral(name, t):
    A = Transform(list(t))
    I = Transform.identity()
    for got in (A * I).getList(), (I * A).getList():
        for g, e in zip(got, t):
            assert g == pytest.approx(e, abs=1e-12)


def test_mul_returns_transform():
    A = Transform([1.3, 0.2, 4.0, -0.1, 0.9, 2.5])
    assert isinstance(A * A, Transform)


# ---------------------------------------------------------------------------
# inverted()
# ---------------------------------------------------------------------------

def test_inverted_hand_computed():
    # t: x' = 2x + 3, y' = 4y + 5. Inverse: x = (x'-3)/2, y = (y'-5)/4
    # => [0.5, 0, -1.5, 0, 0.25, -1.25].
    inv = Transform([2, 0, 3, 0, 4, 5]).inverted()
    expected = [0.5, 0.0, -1.5, 0.0, 0.25, -1.25]
    for got, exp in zip(inv.getList(), expected):
        assert got == pytest.approx(exp, abs=1e-12)


@pytest.mark.parametrize("name,t", INVERTIBLE, ids=[x[0] for x in INVERTIBLE])
def test_inverted_double_roundtrip(name, t):
    tform = Transform(list(t))
    twice = tform.inverted().inverted()
    assert tform.equals(twice)
    # And explicitly within a tight tolerance.
    for got, exp in zip(twice.getList(), t):
        assert got == pytest.approx(exp, abs=1e-9)


@pytest.mark.parametrize("name,t", INVERTIBLE, ids=[x[0] for x in INVERTIBLE])
def test_inverted_composes_to_identity_in_mapping(name, t):
    tform = Transform(list(t))
    inv = tform.inverted()
    # t followed by its inverse maps every point back to itself.
    for p in PTS:
        bx, by = inv.map(*tform.map(*p))
        assert bx == pytest.approx(p[0], abs=1e-7)
        assert by == pytest.approx(p[1], abs=1e-7)
    # And the composed transform is the identity (to numeric tolerance).
    assert (tform * inv).equals(Transform.identity())
    assert (inv * tform).equals(Transform.identity())


def test_inverted_of_identity_is_identity():
    assert Transform.identity().inverted().equals(Transform.identity())


def test_inverted_singular_raises():
    # Determinant 1*4 - 2*2 = 0 -> not invertible.
    with pytest.raises(Exception):
        Transform([1, 2, 0, 2, 4, 0]).inverted()


# ---------------------------------------------------------------------------
# imageTransform()
# ---------------------------------------------------------------------------

def test_imageTransform_formula():
    # imageTransform of [a,b,c,d,e,f] == [a, -b, 0, -d, e, 0].
    out = Transform([2.0, 0.5, 9.0, 0.3, 4.0, -8.0]).imageTransform()
    assert out.getList() == [2.0, -0.5, 0, -0.3, 4.0, 0]


def test_imageTransform_drops_translation_and_negates_offdiag():
    a, b, c, d, e, f = 1.3, 0.2, 4.0, -0.1, 0.9, 2.5
    out = Transform([a, b, c, d, e, f]).imageTransform().getList()
    assert out[0] == pytest.approx(a)
    assert out[1] == pytest.approx(-b)
    assert out[2] == 0
    assert out[3] == pytest.approx(-d)
    assert out[4] == pytest.approx(e)
    assert out[5] == 0


def test_imageTransform_returns_new_transform():
    src = Transform([2.0, 0.5, 9.0, 0.3, 4.0, -8.0])
    out = src.imageTransform()
    assert isinstance(out, Transform)
    # Source is not mutated.
    assert src.getList() == [2.0, 0.5, 9.0, 0.3, 4.0, -8.0]


# ---------------------------------------------------------------------------
# magScale() -- MUTATES in place, scales translation by new/prev
# ---------------------------------------------------------------------------

def test_magScale_mutates_translation_components():
    t = Transform([1.0, 0.0, 10.0, 0.0, 1.0, 20.0])
    ret = t.magScale(2.0, 6.0)  # factor new/prev = 3
    assert ret is None  # mutates in place, returns nothing
    assert t.getList() == [1.0, 0.0, 30.0, 0.0, 1.0, 60.0]


def test_magScale_leaves_linear_part_untouched():
    t = Transform([1.3, 0.2, 4.0, -0.1, 0.9, 2.5])
    t.magScale(4.0, 1.0)  # factor 0.25
    lst = t.getList()
    # Linear components unchanged.
    assert lst[0] == pytest.approx(1.3)
    assert lst[1] == pytest.approx(0.2)
    assert lst[3] == pytest.approx(-0.1)
    assert lst[4] == pytest.approx(0.9)
    # Translation scaled by 0.25.
    assert lst[2] == pytest.approx(1.0)
    assert lst[5] == pytest.approx(0.625)


def test_magScale_identity_factor_is_noop():
    t = Transform([1.3, 0.2, 4.0, -0.1, 0.9, 2.5])
    t.magScale(3.0, 3.0)  # factor 1.0
    for got, exp in zip(t.getList(), [1.3, 0.2, 4.0, -0.1, 0.9, 2.5]):
        assert got == pytest.approx(exp)


# ---------------------------------------------------------------------------
# det property
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "tform,expected",
    [
        ([2, 0, 0, 0, 3, 0], 6.0),     # diagonal scale: 2*3
        ([1, 2, 0, 3, 4, 0], -2.0),    # a*e - b*d = 1*4 - 2*3
        ([1, 2, 0, 2, 4, 0], 0.0),     # singular
        ([1, 0, 0, 0, 1, 0], 1.0),     # identity
        ([1, 0, 99, 0, 1, -42], 1.0),  # translation does not affect det
    ],
)
def test_det_equals_linear_determinant(tform, expected):
    # det of [a,b,c,d,e,f] == a*e - b*d (translation row ignored).
    assert Transform(tform).det == pytest.approx(expected, abs=1e-12)


def test_det_negative_for_reflection():
    # A reflection (e.g. negative x-scale) has negative determinant.
    assert Transform([-1, 0, 0, 0, 1, 0]).det == pytest.approx(-1.0, abs=1e-12)


# ---------------------------------------------------------------------------
# equals() -- tolerance 1e-6
# ---------------------------------------------------------------------------

def test_equals_identical():
    a = Transform([1.3, 0.2, 4.0, -0.1, 0.9, 2.5])
    b = Transform([1.3, 0.2, 4.0, -0.1, 0.9, 2.5])
    assert a.equals(b)


def test_equals_within_tolerance():
    base = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    nudged = [v + 9e-7 for v in base]  # below 1e-6 threshold
    assert Transform(base).equals(Transform(nudged))


def test_equals_outside_tolerance():
    base = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    off = list(base)
    off[0] += 2e-6  # above 1e-6 threshold
    assert not Transform(base).equals(Transform(off))


def test_equals_difference_in_any_component():
    base = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    for i in range(6):
        other = list(base)
        other[i] += 1.0
        assert not Transform(base).equals(Transform(other)), f"component {i}"


def test_equals_is_symmetric():
    a = Transform([1.0, 0.0, 0.0, 0.0, 1.0, 0.0])
    b = Transform([1.0, 0.0, 0.0, 0.0, 1.0, 5e-7])
    assert a.equals(b) == b.equals(a)


# ---------------------------------------------------------------------------
# getLinear() -- zeros the translation, keeps linear part
# ---------------------------------------------------------------------------

def test_getLinear_zeros_translation():
    out = Transform([1.3, 0.2, 4.0, -0.1, 0.9, 2.5]).getLinear()
    assert out.getList() == [1.3, 0.2, 0, -0.1, 0.9, 0]


def test_getLinear_does_not_mutate_source():
    src = Transform([1.3, 0.2, 4.0, -0.1, 0.9, 2.5])
    src.getLinear()
    assert src.getList() == [1.3, 0.2, 4.0, -0.1, 0.9, 2.5]


def test_getLinear_maps_origin_to_origin():
    # With translation removed, the origin is a fixed point.
    out = Transform([1.3, 0.2, 4.0, -0.1, 0.9, 2.5]).getLinear()
    x, y = out.map(0.0, 0.0)
    assert x == pytest.approx(0.0)
    assert y == pytest.approx(0.0)


@pytest.mark.parametrize("name,t", TFORMS, ids=[x[0] for x in TFORMS])
def test_getLinear_preserves_vector_differences(name, t):
    # The linear part is exactly the full map minus its action on the origin,
    # so map(p) - map(0) is unchanged by dropping the translation.
    full = Transform(list(t))
    lin = full.getLinear()
    o = full.map(0.0, 0.0)
    for p in PTS:
        fx, fy = full.map(*p)
        lx, ly = lin.map(*p)
        assert lx == pytest.approx(fx - o[0], abs=1e-9)
        assert ly == pytest.approx(fy - o[1], abs=1e-9)


# ---------------------------------------------------------------------------
# identity()
# ---------------------------------------------------------------------------

def test_identity_list():
    assert Transform.identity().getList() == [1, 0, 0, 0, 1, 0]


@pytest.mark.parametrize("p", PTS)
def test_identity_maps_points_unchanged(p):
    x, y = Transform.identity().map(*p)
    assert x == pytest.approx(p[0])
    assert y == pytest.approx(p[1])


def test_identity_det_is_one():
    assert Transform.identity().det == pytest.approx(1.0)
