"""Points class."""

from typing import TypeAlias, List, Tuple, Union

from PyReconstruct.modules.calc import interpolate_points, rolling_average


## Define complex types
Coordinate = Union[int, float]
Point = Tuple[Coordinate, Coordinate]
PointSeq = List[Point]


def get_int_list(points: PointSeq) -> PointSeq:
    """Return PointSeq as integers"""

    integerize = lambda x: (int(x[0]), int(x[1]))
    mapped_points = map(integerize, points)

    return list(mapped_points)


class Points:

    def __init__(self, points: PointSeq, closed: bool) -> None:

        self.points: PointSeq

        ends_match = points[0] == points[-1]

        if closed:

            if ends_match:
            
                self.points = points

            else:

                self.points = points + [points[0]]
            
        elif not closed:

            if ends_match:

                self.points = points[:-1]

            else:

                self.points = points
            
        self.closed: bool = closed

    def __str__(self) -> str:

        return f"{self.points}"

    def __add__(self, other_points) -> None:

        if isinstance(other_points, tuple or list):

            self.points.append(other_points)

        else:

            self.points += other_points

        return None

    def __len__(self) -> int:

        return len(self.points)

    def as_ints(self) -> PointSeq:
        """Return coordinates as integers."""

        return get_int_list(self.points)

    def interpolate(self, spacing=0.01):
        """Return new interpolated Point object."""

        interpolated = interpolate_points(self.points, spacing)
        
        return type(self)(interpolated, self.closed)

    def interp_rolling_average(self, spacing: Union[float, int]=0.01, window: int=20, as_int: bool=True) -> PointSeq:
        """Return output from rolling average with interpolation."""

        interpolated = self.interpolate(spacing)

        ## If less than window, return points
        if len(interpolated) <= window:

            if as_int:
            
                return interpolated.as_ints()

            else:

                return interpolated.points

        ## Otherwise perform moving average smoothing
        mode = "circular" if self.closed else "shrinking"
        smoothed = rolling_average(interpolated.points, window, edge_mode=mode)

        if as_int:

            return get_int_list(smoothed)

        else:

            return smoothed
        
