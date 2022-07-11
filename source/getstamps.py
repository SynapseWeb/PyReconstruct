from concurrent.futures import process
from pyrecon.utils.reconstruct_reader import process_series_directory
series = process_series_directory("C:\\Users\\jfalco\\Documents\\Series\\getstamps")

for contour in series.contours:
    x = [p[0] for p in contour.points]
    y = [p[1] for p in contour.points]
    max_x = max(x)
    max_y = max(y)
    m = max(max_x, max_y)
    factor = 0.5 / m
    points = []
    for i in range(len(contour.points)):
        x, y = contour.points[i]
        x *= factor
        y *= factor
        points.append((round(x,4),round(y,4)))
    print(points)