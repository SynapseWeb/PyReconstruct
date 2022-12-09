import os
import json

from constants.blank_legacy_files import blank_series, blank_section
from constants.locations import backend_series_dir

from modules.gui.gui_functions import progbar

from modules.backend.grid import reducePoints

from modules.pyrecon.series import Series
from modules.pyrecon.section import Section
from modules.pyrecon.transform import Transform
from modules.pyrecon.trace import Trace

from modules.legacy_recon.utils.reconstruct_reader import process_series_file, process_section_file
from modules.legacy_recon.classes.transform import Transform as XMLTransform

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
        elif f.endswith(".json"):
            json_fp = os.path.join(xml_dir, f)
        elif f[f.rfind(".")+1:].isnumeric():
            section_fps.append(os.path.join(xml_dir, f))

    # set up progress
    update, canceled = progbar(
        "XML Series",
        "Converting series..."
    )
    progress = 0
    final_value = len(section_fps) + 1
    if json_fp: final_value += 1
    
    # convert the series file
    json_series_fp = seriesXMLToJSON(series_fp, section_fps)
    if canceled(): return
    progress += 1
    update(progress/final_value * 100)

    # get the reconcropper data
    if json_fp:
        alignment_dict = getReconcropperData(json_fp)
    else:
        alignment_dict = None
    if canceled(): return
    progress += 1
    update(progress/final_value * 100)

    # convert the section files
    for section_fp in section_fps:
        sectionXMLtoJSON(section_fp, alignment_dict)
        if canceled(): return
        progress += 1
        update(progress/final_value * 100)
    
    # open and return the series file
    return Series(json_series_fp)

def seriesXMLToJSON(series_fp, section_fps):
    # grab the series file
    xml_series = process_series_file(series_fp)
    # create an empty JSON series
    series_dict = Series.getEmptyDict()

    # get the current section
    series_dict["current_section"] = xml_series.index

    # get the view window
    series_dict["window"] = list(xml_series.viewport[:2]) + [1, 1]

    # get the section names
    series_dict["sections"] = {}
    for section_fp in section_fps:
        section_fname = os.path.basename(section_fp)
        section_num = int(section_fname[section_fname.rfind(".")+1:])
        series_dict["sections"][section_num] = section_fname
    
    # import the palette
    series_dict["palette_traces"] = []
    for xml_contour in xml_series.contours:
        series_dict["palette_traces"].append(Trace.dictFromXMLObj(xml_contour, hist=False))
    
    # IMPLEMENT THIS EVENTAULLY: ztraces
    series_dict["ztraces"] = ""

    # get the series filename and save
    fname = os.path.basename(series_fp)
    json_series_fp = os.path.join(backend_series_dir, fname)
    with open(json_series_fp, "w") as f:
        json.dump(series_dict, f)
    return json_series_fp

def getReconcropperData(json_fp):
    with open(json_fp, "r") as f:
        json_data = json.load(f)
    
    alignment_dict = {}

    for item in json_data:
        if item.startswith("LOCAL") or item.startswith("ALIGNMENT") or item == "GLOBAL":
            for section_name in json_data[item]:
                # get the transform data
                xcoef = json_data[item][section_name]["xcoef"]
                ycoef = json_data[item][section_name]["ycoef"]
                leg_tform = XMLTransform(xcoef=xcoef, ycoef=ycoef)
                tform_list = leg_tform.getTformList()

                # store the transform data
                aname = "default" if item == "GLOBAL" else item
                if section_name not in alignment_dict:
                    alignment_dict[section_name] = {}
                alignment_dict[section_name][aname] = tform_list
                
    
    return alignment_dict

def sectionXMLtoJSON(section_fp, alignment_dict=None):
    # grab the section file
    xml_section = process_section_file(section_fp)
    fname = os.path.basename(section_fp)

    # get an empty section dict
    section_dict = Section.getEmptyDict()

    # get image data
    image = xml_section.images[0] # assume only one image
    section_dict["src"] = image.src
    section_dict["mag"] = image.mag

    # get thickness
    section_dict["thickness"] = xml_section.thickness

    # get transform data
    if alignment_dict:
        section_dict["tforms"] = alignment_dict[fname]
        tform = Transform(section_dict["tforms"]["default"])
    else:
        tform = Transform(
            list(image.transform.tform()[:2,:].reshape(6))
        )
        section_dict["tforms"]["default"] = tform.getList()
    section_dict["align_locked"] = xml_section.alignLocked

    # get trace/contour data
    contours = section_dict["contours"]  # for ease of access
    for xml_contour in xml_section.contours:
        trace = Trace.dictFromXMLObj(xml_contour, tform)
        if xml_contour.name in contours:
            contours[xml_contour.name].append(trace)
        else:
            contours[xml_contour.name] = [trace]
    
    # save the section
    with open(os.path.join(backend_series_dir, fname), "w") as f:
        json.dump(section_dict, f)







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
    xml_text = xml_text.replace("[SECTION_NUM]", str(series.current_section))
    new_path = os.path.join(
        new_dir,
        os.path.basename(series.filepath)
    )
    with open(new_path, "w") as xml_file:
        xml_file.write(xml_text)
    # load the xml series
    xml_series = Series(new_path)
    xml_series.window = series.window
    xml_series.palette_traces = series.palette_traces
    xml_series.save()

# # save series
# elif self.filetype == "XML":
#     self.xml_series.index = self.current_section
#     self.xml_series.viewport = tuple(self.window[:2]) + (self.screen_mag,)
#     self.xml_series.contours = []
#     for trace in self.palette_traces:
#         self.xml_series.contours.append(trace.getXMLObj())
#     write_series(self.xml_series, directory=os.path.dirname(self.filepath), outpath=self.filepath, overwrite=True)

# # save section
# elif self.filetype == "XML":
#     self.xml_section.images[0].src = self.src
#     self.xml_section.images[0].mag = self.mag
#     self.xml_section.alignLocked = self.align_locked
#     self.xml_section.thickness = self.thickness
#     t = self.tforms["default"].getList()
#     xcoef = [t[2], t[0], t[1]]
#     ycoef = [t[5], t[3], t[4]]
#     xml_tform = XMLTransform(xcoef=xcoef, ycoef=ycoef).inverse
#     self.xml_section.images[0].transform = xml_tform
#     self.xml_section.contours = []
#     for trace in self.tracesAsList():
#         self.xml_section.contours.append(trace.getXMLObj(xml_tform))
#     write_section(self.xml_section, directory=os.path.dirname(self.filepath), outpath=self.filepath, overwrite=True)



        
