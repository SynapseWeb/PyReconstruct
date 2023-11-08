"""Functions for writing to RECONSTRUCT XML files."""
import os

from lxml import etree

from ..classes.series import Series
from ..classes.section import Section
from ..classes.contour import Contour
from ..classes.image import Image
from ..classes.transform import Transform
from ..classes.zcontour import ZContour


def image_to_contour_xml(image):
    element = etree.Element(
        "Contour",
        name=str(image.name),
        hidden=str(image.hidden).lower(),
        closed=str(image.closed).lower(),
        simplified=str(image.simplified).lower(),
        border=" ".join(map(str, map(int, image.border))),
        fill=" ".join(map(str, map(int, image.fill))),
        mode=str(image.mode),
        points=",     ".join([" ".join(map(str, map(int, list(pt)))) for pt in image.points])+",     "
    )
    return element


def section_contour_to_xml(contour):
    element = etree.Element(
        "Contour",
        name=str(contour.name),
        hidden=str(contour.hidden).lower(),
        closed=str(contour.closed).lower(),
        simplified=str(contour.simplified).lower(),
        border=" ".join(map(str, map(float, contour.border))),
        fill=" ".join(map(str, map(float, contour.fill))),
        mode=str(contour.mode),
        points=",     ".join([" ".join(map(str, map(float, list(pt)))) for pt in contour.points])+",     "
    )
    return element


def series_contour_to_xml(contour):
    element = etree.Element(
        "Contour",
        name=str(contour.name),
        closed=str(contour.closed).lower(),
        border=" ".join(map("{:.3f}".format, map(float, contour.border))),
        fill=" ".join(map("{:.3f}".format, map(float, contour.fill))),
        mode=str(contour.mode),
        points=",     ".join([" ".join(map(str, map(float, list(pt)))) for pt in contour.points])+",     "
    )
    return element


def image_to_xml(image):
    element = etree.Element(
        "Image",
        mag=str(image.mag),
        contrast=str(float(image.contrast)),
        brightness=str(float(image.brightness)),
        red=str(image.red).lower(),
        green=str(image.green).lower(),
        blue=str(image.blue).lower(),
        src=str(image.src)
    )
    return element


def section_to_xml(section):
    element = etree.Element(
        "Section",
        index=str(section.index),
        thickness=str(section.thickness),
        alignLocked=str(section.alignLocked).lower()
    )
    return element


