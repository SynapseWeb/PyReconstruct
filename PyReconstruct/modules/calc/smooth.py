"""Per-section offsets that smooth an object in 3D along a z-trace.

A z-trace drawn through an object's midpoints wiggles where the sections sit
at the wrong offsets. Either a smoothed copy of that z-trace or a second
z-trace drawn by hand says where each section should sit; that point minus
the source point is the section's offset. The offset is a pure translation,
so no contour changes shape, area or volume.

Everything here works in field coordinates and knows nothing about series,
sections or Qt.
"""

from bisect import bisect_left


def smoothedPath(points : list, window : int, depths : list = None) -> list:
    """Smooth a path by fitting a line through each point's window of neighbors.

    The window holds window // 2 points on each side, the width of the moving
    average Ztrace.smooth uses. Near the ends it shifts to stay inside the
    path instead of repeating the end point. Each line is fitted against
    depth, so a path that is straight in space stays where it is, however its
    points are spaced. With evenly spaced points and a window that fits, the
    result equals the moving average.

        Params:
            points (list): (x, y) points in path order
            window (int): the smoothing window
            depths (list): the depth of each point (default: its index)
        Returns:
            (list): the smoothed (x, y) points
    """
    n = len(points)
    if depths is None:
        depths = list(range(n))
    width = min(2 * (window // 2) + 1, n)

    smoothed = []
    for i in range(n):
        start = min(max(i - width // 2, 0), n - width)
        span = range(start, start + width)
        mean_z = sum(depths[j] for j in span) / width
        spread = sum((depths[j] - mean_z) ** 2 for j in span)
        fitted = []
        for axis in (0, 1):
            mean_v = sum(points[j][axis] for j in span) / width
            if spread == 0:  # every point in the window at one depth
                fitted.append(mean_v)
                continue
            slope = sum(
                (depths[j] - mean_z) * (points[j][axis] - mean_v) for j in span
            ) / spread
            fitted.append(mean_v + slope * (depths[i] - mean_z))
        smoothed.append(tuple(fitted))

    return smoothed


def ztraceResiduals(field_points : list, window : int, depths : dict = None) -> list:
    """Return the smoothed-minus-raw offset of every z-trace point.

        Params:
            field_points (list): (x, y, snum) z-trace points in field coordinates
            window (int): the smoothing window
            depths (dict): section number : depth (default: the section number)
        Returns:
            (list): (dx, dy, snum) for each point, in the same order
    """
    smoothed = smoothedPath(
        [(x, y) for x, y, _ in field_points],
        window,
        [depths[snum] if depths else snum for _, _, snum in field_points],
    )

    return [
        (sx - x, sy - y, snum)
        for (sx, sy), (x, y, snum) in zip(smoothed, field_points)
    ]


def ztraceDifferences(source_points : list, target_points : list) -> list:
    """Return the target-minus-source offset on each section both z-traces cover.

    Several points on one section are averaged first. A section only one of
    the z-traces covers gives no offset here; sectionOffsets fills it in.

        Params:
            source_points (list): (x, y, snum) source points in field coordinates
            target_points (list): (x, y, snum) target points in field coordinates
        Returns:
            (list): (dx, dy, snum) for each shared section, in section order
    """
    def means(points):
        sums = {}
        for x, y, snum in points:
            sx, sy, n = sums.get(snum, (0.0, 0.0, 0))
            sums[snum] = (sx + x, sy + y, n + 1)
        return {snum: (sx / n, sy / n) for snum, (sx, sy, n) in sums.items()}

    source, target = means(source_points), means(target_points)

    return [
        (target[snum][0] - source[snum][0], target[snum][1] - source[snum][1], snum)
        for snum in sorted(source.keys() & target.keys())
    ]


def sectionOffsets(residuals : list, section_numbers) -> dict:
    """Return one (dx, dy) offset for each requested section.

    Rules, in order:
      - a section with several z-trace points gets the mean of their offsets;
      - a section between covered sections gets a linear interpolation by
        section number, which is how the z-trace line is drawn across skipped
        sections;
      - a section before the first or after the last covered section holds the
        nearest end's offset (clamped), so the mesh has no step at the ends.

        Params:
            residuals (list): (dx, dy, snum) offsets
            section_numbers (iterable): the sections that need an offset
        Returns:
            (dict): section number : (dx, dy)
    """
    sums = {}
    for dx, dy, snum in residuals:
        sx, sy, n = sums.get(snum, (0.0, 0.0, 0))
        sums[snum] = (sx + dx, sy + dy, n + 1)

    if not sums:
        raise ValueError("No z-trace points to take offsets from.")

    covered = {snum: (sx / n, sy / n) for snum, (sx, sy, n) in sums.items()}
    ordered = sorted(covered)
    first, last = ordered[0], ordered[-1]

    offsets = {}
    for snum in section_numbers:
        if snum in covered:
            offsets[snum] = covered[snum]
        elif snum < first:
            offsets[snum] = covered[first]
        elif snum > last:
            offsets[snum] = covered[last]
        else:
            # the nearest covered sections on either side
            k = bisect_left(ordered, snum)
            below, above = ordered[k - 1], ordered[k]
            t = (snum - below) / (above - below)
            (x0, y0), (x1, y1) = covered[below], covered[above]
            offsets[snum] = (x0 + t * (x1 - x0), y0 + t * (y1 - y0))

    return offsets
