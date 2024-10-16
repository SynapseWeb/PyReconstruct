from pathlib import Path
from typing import Union
from tempfile import mkstemp
from io import BytesIO
import base64

import zarr
from PIL import Image

from PyReconstruct.modules.calc import getImgDims


def export_svg(section_data, svg_fp) -> Union[str, Path]:
    """Export untransformed section with traces as an svg."""

    import svgwrite
    from svgwrite.extensions import Inkscape

    img_fp = section_data.src_fp
    mag = section_data.mag
    h, w = getImgDims(section_data.src_fp)

    ## Create drawing
    dwg = svgwrite.Drawing(
        svg_fp,
        profile="tiny",
        size=(w, h)
    )

    ## Add image layer and add image

    ## Convert img to base64-encoded string to embed in svg
    if "scale_" in str(img_fp):  # NOTE: Turn this into a utility
        
        z = zarr.open(str(img_fp))
        z_array = z[:]
        image = Image.fromarray(z_array)

        del z, z_array

    else:

        image=Image.open(img_fp)

    buffered = BytesIO()
    image.save(buffered, format="PNG")
    image_base64 = base64.b64encode(buffered.getvalue()).decode()

    # Create data URI
    image_data_uri = f"data:image/png;base64,{image_base64}"
            
    inkscape = Inkscape(dwg)
    image_layer = inkscape.layer(label="image", locked=False)

    image_layer.add(
        dwg.image(
            image_data_uri,
            insert=(0, 0),
            size=(w, h)
        )
    )

    ## Make trace layer and add traces
    trace_layer = inkscape.layer(label="traces", locked=False)

    for _, con_data in section_data.contours.items():

        for trace in con_data.getTraces():

            if trace.hidden:  # don't render hidden traces
                continue

            points = trace.asPixels(mag, h)
            color = svgwrite.rgb(*trace.color)

            path_data = "M " + " L ".join(f"{x},{y}" for x, y in points)

            if trace.closed: path_data = path_data + " Z"

            path_obj = dwg.path(
                d=path_data,
                id=trace.name,
                stroke=color,
                stroke_width=4,
                fill=color,
                fill_opacity=0.2
            )

            trace_layer.add(path_obj)

    ## Insert scale bar

    sb_length = 1  # microns 
    px_micron = 1 // mag
    
    sb_w = int(sb_length * px_micron)
    sb_h = int(sb_w * 0.2)

    color = svgwrite.rgb(0, 0, 0)  # black scale bar
    points = [(0, 0), (0, sb_h), (sb_w, sb_h), (sb_w, 0)]
    
    path_data = "M " + " L ".join(f"{x},{y}" for x, y in points) + " Z"

    path_obj = dwg.path(
                d=path_data,
                id="scale_bar",
                stroke=color,
                stroke_width=0,
                fill=color,
                fill_opacity=1.0
            )

    trace_layer.add(path_obj)

    ## Add layers to drawing
    dwg.add(image_layer)
    dwg.add(trace_layer)

    ## Save
    dwg.save()

    return svg_fp


def export_png(section_data, png_fp, scale: float=1.0):
    """Export untransformed section with traces as a png."""

    _, tmp_svg = mkstemp(suffix=".svg")
    export_svg(section_data, tmp_svg)

    from cairosvg import svg2png

    svg2png(
        url=tmp_svg,
        write_to=png_fp,
        scale=scale
    )

    Path(tmp_svg).unlink()
    
    return png_fp
