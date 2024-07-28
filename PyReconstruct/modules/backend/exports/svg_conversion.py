from pathlib import Path

import svgwrite

from PyReconstruct.modules.calc import getImgDims


def export_svg(section_data, svg_fp) -> Path:
    """Export untransformed traces as an svg."""

    h, w = getImgDims(section_data.src_fp)

    dwg = svgwrite.Drawing(
        svg_fp,
        profile="tiny",
        size=(w, h)
    )

    for _, con_data in section_data.contours.items():

        for trace in con_data.getTraces():

            points = trace.asPixels(section_data.mag, h)
            stroke_color = svgwrite.rgb(*trace.color)
            
            path_data = "M " + " L ".join(f"{x},{y}" for x, y in points)

            if trace.closed: path_data = path_data + " Z"

            path_obj = dwg.path(
                d=path_data,
                id=trace.name,
                stroke=stroke_color,
                stroke_width=4,
                fill="none"
            )

            dwg.add(path_obj)

    dwg.save()

    return svg_fp

