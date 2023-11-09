import pathlib
from setuptools import setup, find_packages

HERE = pathlib.Path(__file__).parent

# It can be convenient to put the metadata for a package at the top
# of a file
VERSION = '0.1.2'
PACKAGE_NAME = 'PyReconstruct'
AUTHOR = 'Julian Falco & Michael Chirillo'
AUTHOR_EMAIL = 'julian.falco@utexas.edu'
URL = 'https://github.com/SynapseWeb/PyReconstruct'
LICENSE = 'None'
DESCRIPTION = 'A version of RECONSTRUCT written in Python'

# PyPI supports a "long description," which basically a README
# file that is published alongside your package metadata.
# The code here shows how to dynamically load the text of 
# your package README and provide it for the long description.
# The example in this article uses Mardown for readme and 
# documentation, other supported formats include
# Restructured Text (RST).
LONG_DESCRIPTION = (HERE / "readme.md").read_text()
LONG_DESC_TYPE = "text/markdown"

# Dependencies for the package
INSTALL_REQUIRES = [
      'PySide6',
      'opencv-python',
      'numpy',
      'scikit-image',
      'trimesh',
      'vedo',
      'zarr',
      'lxml'
]

# Initialize setup with metadata and package dependencies.
# find_packages is used to recourse the structure of the 
# project and dynamically generate the package
setup(
    name=PACKAGE_NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type=LONG_DESC_TYPE,
    author=AUTHOR,
    license=LICENSE,
    author_email=AUTHOR_EMAIL,
    url=URL,
    install_requires=INSTALL_REQUIRES,
    packages=find_packages(),
    package_data={'PyReconstruct': ['assets/**/*', 'assets/welcome_series/.welcome/*']},
    entry_points={
        'console_scripts': [
            'PyReconstruct=PyReconstruct.cli:main'
        ]
    }
)