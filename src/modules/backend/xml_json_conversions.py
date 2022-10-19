import os

from constants.blank_legacy_files import blank_series, blank_section

from modules.pyrecon.series import Series
from modules.pyrecon.section import Section

def xmlToJSON(original_series : Series, new_dir : str):
    """Convert a series in XML to JSON.
    
        Params:
            original_series (Series): the series to convert
            new_dir (str): the directory to store the new files
    """
    # load a new series
    series = Series(original_series.filepath)
    # save sections as JSON
    for snum in series.sections:
        section = series.loadSection(snum)
        section.filetype = "JSON"
        section.filepath = os.path.join(
            new_dir,
            os.path.basename(section.filepath)
        )
        section.save()
    # save series as XML
    series.filetype = "JSON"
    series.filepath = os.path.join(
        new_dir,
        os.path.basename(series.filepath)
    )
    series.save()

def jsonToXML(original_series : Series, new_dir : str):
    """Convert a series in JSON to XML.
    
        Params:
            original_series (Series): the series to convert
            new_dir (str): the directory to store the new files
    """
    # reload series
    series = Series(original_series.filepath)
    # save sections as XML
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
        xml_section.tform = json_section.tform
        xml_section.traces = json_section.traces
        xml_section.save()
    
    # save series as xml
    xml_text = blank_series
    xml_text.replace("[SECTION_NUM]", str(list(series.sections.keys())[0]))
    new_path = os.path.join(
        new_dir,
        os.path.basename(series.filepath)
    )
    with open(new_path, "w") as xml_file:
        xml_file.write(xml_text)



        
