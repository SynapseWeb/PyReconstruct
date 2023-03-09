from PySide6.QtWidgets import (
    QDialog, 
    QDialogButtonBox, 
    QLabel, 
    QVBoxLayout, 
    QCheckBox
)

class TableColumnsDialog(QDialog):

    def __init__(self, parent, columns : dict):
        """Create an object table column dialog.
        
            Params:
                parent (QWidget): the parent widget for the dialog
                columns (dict): the existing columns and their status
        """
        super().__init__(parent)

        self.setWindowTitle("Table Columns")

        self.title_text = QLabel(self)
        self.title_text.setText("Table columns:")

        self.cbs = []
        for c in columns:
            c_cb = QCheckBox(self)
            c_cb.setText(c)
            c_cb.setChecked(columns[c])
            self.cbs.append(c_cb)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonbox = QDialogButtonBox(QBtn)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.vlayout = QVBoxLayout(self)
        self.vlayout.setSpacing(10)
        self.vlayout.addWidget(self.title_text)
        for c_row in self.cbs:
            self.vlayout.addWidget(c_row)
        self.vlayout.addWidget(self.buttonbox)

        self.setLayout(self.vlayout)
    
    def exec(self):
        """Run the dialog."""
        confirmed = super().exec()
        if confirmed:
            columns = {}
            for cb in self.cbs:
                columns[cb.text()] = cb.isChecked()
            return columns, True
        else:
            return {}, False