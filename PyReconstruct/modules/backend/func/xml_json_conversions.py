import os
import json
import sys

from PyReconstruct.modules.calc import reducePoints

from PyReconstruct.modules.constants import blank_section, blank_series_no_contours
from PyReconstruct.modules.gui.utils import getProgbar, notify
from PyReconstruct.modules.constants import createHiddenDir
from PyReconstruct.modules.datatypes import (
    Series,
    Section,
    Transform,
    Trace,
    Ztrace
)
from PyReconstruct.modules.datatypes_legacy import (
    Transform as XMLTransform,
    process_series_file, 
    process_section_file,
    write_section,
    write_series
)

def xmlToJSON(xml_dir : str) -> Series:
    """Convert a series in XML to JSON.
    
        Params:
            xml_dir (str): the directory for the xml series
    """
    # gather the series and section filepaths
    series_fp = ""
    section_fps = []
    json_fp = ""
    for f in os.listdir(xml_dir):
        if f.endswith(".ser"):
            series_fp = os.path.join(xml_dir, f)
            series_name = f[:-4]
        elif f.endswith(".json"):
            json_fp = os.path.join(xml_dir, f)
        elif f[f.rfind(".")+1:].isnumeric():
            section_fps.append(os.path.join(xml_dir, f))
    
    # create the hidden folder containing the JSON files
    sname = os.path.basename(series_fp)
    sname = sname[:sname.rfind(".")]
    hidden_dir = createHiddenDir(xml_dir, sname)

    # set up progress
    progbar = getProgbar(
        "Converting series..."
    )
    progress = 0
    final_value = len(section_fps) + 1
    if json_fp: final_value += 1
    
    # convert the series file
    json_series_fp = seriesXMLToJSON(series_fp, section_fps, hidden_dir)
    if progbar.wasCanceled(): return
    progress += 1
    progbar.setValue(progress/final_value * 100)

    # get the reconcropper data
    if json_fp:
        alignment_dict = getReconcropperData(json_fp)
    else:
        alignment_dict = None
    if progbar.wasCanceled(): return
    progress += 1
    progbar.setValue(progress/final_value * 100)

    # convert the section files and gather section names and tforms
    sections = {}
    section_tforms = {}
    for section_fp in section_fps:
        snum = int(section_fp[section_fp.rfind(".")+1:])
        tform = sectionXMLtoJSON(section_fp, alignment_dict, hidden_dir)
        sections[snum] = f"{sname}.{snum}"
        section_tforms[snum] = tform
        if progbar.wasCanceled(): return
        progress += 1
        progbar.setValue(progress/final_value * 100)
    
    # create an empty log file
    with open(os.path.join(hidden_dir, "existing_log.csv"), "w") as f:
        f.write("Date, Time, User, Obj, Sections, Event")
    
    # open the series file
    series = Series(json_series_fp, sections)

    # modify the ztraces
    for ztrace in series.ztraces.values():
        new_points = []
        for point in ztrace.points:
            x, y, snum = point
            if snum in section_tforms:
                new_point = (
                    *section_tforms[snum].map(x, y, inverted=True),
                    snum
                )
                new_points.append(new_point)
        ztrace.points = new_points
    
    # save the jser file
    # series.save()
    # series.jser_fp = os.path.join(
    #     xml_dir,
    #     f"{series_name}.jser"
    # )
    # series.saveJser()

    # log create the first log in the series
    series.addLog(None, None, "Create series from XML files")

    return series

def seriesXMLToJSON(series_fp, section_fps, hidden_dir):
    # grab the series file
    xml_series = process_series_file(series_fp)
    # create an empty JSON series
    series_dict = Series.getEmptyDict()

    # get the current section
    series_dict["current_section"] = xml_series.index

    # get the view window
    series_dict["window"] = list(xml_series.viewport[:2]) + [1, 1]
    
    # import the palette
    series_dict["palette_traces"] = []
    for xml_contour in xml_series.contours:
        trace = Trace.fromXMLObj(
            xml_contour,
        )
        series_dict["palette_traces"].append(trace.getList())
    series_dict["current_trace"] = series_dict["palette_traces"][0]
    
    # import ztraces
    series_dict["ztraces"] = {}
    for xml_zcontour in xml_series.zcontours:
        series_dict["ztraces"][xml_zcontour.name] = Ztrace.dictFromXMLObj(xml_zcontour)

    # get the series filename and save
    fname = os.path.basename(series_fp)
    json_series_fp = os.path.join(hidden_dir, fname)
    with open(json_series_fp, "w") as f:
        json.dump(series_dict, f)
    return json_series_fp

def getReconcropperData(json_fp):
    with open(json_fp, "r") as f:
        json_data = json.load(f)
    
    alignment_dict = {}

    for item in json_data:
        if item.startswith("LOCAL") or item.startswith("ALIGNMENT"):
            for section_name in json_data[item]:
                # get the transform data
                xcoef = json_data[item][section_name]["xcoef"]
                ycoef = json_data[item][section_name]["ycoef"]
                leg_tform = XMLTransform(xcoef=xcoef, ycoef=ycoef)
                tform_list = leg_tform.getTformList()

                # store the transform data
                aname = item
                if section_name not in alignment_dict:
                    alignment_dict[section_name] = {}
                alignment_dict[section_name][aname] = tform_list
                
    return alignment_dict

