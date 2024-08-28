import sys

from PySide6.QtWidgets import QMessageBox


def customExcepthook(exctype, value, traceback):
    """Global exception hook: Show notification."""
    sys.__excepthook__(exctype, value, traceback)  # call default exception hook
            
    message = (
        f"An error occurred:\n\n{str(value)}\n\n"
        "(See console for more info.)\n\n"
        "If you think this is a bug or need help, "
        "please issue a bug report at:\n\n"
        "https://github.com/synapseweb/pyreconstruct/issues"
    )
    
    QMessageBox.critical(None, "Error", message, QMessageBox.Ok)
