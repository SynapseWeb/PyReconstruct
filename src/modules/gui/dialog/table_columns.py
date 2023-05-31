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

        title_text = QLabel(self)
        title_text.setText("Table columns:")

        self.cbs = []
        for c in columns:
            c_cb = QCheckBox(self)
            c_cb.setText(c)
            c_cb.setChecked(columns[c])
            self.cbs.append(c_cb)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonbox = QDialogButtonBox(QBtn)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        vlayout = QVBoxLayout(self)
        vlayout.setSpacing(10)
        vlayout.addWidget(title_text)
        for c_row in self.cbs:
            vlayout.addWidget(c_row)
        vlayout.addWidget(buttonbox)

        self.setLayout(vlayout)
    
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