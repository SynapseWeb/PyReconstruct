"""Functions for creating Python objects from RECONSTRUCT XML files."""
import re
import os

from lxml import etree

from ..classes.series import Series
from ..classes.section import Section
from ..classes.contour import Contour
from ..classes.image import Image
from ..classes.transform import Transform
from ..classes.zcontour import ZContour


def str_to_bool(string):
    """Converts str to str_to_bool(bool."""
    if type(string) is not str:
        return False
    return string.capitalize() == "True"


def process_series_directory(path, data_check=False, progbar=None):
    """Return a Series, fully loaded with data found in the provided path."""
    # Gather Series from provided path
    series_files = []
    for filename in os.listdir(path):
        if ".ser" in filename:
            series_files.append(filename)
    assert len(series_files) == 1, "There is more than one Series file in the provided directory"
    series_file = series_files[0]
    series_path = os.path.join(path, series_file)
    series = process_series_file(series_path)

    # if there is a progress bar, set up
    section_regex = re.compile(r"{}.[0-9]+$".format(series.name))
    final_value = 0
    if progbar:
        for filename in os.listdir(path):
            if re.match(section_regex, filename):
                final_value += 1
        prog_value = 0
    # Gather Sections from provided path
    for filename in os.listdir(path):
        if re.match(section_regex, filename):
            section_path = os.path.join(path, filename)
            section = process_section_file(section_path, data_check=data_check)
            series.sections[section.index] = section
            if progbar:
                if progbar.wasCanceled(): return
                prog_value += 1
                progbar.setValue(prog_value/final_value * 100)    

    if data_check:
        thickness_set = set([sec.thickness for _, sec in series.sections.items()])
        if len(thickness_set) > 1:
            print("One or more section(s) in series {} contain different thicknesses.".format(
                series.name
            ))

    return series


def process_series_file(path):
    """Return a Series object from Series XML file."""
    tree = etree.parse(path)
    root = tree.getroot()

    # Create Series and populate with metadata
    data = extract_series_attributes(root)
    data["name"] = os.path.basename(path).replace(".ser", "")
    data["path"] = os.path.dirname(path)
    series = Series(**data)

    # Add Contours, ZContours
    for elem in root:
        if elem.tag == "Contour":
            # TODO: no Contour import
            contour_data = extract_series_contour_attributes(elem)
            contour = Contour(**contour_data)
            series.contours.append(contour)
        elif elem.tag == "ZContour":
            # TODO: no ZContour import
            zcontour_data = extract_zcontour_attributes(elem)  # TODO
            zcontour = ZContour(**zcontour_data)
            series.zcontours.append(zcontour)

    return series


def process_section_file(path, data_check=False):
    """Return a Section object from a Section XML file."""
    tree = etree.parse(path)
    root = tree.getroot()

    # Create Section and populate with metadata
    data = extract_section_attributes(root)
    data["name"] = os.path.basename(path)
    data["_path"] = os.path.dirname(path)
    section = Section(**data)

    # Process Images, Contours, Transforms
    for node in root:
        # make Transform object
        transform_data = extract_transform_attributes(node)
        transform = Transform(**transform_data)
        children = [child for child in node]

        # Image node
        images = [child for child in children if child.tag == "Image"]
        if images:
            image_data = extract_image_attributes(images[0])
            image_data["_path"] = section._path
            image_data["transform"] = transform

            # Image contours (usually 1 but can be multiple or none)
    
            image_contours = [child for child in children if child.tag == "Contour"]
            
            if len(image_contours) > 1:
                
                raise Exception(f"No support for images with multiple domain contours: index {data['index']}.")
            
            elif not image_contours:

                ## If no domain contour proceed with fake contour
                
                fake_image_contour_data = {
                    "name": "domain_fake",
                    "comment": "None",
                    "hidden": "False",
                    "closed": "True",
                    "simplified": False,
                    "mode": 11,
                    "boder": (1.0, 0.0, 1.0),
                    "fill": (1.0, 0.0, 1.0),
                    "points": _get_points_float("0 0, 1 0, 1 1, 1 0,")
                }
                    
                image_contour_data = fake_image_contour_data
                
            else:
                
                image_contour_data = extract_section_contour_attributes(
                    image_contours[0]
                )

                print(f"{image_contour_data = }")
                
                image_data.update(image_contour_data)

            image = Image(**image_data)
            if data_check:
                # Check if ref exists
                image_path = os.path.join(image._path, image.src)
                if not os.path.isfile(image_path):
                    print("WARNING: Could not find referenced image: {}".format(image_path))

            section.images.append(image)

        # Non-Image Node
        else:
            for child in children:
                if child.tag == "Contour":
                    contour_data = extract_section_contour_attributes(child)
                    contour_data["transform"] = transform
                    contour = Contour(**contour_data)
                    section.contours.append(contour)

    if data_check:
        if not section.images:
            print("WARNING: section {} is missing an Image.".format(section.index))
        elif len(section.images) > 1:
            print("WARNING: section {} contains more than one Image.".format(section.index))

    return section