def sectionXMLtoJSON(section_fp, alignment_dict, hidden_dir):

    # # grab the section file
    # try:
        
    xml_section = process_section_file(section_fp)
    fname = os.path.basename(section_fp)

    # except Exception as e:

    #     notify(f"A problem has been encountered while importing:\n\n{section_fp}\n\nError:\n\n{e}")

    # get an empty section dict
    section_dict = Section.getEmptyDict()

    # get image data
    if xml_section.images:
        image = xml_section.images[0] # assume only one image
    else:
        image = None
    
    if image:
        section_dict["src"] = image.src
        section_dict["mag"] = image.mag
        xml_tform = image.transform
        tform = Transform(
            list(xml_tform.tform()[:2,:].reshape(6))
        )
    else:
        print(f"Section: {fname} does not contain any image data.")
        section_dict["src"] = ""
        section_dict["mag"] = 0.00254
        xml_tform = XMLTransform(xcoef=[1, 0, 0, 0, 0, 0], ycoef=[0, 1, 0, 0, 0, 0])
        tform = Transform.identity()

    # get thickness
    section_dict["thickness"] = xml_section.thickness

    # get transform data
    section_dict["tforms"] = {}
    if alignment_dict:
        section_dict["tforms"] = alignment_dict[fname]
    else:
        section_dict["tforms"] = {}
    
    section_dict["tforms"]["default"] = tform.getList()
    section_dict["align_locked"] = xml_section.alignLocked

    # get trace/contour data
    contours = section_dict["contours"]  # for ease of access
    for xml_contour in xml_section.contours:
        trace = Trace.fromXMLObj(
            xml_contour,
            xml_tform,
        )
        if len(trace.points) > 1:
            # reduce the points on the trace
            trace.points = reducePoints(
                trace.points,
                closed=trace.closed,
                mag=2/section_dict["mag"]
            )
            if trace.name in contours:
                contours[trace.name].append(trace.getList(include_name=False))
            else:
                contours[trace.name] = [trace.getList(include_name=False)]
    
    # save the section
    with open(os.path.join(hidden_dir, fname), "w") as f:
        json.dump(section_dict, f)
    
    # return the section's transform
    return tform

def jsonToXML(series : Series, new_dir : str):
    """Convert a series in JSON to XML.
    
        Params:
            original_series (Series): the series to convert
            new_dir (str): the directory to store the new files
    """
    # convert the sections
    for snum, section in series.enumerateSections(message="Exporting series as XML..."):
        thickness = sectionJSONtoXML(series, section, new_dir)

    # convert the series
    seriesJSONtoXML(series, new_dir, thickness)
    

def seriesJSONtoXML(series : Series, new_dir : str, thickness: float):
    # create the blank series and replace text as needed
    xml_text = blank_series_no_contours
    xml_text = xml_text.replace("[SECTION_NUM]", str(series.current_section))
    xml_text = xml_text.replace("[SECTION_THICKNESS]", str(thickness))

    xml_palette = []
    for trace in series.palette_traces[series.palette_index[0]]:
        xml_palette.append(trace.getXMLObj(legacy_format=True))
    all_contours = '\n'.join(xml_palette)

    xml_text = xml_text.replace("[CONTOURS]", all_contours)

    # create the series file
    series_fp = os.path.join(new_dir, series.name + ".ser")
    with open(series_fp, "w") as f:
        f.write(xml_text)
    
    # load the series file and insert ztraces
    xml_series = process_series_file(series_fp)
    for ztrace in series.ztraces.values():
        xml_series.zcontours.append(ztrace.getXMLObj(series))
    
    # set the section thickness
    xml_series.defaultThickness = series.avg_thickness
    
    write_series(
        xml_series,
        directory=os.path.dirname(series_fp),
        outpath=series_fp,
        overwrite=True
    )
        

def sectionJSONtoXML(series : Series, section : Section, new_dir : str):
    # create a blank xml section
    xml_text = blank_section
    xml_text = xml_text.replace("[SECTION_INDEX]", str(section.n))
    xml_text = xml_text.replace("[SECTION_THICKNESS]", str(section.thickness))
    xml_text = xml_text.replace("[TRANSFORM_DIM]", "3")
    xml_text = xml_text.replace("[XCOEF]", "0 1 0 0 0 0") # to be replaced
    xml_text = xml_text.replace("[YCOEF]", "0 0 1 0 0 0") # to be replaced
    xml_text = xml_text.replace("[IMAGE_MAG]", str(section.mag))
    xml_text = xml_text.replace("[IMAGE_SOURCE]", section.src)
    xml_text = xml_text.replace("[IMAGE_LENGTH]", "100000")
    xml_text = xml_text.replace("[IMAGE_HEIGHT]", "100000")

    # save the file
    section_fp = os.path.join(
        new_dir,
        f"{series.name}.{section.n}"
    )
    with open(section_fp, "w") as xml_file:
        xml_file.write(xml_text)
    
    # load the xml section and input data
    xml_section = process_section_file(section_fp)
    xml_section.images[0].src = section.src
    xml_section.images[0].mag = section.mag
    xml_section.alignLocked = section.align_locked
    xml_section.thickness = section.thickness
    t = section.tform.getList()
    xcoef = [t[2], t[0], t[1]]
    ycoef = [t[5], t[3], t[4]]
    xml_tform = XMLTransform(xcoef=xcoef, ycoef=ycoef).inverse
    xml_section.images[0].transform = xml_tform
    xml_section.contours = []
    for trace in section.tracesAsList():
        xml_section.contours.append(trace.getXMLObj(xml_tform))
    write_section(
        xml_section,
        directory=os.path.dirname(section_fp),
        outpath=section_fp,
        overwrite=True
    )

    return section.thickness



        
