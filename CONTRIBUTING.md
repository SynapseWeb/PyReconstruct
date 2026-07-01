# Contributing to PyReconstruct

Thanks for your interest in improving PyReconstruct! PyReconstruct is developed
and maintained in the [Kristen Harris Lab](https://synapseweb.clm.utexas.edu/)
at **The University of Texas at Austin**. Contributions of bug reports, fixes,
features, docs, and screenshots are all welcome.

- **Found a bug or have an idea?** [Open an issue](#filing-issues).
- **Want to write code or docs?** See [development setup](#development-setup)
  and [branch and commit conventions](#branch-and-commit-conventions).

By contributing, you agree that your contributions are licensed under the
project's [GPL-3.0-or-later](license.md) license.

---

## Filing issues

Open issues on the project's
**[GitHub Issues](https://github.com/SynapseWeb/PyReconstruct/issues)**. Three
issue templates are available from the "New issue" chooser:

- **Bug report** — please include the **version or commit** you're running.
  Find it in the app's **Help** menu, along with your OS, Python version, steps
  to reproduce, and any console error output.
- **Feature request** — describe the problem you're trying to solve, not only a
  proposed solution.
- **Documentation request** — tell us what's missing or unclear.

Documentation, an installation guide, and manuals are hosted on the lab's
[wiki site](https://wikis.utexas.edu/display/khlab/PyReconstruct+user+guide) and
the [repository wiki](https://github.com/SynapseWeb/PyReconstruct/wiki).

---

## Development setup

PyReconstruct targets **Python 3.11** and **PySide6**.

### Conda environment

The developer workflow uses a conda environment created by the `Makefile` in
`dev/`:

```bash
cd dev
make env              # create the `pyrecon_dev` conda env and link the source tree
conda activate pyrecon_dev
```

`make env` creates the environment from `dev/environment_dev.yaml` (Python 3.11
plus the runtime dependencies from `requirements.txt`) and runs
`dev/link_shell.sh`, which puts the repository root on the environment's import
path (so the source checkout is importable without installing) and registers the
helper scripts in `dev/scripts/` on `PATH`.

Other `Makefile` targets (run from `dev/`):

| Command | What it does |
|---|---|
| `make help` | Show the available commands (the default target) |
| `make env` | Create the `pyrecon_dev` environment and link the source tree |
| `make update` | Update the environment from `environment_dev.yaml` (`--prune`) |
| `make clean` | Remove the `pyrecon_dev` environment (alias: `make remove`) |

You can change the environment name by editing `ENV_NAME` in `dev/Makefile`.
See the [Developers](https://github.com/SynapseWeb/PyReconstruct/wiki/Developers)
wiki page for more.

### Running the app from a checkout

In the activated environment, run the app from the repository root:

```bash
python PyReconstruct/run.py
```

Alternatively, `pip install -e .` installs the package in editable mode and
provides the `PyReconstruct` console command (the entry point declared in
`setup.py`, `PyReconstruct.cli:main`).

---

## Project layout

PyReconstruct is a PySide6 desktop app. The Python package is `PyReconstruct/`:

```
PyReconstruct/
├── run.py                  # Qt bootstrap and launch
├── cli.py                  # `PyReconstruct` console entry point
└── modules/
    ├── backend/            # non-GUI logic, grouped by concern
    │   ├── view/           #   field rendering layers (image, section, trace, zarr)
    │   ├── volume/         #   3D mesh generation and export
    │   ├── table/          #   data-list/table manager
    │   ├── func/           #   transforms, imports, undo/redo state, conversions
    │   ├── imports/        #   ImageJ ROI and other imports
    │   ├── exports/        #   SVG / ROI export
    │   ├── autoseg/        #   auto-segmentation conversions
    │   ├── remote/         #   remote/example-data access
    │   └── threading/      #   QThreadPool worker helpers
    ├── gui/                # Qt / PySide6 UI
    │   ├── main/           #   main window, menubar, field-widget mixins, context menus
    │   ├── dialog/         #   dialogs (options, alignment, trace, grid, flag, …)
    │   ├── palette/        #   floating tool/trace palettes and overlays
    │   ├── popup/          #   3D scene window, about, help
    │   ├── table/          #   the list/table widgets (object, trace, section, ztrace, flag, history)
    │   └── utils/          #   UI helpers (notifications, progress bars, colors)
    ├── datatypes/          # core domain model (Series, Section, Trace, Transform, Ztrace, Flag, …)
    ├── datatypes_legacy/   # readers/writers for the legacy Reconstruct XML format
    ├── calc/               # pure numeric/geometry (quantification, polygon, Feret, …)
    ├── constants/          # constants and small helpers (paths, repo info, websites)
    └── assets/             # bundled data (icons/cursors, welcome series, test fixtures)
```

Top-level directories outside the package:

- `dev/` — developer tooling (`Makefile`, `environment_dev.yaml`,
  `link_shell.sh`, helper `scripts/`).
- `launch/` — clone-and-run scripts for end users.
- `manual/` — the user manual.
- `.github/` — issue and pull-request templates.

Where it's practical, keep computation and data-model logic in `backend/`,
`datatypes/`, and `calc/` (GUI-free and testable), and keep `gui/` focused on
presentation.

---

## Branch and commit conventions

This repository follows a lightweight, conventional workflow.

### Branches

Create feature branches on this repository using short `type/slug` names, where
`type` matches the change:

```
feat/…   fix/…   docs/…   perf/…   refactor/…   test/…   build/…   ci/…   chore/…
```

For example: `feat/ui-theme`, `fix/knife-small-piece`, `docs/guides`.

### Commits

Write commit messages as [Conventional Commits](https://www.conventionalcommits.org/):

```
type(optional-scope): short summary in the imperative mood

Optional body explaining what and why.
```

Keep messages **measured and factual** — describe the change and its rationale;
avoid hyperbole. Please don't add automated co-author or attribution trailers
(for example, trailers crediting AI assistants) to commits or pull requests.

### Pull requests

- Open pull requests **against this repository**
  (`SynapseWeb/PyReconstruct`, `main` branch).
- Keep a PR focused on **one logical change**.
- A maintainer reviews each PR before it is merged.
- PRs are **squash-merged**, so the **PR title becomes the squashed commit
  subject** — write the PR title as a Conventional Commit header. The merged
  commit keeps the `(#N)` PR reference.
- Verify your change by running the app from a checkout, and add tests for
  fixes and behavioral changes where practical.

---

## Credits and license

PyReconstruct was created in the Kristen Harris Lab at **The University of Texas
at Austin** (Michael A. Chirillo, Julian N. Falco, Michael D. Musslewhite,
Larry F. Lindsey, and Kristen M. Harris) and introduced in
[*PNAS* (2025)](https://doi.org/10.1073/pnas.2505822122). See the
[readme](readme.md) for full citation details.

PyReconstruct is licensed under [GPL-3.0-or-later](license.md).