def _get_points_int(points):
    return zip(
        [int(x.replace(",", "")) for x in points.split()][0::2],
        [int(x.replace(",", "")) for x in points.split()][1::2]
    )


def _get_points_float(points):
    if points:
        return zip(
            [float(x.replace(",", "")) for x in points.split()][0::2],
            [float(x.replace(",", "")) for x in points.split()][1::2]
        )
    else:
        return []


def extract_series_contour_attributes(node):
    """Return a dict of Series' Contour's attributes."""
    attributes = {
        "name": str(node.get("name")),
        "closed": str_to_bool(node.get("closed")),
        "mode": int(node.get("mode")),
        "border": tuple(float(x) for x in node.get("border").strip().split(" ")),
        "fill": tuple(float(x) for x in node.get("fill").strip().split(" ")),
    }

    try:
        attributes["points"] = _get_points_int(node.get("points"))
    except ValueError:
        # series contour points can be ints or floats
        attributes["points"] = _get_points_float(node.get("points"))
    return attributes


def extract_section_contour_attributes(node):
    """Return a dict of Section Contour's attributes."""
    attributes = {
        "name": str(node.get("name")),
        "comment": str(node.get("comment")),
        "hidden": str_to_bool(node.get("hidden")),
        "closed": str_to_bool(node.get("closed")),
        "simplified": str_to_bool(node.get("simplified")),
        "mode": int(node.get("mode")),
        "border": tuple(float(x) for x in node.get("border").strip().split(" ")),
        "fill": tuple(float(x) for x in node.get("fill").strip().split(" ")),
        "points": _get_points_float(node.get("points")),
    }
    return attributes


def extract_image_attributes(node):
    attributes = {
        "src": str(node.get("src")),
        "mag": float(node.get("mag")),
        "contrast": float(node.get("contrast")),
        "brightness": float(node.get("brightness")),
        "red": str_to_bool(node.get("red")),
        "green": str_to_bool(node.get("green")),
        "blue": str_to_bool(node.get("blue")),
    }
    return attributes


def extract_section_attributes(node):
    attributes = {
        "index": int(node.get("index")),
        "thickness": float(node.get("thickness")),
        "alignLocked": str_to_bool(node.get("alignLocked")),
    }
    return attributes


