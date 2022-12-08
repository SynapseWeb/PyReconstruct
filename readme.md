
# Table of Contents

1.  [PyReconstruct](#org4347386)
2.  [Installation](#org81adb01)
    1.  [Checking Python version](#orgc728bb9)
    2.  [Cloning this repository](#org6ebd9a4)
    3.  [Installing dependencies](#orgeb0fdbf)
    4.  [Uninstalling](#org2abcbc8)
3.  [Getting started](#org1e33668)
    1.  [Launching PyReconstruct](#orgc29190b)
    2.  [The main window](#org5aff911)
    3.  [Starting a new series](#org4d672b0)
    4.  [Tracing your first object](#org42f42ae)
    5.  [Exiting](#org7e52134)
4.  [Other](#orgade73cc)
    1.  [Repository structure](#orgdf2f751)
    2.  [Dependencies](#org2fe2a25)
    3.  [Running pyReconstruct](#org7806963)



<a id="org4347386"></a>

# PyReconstruct

PyReconstruct is an actively maintained, updated, and extensible version of **RECONSTRUCT** written entirely in Python. We are currently alpha-testing this program, but we are more than happy to make it available now.

Because the program is undergoing rapid changes, we are not yet ready to provide a single executable file. For the time being, to access PyReconstruct you will need to download the code through this GitHub repository. We have worked hard to make this process as painless as possible.


<a id="org81adb01"></a>

# Installation

Installing PyReconstruct is a three-step process:

1.  Make sure you have Python 3.9 or higher.
2.  Clone the repository to your local machine.
3.  Install dependencies that are required to run the program.

(Do not fret: For Windows users, we have written scripts that automate the process of installing dependencies.)


<a id="orgc728bb9"></a>

## Checking Python version

To check which version of Python you currently have, run the command `python --version` in a terminal. (In Windows, this can be down by clicking `START` and searching from `command prompt`. In the command prompt window, type `python --version` and press enter.)

The output of the above command will let you know which version of python you are running. You should be running Python 3.9 or higher for PyReconstruct. If there is a error (this likely means you do not have Python installed) or if you need to upgrade, search for and download Python, for example, in the Microsoft App Store.

Once downloaded, you can restart the command prompt and run `python --version` again to see if you successfully installed Python.


<a id="org6ebd9a4"></a>

## Cloning this repository

*Cloning* is similar to copying the code in a repository onto your local machine. However, unlike copying the code directly, a clone remains "linked" to the repository hosted on GitHub, and any changes we make can be easily and quickly incorporated into your cloned copy.

Cloning can be done through git's command line interface or through GitHub's excellent desktop application. You can clone the repository anywhere you like on your machine,. The 


### GitHub Desktop

1.  Download and install GitHub's desktop application [here](https://desktop.github.com/).

2.  


### Command line

1.  Make sure you have `git`. (For Windows, `git` can be downloaded [here](https://git-scm.com/download/win).)

2.  Clone the respository: `git clone https://www.github.com/SynapseWeb/pyReconstruct /destination/path/to/repo`


<a id="orgeb0fdbf"></a>

## Installing dependencies

PyReconstruct depends (hence, "dependencies") on a host of other Python packages that must be downloaded in order to run the program. For Windows users, we have automated this process.


### Automated installation (Windows)

If you don't want to hassle with installing dependencies manually, we have written a convenience script that does this for you.

This script will download and save dependencies in an `env` directory in the root of the repository. It will not save files anywhere else on your machine.

1.  Open the repository and find and open the `windows` directory.
2.  Double-click on `install.bat`.
3.  A console window will open and downloading will start automatically.
4.  Wait until dependencies have been installed. (This might take several minutes.)
5.  After installation, click any key to exit the console.


### Manual installation

Dependencies needed to run pyReconstruct can be found in this repo (`/src/requirements.txt`) and can be installed via PIP: `pip install -r src/requirements.txt`

Using virtual environments such as Python's built-in *venv* module is an excellent way of managing dependencies necessary to run PyReconstruct.

Here is an example of installing dependencies in a newly created virtual environment in Linux and Mac machines:

-   Change current working directory to your local copy of this repo: `cd /path/to/local/repo`
-   Create a virtual environment (for this example, we will call it `env`): `python -m venv env`
-   Activate the virtual environment: `source env/bin/activate`
-   Install dependencies: `pip install -r src/requirements.txt`


<a id="org2abcbc8"></a>

## Uninstalling

If you'd like to uninstall PyReconstruct, simply delete the entire PyReconstruct repository on your local machine. (If you cloned the repository through GitHub Desktop, you can also delete it there.)


<a id="org1e33668"></a>

# Getting started


<a id="orgc29190b"></a>

## Launching PyReconstruct


### After automated installation (Windows)

If you followed the steps above to automatically install dependencies, you can easily start PyReconstruct by clicking on `pyReconstruct.bat` in the `windows` directory of the repository.

You can right-click on this file and make a shortcut, which can be place anywhere on your machine for easy access. (Do not move the actual `pyReconstruct.bat` file itself.)


### Manually

Refer above for instructions on manually installing dependencies. If you are using a virtual environment, activate it and run the following command in a terminal: `python src/pyReconstruct.py`


<a id="org5aff911"></a>

## The main window

When you first open PyReconstruct, you will see a welcome image on top of a black field. This is the **main window** and it is where the majority of your time is spent. The various parts of the main window are outlined in the following figure.

![img](./manual/img/main_window_labeled.png)


### Tools palette

There are 6 tools available in the **tools palette** (each can be accessed by clicking on it or by pressing a keyboard shortcut):

1.  Pointer / select (p)
2.  Pan / Zoom (z)
3.  Knife (k)
4.  Closed trace (c)
5.  Open trace (o)
6.  Stamp (s)

Hovering over each tool reveals its name and shortcut. For example, hovering over the top-most tool shows that it is the pointer tool and that it can be selected by pressing `p` on the keyboard.

(Note: `Shift-L` will move the tool palette, the color/contrast, and the change section buttons to the other side of the main window, which left-handed user might find useful if reconstructing on a tablet.)


### Trace palette

Trace attributes can be quickly accessed through the **trace palette**, a set of 20 user-defined trace attributes at the bottom of the main window. Each can be changed by right-clicking and editing the attributes. The name of the currently selected trace attributes appears above the trace palette.


<a id="org4d672b0"></a>

## Starting a new series


<a id="org42f42ae"></a>

## Tracing your first object


<a id="org7e52134"></a>

## Exiting


<a id="orgade73cc"></a>

# Other


<a id="orgdf2f751"></a>

## Repository structure

This GitHub repository is structured to be easily understandable. All source files can be found under `src/` and other file types are here:

<table border="2" cellspacing="0" cellpadding="6" rules="groups" frame="hsides">


<colgroup>
<col  class="org-left" />

<col  class="org-left" />
</colgroup>
<thead>
<tr>
<th scope="col" class="org-left">File type(s)</th>
<th scope="col" class="org-left">Location</th>
</tr>
</thead>

<tbody>
<tr>
<td class="org-left">Script to run pyReconstruct</td>
<td class="org-left">src/pyReconstruct.py</td>
</tr>


<tr>
<td class="org-left">List of dependencies</td>
<td class="org-left">src/requirements.txt</td>
</tr>


<tr>
<td class="org-left">Modules</td>
<td class="org-left">src/modules</td>
</tr>


<tr>
<td class="org-left">Images and example series</td>
<td class="org-left">src/assets</td>
</tr>


<tr>
<td class="org-left">File locations and other constants</td>
<td class="org-left">src/constants</td>
</tr>


<tr>
<td class="org-left">Notes and features</td>
<td class="org-left">notes/</td>
</tr>


<tr>
<td class="org-left">Miscellaneous</td>
<td class="org-left">misc/</td>
</tr>
</tbody>
</table>


<a id="org2fe2a25"></a>

## Dependencies


<a id="org7806963"></a>

## Running pyReconstruct

Once in the correct directory, pyReconstruct can be started with the following command: `python pyReconstruct.py`

