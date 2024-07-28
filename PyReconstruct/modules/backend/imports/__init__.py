from PyReconstruct.modules.gui.utils import notify as note

def module_available(module, notify=True):
    """Check if module available."""

    try:

        __import__(module)

    except ModuleNotFoundError:

        if notify:
            
            note(
                f"This feature requires the python package '{module}' to work. "
                f"Please install into your environment with the following command:\n\n"
                f"pip install {module}"
            )
            
        return False

    return True