def extract_series_attributes(node):
    attributes = {
        "index": int(node.get("index")),
        "viewport": tuple(float(x) for x in node.get("viewport").split(" ")),
        "units": str(node.get("units")),
        "autoSaveSeries": str_to_bool(node.get("autoSaveSeries")),
        "autoSaveSection": str_to_bool(node.get("autoSaveSection")),
        "warnSaveSection": str_to_bool(node.get("warnSaveSection")),
        "beepDeleting": str_to_bool(node.get("beepDeleting")),
        "beepPaging": str_to_bool(node.get("beepPaging")),
        "hideTraces": str_to_bool(node.get("hideTraces")),
        "unhideTraces": str_to_bool(node.get("unhideTraces")),
        "hideDomains": str_to_bool(node.get("hideDomains")),
        "unhideDomains": str_to_bool(node.get("hideDomains")),
        "useAbsolutePaths": str_to_bool(node.get("useAbsolutePaths")),
        "defaultThickness": float(node.get("defaultThickness")),
        "zMidSection": str_to_bool(node.get("zMidSection")),
        "thumbWidth": int(node.get("thumbWidth")),
        "thumbHeight": int(node.get("thumbHeight")),
        "fitThumbSections": str_to_bool(node.get("fitThumbSections")),
        "firstThumbSection": int(node.get("firstThumbSection")),
        "lastThumbSection": int(node.get("lastThumbSection")),
        "skipSections": int(node.get("skipSections")),
        "displayThumbContours": str_to_bool(node.get("displayThumbContours")),
        "useFlipbookStyle": node.get("useFlipbookStyle").capitalize()  == "True",
        "flipRate": int(node.get("flipRate")),
        "useProxies": str_to_bool(node.get("useProxies")),
        "widthUseProxies": int(node.get("widthUseProxies")),
        "heightUseProxies": int(node.get("heightUseProxies")),
        "scaleProxies": float(node.get("scaleProxies")),
        "significantDigits": int(node.get("significantDigits")),
        "defaultBorder": tuple(float(x) for x in node.get("defaultBorder").split(" ")),
        "defaultFill": tuple(float(x) for x in node.get("defaultFill").split(" ")),
        "defaultMode": int(node.get("defaultMode")),
        "defaultName": str(node.get("defaultName")),
        "defaultComment": str(node.get("defaultComment")),
        "listSectionThickness": str_to_bool(node.get("listSectionThickness")),
        "listDomainSource": str_to_bool(node.get("listDomainSource")),
        "listDomainPixelsize": str_to_bool(node.get("listDomainPixelsize")),
        "listDomainLength": str_to_bool(node.get("listDomainLength")),
        "listDomainArea": str_to_bool(node.get("listDomainArea")),
        "listDomainMidpoint": str_to_bool(node.get("listDomainMidpoint")),
        "listTraceComment": str_to_bool(node.get("listTraceComment")),
        "listTraceLength": node.get("listTraceLength").capitalize()  == "True",
        "listTraceArea": str_to_bool(node.get("listTraceArea")),
        "listTraceCentroid": str_to_bool(node.get("listTraceCentroid")),
        "listTraceExtent": str_to_bool(node.get("listTraceExtent")),
        "listTraceZ": str_to_bool(node.get("listTraceZ")),
        "listTraceThickness": str_to_bool(node.get("listTraceThickness")),
        "listObjectRange": str_to_bool(node.get("listObjectRange")),
        "listObjectCount": str_to_bool(node.get("listObjectCount")),
        "listObjectSurfarea": str_to_bool(node.get("listObjectSurfarea")),
        "listObjectFlatarea": str_to_bool(node.get("listObjectFlatarea")),
        "listObjectVolume": str_to_bool(node.get("listObjectVolume")),
        "listZTraceNote": str_to_bool(node.get("listZTraceNote")),
        "listZTraceRange": str_to_bool(node.get("listZTraceRange")),
        "listZTraceLength": str_to_bool(node.get("listZTraceLength")),
        "borderColors": [tuple(float(x) for x in x.split(" ") if x != "") for x in [x.strip() for x in node.get("borderColors").split(",")] if len(tuple(float(x) for x in x.split(" ") if x != "")) == 3],
        "fillColors": [tuple(float(x) for x in x.split(" ") if x != "") for x in [x.strip() for x in node.get("fillColors").split(",")] if len(tuple(float(x) for x in x.split(" ") if x != "")) == 3],
        "offset3D": tuple(float(x) for x in node.get("offset3D").split(" ")),
        "type3Dobject": int(node.get("type3Dobject")),
        "first3Dsection": int(node.get("first3Dsection")),
        "last3Dsection": int(node.get("last3Dsection")),
        "max3Dconnection": float(node.get("max3Dconnection")),
        "upper3Dfaces": str_to_bool(node.get("upper3Dfaces")),
        "lower3Dfaces": str_to_bool(node.get("lower3Dfaces")),
        "faceNormals": str_to_bool(node.get("faceNormals")),
        "vertexNormals": str_to_bool(node.get("vertexNormals")),
        "facets3D": int(node.get("facets3D")),
        "dim3D": tuple(float(x) for x in node.get("dim3D").split()),
        "gridType": int(node.get("gridType")),
        "gridSize": tuple(float(x) for x in node.get("gridSize").split(" ")),
        "gridDistance": tuple(float(x) for x in node.get("gridDistance").split(" ")),
        "gridNumber": tuple(float(x) for x in node.get("gridNumber").split(" ")),
        "hueStopWhen": int(node.get("hueStopWhen")),
        "hueStopValue": int(node.get("hueStopValue")),
        "satStopWhen": int(node.get("satStopWhen")),
        "satStopValue": int(node.get("satStopValue")),
        "brightStopWhen": int(node.get("brightStopWhen")),
        "brightStopValue": int(node.get("brightStopValue")),
        "tracesStopWhen": str_to_bool(node.get("tracesStopWhen")),
        "areaStopPercent": int(node.get("areaStopPercent")),
        "areaStopSize": int(node.get("areaStopSize")),
        "ContourMaskWidth": int(node.get("ContourMaskWidth")),
        "smoothingLength": int(node.get("smoothingLength")),
        "mvmtIncrement": tuple(float(x) for x in node.get("mvmtIncrement").split(" ")),
        "ctrlIncrement": tuple(float(x) for x in node.get("ctrlIncrement").split(" ")),
        "shiftIncrement": tuple(float(x) for x in node.get("shiftIncrement").split(" ")),
    }
    return attributes


def extract_transform_attributes(node):
    def intorfloat(input):
        """Returns number data type from string."""
        if "." in input:
            return float(input)
        else:
            try:  # TODO
                return int(input)
            except:
                print(
                    "\n\treconstruct_reader.intorfloat(): "
                    "{} "
                    "converted to float "
                    "{}".format(input, float(input))
                )
                return float(input)
    attributes = {
        "dim": int(node.get("dim")),
        "xcoef": [intorfloat(x) for x in node.get("xcoef").strip().split(" ")],
        "ycoef": [intorfloat(x) for x in node.get("ycoef").strip().split(" ")],
    }
    return attributes


def extract_zcontour_attributes(node):
    attributes = {
        "name": str(node.get("name")),
        "closed": str_to_bool(node.get("closed")),
        "border": tuple(float(x) for x in node.get("border").split(" ")),
        "fill": tuple(float(x) for x in node.get("fill").split(" ")),
        "mode": int(node.get("mode")),
        "points": [(float(x.split(" ")[0]), float(x.split(" ")[1]), int(x.split(" ")[2])) for x in [x.strip() for x in node.get("points").split(",")] if len(tuple(float(x) for x in x.split(" ") if x != "")) == 3],
    }
    return attributes
