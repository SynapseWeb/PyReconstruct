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
    QTableWidgetItem, 
    QAbstractItemView,
)

from PyReconstruct.modules.gui.utils import notify
from PyReconstruct.modules.datatypes.objects import Objects, SeriesObject

class AlignmentDialog(QDialog):

    def __init__(self, parent : QWidget, alignment_names : list, current_alignment : str):
        """Create an object group dialog.
        
            Params:
                parent (QWidget): the parent widget
                alignment_names (list): the list of alignments
        """
        super().__init__(parent)
        self.mainwindow = parent

        self.setWindowTitle(" ")

        title_text = QLabel(self, text="Switch to Alignment")

        self.table = AlignmentList(self, alignment_names, current_alignment)

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
    
    def newAlignment(self):
        """Add a new alignment to the list."""
        new_alignment, confirmed = QInputDialog.getText(self, "New Alignment", "New alignment name:")
        if not confirmed:
            return
        if (new_alignment in self.table.adict and self.table.adict[new_alignment] is not None):
            notify("This alignment already exists")
            return
        self.table.addAlignment(new_alignment)
    
    def removeAlignments(self):
        """Remove selected alignments from the list."""
        alignments = self.table.getSelectedAlignments()
        if "no-alignment" in alignments:
            notify("Cannot remove no-alignment setting.")
            return
        
        for a in alignments:
            self.table.removeAlignment(a)
    
    def renameAlignment(self):
        """Rename a selected alignment."""
        alignments = self.table.getSelectedAlignments()
        if len(alignments) > 1:
            notify("Please select only one alignment to rename.")
            return
        elif len(alignments) == 0:
            return
        a = alignments[0]
        if a == "no-alignment":
            notify("Cannot rename no-alignment setting.")
            return
        
        new_name, confirmed = QInputDialog.getText(self, "Rename Alignment", "New alignment name:")
        if not confirmed:
            return
        if new_name in self.table.adict:
            notify("This alignment already exists.")
            return
        
        self.table.renameAlignment(a, new_name)
        
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
                self.table.adict
            ), True
        else:
            return None, False

class AlignmentList(QTableWidget):

    def __init__(self, parent : AlignmentDialog, alignment_names : list, current_alignment : str):
        """Create an alignment list widget."""
        self.adict = {}
        for a in sorted(alignment_names):
            self.adict[a] = a
        self.current_alignment = current_alignment

        super().__init__(0, 1, parent)
        
        self.series = parent.mainwindow.series
        self.setShowGrid(False)
        self.verticalHeader().hide()
        self.horizontalHeader().hide()
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.createTable()
            
    def createTable(self):
        """Create the table."""
        # remove rows
        while self.rowCount():
            self.removeRow(0)
        # create the rows
        r = 0
        for i, a in enumerate(sorted(self.adict.keys())):
            if self.adict[a] is not None:
                self.insertRow(r)
                self.setItem(r, 0, QTableWidgetItem(str(a)))
                r += 1
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
        if alignment in self.adict and self.adict[alignment] is not None:
            return
        self.adict[alignment] = self.current_alignment
        self.createTable()
    
    def removeAlignment(self, alignment : str):
        """Remove an alignment from the list.
        
            Params:
                alignment(str): the name of the alignment to remove
        """
        if alignment not in self.adict or alignment == "no-alignment":
            return
        self.adict[alignment] = None
        self.createTable()
    
    def renameAlignment(self, alignment : str, new_name : str):
        """Rename an alignment on the list.
        
            Params:
                alignment (str): the alignment to rename
                new_name (str): the new name for the alignment
        """
        if (alignment not in self.adict or 
            (new_name in self.adict and self.adict[alignment] is not None) or 
            alignment == "no-alignment"):
            return
        self.adict[new_name] = self.adict[alignment]

        ## Set objs to new alignment name
        
        series_objs = Objects(self.series).getNames()

        for obj in series_objs:

            obj_data = SeriesObject(self.series, obj)

            if not obj_data.alignment == alignment:
                continue

            self.series.setAttr(obj, "alignment", new_name)

        self.adict[alignment] = None
        
        self.createTable()
