from PySide6.QtWidgets import (
    QWidget, 
    QDialog, 
    QDialogButtonBox,  
    QVBoxLayout, 
    QRadioButton,
    QLabel
)

class PointerDialog(QDialog):

    def __init__(self, parent : QWidget, pointer_opts : tuple):
        """Create an attribute dialog.
        
            Params:
                parent (QWidget): the parent widget
                pointer_opts (tuple): the current pointer options
        """
        super().__init__(parent)

        self.setWindowTitle("Pointer")

        shape, intersect = pointer_opts

        vlayout = QVBoxLayout()

        shape_widget = QWidget(self)
        shape_vlayout = QVBoxLayout()
        shape_widget.setLayout(shape_vlayout)

        shape_vlayout.addWidget(QLabel(shape_widget, text="Shape:"))

        self.rect_bttn = QRadioButton("Rectangle", self)
        shape_vlayout.addWidget(self.rect_bttn)
        if shape == "rect": self.rect_bttn.setChecked(True)

        self.lasso_bttn = QRadioButton("Lasso", shape_widget)
        shape_vlayout.addWidget(self.lasso_bttn)
        if shape == "lasso": self.lasso_bttn.setChecked(True)

        type_widget = QWidget(self)
        type_vlayout = QVBoxLayout()
        type_widget.setLayout(type_vlayout)

        type_vlayout.addWidget(QLabel(type_widget, text="Type:"))

        self.inc_bttn = QRadioButton("Include intersected traces", type_widget)
        type_vlayout.addWidget(self.inc_bttn)
        if intersect == "inc": self.inc_bttn.setChecked(True)

        self.exc_bttn = QRadioButton("Exclude intersected traces", type_widget)
        type_vlayout.addWidget(self.exc_bttn)
        if intersect == "exc": self.exc_bttn.setChecked(True)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonbox = QDialogButtonBox(QBtn)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        vlayout.addWidget(QLabel(self, text="Multiple Section Settings"))
        vlayout.addWidget(shape_widget)
        vlayout.addWidget(type_widget)
        vlayout.addWidget(buttonbox)

        self.setLayout(vlayout)
    
    def exec(self):
        """Run the dialog."""
        confirmed = super().exec()

        if confirmed:
            if self.rect_bttn.isChecked():
                shape = "rect"
            elif self.lasso_bttn.isChecked():
                shape = "lasso"
            else:
                return None, False
            if self.inc_bttn.isChecked():
                intersect = "inc"
            elif self.exc_bttn.isChecked():
                intersect = "exc"
            else:
                return None, False
            return [shape, intersect], True
        
        return None, False
