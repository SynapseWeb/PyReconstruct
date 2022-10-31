from PySide6.QtGui import QTransform

from modules.pyrecon.series import Series
from modules.pyrecon.section import Section

from modules.backend.object_table_item import ObjectTableItem

def loadSeriesData(series : Series, progbar) -> dict:
    """Load all of the data for each object in the series.
    
        Params:
            series (Series): the series object
            progbar (QProgressDialog): progress bar to update as function progresses
        Returns:
            (dict): obj_name : ObjectTableItem
    """
    objdict = {}  # object name : ObjectTableItem (contains data on object)
    prog_value = 0
    final_value = len(series.sections)
    # iterate through sections, keep track of progress
    for section_num in series.sections:
        section = series.loadSection(section_num)
        t = section.tforms[series.alignment]
        point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5])
        # iterate through contours
        for contour_name in section.traces:
            if contour_name not in objdict:
                objdict[contour_name] = ObjectTableItem(contour_name)
            # iterate through traces
            for trace in section.traces[contour_name]:
                # transform the points to get accurate data
                points = trace.points.copy()
                for i in range(len(points)):
                    points[i] = point_tform.map(*points[i])
                # add to existing data
                objdict[contour_name].addTrace(points, trace.closed, section_num, section.thickness)
        prog_value += 1
        progbar.setValue(prog_value / final_value * 100)
        if progbar.wasCanceled(): return
    
    return objdict

def getObjectsToUpdate(objdict : dict, section_num : int, series : Series, section : Section) -> list:
    """Get the objects that need to be updated on the object table.
    
        Params:
            objdict (dict): the dictionary containing the object data
            section_num (int): the section number
            section (Section): the section object
        Returns:
            (set): the name of the objects that need to be updated on the table
    """
    # keep track of objects that need to be updated
    objects_to_update = []
    # clear object data for the specific section
    for name, item in objdict.items():
        had_existing_data = item.clearSectionData(section_num)
        if had_existing_data:
            objects_to_update.append(name)  # note: fully deleted objects will still appear in this list
    # iterate through all objects and re-calculate section totals
    t = section.tforms[series.alignment]
    point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5])
    section_thickness = section.thickness
    for contour_name in section.traces:
        for trace in section.traces[contour_name]:
            closed = trace.closed
            points = trace.points.copy()
            for i in range(len(points)):
                points[i] = point_tform.map(*points[i]) # transform the point
            if name not in objdict:  # note: objects that need to be added will NOT appear in return list
                objdict[name] = ObjectTableItem(name)
            objdict[name].addTrace(points, closed, section_num, section_thickness)
    
    return objects_to_update

def deleteObject(series : Series, obj_name : str):
    """Delete an object on every section.
    
        Params:
            series (Series): the series object
            obj_name (str): the name of the object to delete.
    """
    for snum in series.sections:
        section = series.loadSection(snum)
        if obj_name in section.traces:
            del(section.traces[obj_name])
        section.save()

def renameObject(series : Series, obj_name : str, new_obj_name : str):
    """Rename an object on every section.
    
        Params:
            series (Series): the series object
            obj_name (str): the name of the object to rename
            new_obj_name (str): the new name for the object
    """
    # rename the object on each section
    for snum in series.sections:
        section = series.loadSection(snum)
        if obj_name in section.traces:
            for trace in section.traces[obj_name]:
                trace.name = new_obj_name
        # check if the new name exists in the section
        if new_obj_name in section.traces:
            section.traces[new_obj_name] += section.traces[obj_name]
        else:
            section.traces[new_obj_name] = section.traces[obj_name]
        del(section.traces[obj_name])
