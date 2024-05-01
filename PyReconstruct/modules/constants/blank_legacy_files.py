blank_section = """<?xml version="1.0"?>
<!DOCTYPE Section SYSTEM "section.dtd">
<Section index="[SECTION_INDEX]" thickness="[SECTION_THICKNESS]" alignLocked="false">
<Transform dim="[TRANSFORM_DIM]"
xcoef="[XCOEF]"
ycoef="[YCOEF]">
<Image mag="[IMAGE_MAG]" contrast="1" brightness="0" red="true" green="true" blue="true"
src="[IMAGE_SOURCE]" />
<Contour name="domain1" hidden="false" closed="true" simplified="false" border="1 0 1" fill="1 0 1" mode="11"
points="0 0,
    [IMAGE_LENGTH] 0,
    [IMAGE_LENGTH] [IMAGE_HEIGHT],
    0 [IMAGE_HEIGHT],
    "/>
</Transform>
</Section>"""

blank_series = """<?xml version="1.0"?>
<!DOCTYPE Series SYSTEM "series.dtd">
<Series index="[SECTION_NUM]" viewport="0 0 0.00254"
    units="microns"
    autoSaveSeries="true"
    autoSaveSection="true"
    warnSaveSection="true"
    beepDeleting="true"
    beepPaging="true"
    hideTraces="false"
    unhideTraces="false"
    hideDomains="false"
    unhideDomains="false"
    useAbsolutePaths="false"
    defaultThickness="0.05"
    zMidSection="false"
    thumbWidth="128"
    thumbHeight="96"
    fitThumbSections="false"
    firstThumbSection="1"
    lastThumbSection="2147483647"
    skipSections="1"
    displayThumbContours="true"
    useFlipbookStyle="false"
    flipRate="5"
    useProxies="true"
    widthUseProxies="2048"
    heightUseProxies="1536"
    scaleProxies="0.25"
    significantDigits="6"
    defaultBorder="1.000 0.000 1.000"
    defaultFill="1.000 0.000 1.000"
    defaultMode="9"
    defaultName="domain$+"
    defaultComment=""
    listSectionThickness="true"
    listDomainSource="true"
    listDomainPixelsize="true"
    listDomainLength="false"
    listDomainArea="false"
    listDomainMidpoint="false"
    listTraceComment="true"
    listTraceLength="false"
    listTraceArea="true"
    listTraceCentroid="false"
    listTraceExtent="false"
    listTraceZ="false"
    listTraceThickness="false"
    listObjectRange="true"
    listObjectCount="true"
    listObjectSurfarea="false"
    listObjectFlatarea="false"
    listObjectVolume="false"
    listZTraceNote="true"
    listZTraceRange="true"
    listZTraceLength="true"
    borderColors="0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            "
    fillColors="0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            "
    offset3D="0 0 0"
    type3Dobject="0"
    first3Dsection="1"
    last3Dsection="2147483647"
    max3Dconnection="-1"
    upper3Dfaces="true"
    lower3Dfaces="true"
    faceNormals="false"
    vertexNormals="true"
    facets3D="8"
    dim3D="-1 -1 -1"
    gridType="0"
    gridSize="1 1"
    gridDistance="1 1"
    gridNumber="1 1"
    hueStopWhen="3"
    hueStopValue="50"
    satStopWhen="3"
    satStopValue="50"
    brightStopWhen="0"
    brightStopValue="100"
    tracesStopWhen="false"
    areaStopPercent="999"
    areaStopSize="0"
    ContourMaskWidth="0"
    smoothingLength="7"
    mvmtIncrement="0.022 1 1 1.01 1.01 0.02 0.02 0.001 0.001"
    ctrlIncrement="0.0044 0.01 0.01 1.002 1.002 0.004 0.004 0.0002 0.0002"
    shiftIncrement="0.11 100 100 1.05 1.05 0.1 0.1 0.005 0.005"
    >
<Contour name="a$+" closed="true" border="1.000 0.500 0.000" fill="1.000 0.500 0.000" mode="13"
points="-3 1,
    -3 -1,
    -1 -3,
    1 -3,
    3 -1,
    3 1,
    1 3,
    -1 3,
    "/>
<Contour name="b$+" closed="true" border="0.500 0.000 1.000" fill="0.500 0.000 1.000" mode="13"
points="-2 1,
    -5 0,
    -2 -1,
    -4 -4,
    -1 -2,
    0 -5,
    1 -2,
    4 -4,
    2 -1,
    5 0,
    2 1,
    4 4,
    1 2,
    0 5,
    -1 2,
    -4 4,
    "/>
<Contour name="pink$+" closed="true" border="1.000 0.000 0.500" fill="1.000 0.000 0.500" mode="-13"
points="-6 -6,
    6 -6,
    0 5,
    "/>
<Contour name="X$+" closed="true" border="1.000 0.000 0.000" fill="1.000 0.000 0.000" mode="-13"
points="-7 7,
    -2 0,
    -7 -7,
    -4 -7,
    0 -1,
    4 -7,
    7 -7,
    2 0,
    7 7,
    4 7,
    0 1,
    -4 7,
    "/>
<Contour name="yellow$+" closed="true" border="1.000 1.000 0.000" fill="1.000 1.000 0.000" mode="-13"
points="8 8,
    8 -8,
    -8 -8,
    -8 6,
    -10 8,
    -10 -10,
    10 -10,
    10 10,
    -10 10,
    -8 8,
    "/>
<Contour name="blue$+" closed="true" border="0.000 0.000 1.000" fill="0.000 0.000 1.000" mode="9"
points="0 7,
    -7 0,
    0 -7,
    7 0,
    "/>
<Contour name="magenta$+" closed="true" border="1.000 0.000 1.000" fill="1.000 0.000 1.000" mode="9"
points="-6 2,
    -6 -2,
    -2 -6,
    2 -6,
    6 -2,
    6 2,
    2 6,
    -2 6,
    "/>
<Contour name="red$+" closed="true" border="1.000 0.000 0.000" fill="1.000 0.000 0.000" mode="9"
points="6 -6,
    0 -6,
    0 -3,
    3 0,
    12 3,
    6 6,
    3 12,
    -3 6,
    -6 0,
    -6 -6,
    -12 -6,
    -3 -12,
    "/>
<Contour name="green$+" closed="true" border="0.000 1.000 0.000" fill="0.000 1.000 0.000" mode="9"
points="-12 4,
    -12 -4,
    -4 -4,
    -4 -12,
    4 -12,
    4 -4,
    12 -4,
    12 4,
    4 4,
    4 12,
    -4 12,
    -4 4,
    "/>
<Contour name="cyan$+" closed="true" border="0.000 1.000 1.000" fill="0.000 1.000 1.000" mode="9"
points="0 12,
    4 8,
    -12 -8,
    -8 -12,
    8 4,
    12 0,
    12 12,
    "/>
<Contour name="a$+" closed="true" border="1.000 0.500 0.000" fill="1.000 0.500 0.000" mode="13"
points="-3 1,
    -3 -1,
    -1 -3,
    1 -3,
    3 -1,
    3 1,
    1 3,
    -1 3,
    "/>
<Contour name="b$+" closed="true" border="0.500 0.000 1.000" fill="0.500 0.000 1.000" mode="13"
points="-2 1,
    -5 0,
    -2 -1,
    -4 -4,
    -1 -2,
    0 -5,
    1 -2,
    4 -4,
    2 -1,
    5 0,
    2 1,
    4 4,
    1 2,
    0 5,
    -1 2,
    -4 4,
    "/>
<Contour name="pink$+" closed="true" border="1.000 0.000 0.500" fill="1.000 0.000 0.500" mode="-13"
points="-6 -6,
    6 -6,
    0 5,
    "/>
<Contour name="X$+" closed="true" border="1.000 0.000 0.000" fill="1.000 0.000 0.000" mode="-13"
points="-7 7,
    -2 0,
    -7 -7,
    -4 -7,
    0 -1,
    4 -7,
    7 -7,
    2 0,
    7 7,
    4 7,
    0 1,
    -4 7,
    "/>
<Contour name="yellow$+" closed="true" border="1.000 1.000 0.000" fill="1.000 1.000 0.000" mode="-13"
points="8 8,
    8 -8,
    -8 -8,
    -8 6,
    -10 8,
    -10 -10,
    10 -10,
    10 10,
    -10 10,
    -8 8,
    "/>
<Contour name="blue$+" closed="true" border="0.000 0.000 1.000" fill="0.000 0.000 1.000" mode="9"
points="0 7,
    -7 0,
    0 -7,
    7 0,
    "/>
<Contour name="magenta$+" closed="true" border="1.000 0.000 1.000" fill="1.000 0.000 1.000" mode="9"
points="-6 2,
    -6 -2,
    -2 -6,
    2 -6,
    6 -2,
    6 2,
    2 6,
    -2 6,
    "/>
<Contour name="red$+" closed="true" border="1.000 0.000 0.000" fill="1.000 0.000 0.000" mode="9"
points="6 -6,
    0 -6,
    0 -3,
    3 0,
    12 3,
    6 6,
    3 12,
    -3 6,
    -6 0,
    -6 -6,
    -12 -6,
    -3 -12,
    "/>
<Contour name="green$+" closed="true" border="0.000 1.000 0.000" fill="0.000 1.000 0.000" mode="9"
points="-12 4,
    -12 -4,
    -4 -4,
    -4 -12,
    4 -12,
    4 -4,
    12 -4,
    12 4,
    4 4,
    4 12,
    -4 12,
    -4 4,
    "/>
<Contour name="cyan$+" closed="true" border="0.000 1.000 1.000" fill="0.000 1.000 1.000" mode="9"
points="0 12,
    4 8,
    -12 -8,
    -8 -12,
    8 4,
    12 0,
    12 12,
    "/>
</Series>"""