def series_to_xml(series):
    element = etree.Element(
        "Series",
        index=str(series.index),
        viewport=" ".join(map(str, map(float, series.viewport))),
        units=str(series.units),
        autoSaveSeries=str(series.autoSaveSeries).lower(),
        autoSaveSection=str(series.autoSaveSection).lower(),
        warnSaveSection=str(series.warnSaveSection).lower(),
        beepDeleting=str(series.beepDeleting).lower(),
        beepPaging=str(series.beepPaging).lower(),
        hideTraces=str(series.hideTraces).lower(),
        unhideTraces=str(series.unhideTraces).lower(),
        hideDomains=str(series.hideDomains).lower(),
        unhideDomains=str(series.unhideDomains).lower(),
        useAbsolutePaths=str(series.useAbsolutePaths).lower(),
        defaultThickness=str(series.defaultThickness),
        zMidSection=str(series.zMidSection).lower(),
        thumbWidth=str(series.thumbWidth),
        thumbHeight=str(series.thumbHeight),
        fitThumbSections=str(series.fitThumbSections).lower(),
        firstThumbSection=str(series.firstThumbSection),
        lastThumbSection=str(series.lastThumbSection),
        skipSections=str(series.skipSections),
        displayThumbContours=str(series.displayThumbContours).lower(),
        useFlipbookStyle=str(series.useFlipbookStyle).lower(),
        flipRate=str(series.flipRate),
        useProxies=str(series.useProxies).lower(),
        widthUseProxies=str(series.widthUseProxies),
        heightUseProxies=str(series.heightUseProxies),
        scaleProxies=str(series.scaleProxies),
        significantDigits=str(series.significantDigits),
        defaultBorder=" ".join(map("{:.3f}".format, series.defaultBorder)),
        defaultFill=" ".join(map("{:.3f}".format, series.defaultFill)),
        defaultMode=str(series.defaultMode),
        defaultName=str(series.defaultName),
        defaultComment=str(series.defaultComment),
        listSectionThickness=str(series.listSectionThickness).lower(),
        listDomainSource=str(series.listDomainSource).lower(),
        listDomainPixelsize=str(series.listDomainPixelsize).lower(),
        listDomainLength=str(series.listDomainLength).lower(),
        listDomainArea=str(series.listDomainArea).lower(),
        listDomainMidpoint=str(series.listDomainMidpoint).lower(),
        listTraceComment=str(series.listTraceComment).lower(),
        listTraceLength=str(series.listTraceLength).lower(),
        listTraceArea=str(series.listTraceArea).lower(),
        listTraceCentroid=str(series.listTraceCentroid).lower(),
        listTraceExtent=str(series.listTraceExtent).lower(),
        listTraceZ=str(series.listTraceZ).lower(),
        listTraceThickness=str(series.listTraceThickness).lower(),
        listObjectRange=str(series.listObjectRange).lower(),
        listObjectCount=str(series.listObjectCount).lower(),
        listObjectSurfarea=str(series.listObjectSurfarea).lower(),
        listObjectFlatarea=str(series.listObjectFlatarea).lower(),
        listObjectVolume=str(series.listObjectVolume).lower(),
        listZTraceNote=str(series.listZTraceNote).lower(),
        listZTraceRange=str(series.listZTraceRange).lower(),
        listZTraceLength=str(series.listZTraceLength).lower(),
        borderColors=",         ".join([" ".join(map("{:.3f}".format, map(float, list(pt)))) for pt in series.borderColors])+",         ",
        fillColors=",         ".join([" ".join(map("{:.3f}".format, map(float, list(pt)))) for pt in series.fillColors])+",         ",
        offset3D=" ".join(map(str, map(int, series.offset3D))),  # TODO: is this always int?
        type3Dobject=str(series.type3Dobject),
        first3Dsection=str(series.first3Dsection),
        last3Dsection=str(series.last3Dsection),
        max3Dconnection=str(series.max3Dconnection),
        upper3Dfaces=str(series.upper3Dfaces).lower(),
        lower3Dfaces=str(series.lower3Dfaces).lower(),
        faceNormals=str(series.faceNormals).lower(),
        vertexNormals=str(series.vertexNormals).lower(),
        facets3D=str(series.facets3D),
        dim3D=" ".join(map(str, map(int, series.dim3D))),
        gridType=str(series.gridType),
        gridSize=" ".join(map(str, map(float, series.gridSize))),
        gridDistance=" ".join(map(str, map(float, series.gridDistance))),
        gridNumber=" ".join(map(str, map(int, series.gridNumber))),
        hueStopWhen=str(series.hueStopWhen),
        hueStopValue=str(series.hueStopValue),
        satStopWhen=str(series.satStopWhen),
        satStopValue=str(series.satStopValue),
        brightStopWhen=str(series.brightStopWhen),
        brightStopValue=str(series.brightStopValue),
        tracesStopWhen=str(series.tracesStopWhen).lower(),
        areaStopPercent=str(series.areaStopPercent),
        areaStopSize=str(series.areaStopSize),
        ContourMaskWidth=str(series.ContourMaskWidth),
        smoothingLength=str(series.smoothingLength),
        mvmtIncrement=" ".join(map("{:g}".format, map(float, series.mvmtIncrement))),
        ctrlIncrement=" ".join(map(str, map(float, series.ctrlIncrement))),
        shiftIncrement=" ".join(map("{:g}".format, map(float, series.shiftIncrement)))
    )
    return element


def transform_to_xml(transform):
    element = etree.Element(
        "Transform",
        dim=str(transform.dim),
        xcoef=" " + " ".join(map(str, transform.xcoef)),
        ycoef=" " + " ".join(map(str, transform.ycoef))
    )
    return element


