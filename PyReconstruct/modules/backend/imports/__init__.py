import subprocess
from pathlib import Path

from PyReconstruct.modules.gui.utils import notifyConfirm, notify as note


def module_path(module) -> Path:
    """Return path to a module."""

    mod = __import__(module)
    
    return Path(mod.__file__).parent
    

def module_available(module, notify=True) -> bool:
    """Check if module available."""

    try:

        __import__(module)

    except ModuleNotFoundError:

        if notify:
            
            response = notifyConfirm(
                f"This feature requires the python package '{module}' to work. "
                "Would you like to install it into your current environment?"
            )

            if response == True:

                pip_outcome = install_module(module)
                
                return pip_outcome
            
        return False

    return True


def install_module(module) -> bool:
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

        note(
            "Something went wrong. "
            f"Please try pip installing {module} in a terminal."
        )

        return False
