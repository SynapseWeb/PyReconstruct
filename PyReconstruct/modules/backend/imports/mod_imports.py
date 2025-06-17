import subprocess
from pathlib import Path
from typing import List, Tuple, Union

from PyReconstruct.modules.gui.utils import notifyConfirm, notify as note


def module_path(module: str) -> Path:
    """Return path to a module."""

    mod = __import__(module)
    mod_init = mod.__file__
    
    if not mod_init:
        
        _, submod = module.split(".")
        mod_init = getattr(mod, submod).__file__

    return Path(mod_init).parent
        

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
            f"This feature requires additional Python packages to work ({unavail_str}). "
            "Would you like to install them into your current environment?",
            yn=True
        )

        if response == True:

            ## Catch modules with different names on pip install
            mod_pip_names = {
                "cloudvolume": "cloud-volume",
                "dask": "dask==2024.12.1"
            }
            
            for mod, pip_install_name in mod_pip_names.items():
                if mod in unavailable:
                    index = unavailable.index(mod)
                    unavailable[index] = (mod, pip_install_name)

            pip_outcomes = map(install_module, unavailable)
            return all(list(pip_outcomes))
            
        else:

            return False

    return False


def install_module(module: Union[str, Tuple[str, str]]) -> bool:
    """Interactively install a pip module."""

    if isinstance(module, tuple):
        
        module, pip_install_name = module
        
    else:
        
        pip_install_name = module

    output = subprocess.run(
        f"pip install {pip_install_name}",
        capture_output=True,
        text=True,
        shell=True
    )

    if output.returncode == 0:

        note(
            f"{module} successfully installed to:\n\n{module_path(module)}"
        )

        return True

    else:

        note(
            "Something went wrong. "
            f"Please try pip installing {module} in a terminal."
        )

        return False


def is_conda_package_installed(package_name: str) -> bool:
    """Check if conda package installed"""

    try:
        
        result = subprocess.run(
            ['conda', 'list', package_name], capture_output=True, text=True, check=True
        )

        results = result.stdout.strip().split("\n")
        
        results = [line for line in results if not line.startswith("#")]
        
        if not results:
            
            return False
        
        else:
            
            return True
    
    except subprocess.CalledProcessError:
        
        return False

