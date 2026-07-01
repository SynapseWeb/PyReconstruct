import json
from pathlib import Path
from importlib.metadata import version as get_version

import PyReconstruct
from .frozen import is_frozen


def _installed_version():
    """Best-effort version string for an installed or frozen build."""
    # setuptools-scm writes PyReconstruct/_version.py at build time.
    try:
        from PyReconstruct._version import version as scm_version
        return scm_version
    except Exception:
        pass
    try:
        return get_version("PyReconstruct")
    except Exception:
        return "unknown"


def returnRepoInfo():
    """Return current branch/commit (source) or version (installed/frozen)."""

    # Frozen build: no .git, no .dist-info -- use the baked setuptools-scm version.
    if is_frozen():
        return {"branch": "PyReconstruct", "commit": _installed_version()}

    # Source checkout: use git if gitpython is available and this is a repo.
    try:
        import git
        repo_dir = Path(PyReconstruct.__file__).parents[1]
        repo = git.Repo(repo_dir)
        commit = repo.head.commit.hexsha[0:7]
        try:
            branch = repo.active_branch.name
        except TypeError:
            branch = "detached head"
        return {"branch": branch, "commit": commit}
    except ImportError:
        pass  # gitpython not installed
    except Exception:
        pass  # not a git repo (e.g. installed) -- fall through

    # pip install from a VCS: read direct_url.json from the dist-info.
    try:
        from packaging.version import parse as v_check
        site_packages = Path(PyReconstruct.__file__).parents[1]
        dist_dirs = list(site_packages.glob("PyReconstruct-*.dist-info"))
        if dist_dirs:
            dist_dirs.sort(key=lambda x: v_check(x.stem.split('-')[-1]))
            direct_url = dist_dirs[-1] / "direct_url.json"
            with direct_url.open("r") as fp:
                data = json.load(fp)
            vcs_info = data.get("vcs_info", None)
            if vcs_info is not None:
                commit = vcs_info.get("commit_id", "unknown")
                if commit != "unknown":
                    commit = commit[0:7]
                branch = vcs_info.get("requested_revision", "main")
                return {"branch": branch, "commit": commit}
    except Exception:
        pass

    # Plain pip install: fall back to installed metadata version.
    version = _installed_version()
    if version != "unknown":
        return {"branch": "PyReconstruct", "commit": version}

    return {"branch": "unknown", "commit": "unknown"}


repo_info = returnRepoInfo()

if repo_info["branch"] == "PyReconstruct":
    repo_string = f"PyReconstruct version {repo_info['commit']}"
else:
    repo_string = f"Repo info - {repo_info['branch']} ({repo_info['commit']})"