blank_series_no_contours = """<?xml version="1.0"?>
<!DOCTYPE Series SYSTEM "series.dtd">
<Series index="[SECTION_NUM]" viewport="0 0 0.00254"
    units="microns"
    autoSaveSeries="true"
    autoSaveSection="true"
    warnSaveSection="true"
    beepDeleting="true"
    beepPaging="true"
    hideTraces="false"
    unhideTraces="false"
    hideDomains="false"
    unhideDomains="false"
    useAbsolutePaths="false"
    defaultThickness="[SECTION_THICKNESS]"
    zMidSection="false"
    thumbWidth="128"
    thumbHeight="96"
    fitThumbSections="false"
    firstThumbSection="1"
    lastThumbSection="2147483647"
    skipSections="1"
    displayThumbContours="true"
    useFlipbookStyle="false"
    flipRate="5"
    useProxies="true"
    widthUseProxies="2048"
    heightUseProxies="1536"
    scaleProxies="0.25"
    significantDigits="6"
    defaultBorder="1.000 0.000 1.000"
    defaultFill="1.000 0.000 1.000"
    defaultMode="9"
    defaultName="domain$+"
    defaultComment=""
    listSectionThickness="true"
    listDomainSource="true"
    listDomainPixelsize="true"
    listDomainLength="false"
    listDomainArea="false"
    listDomainMidpoint="false"
    listTraceComment="true"
    listTraceLength="false"
    listTraceArea="true"
    listTraceCentroid="false"
    listTraceExtent="false"
    listTraceZ="false"
    listTraceThickness="false"
    listObjectRange="true"
    listObjectCount="true"
    listObjectSurfarea="false"
    listObjectFlatarea="false"
    listObjectVolume="false"
    listZTraceNote="true"
    listZTraceRange="true"
    listZTraceLength="true"
    borderColors="0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            "
    fillColors="0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            0.000 0.000 0.000,
            "
    offset3D="0 0 0"
    type3Dobject="0"
    first3Dsection="1"
    last3Dsection="2147483647"
    max3Dconnection="-1"
    upper3Dfaces="true"
    lower3Dfaces="true"
    faceNormals="false"
    vertexNormals="true"
    facets3D="8"
    dim3D="-1 -1 -1"
    gridType="0"
    gridSize="1 1"
    gridDistance="1 1"
    gridNumber="1 1"
    hueStopWhen="3"
    hueStopValue="50"
    satStopWhen="3"
    satStopValue="50"
    brightStopWhen="0"
    brightStopValue="100"
    tracesStopWhen="false"
    areaStopPercent="999"
    areaStopSize="0"
    ContourMaskWidth="0"
    smoothingLength="7"
    mvmtIncrement="0.022 1 1 1.01 1.01 0.02 0.02 0.001 0.001"
    ctrlIncrement="0.0044 0.01 0.01 1.002 1.002 0.004 0.004 0.0002 0.0002"
    shiftIncrement="0.11 100 100 1.05 1.05 0.1 0.1 0.005 0.005"
    >
[CONTOURS]
</Series>"""

blank_palette_contour = """<Contour name="[NAME]" closed="true" border="[BORDER]" fill="[FILL]" mode="[MODE]" points="[POINTS] "/>"""
