from PySide6.QtWidgets import (
    QWidget, 
    QDialog, 
    QDialogButtonBox, 
    QHBoxLayout, 
    QLabel,
    QVBoxLayout, 
    QPushButton, 
    QInputDialog,
    QTableWidget,
    QTableWidgetItem
)

from PyReconstruct.modules.gui.utils import notify

class ProfileList(QTableWidget):

    def __init__(self, parent : QWidget, profile_names : list, current_profile : str):
        """Create an profile list widget."""
        self.pdict = {}
        for a in sorted(profile_names):
            self.pdict[a] = a
        self.current_profile = current_profile

        super().__init__(0, 1, parent)
        self.setShowGrid(False)
        self.verticalHeader().hide()
        self.horizontalHeader().hide()

        self.createTable()
            
    def createTable(self):
        """Create the table."""
        # remove rows
        while self.rowCount():
            self.removeRow(0)
        # create the rows
        r = 0
        for i, a in enumerate(sorted(self.pdict.keys())):
            if self.pdict[a] is not None:
                self.insertRow(r)
                self.setItem(r, 0, QTableWidgetItem(str(a)))
                r += 1
        self.resizeColumnsToContents()
    
    def getSelectedProfiles(self) -> list[str]:
        """Get the name of the objects highlighted by the user.
        
            Returns:
                (list): the name of the objects
        """
        selected_indexes = self.selectedIndexes()
        profiles = []
        for i in selected_indexes:
            r = i.row()
            profiles.append(self.item(r, 0).text())
        return profiles
    
    def addProfile(self, profile : str):
        """Add an profile to the list.
        
            Params:
                profile (str): the name for the new profile
        """
        if profile in self.pdict and self.pdict[profile] is not None:
            return
        self.pdict[profile] = self.current_profile
        self.createTable()
    
    def removeProfile(self, profile : str):
        """Remove an profile from the list.
        
            Params:
                profile(str): the name of the profile to remove
        """
        if profile not in self.pdict or profile == "default":
            return
        self.pdict[profile] = None
        self.createTable()
    
    def renameProfile(self, profile : str, new_name : str):
        """Rename an profile on the list.
        
            Params:
                profile (str): the profile to rename
                new_name (str): the new name for the profile
        """
        if (profile not in self.pdict or 
            (new_name in self.pdict and self.pdict[profile] is not None) or 
            profile == "default"):
            return
        self.pdict[new_name] = self.pdict[profile]
        self.pdict[profile] = None
        self.createTable()

class BCProfilesDialog(QDialog):

    def __init__(self, parent : QWidget, profile_names : list, current_profile : str):
        """Create an object group dialog.
        
            Params:
                parent (QWidget): the parent widget
                profile_names (list): the list of profiles
        """
        super().__init__(parent)

        self.setWindowTitle(" ")

        title_text = QLabel(self, text="Switch to Profile")

        self.table = ProfileList(self, profile_names, current_profile)

        remove_bttn = QPushButton(self, "remove", text="Remove")
        remove_bttn.clicked.connect(self.removeProfiles)

        rename_bttn = QPushButton(self, "rename", text="Rename...")
        rename_bttn.clicked.connect(self.renameProfile)

        new_bttn = QPushButton(self, "new", text="New...")
        new_bttn.clicked.connect(self.newProfile)

        bttns = QHBoxLayout()
        bttns.addWidget(remove_bttn)
        bttns.addWidget(rename_bttn)
        bttns.addWidget(new_bttn)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonbox = QDialogButtonBox(QBtn)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        vlayout = QVBoxLayout()
        vlayout.setSpacing(10)
        vlayout.addWidget(title_text)
        vlayout.addWidget(self.table)
        vlayout.addLayout(bttns)
        vlayout.addWidget(buttonbox)

        self.setLayout(vlayout)
    
    def newProfile(self):
        """Add a new profile to the list."""
        new_profile, confirmed = QInputDialog.getText(self, "New Profile", "New profile name:")
        if not confirmed:
            return
        if (new_profile in self.table.pdict and self.table.pdict[new_profile] is not None):
            notify("This profile already exists")
            return
        self.table.addProfile(new_profile)
    
    def removeProfiles(self):
        """Remove selected profiles from the list."""
        profiles = self.table.getSelectedProfiles()
        if "default" in profiles:
            notify("Cannot remove default setting.")
            return
        
        for a in profiles:
            self.table.removeProfile(a)
    
    def renameProfile(self):
        """Rename a selected profile."""
        profiles = self.table.getSelectedProfiles()
        if len(profiles) > 1:
            notify("Please select only one profile to rename.")
            return
        elif len(profiles) == 0:
            return
        a = profiles[0]
        if a == "default":
            notify("Cannot rename default setting.")
            return
        
        new_name, confirmed = QInputDialog.getText(self, "Rename Profile", "New profile name:")
        if not confirmed:
            return
        if new_name in self.table.pdict:
            notify("This profile already exists.")
            return
        
        self.table.renameProfile(a, new_name)
        
    def accept(self):
        """Overwritten from parent class."""
        profiles = self.table.getSelectedProfiles()
        if len(profiles) > 1:
            notify("Please select only one profile from the list.")
            return
        super().accept()
        
    def exec(self):
        """Run the dialog."""
        confirmed = super().exec()
        profiles = self.table.getSelectedProfiles()
        if profiles:
            a = profiles[0]
        else:
            a = None
        if confirmed:
            return (
                a,
                self.table.pdict
            ), True
        else:
            return None, False