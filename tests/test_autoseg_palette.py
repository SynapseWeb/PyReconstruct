"""Tests for the autoseg trace-color palette.

Verifies that autoseg import assigns colors from a curated, grayscale-visible
whitelist, deterministically mapped from each label id.
"""

import pytest

from PyReconstruct.modules.backend.autoseg.palette import (
    DEFAULT_AUTOSEG_PALETTE,
    palette_color,
    palette_color_array,
    next_shuffle_seed,
)

# Thresholds separating a usable overlay color from the grayscale background.
# chroma = max(RGB) - min(RGB): distance from the achromatic ("gray") axis.
# value  = max(RGB): overall brightness (guards against near-black tones).
MIN_CHROMA = 60
MIN_VALUE = 120

# Sampling range for id -> color assertions.
SAMPLE_IDS = range(1, 5000)


def _chroma(color):
    return max(color) - min(color)


def _value(color):
    return max(color)


# --- palette content -------------------------------------------------------


def test_palette_is_nonempty_and_reasonable_size():
    assert 8 <= len(DEFAULT_AUTOSEG_PALETTE) <= 24


def test_palette_entries_are_rgb_int_triples_in_range():
    for color in DEFAULT_AUTOSEG_PALETTE:
        assert len(color) == 3
        for channel in color:
            assert isinstance(channel, int)
            assert 0 <= channel <= 255


def test_palette_has_no_near_gray_or_dark_colors():
    """Every whitelist color must sit off the gray axis and not be too dark."""
    for color in DEFAULT_AUTOSEG_PALETTE:
        assert _chroma(color) >= MIN_CHROMA, f"{color} is too close to gray"
        assert _value(color) >= MIN_VALUE, f"{color} is too dark"


def test_palette_entries_are_distinct():
    assert len(set(DEFAULT_AUTOSEG_PALETTE)) == len(DEFAULT_AUTOSEG_PALETTE)


# --- deterministic id -> color mapping -------------------------------------


def test_mapping_is_deterministic():
    """Same id (and seed) always yields the same color."""
    for label_id in SAMPLE_IDS:
        assert palette_color(label_id) == palette_color(label_id)


def test_mapping_matches_known_reference_values():
    """Pin the exact id -> color mapping so the hash cannot drift silently."""
    expected = {
        0: (240, 228, 66),
        1: (204, 121, 167),
        2: (86, 180, 233),
        3: (178, 0, 0),
        5: (0, 0, 178),
        42: (240, 228, 66),
        100: (51, 255, 187),
        1000: (0, 158, 115),
    }
    for label_id, color in expected.items():
        assert palette_color(label_id) == color


def test_every_produced_color_is_from_the_whitelist():
    whitelist = set(DEFAULT_AUTOSEG_PALETTE)
    for seed in (0, 1, 7, 12345):
        for label_id in SAMPLE_IDS:
            assert palette_color(label_id, seed=seed) in whitelist


def test_produced_colors_are_never_near_gray():
    for label_id in SAMPLE_IDS:
        color = palette_color(label_id)
        assert _chroma(color) >= MIN_CHROMA
        assert _value(color) >= MIN_VALUE


def test_mapping_covers_whole_palette():
    """A good hash should reach every palette entry over enough ids."""
    seen = {palette_color(label_id) for label_id in SAMPLE_IDS}
    assert seen == set(DEFAULT_AUTOSEG_PALETTE)


def test_consecutive_ids_are_scattered():
    """Consecutive label ids should not all collapse to one color."""
    colors = [palette_color(label_id) for label_id in range(1, 13)]
    assert len(set(colors)) >= len(DEFAULT_AUTOSEG_PALETTE) // 2


# --- seed behavior ---------------------------------------------------------


def test_seed_reshuffles_assignment():
    """Changing the seed changes at least some id -> color assignments."""
    differ = any(
        palette_color(label_id, seed=0) != palette_color(label_id, seed=1)
        for label_id in SAMPLE_IDS
    )
    assert differ


def test_seed_is_still_deterministic():
    for label_id in SAMPLE_IDS:
        assert palette_color(label_id, seed=99) == palette_color(label_id, seed=99)


