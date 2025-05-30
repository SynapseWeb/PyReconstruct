"""Polygon operations."""

from typing import Any, List
import numpy as np

from shapely.geometry import (
    Polygon,
    GeometryCollection,
    LineString,
    MultiPoint,
    MultiPolygon,
    Point
)


def cut_closed_traces(trace_list, cut_trace, del_threshold=0.0) -> List[Any]:
    """Cut closed polygons."""

    # Convert cut_trace to a LineString
    cut_line = LineString(cut_trace)
        
    # Create a list to store resulting traces
    new_traces = []
        
    # Process each trace
    for trace in trace_list:

        poly = Polygon(trace)

        # Skip invalid polygons
        if not poly.is_valid:
            continue

        ## Determine trace area threshold
        threshold = poly.area * (del_threshold / 100)

        # Cut the polygon
        if cut_line.intersects(poly):
            # Create a very thin polygon from the cut line
            # by buffering it slightly
            cut_poly = cut_line.buffer(0.001)

            # Perform the cut
            result = poly.difference(cut_poly)

            # Process the result (could be a single polygon or multiple)
            if isinstance(result, Polygon):
                if result.area >= threshold:
                    new_traces.append(list(result.exterior.coords)[:-1])
                    
            elif isinstance(result, MultiPolygon):
                for p in result.geoms:
                    if p.area >= threshold:
                        new_traces.append(list(p.exterior.coords)[:-1])
                        
        else:
            # If no intersection, keep the original trace
            new_traces.append(trace)

    return new_traces


def cut_open_traces (trace_list, cut_trace, del_threshold=0.0):
    """Cut open polygons."""

    new_traces = []

    # For open traces
    for trace in trace_list:
        line = LineString(trace)
        cut_line = LineString(cut_trace)
        threshold = line.length * (del_threshold / 100)
            
        if cut_line.intersects(line):
            # Find intersection points
            intersection = line.intersection(cut_line)
                
            # Cut the line - handling multiple intersection points
            pieces = cut_open_trace(line, intersection)
                
            # Filter by length threshold
            for piece in pieces:
                if piece.length >= threshold:
                    new_traces.append(list(piece.coords))
        else:
            # If no intersection, keep the original trace
            new_traces.append(trace)
                
    return new_traces


def cut_open_trace(line, intersection):
    """Cut an open trace at intersection points.
    
    Args:
        line: LineString to cut
        intersection: Intersection geometry from shapely
        
    Returns:
        list: List of LineString segments
    """
    # Handle different types of intersections
    if isinstance(intersection, Point):
        # Single intersection point
        return cut_at_point(line, intersection)
    elif isinstance(intersection, MultiPoint):
        # Multiple intersection points
        return cut_at_points(line, intersection)
    elif isinstance(intersection, GeometryCollection):
        # Mixed geometry - extract points
        points = []
        for geom in intersection.geoms:
            if isinstance(geom, Point):
                points.append(geom)
        if points:
            return cut_at_points(line, points)
    
    # Fallback - return original
    return [line]

def cut_at_points(line, points):
    """Cut a line at multiple points.
    
    Args:
        line: LineString to cut
        points: Collection of Point objects
        
    Returns:
        list: List of LineString segments
    """
    # Handle MultiPoint by converting to a list of points
    if isinstance(points, MultiPoint):
        points = list(points.geoms)
    
    # Sort points by distance along the line
    points_with_distance = [(point, line.project(point)) for point in points]
    sorted_points = [p[0] for p in sorted(points_with_distance, key=lambda x: x[1])]
    
    # Start with the full line
    result = [line]
    
    # Cut each segment at each point
    for point in sorted_points:
        new_result = []
        for segment in result:
            # Skip empty or very short segments
            if segment.length < 1e-8:
                continue
                
            # Cut this segment at the point
            segments = cut_at_point(segment, point)
            new_result.extend(segments)
        result = new_result
    
    return result

def cut_at_point(line, point):
    """Cut a line at a single point.
    
    Args:
        line: LineString to cut
        point: Point to cut at
        
    Returns:
        list: List of LineString segments (0, 1, or 2)
    """
    # Get distance along the line
    distance = line.project(point)
    
    # If point is at start or end, return original line
    if distance <= 1e-8 or abs(distance - line.length) <= 1e-8:
        return [line]
    
    # Get coordinates
    coords = list(line.coords)
    
    # Initialize segments
    segment1_coords = [point.coords[0]]
    segment2_coords = [point.coords[0]]
    
    # Find the segment containing the point
    current_length = 0
    for i in range(len(coords) - 1):
        segment = LineString([coords[i], coords[i+1]])
        if current_length <= distance <= current_length + segment.length:
            # This segment contains the point
            # Add all previous points to segment1
            segment1_coords = list(coords[:i+1]) + [point.coords[0]]
            # Add all following points to segment2
            segment2_coords = [point.coords[0]] + list(coords[i+1:])
            break
        current_length += segment.length
    
    # Create LineStrings
    segments = []
    if len(segment1_coords) > 1:
        segments.append(LineString(segment1_coords))
    if len(segment2_coords) > 1:
        segments.append(LineString(segment2_coords))
        
    return segments
