import json
from PySide2.QtWidgets import QProgressDialog

from pyrecon.utils.reconstruct_reader import process_series_directory
from trace import Trace

def createJSONFromXML(xml_dir, json_dir, progbar):
    progbar = QProgressDialog("Loading Series...", "Cancel", 0, 100, self)
    series = process_series_directory(xml_dir, progbar=progbar)
    series_data = {}
    series_data["sections"] = []
    series_data["current_section"] = 0
    series_data["window"] = [0, 0, 1, 1]
    series_data["sections"] = []


    for n, section in sorted(series.sections.items()):
        series_data["sections"].append(section.name)
        section_data = {}
        image = section.images[0]
        section_data["src"] = image.src
        section_data["mag"] = image.mag
        section_data["thickness"] = section.thickness
        transform = image.transform
        forward_transform = transform._tform
        ft = forward_transform
        section_data["tform"] = (ft[0, 0], ft[0, 1], ft[0, 2], ft[1, 0], ft[1, 1], ft[1, 2])
        section_data["traces"] = []
        for contour in section.contours:
            name = contour.name
            color = list(contour.border)
            for i in range(len(color)):
                color[i] *= 255
            closed = contour.closed
            new_trace = Trace(name, color, closed=closed, exported=True)
            points = contour.points
            points = contour.transform.transformPoints(points)
            points = transform.inverse.transformPoints(points)
            new_trace.points = points
            section_data["traces"].append(new_trace.getDict())

        with open(json_dir + "/" + section.name, "w") as section_file:
            section_file.write(json.dumps(section_data, indent=2))

    series_fp = json_dir + "/" + series.name + ".ser"
    with open(series_fp, "w") as series_file:
            series_file.write(json.dumps(series_data, indent=2))
    
    return series_fp