import os

from PySide6.QtCore import QSettings, QDir
from PySide6.QtWidgets import QFileDialog

class FileDialog(QFileDialog):

    def __init__(self, parent):
        super().__init__(parent)

        # Retrieve the last opened folder path from QSettings
        settings = QSettings("KHLab", "PyReconstruct")
        last_folder = settings.value("last_folder", QDir.homePath())

        # Set the current directory to the last opened folder
        self.setDirectory(last_folder)
    
    def updateSettings(self, response):
        """Update the last_folder setting in QSettings based on the user response."""
        if type(response) is tuple:
            response = response[0]
        if type(response) is list:
            response = response[0]
        
        if not response:
            return
        
        if os.path.isdir(response):
            new_dir = response
        elif os.path.isdir(os.path.dirname(response)):
            new_dir = os.path.dirname(response)
                
        if new_dir:
            settings = QSettings("KHLab", "PyReconstruct")
            settings.setValue("last_folder", new_dir)
    
    def get(file_mode, parent=None, caption="", filter=None, file_name=""):
        fd = FileDialog(parent)
        if file_mode == "dir":
            if not caption: caption = "Open Folder"
            response = fd.getExistingDirectory(fd, caption)
        elif file_mode == "file":
            if not caption: caption = "Open File"
            response = fd.getOpenFileName(fd, caption, filter=filter)[0]
        elif file_mode == "files":
            if not caption: caption = "Open Files"
            response = fd.getOpenFileNames(fd, caption, filter=filter)[0]
        elif file_mode == "save":
            if not caption: caption = "Save File"
            settings = QSettings("KHLab", "PyReconstruct")
            last_folder = settings.value("last_folder", QDir.homePath())
            d = os.path.join(last_folder, file_name)
            response = fd.getSaveFileName(fd, caption, dir=d, filter=filter)[0]
        fd.updateSettings(response)
        fd.close()

        return response