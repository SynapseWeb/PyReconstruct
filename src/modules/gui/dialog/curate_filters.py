from PySide6.QtWidgets import (
    QDialog,
    QLineEdit, 
    QDialogButtonBox, 
    QLabel, 
    QVBoxLayout, 
    QCheckBox
)

class CurateFiltersDialog(QDialog):

    def __init__(self, parent, cr_statuses : dict, cr_users : set):
        """Create an object table column dialog.
        
            Params:
                parent (QWidget): the parent widget for the dialog
                columns (dict): the existing columns and their status
        """
        super().__init__(parent)

        self.setWindowTitle("Curation Filters")

        title_text = QLabel(self)
        title_text.setText("Curation Status:")

        self.cbs = []
        for s in cr_statuses:
            s_cb = QCheckBox(self)
            s_cb.setText(s)
            s_cb.setChecked(cr_statuses[s])
            self.cbs.append(s_cb)
        
        self.users_lbl = QLabel(self, text="Users (separate with comma and space):")
        self.users_text = QLineEdit(parent=self)
        if cr_users:
            self.users_text.setText(", ".join(cr_users))

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonbox = QDialogButtonBox(QBtn)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        vlayout = QVBoxLayout(self)
        vlayout.setSpacing(10)

        vlayout.addWidget(title_text)

        for c_row in self.cbs:
            vlayout.addWidget(c_row)

        vlayout.addWidget(self.users_lbl)
        vlayout.addWidget(self.users_text)

        vlayout.addWidget(buttonbox)

        self.setLayout(vlayout)
    
    def exec(self):
        """Run the dialog."""
        confirmed = super().exec()
        if confirmed:
            cr_statuses = {}
            for cb in self.cbs:
                t = cb.text()
                cr_statuses[t] = cb.isChecked()
            users_text = self.users_text.text()
            if users_text:
                cr_users = set(self.users_text.text().split(", "))
            else:
                cr_users = set()
            return (cr_statuses, cr_users), True
        else:
            return None, False