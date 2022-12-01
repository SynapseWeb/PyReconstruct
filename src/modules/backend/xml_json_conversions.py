import os
import json

from constants.blank_legacy_files import blank_series, blank_section

from modules.gui.gui_functions import progbar
from modules.backend.grid import reducePoints

from modules.pyrecon.series import Series
from modules.pyrecon.section import Section
from modules.pyrecon.transform import Transform

from modules.legacy_recon.classes.transform import Transform as XMLTransform

def xmlToJSON(original_series : Series, new_dir : str):
    """Convert a series in XML to JSON.
    
        Params:
            original_series (Series): the series to convert
            new_dir (str): the directory to store the new files
            progbar: the QProgressDialog object
    """
    # search for a Reconcropper JSON file
    series_name = os.path.basename(original_series.filepath)[:-4]
    json_name = series_name + "_data.json"
    json_fp = os.path.join(original_series.getwdir(), json_name)
    if os.path.isfile(json_fp):
        has_reconcropper_file = True
    else:
        has_reconcropper_file = False

    # load a new series
    series = Series(original_series.filepath)
    # save sections as JSON
    update, canceled = progbar("Export Series", "Exporting series...")
    progress = 0
    final_value = len(series.sections) # plus one for extra json step
    for snum in series.sections:
        section = series.loadSection(snum)
        section.filetype = "JSON"
        section.filepath = os.path.join(
            new_dir,
            os.path.basename(section.filepath)
        )
        # modify the traces on the section
        for trace in section.tracesAsList():
            trace.points = reducePoints(
                trace.points,
                closed=trace.closed,
                mag=1/section.mag
            )
        # save the section
        section.save()
        # update the progress
        if canceled():
            return
        progress += 1
        if has_reconcropper_file:
            update(progress/final_value * 50)
        else:
            update(progress/final_value * 100)
    # save series as XML
    series.filetype = "JSON"
    series.filepath = os.path.join(
        new_dir,
        os.path.basename(series.filepath)
    )
    series.save()

    # read in alignment data from json
    if has_reconcropper_file:
        with open(json_fp, "r") as f:
            json_data = json.load(f)
        # iterate through all sections
        progress = 0
        final_value = len(series.sections)
        for snum in series.sections:
            section = series.loadSection(snum)
            for item in json_data:
                if item.startswith("LOCAL") or item.startswith("ALIGNMENT"):
                    section_name = os.path.basename(section.filepath)
                    xcoef = json_data[item][section_name]["xcoef"]
                    ycoef = json_data[item][section_name]["ycoef"]
                    leg_tform = XMLTransform(xcoef=xcoef, ycoef=ycoef)
                    pyrecon_tform = leg_tform.getPyreconTform()
                    section.tforms[item] = Transform(pyrecon_tform)
            section.save()
            # update the progress bar
            if canceled():
                return
            progress += 1
            update(50 + progress/final_value * 50)

def jsonToXML(original_series : Series, new_dir : str):
    """Convert a series in JSON to XML.
    
        Params:
            original_series (Series): the series to convert
            new_dir (str): the directory to store the new files
    """
    # reload series
    series = Series(original_series.filepath)
    # save sections as XML
    update, canceled = progbar("Export Series", "Exporting series...")
    progress = 0
    final_value = len(series.sections)
    for snum in series.sections:
        json_section = series.loadSection(snum)
        # create a blank xml section
        xml_text = blank_section
        xml_text = xml_text.replace("[SECTION_INDEX]", str(snum))
        xml_text = xml_text.replace("[SECTION_THICKNESS]", str(json_section.thickness))
        xml_text = xml_text.replace("[TRANSFORM_DIM]", "3")
        xml_text = xml_text.replace("[XCOEF]", "0 1 0 0 0 0") # to be replaced
        xml_text = xml_text.replace("[YCOEF]", "0 0 1 0 0 0") # to be replaced
        xml_text = xml_text.replace("[IMAGE_MAG]", str(json_section.mag))
        xml_text = xml_text.replace("[IMAGE_SOURCE]", json_section.src)
        xml_text = xml_text.replace("[IMAGE_LENGTH]", "100000")
        xml_text = xml_text.replace("[IMAGE_HEIGHT]", "100000")
        # save the file
        new_path = os.path.join(
            new_dir,
            os.path.basename(json_section.filepath)
        )
        with open(new_path, "w") as xml_file:
            xml_file.write(xml_text)
        # load the xml section
        xml_section = Section(new_path)
        xml_section.tforms = json_section.tforms
        xml_section.contours = json_section.contours
        xml_section.save()
        if canceled():
            return
        progress += 1
        update(progress/final_value * 100)
    
    # save series as xml
    xml_text = blank_series
    xml_text.replace("[SECTION_NUM]", str(list(series.sections.keys())[0]))
    new_path = os.path.join(
        new_dir,
        os.path.basename(series.filepath)
    )
    with open(new_path, "w") as xml_file:
        xml_file.write(xml_text)



        
