# Table of Contents

1.  [General Concepts](#general-concepts)
    1. [File Structure](#file-structure)
    2. [JSON vs. XML Files](#json-vs-xml-files)
    3. [Transforms](#transforms)
    4. [Alignments](#alignments)
    5. [History](#history)
    6. [Trace vs. Contour vs. Object](#trace-vs-contour-vs-object)
    7. [Negative Traces](#negative-traces)
2.  [Menu Bar](#menu-bar)
    1. [File](#file)
    2. [Edit](#edit)
    3. [Series](#series)
    4. [Section](#section)
    5. [View](#view)
3.  [Tool Palette](#tool-palette)
    1. [Universal Tools](#universal-tools)
    2. [Pointer](#pointer-p)
    3. [Pan/Zoom](#panzoom-z)
    4. [Knife](#knife-k)
    5. [Closed Trace](#closed-trace-c)
    6. [Open Trace](#open-trace-o)
    7. [Stamp](#stamp-s)
    8. [Corner Buttons](#corner-buttons)
4.  [Trace Palette](#trace-palette)
5.  [Right Click Menu](#right-click-menu)
    1. [Right Click on Selected Traces](#right-click-on-selected-traces)
    2. [Right Click on Field (or unselected trace)](#right-click-on-field-or-unselected-trace)
6.  [Object List](#object-list)
    1. [Quantities](#quantities)
    2. [Qualities](#qualities)
    3. [Menu Bar](#menu-bar-1)
    4. [Right Click Menu](#right-click-menu-1)
7.  [3D Scene](#3d-scene)
    1. [Right Click Menu](#right-click-menu-2)
8.  [Trace List](#trace-list)
    1. [Quantities](#quantities-1)
    2. [Qualities](#qualities-1)
    3. [Menu Bar](#menu-bar-2)
    4. [Right Click Menu](#right-click-menu-3)
9.  [Section List](#section-list)
    1. [Quantities](#quantities-2)
    2. [Qualities](#qualities-2)
    3. [Menu Bar](#menu-bar-3)
    4. [Right Click Menu](#right-click-menu-4)



# General Concepts

## File Structure

Data for each series are stored in a single series file (.jser).

Images are **not** stored in the .jser file.


## JSON vs. XML Files

JSON and XML are ways in which the section/series data are encoded into their files.

PyReconstruct will store data as JSON files by default.

Legacy Reconstruct stores data in XML files. These files can be opened and edited in PyReconstruct, but we strongly recommend to export these to JSON files, as save data will be lost when saving XML files.


## Transforms

A transform is a set of six numbers (a, b, c, d, e, f) that denotes an affine transformation.

The numbers a, b, d, and e describe the stretch/shear/rotation component of the transformation, while c and f describe the horizontal and vertical translation components of the transformation, respectively.

Each section has one transformation that is applied to the image and every trace. This means that the traces are **fixed** to the image. If the transformation for the section is changed, the traces and the image will move together.


## Alignments

Each series begins with the "default" alignment. An alignment is a single set of image transforms for each section. Through the alignments dialog (accessed through Series>Change Alignment or Ctrl+Shift+A), you can create new alignments and switch between them.

For example, if your default alignment works well for object 1 but not for object 2, you can create a new alignment for object 2 and import transforms or manually align it.


## History

Every trace has a history – an set of logs related to the creation and modification of the trace. Each log contains a date, time, username, and description. By default, the username is found through the operating system, but it can also be changed manually (File>Change username).


## Trace vs. Contour vs. Object

A **trace** is a single connected shape or curve on a 
section.

A **contour** is all traces with the same name on a SINGLE section.

An **object** is all traces with the same name throughout the ENTIRE series.
Trace Attributes

Each trace has a set of modifiable attributes. Generally, the name, color, and tags are the most commonly modified attributes.

Additionally, the trace radius can be modified. This is most commonly used for the palette traces, but the radii of existing traces can be modified through the trace and object lists. This should ONLY be used for traces that are known to be stamps.

Traces can also be hidden. This can be done by using the Ctrl+H shortcut on selected traces or through the object and trace lists. Ctrl+U Will unhide all hidden traces on the section.

The fill mode of the trace is important for visuals. Traces can have no fill, a transparent fill, or a solid fill. You can also select whether the trace is filled only when select or only when deselected.


## Negative Traces

Negative traces denote empty space that exists within another trace of the same name. An example of this would be a trace of a donut. The outer trace is positive (as all traces are by default), and the interior trace should be made negative.

Traces can be made negative through the right click menu.


# Menu Bar

## File

### New (Ctrl+N)

Allows you to create a new series. You are first prompted to select all the images for your series. Please note that these images will be sorted in alphanumeric order when creating the series.

You will then be prompted for the name of the series. This is used to name the series file.

After naming the series, you will be prompted to provide a section thickness and calibration. The section thickness (default: 0.05µm) is used to calculate the quantitative values seen on the object list. The section calibration (default 0.0254 µm/pixel) is the length of microns per image pixel.

### Open (Ctrl+O)

Allows you to open an existing series. You are prompted to locate the .ser file for your desired series. PyReconstruct can open both JSON and XML series, but JSON files are strongly preferred.

### Save (Ctrl+S)

Saves data to the section file for the current section and the series file. Please note that this is also done automatically when switching sections.

### Export Series

Allows you to export the series as JSON or XML files, depending on the current file type of the series you are in. You are prompted to locate a folder to store the exported files. Please note the exported version of the series is NOT opened automatically.

### Import Transforms

Allows you to import transforms for the current alignment of the series you are in. You are prompted to select the file containing the data for each section’s transform. Each line in the file must fit the following format:

*s a b c d e f*

Where the first number (*s*) is the section number for the transform, and the following six numbers (*a*, *b*, *c*, *d*, *e*, *f*) describe the affine transform for the section. There must be exactly one transform for each section.

### Change Username

Allows you to change your username that is marked on every trace/edit you make.

### Quit

Saves the series/section data and closes PyReconstruct.


## Edit

### Undo (Ctrl+Z)

Undoes the last action you made on the trace field. Please note that this will NOT undo any action made through the object or section list.

### Redo (Ctrl+Y)

Redoes the last undone action on the trace field. Like undo, this will NOT redo any action made through the object or section list.

### Cut (Ctrl+X)

Deletes any selected traces and adds them to the clipboard.

### Copy (Ctrl+C)

Copies any selected traces to the clipboard.

#### Paste (Ctrl+V)

Pastes any traces stores on the clipboard to the field.

### Paste Attributes (Ctrl+B)

Pastes the ATTRIBUTES (name, color, tags) of the trace on the clipboard to the selected traces (only works if there is exactly one trace on the clipboard).

### Brightness and Contrast

Allows the user to increase or decrease the brightness and/or contrast of the current section image as desired. It is highly suggested to use the keyboard shortcuts for these functions (bracket keys for contrast, plus and minus keys for brightness).


## Series

### Find Images

Prompts the user to select the folder containing the images for the series. Please note that you are selected the FOLDER containing the images, not the images themselves. This image directory is saved and will be used when loading the series until changed.

### Object List (Ctrl+Shift+O)

Opens an object list (multiple lists can be opened).

### View Series History

View the combined history of every trace in the series.

### Change Alignment (Ctrl+Shift+A)

Change the current series alignment.


## Section

### Section List (Ctrl+Shift+S)

Opens the list of sections in the entire series (multiple lists can be opened).

### Go To (Ctrl+G)

Allows you to jump to an entered section.

### Change Transform (Ctrl+T)

Allows you to manually enter the transform for the section as six numbers.

### Next/Previous Section (PgUp, PgDown)

Increments the section number.

### Trace List (Ctrl+Shift+T)

Opens the list of traces for the current section (multiple lists can be opened).

### Find Contour (Ctrl+F)

Locates a contour (every trace with the same name) on the current section. The view becomes focused on these traces.


## View

### Fill Opacity

Edit the fill opacity of any transparently filled traces in the field

### Set Home View

Center the view on the full image (if one exists).

### View Magnification

Set the magnification for the field view (µm per screen pixel). This is useful for maintaining scale when taking screenshots for figures.

### Move Palette to Other Side (Shift+L)

Moves the vertical palette to the other side of the window.

### Toggle Corner Buttons (Shift+T)

Toggles the corner palette buttons (increment section, adjust brightness/contrast)


# Tool Palette

The tool palette is the vertical set of buttons located on the right side of the screen by default.

## Universal Tools

In any mouse mode except pan/zoom, right clicking will open a menu for editing the trace or field settings.

The right click menu for traces will allow you to modify ALL the selected traces.

Scrolling the mouse wheel will increment the section in any mouse mode.

The middle click (mouse wheel click) will allow you to pan and holding Ctrl while mouse scrolling will allow you to zoom in any mouse mode.

## Pointer (P)

Allows the user to select traces.

Left clicking a trace will selected/deselect the trace.

Left clicking and dragging allows you to select a set of traces COMPLETELY within the designated region.

Left clicking a selected trace and dragging moves ALL selected traces.

## Pan/Zoom (Z)

Allows the user to move the field view.

Left clicking and dragging will pan the image.

Right clicking and dragging up/down will zoom in/out of the image.

## Knife (K)

Allows the user to slice a single trace into multiple traces.

This will only work on one closed selected trace at a time.

If one of the resultant slices has an area less than 1% of the area of the original trace, the slice will be deleted.

## Closed Trace (C)

Allows the user to create closed traces.

Left clicking and dragging will create a scribble-style trace.

Left clicking will allow you to create a polygon-style trace.
-   Right clicking while creating a polygon will finish the polygon.
-   Pressing backspace while creating a polygon will remove the last point made.

## Open Trace (O)

Allows the user to create open traces.

This functions identically to the closed trace tool.

## Stamp (S)

Allows the user to create traces of a specific shape and size (see trace palette).

Left clicking will place a stamp centered on your pointer.

## Corner Buttons

### Brightness/Contrast

Allows the user to modify the brightness/contrast of the section through the screen (useful for tablets).

### Increment Section Buttons

Allows the user to increment up/down sections as needed (useful for tablets).


# Trace Palette

This is the set of buttons at the bottom of the screen. The trace displayed on the selected button is used to create new traces.

The shape of the trace only matters for **stamps**.

The name/color of the selected button is displayed above the palette.

The trace attributes (name, color, tags, stamp size) on the palette button can be modified by right clicking the button.

The trace palette buttons can be selected using the numbers on the keyboard (1-10). The second row of buttons can be accessed by pressing Shift with the number (ex. First button on the second row: Shift+1).


# Right Click Menu

## Right Click on Selected Traces

Right clicking on selected traces will open a menu that allows you to edit the traces. Please note that any edits made will affect ALL the selected traces, not just the one that was right clicked.

### Edit Trace Attributes (Ctrl+E)

Allows you to modify the name, color, tags, and fill mode of the selected traces.

### Merge Trace (Ctrl+M)

Merges the exteriors of all selected traces.

Only traces with the same name can be merged.

### Hide Traces (Ctrl+H)

Hides the selected traces. These traces will remain hidden until unhidden by Ctrl+U or the object/trace lists.

Hidden traces cannot be modified/deleted.

### Delete (Del or Backspace)
Deletes the selected traces.

### Negative

Allows you to make the selected traces negative of positive (see General Concepts for an explanation on negative traces).

### Undo (Ctrl+Z)

Undoes the last action you made on the trace field. Please note that this will NOT undo any action made through the object or section list.

### Redo (Ctrl+Y)

Redoes the last undone action on the trace field. Like undo, this will NOT redo any action made through the object or section list.

### Cut (Ctrl+X)

Deletes any selected traces and adds them to the clipboard.

### Copy (Ctrl+C)

Copies any selected traces to the clipboard.

### Paste (Ctrl+V)

Pastes any traces stores on the clipboard to the field.

### Paste Attributes (Ctrl+B)

Pastes the ATTRIBUTES (name, color, tags) of the trace on the clipboard to the selected traces (only works if there is exactly one trace on the clipboard).


## Right Click on Field (or unselected trace)

### Deselect Traces (Ctrl+D)

Deselects all selected traces on the section.

### Select All Traces (Ctrl+A)

Selects all traces on the section.

### Toggle Hide All Traces (H)

Makes all traces invisible **regardless** of their individual hidden/unhidden status. When traces are invisible, the window has a red outline.

Note that this is NOT the same as hiding/unhiding individual traces.

### Toggle Show All Trace (A)

Makes all traces visible **regardless** of their individual hidden/unhidden status. When this mode is on, the window has a green outline.

Note that this is NOT the same as hiding/unhiding individual traces.

### Unhide All Traces (Ctrl+U)

Unhides all hidden traces on the section. This modifies the hidden/unhidden status of each trace individually.

### Toggle Section Blend (Space)

Toggles blending of the current and previous sections.

# Object List

The object list displays all of the objects in the series. An **object** is all traces in a series with same name. The user can view data related to the series objects as well as make changes to objects that affect all traces associated with it.


## Quantities

### Start/End

These values correspond to the first and last section that the object appears on within the series.

### Count

This value is the number of traces that make up the object.

### Flat Area

This value is the 2D area of the object (NOT surface area).

This is calculated by summing the areas of closed traces with the lengths of open traces multiplied by the section thickness.

### Volume

This value is the 3D volume of the object.

This is calculated by summing the areas of closed traces multiplied by the section thickness.

## Qualities

### Group

The group(s) the object belongs to.

### Trace Tags

Any tags associated with any trace that create the object.


## Menu Bar

### List

#### Refresh

Refreshes the object table by reloading the series data.

Note: the object table is auto-refreshing as the user traces.

#### Set columns

Set the object quantities/qualities displayed in the table.

#### Export

Export the current state of the list in CSV format.

#### Regex Filter

Filter the list to display objects that only match a provided regex filter.

Mutiple regex filters can be used by separating each filter with a comma and space (ex. d01, d03).

More information on regex can be found [here](https://docs.python.org/3/library/re.html).

#### Group Filter

Filter the list to display only objects that belong to a specified group.

Multiple group filters can be used by separating each filter with a comma and space (ex. group1, group2).

#### Tag Filter

Filter the list to display only objects that contain at least one trace with a specified tag.

Multiple tag filters can be used by separating each filter with a comma and a space (ex. tag1, tag2).


### Find

#### First

Locates the first contour associated with the selected object on the object list. The series will jump to the section containing the first contour and highlight on the contour.

### Last

Locates the last contour associated with the selected object on the object list. The series will jump to the section containing the last contour and highlight the contour.

## Right Click Menu

### Edit Attributes

Pulls up a menu that allows the user to edit the name, color, tags, and fill style of all traces associated with the selected object(s).

This action cannot be undone with Ctrl+Z or Edit>Undo.

### Edit Radius

Allows the user to edit the radii of all traces associated with the selected objects.

This should **only** be done with objects that are known to be stamps.

This action cannot be undone with Ctrl+Z or Edit>Undo.

### Remove All Tags

Removes all tags on traces associated with the selected object(s)

### Hide/Unhide

Allows the user to set the hidden status for all individual traces associated with an objects.

### 3D

#### Generate 3D

Generates the 3D representation of the object(s).

This can also be done by double clicking.

This will pull up a separate window containing the 3D representation. If a 3D scene window already exists, the selected object(s) will be added to the scene.

Note: this may take up to 20 seconds depending on the size and complexity of the object.

#### Edit 3D Settings

Pulls up a menu that allows the user to modify the 3D type and opacity of the selected object(s).

3D types:
- Surface (default): a surface estimated from the all traces associated with the object
- Spheres: creates a sphere for each trace with a radius the size of the trace radius 


### Groups

#### Add to Group

Allows the user to add the selected object(s) to a specified group.

#### Remove from Group

Allows the user to remove the selected object(s) from a specified group.

#### Remove from All Groups

Allows the user to remove the selected object(s) from all of their groups.

### View History

View the history of all traces associated with the selected object(s).

### Delete

Deletes all traces associated with the selected object(s).


# 3D Scene

This window is pulled up through the "Generate 3D" option in the object list.

If "Generate 3D" is called when the 3D scene already exists, the requested objects will be added to the scene.

The user can pan around the scene by dragging the left mouse and zoom by scrolling in/out.

## Right Click Menu

### Scale Cube (S)

Toggles the existence of the gray scale sube in the scene.

This scale cube can be moved in the scene in xy using the arrow keys and in z using up and down arrow keys while pressing Ctrl.

### Edit Scale Cube Size

Allows the user to modify the side length of the scale cube.

### Set Background Color

Allows the user to set the background color for the 3D scene.

# Trace List

The trace list displays information for all traces on the current section.

## Quantities

### Length

The length of the trace.

### Area

The area of the trace (0 if the trace is open).

### Radius

The radius of the trace (the distance from its centroid to the point furthest from the centroid).

## Qualities

### Index

The index of the trace within its contour. This value is only representative of the order the trace was made in comparison to other traces in the same contour.

### Tags

Any tags given to the trace.


## Menu Bar

### List

#### Set columns

Set the trace quantities/qualities displayed in the table.

#### Export

Export the current state of the list in CSV format.

#### Regex Filter

Filter the list to display objects that only match a provided regex filter.

Mutiple regex filters can be used by separating each filter with a comma and space (ex. d01, d03).

More information on regex can be found [here](https://docs.python.org/3/library/re.html).

#### Group Filter

Filter the list to display only objects that belong to a specified group.

Multiple group filters can be used by separating each filter with a comma and space (ex. group1, group2).

#### Tag Filter

Filter the list to display only objects that contain at least one trace with a specified tag.

Multiple tag filters can be used by separating each filter with a comma and a space (ex. tag1, tag2).


## Right Click Menu

### Edit

Allows the user to edit the attributes (name, color, tags, fill style) of the the trace(s) selected in the trace list.

### Change Radius

Modify the radius of the trace(s) selected in the trace list.

This should only be used for traces that are known to be stamps.

### Hide/Unhide

Hide/unhide the trace(s) selected in the trace list.

### Find

Find and highlight the trace(s) selected in the trace list.

This can also be done by double clicking the selected trace(s).

### View History

View the history of the trace(s) selected in the trace list.

### Delete

Delete the trace(s) selected in the trace list.


# Section List

This will display all the sections in the series.

## Quantities

### Thickness

The thickness of the section (in microns).

## Qualities

### Locked

Whether the section is locked or unlocked.

If the section is locked, its transformation CANNOT be modified by any means.


## Menu Bar

### List

#### Export

Export the current state of the list in CSV format.


## Right Click Menu

### Lock/Unlock Sections

Set the selected section(s) as locked or unlocked.

If a section is locked, its transformation CANNOT be changed by any means.

### Edit Thickness

Allows the user to edit the thickness of the section.

### Delete

Allows the user to delete a section entirely.

This action CANNOT be undone with Ctrl+Z or Edit>Undo.