# --- shuffle ("Shuffle colors" button) -------------------------------------
#
# The button calls next_shuffle_seed to pick a new seed. Each click must
# visibly change the id -> color arrangement, and the result must stay a plain
# deterministic seed so preview==import still holds.


def _arrangement(seed, palette=None):
    return [palette_color(i, palette, seed) for i in range(1, 64)]


def test_shuffle_changes_the_arrangement():
    """A shuffle must produce a genuinely different id -> color mapping."""
    import random
    seed = 0
    for _ in range(25):  # simulate repeated clicks
        new_seed = next_shuffle_seed(seed, rng=random.Random(_))
        assert _arrangement(new_seed) != _arrangement(seed)
        seed = new_seed


def test_shuffle_returns_plain_int_seed():
    """Result is a concrete non-negative int -> stays deterministic/persistable."""
    import random
    new_seed = next_shuffle_seed(0, rng=random.Random(1))
    assert isinstance(new_seed, int)
    assert new_seed >= 0
    # and it drives the same deterministic mapping every time it is reused
    assert _arrangement(new_seed) == _arrangement(new_seed)


def test_shuffle_is_reproducible_with_seeded_rng():
    """Injecting the same rng yields the same choice (testability/determinism)."""
    import random
    a = next_shuffle_seed(0, rng=random.Random(1234))
    b = next_shuffle_seed(0, rng=random.Random(1234))
    assert a == b


def test_shuffle_noop_on_single_color_palette():
    """No reshuffle exists for a <2 color palette; the seed is left unchanged."""
    import random
    assert next_shuffle_seed(5, palette=[(1, 2, 3)], rng=random.Random(0)) == 5


def test_shuffle_changes_the_visible_ids_when_supplied():
    """When present ids are supplied, the guarantee applies to THEM: the
    visible ids' colors must change on every click, not just some fixed 1..63
    fingerprint (which could move while the on-screen labels do not)."""
    import random
    visible = [3, 17, 42]

    def vis_arr(seed):
        return [palette_color(i, DEFAULT_AUTOSEG_PALETTE, seed) for i in visible]

    seed = 0
    for _ in range(25):  # simulate repeated clicks
        new_seed = next_shuffle_seed(seed, ids=visible, rng=random.Random(_))
        assert vis_arr(new_seed) != vis_arr(seed)
        seed = new_seed


def test_shuffle_empty_or_none_ids_fall_back_to_default_range():
    """Empty/None ids -> the default 1..63 fingerprint (still reshuffles)."""
    import random
    a = next_shuffle_seed(0, ids=[], rng=random.Random(1))
    b = next_shuffle_seed(0, ids=None, rng=random.Random(1))
    c = next_shuffle_seed(0, rng=random.Random(1))
    assert a == b == c
    assert _arrangement(a) != _arrangement(0)


def test_shuffle_ids_drop_background_zero():
    """id 0 (background) is dropped from the fingerprint; [0] behaves as empty
    and falls back to the default range."""
    import random
    a = next_shuffle_seed(0, ids=[0], rng=random.Random(7))
    b = next_shuffle_seed(0, rng=random.Random(7))
    assert a == b


# --- override / fallback ---------------------------------------------------


def test_empty_or_none_palette_falls_back_to_default():
    """An empty override (the shipped option default) uses the built-in palette."""
    assert palette_color(3, palette=None) == palette_color(3)
    assert palette_color(3, palette=[]) == palette_color(3)


def test_custom_palette_is_respected():
    custom = [(1, 2, 3), (4, 5, 6)]
    for label_id in SAMPLE_IDS:
        assert palette_color(label_id, palette=custom) in custom


def test_return_type_is_int_tuple():
    color = palette_color(7)
    assert isinstance(color, tuple)
    assert all(isinstance(channel, int) for channel in color)


