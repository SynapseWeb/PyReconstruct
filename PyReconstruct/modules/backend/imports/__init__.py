import subprocess
from pathlib import Path
from typing import List, Union

from PyReconstruct.modules.gui.utils import notifyConfirm, notify as note


def module_path(module: str) -> Path:
    """Return path to a module."""

    mod = __import__(module)
    
    return Path(mod.__file__).parent
    

def modules_available(modules: Union[str, List[str]], notify: bool=True) -> bool:
    """Check if module available."""

    if not isinstance(modules, list):
        modules = [modules]
    
    unavailable = []

    ## Test if modules unavailable
    for module in modules:

        try:

            __import__(module)

        except ModuleNotFoundError:

            unavailable.append(module)

    if not unavailable:  # all modules available

        return True

    if notify:

        unavail_str = ", ".join(unavailable)
            
        response = notifyConfirm(
            f"This feature requires additional python packages to work ({unavail_str}). "
            "Would you like to install them into your current environment?"
        )

        if response == True:

            pip_outcomes = map(install_module, unavailable)
            return all(list(pip_outcomes))
            
        else:

            return False

    return True


def install_module(module: str) -> bool:
    """Interactively install a pip module."""

    output = subprocess.run(
        f"pip install {module}",
        capture_output=True,
        text=True,
        shell=True
    )

    if output.returncode == 0:

        note(
            f"{module} successfully installed to:\n\n{module_path(module)}")

        return True

    else:

        print(output.stderr)

        note(
            "Something went wrong. "
            f"Please try pip installing {module} in a terminal."
        )

        return False
