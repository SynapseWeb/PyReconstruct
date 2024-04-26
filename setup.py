import os
import pathlib
from setuptools import setup, find_packages

HERE = pathlib.Path(__file__).parent

VERSION = '0.1.0'
PACKAGE_NAME = 'PyReconstruct'
AUTHOR = 'Julian Falco & Michael Chirillo'
AUTHOR_EMAIL = 'julian.falco@utexas.edu'
URL = 'https://github.com/SynapseWeb/PyReconstruct'
LICENSE = 'None'
DESCRIPTION = 'A version of RECONSTRUCT written in Python'

LONG_DESCRIPTION = (HERE / "readme.md").read_text()
LONG_DESC_TYPE = "text/markdown"

INSTALL_REQUIRES = [
      'PySide6==6.6.1',
      'opencv-python',
      'numpy',
      'scikit-image',
      'trimesh==3.18.1',
      'vedo',
      'zarr',
      'lxml',
      'gitpython'
]


SHELL_SCRIPTS = []  # List shell scripts to install

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
    scripts=SHELL_SCRIPTS,
    entry_points={
        'console_scripts': [
            'PyReconstruct=PyReconstruct.cli:main'
        ]
    }
)