# --- color-vision-deficiency (CVD) distinguishability ----------------------
#
# Simulate deuteranopia / protanopia / tritanopia with the Machado et al. (2009)
# severity-1.0 matrices (applied in linear RGB) and require every pair of
# palette colors to stay perceptually separated (CIEDE2000) under each
# deficiency. This guards against a future edit reintroducing a CVD collision
# (e.g. the yellow/lime pair that merges under red-green deficiency).

# Minimum acceptable pairwise CIEDE2000 separation. The shipped palette holds a
# worst case of ~10.9 under tritanopia; 9.0 leaves margin while still catching a
# regression that pulls two colors together.
MIN_CVD_DELTA_E = 9.0
MIN_NORMAL_DELTA_E = 10.0

_MACHADO = {
    "protan": [[0.152286, 1.052583, -0.204868],
               [0.114503, 0.786281, 0.099216],
               [-0.003882, -0.048116, 1.051998]],
    "deutan": [[0.367322, 0.860646, -0.227968],
               [0.280085, 0.672501, 0.047413],
               [-0.011820, 0.042940, 0.968881]],
    "tritan": [[1.255528, -0.076749, -0.178779],
               [-0.078411, 0.930809, 0.147602],
               [0.004733, 0.691367, 0.303900]],
}


def _simulate(rgb255, kind, np):
    c = np.asarray(rgb255, float) / 255.0
    if kind == "normal":
        return c
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    sim = np.clip(np.asarray(_MACHADO[kind]) @ lin, 0.0, 1.0)
    return np.where(sim <= 0.0031308, sim * 12.92,
                    1.055 * (sim ** (1 / 2.4)) - 0.055)


def _min_pairwise_delta_e(kind):
    import numpy as np
    from itertools import combinations
    from skimage.color import rgb2lab, deltaE_ciede2000

    labs = []
    for color in DEFAULT_AUTOSEG_PALETTE:
        sim = _simulate(color, kind, np).reshape(1, 1, 3)
        labs.append(rgb2lab(sim))
    return min(
        # deltaE_ciede2000 on (1,1,3) Lab inputs returns a (1,1) array; numpy
        # >= 2.0 refuses float() on a non-0-d array, so flatten to a scalar
        # (robust across numpy/skimage versions).
        float(np.ravel(deltaE_ciede2000(a, b))[0]) for a, b in combinations(labs, 2)
    )


# --- vectorized overlay mapping ---------------------------------------------
#
# The live label overlay is colored with palette_color_array; it must produce
# exactly the color palette_color would give each id, so the preview matches
# the imported traces.


def test_overlay_array_matches_scalar_mapping():
    np = pytest.importorskip("numpy")
    arr = np.array([[0, 1, 2, 3], [5, 42, 100, 1000]], dtype=np.int64)
    out = palette_color_array(arr, None, seed=0, background=(100, 100, 100))
    assert out.shape == (2, 4, 3)
    assert out.dtype == np.uint8
    for y in range(arr.shape[0]):
        for x in range(arr.shape[1]):
            lid = int(arr[y, x])
            expected = (100, 100, 100) if lid == 0 else palette_color(lid)
            assert tuple(int(v) for v in out[y, x]) == tuple(expected)


def test_overlay_array_respects_background():
    np = pytest.importorskip("numpy")
    arr = np.zeros((3, 3), dtype=np.int64)
    out = palette_color_array(arr, None, seed=0, background=(7, 8, 9))
    assert (out == np.array([7, 8, 9], dtype=np.uint8)).all()


def test_overlay_array_tracks_seed():
    np = pytest.importorskip("numpy")
    arr = np.array([[1, 2, 3]], dtype=np.int64)
    a = palette_color_array(arr, None, seed=0)
    b = palette_color_array(arr, None, seed=1)
    assert not np.array_equal(a, b)


@pytest.mark.parametrize("kind", ["protan", "deutan", "tritan"])
def test_palette_is_cvd_distinguishable(kind):
    pytest.importorskip("skimage")
    assert _min_pairwise_delta_e(kind) >= MIN_CVD_DELTA_E


def test_palette_is_distinguishable_to_normal_vision():
    pytest.importorskip("skimage")
    assert _min_pairwise_delta_e("normal") >= MIN_NORMAL_DELTA_E


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
