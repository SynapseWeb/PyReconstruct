from PySide6.QtCore import QSettings, QDir, QFileInfo
from PySide6.QtWidgets import QFileDialog

class FileDialog(QFileDialog):

    def __init__(self, parent):
        super().__init__(parent)

        # Retrieve the last opened folder path from QSettings
        settings = QSettings("KHLab", "PyReconstruct")
        last_folder = settings.value("last_folder", QDir.homePath())

        # Set the current directory to the last opened folder
        self.setDirectory(last_folder)

        self.accepted.connect(self.updateSettings)
    
    def updateSettings(self):
        # Get the selected folder and update the last opened folder in QSettings
        selected_files = self.selectedFiles()
        if selected_files:
            selected_folder = QFileInfo(selected_files[0]).absolutePath()
            settings = QSettings("KHLab", "PyReconstruct")
            settings.setValue("last_folder", selected_folder)
    
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
            response = fd.getSaveFileName(fd, caption, dir=f".{file_name}", filter=filter)[0]
        fd.close()

        return response