def zcontour_to_xml(zcontour):
    element = etree.Element(
        "ZContour",
        name=str(zcontour.name),
        closed=str(zcontour.closed).lower(),
        border=" ".join(map("{:.3f}".format, zcontour.border)),
        fill=" ".join(map("{:.3f}".format, zcontour.fill)),
        mode=str(zcontour.mode),
        points=",     ".join(["{} {} {:g}".format(*map(float, list(pt))) for pt in zcontour.points])+",     "
    )
    return element


def entire_section_to_xml(section):
    # Make root (Section attributes: index, thickness, alignLocked)
    root = section_to_xml(section)

    # Add Transform nodes for images (assumes they can all have different tform)
    for image in section.images:
        trnsfrm = transform_to_xml(image.transform)
        img = image_to_xml(image)
        # RECONSTRUCT has a Contour for Images
        cntr = image_to_contour_xml(image)  # Section or Series?
        trnsfrm.append(img)
        trnsfrm.append(cntr)
        root.append(trnsfrm)  # append images transform node to XML file

    # Non-Image Contours
    # - Build list of unique Transform objects
    unique_transform = []
    for contour in section.contours:
        unique = True
        for tform in unique_transform:
            if tform == contour.transform:
                unique = False
                break
        if unique:
            unique_transform.append(contour.transform)

    # - Add contours to their equivalent Transform objects
    for transform in unique_transform:
        transform_elem = transform_to_xml(transform)
        for contour in section.contours:
            if contour.transform == transform:
                cont = section_contour_to_xml(contour)
                transform_elem.append(cont)
        root.append(transform_elem)

    # Make tree and write
    return root


def entire_series_to_xml(series):
    # Build series root element
    root = series_to_xml(series)
    # Add Contours/ZContours to root
    for contour in series.contours:
        root.append(series_contour_to_xml(contour))
    for zcontour in series.zcontours:
        root.append(zcontour_to_xml(zcontour))

    # Make tree and write
    return root


def write_section(section, directory, outpath=None, overwrite=False):
    """Writes <section> to an XML file in directory"""
    if not outpath:
        outpath = os.path.join(directory, section.name)

    root = entire_section_to_xml(section)
    elemtree = etree.ElementTree(root)

    if os.path.exists(outpath) and not overwrite:
        print("Will not write {} due to overwrite conflict. Set overwrite=True to overwrite".format(section.name))
        return
    elemtree.write(outpath, pretty_print=True, xml_declaration=True, encoding="UTF-8")


def write_series(series, directory, outpath=None, sections=False, overwrite=False, progbar=None):
    """Writes <series> to an XML file in directory"""
    # Check if directory exists, make if does not exist
    if not os.path.exists(directory):
        os.makedirs(directory)
    if not outpath:
        outpath = os.path.join(directory, series.name + ".ser")

    # Raise error if this file already exists to prevent overwrite
    if not overwrite and os.path.exists(outpath):
        msg = "CAUTION: Files already exist in ths directory: Do you want to overwrite them?"
        # StdOut
        a = input("{} (y/n)".format(msg))
        overwrite = str(a).lower() in ["y", "yes"]
        if not overwrite:
            raise IOError("\nFilename %s already exists.\nQuiting write command to avoid overwrite"%outpath)
        print ("!!! OVERWRITE ENABLED !!!")

    root = entire_series_to_xml(series)
    elemtree = etree.ElementTree(root)
    elemtree.write(outpath, pretty_print=True, xml_declaration=True, encoding="UTF-8")
    # Write all sections if <sections> == True
    if sections:
        # set up progress bar
        if progbar:
            final_value = len(series.sections)
            prog_value = 0
        for section_index, section in series.sections.items():
            # update progress bar
            if progbar:
                if progbar.wasCanceled(): return
                prog_value += 1
                progbar.setValue(prog_value/final_value * 100)
            write_section(section, directory, overwrite=overwrite)
