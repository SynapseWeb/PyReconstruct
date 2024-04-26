import json
import git
from pathlib import Path
from packaging.version import parse as v_check

import PyReconstruct


def returnRepoInfo():
    """Return current commit of the repo."""
    
    try:

        ## Check if git repo available
        repo_dir = Path(PyReconstruct.__file__).parents[1]
        repo = git.Repo(repo_dir)
        commit = repo.head.commit.hexsha[0:7]
        branch = repo.active_branch.name

        return {"branch": branch, "commit": commit}

    except git.exc.InvalidGitRepositoryError:

        ## Check if dist-info available following pip install

        site_packages = Path(PyReconstruct.__file__).parents[1]
        dist_dirs = list(site_packages.glob("PyReconstruct-*.dist-info"))  # get all potential versions

        if len(dist_dirs) > 0:

            dist_dirs.sort(key = lambda x: v_check(x.stem.split('-')[-1]))  # explicitly sort versions
            direct_url = dist_dirs[-1] / "direct_url.json"  # get latest version json

            with direct_url.open("r") as fp:
                data = json.load(fp)

            vcs_info = data.get("vcs_info", None)

            if vcs_info is not None:

                commit = vcs_info.get("commit_id", "unknown")
                
                if commit != "unknown":
                    commit = commit[0:7]

                    branch = vcs_info.get("requested_revision", "main")  # if no revision, on main

                    return {"branch": branch, "commit": commit}

    ## If above fail to return, cannot determing repo details and return "unknown"
        
    return {"branch": "unknown", "commit": "unknown"}


repo_info = returnRepoInfo()
