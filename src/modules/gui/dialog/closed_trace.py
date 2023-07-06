from PySide6.QtWidgets import (
    QWidget, 
    QDialog, 
    QDialogButtonBox, 
    QRadioButton, 
    QVBoxLayout, 
)

class ClosedTraceDialog(QDialog):

    def __init__(self, parent : QWidget, mode : str):
        """Create an attribute dialog.
        
            Params:
                parent (QWidget): the parent widget
                mode (str): the current closed trace mode
        """
        super().__init__(parent)

        self.setWindowTitle("Closed Trace Mode")

        vlayout = QVBoxLayout()

        self.trace_bttn = QRadioButton("Trace", self)
        vlayout.addWidget(self.trace_bttn)
        if mode == "trace": self.trace_bttn.setChecked(True)

        self.rect_bttn = QRadioButton("Rectangle", self)
        vlayout.addWidget(self.rect_bttn)
        if mode == "rect": self.rect_bttn.setChecked(True)

        self.circle_bttn = QRadioButton("Circle", self)
        vlayout.addWidget(self.circle_bttn)
        if mode == "circle": self.circle_bttn.setChecked(True)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonbox = QDialogButtonBox(QBtn)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        vlayout.addWidget(buttonbox)

        self.setLayout(vlayout)
    
    def exec(self):
        """Run the dialog."""
        confirmed = super().exec()
        if confirmed:
            if self.trace_bttn.isChecked():
                return "trace", True
            elif self.rect_bttn.isChecked():
                return "rect", True
            elif self.circle_bttn.isChecked():
                return "circle", True
        
        return None, False
