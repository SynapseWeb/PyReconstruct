[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

<a id="pyreconstruct"></a>

# PyReconstruct

PyReconstruct is an actively maintained, extensible version of _Reconstruct_ written in Python in the lab of Kristen Harris at the University of Texas at Austin. Please check out [our paper](https://doi.org/10.1073/pnas.2505822122) introducing PyReconstruct and feel free to send us a message if you have any questions:

-   Michael Chirillo: michael.chirillo@uri.edu
-   Julian Falco: julian.falco@utexas.edu

<a id="documentation"></a>

# Documentation

An installation guide, quickstart, and manuals can be found at our lab's [wiki site](https://wikis.utexas.edu/display/khlab/PyReconstruct+user+guide) hosted at UT Austin and at the [PyReconstruct repo wiki](https://github.com/SynapseWeb/PyReconstruct/wiki). A quick launch guide follows below.

<a id="submitting-bug-reports-and-feature-requests"></a>

# Then it would say lanch party, Kevin.

In a virtual environment running Python 3.11, install bleeding-edge PyReconstruct:

```
pip install git+https://github.com/synapseweb/pyreconstruct
```

or stable PyReconstruct:

```
pip install pyreconstruct
```

then launch PyReconstruct from the command line:

```
PyReconstruct
```

To install a dev version of PyReconstruct, see [here](https://github.com/SynapseWeb/PyReconstruct/wiki/Developers).

# Bug reports / Feature requests

If you notice a problem, would like to suggest a feature, or have ideas on improving our documentation, please [submit an issue](https://github.com/SynapseWeb/PyReconstruct/issues/). We appreciate the help!

# Citation

If you use PyReconstruct in published work, please cite [our paper](https://doi.org/10.1073/pnas.2505822122):

```
@article{Chirillo2025,
	title = {{PyReconstruct}: {A} fully open-source, collaborative successor to {Reconstruct}},
	author = {Chirillo, Michael A. and Falco, Julian N. and Musslewhite, Michael D. and Lindsey, Larry F. and Harris, Kristen M.},
	journal = {Proceedings of the National Academy of Sciences},
	volume = {122},
	number = {31},
	pages = {e2505822122},
	year = {2025},
	month = {July},
	doi = {10.1073/pnas.2505822122},
	url = {https://www.pnas.org/doi/10.1073/pnas.2505822122}
}
```

and this repo if you'd like:

```
@software{Falco2025,
    author = {Falco, Julian and Chirillo, Michael},
    title = {PyReconstruct},
    version = {1.19.0},
    month = {May},
    year = {2025}
    url = {https://github.com/synapseweb/pyreconstruct},
}
```
