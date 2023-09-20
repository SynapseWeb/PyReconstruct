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

from modules.gui.utils import notify

class AlignmentList(QTableWidget):

    def __init__(self, parent : QWidget, alignment_names : list):
        """Create an alignment list widget."""
        self.alignments = sorted(alignment_names)
        super().__init__(len(self.alignments), 1, parent)
        self.setShowGrid(False)
        self.verticalHeader().hide()
        self.horizontalHeader().hide()

        # create the table
        for i, a in enumerate(self.alignments):
            self.setItem(i, 0, QTableWidgetItem(a))
        
        self.resizeColumnsToContents()
    
    def getSelectedAlignments(self) -> list[str]:
        """Get the name of the objects highlighted by the user.
        
            Returns:
                (list): the name of the objects
        """
        selected_indexes = self.selectedIndexes()
        alignments = []
        for i in selected_indexes:
            r = i.row()
            alignments.append(self.item(r, 0).text())
        return alignments
    
    def addAlignment(self, alignment : str):
        """Add an alignment to the list.
        
            Params:
                alignment (str): the name for the new alignment
        """
        if alignment in self.alignments:
            return
        
        self.alignments.append(alignment)
        self.alignments.sort()
        i = self.alignments.index(alignment)
        self.insertRow(i)
        self.setItem(i, 0, QTableWidgetItem(alignment))
        self.resizeColumnsToContents()
    
    def removeAlignment(self, alignment : str):
        """Remove an alignment from the list.
        
            Params:
                alignment(str): the name of the alignment to remove
        """
        if alignment not in self.alignments:
            return
        
        i = self.alignments.index(alignment)
        self.alignments.remove(alignment)
        self.removeRow(i)
        self.resizeColumnsToContents()
    
    def renameAlignment(self, alignment : str, new_name : str):
        """Rename an alignment on the list.
        
            Params:
                alignment (str): the alignment to rename
                new_name (str): the new name for the alignment
        """
        self.removeAlignment(alignment)
        self.addAlignment(new_name)
        self.resizeColumnsToContents()

class AlignmentDialog(QDialog):

    def __init__(self, parent : QWidget, alignment_names : list):
        """Create an object group dialog.
        
            Params:
                parent (QWidget): the parent widget
                alignment_names (list): the list of alignments
        """
        super().__init__(parent)

        self.setWindowTitle("Change Alignment")

        title_text = QLabel(self, text="Switch to Alignment")

        self.table = AlignmentList(self, alignment_names)

        remove_bttn = QPushButton(self, "remove", text="Remove")
        remove_bttn.clicked.connect(self.removeAlignments)

        rename_bttn = QPushButton(self, "rename", text="Rename...")
        rename_bttn.clicked.connect(self.renameAlignment)

        new_bttn = QPushButton(self, "new", text="New...")
        new_bttn.clicked.connect(self.newAlignment)

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

        self.added = []
        self.removed = []
        self.renamed = []
    
    def newAlignment(self):
        """Add a new alignment to the list."""
        new_alignment, confirmed = QInputDialog.getText(self, "New Alignment", "New alignment name:")
        if not confirmed:
            return
        if new_alignment in self.table.alignments:
            notify("This alignment already exists")
            return
        self.table.addAlignment(new_alignment)
        if new_alignment in self.removed:
            self.removed.remove(new_alignment)
        else:
            self.added.append(new_alignment)
    
    def removeAlignments(self):
        """Remove selected alignments from the list."""
        alignments = self.table.getSelectedAlignments()
        for a in alignments:
            self.table.removeAlignment(a)
            if a in self.added:
                self.added.remove(a)
            else:
                self.removed.append(a)
            newly_renamed = [i[1] for i in self.renamed]
            if a in newly_renamed:
                self.renamed.pop(newly_renamed.index(a))
    
    def renameAlignment(self):
        """Rename a selected alignment."""
        alignments = self.table.getSelectedAlignments()
        if len(alignments) > 1:
            notify("Please select only one alignment to rename.")
            return
        elif len(alignments) == 0:
            return
        a = alignments[0]
        
        new_name, confirmed = QInputDialog.getText(self, "Rename Alignment", "New alignment name:")
        if not confirmed:
            return
        if new_name in self.table.alignments:
            notify("This alignment already exists.")
            return
        
        self.table.renameAlignment(a, new_name)
        self.renamed.append((a, new_name))
        
    def accept(self):
        """Overwritten from parent class."""
        alignments = self.table.getSelectedAlignments()
        if len(alignments) > 1:
            notify("Please select only one alignment from the list.")
            return
        super().accept()
        
    def exec(self):
        """Run the dialog."""
        confirmed = super().exec()
        alignments = self.table.getSelectedAlignments()
        if alignments:
            a = alignments[0]
        else:
            a = None
        if confirmed:
            return (
                a,
                self.added,
                self.removed,
                self.renamed
            ), True
        else:
            return None, False