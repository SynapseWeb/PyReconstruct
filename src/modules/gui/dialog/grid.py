from PySide6.QtWidgets import (
    QDialog, 
    QDialogButtonBox, 
    QHBoxLayout, 
    QLabel, 
    QLineEdit, 
    QVBoxLayout
)

from modules.gui.utils import notify

class GridDialog(QDialog):

    def __init__(self, parent, properties : tuple):
        """Create a dialog for brightness/contrast."""
        super().__init__(parent)

        w, h, dx, dy, nx, ny = properties

        self.setWindowTitle("Set Grid")

        size_row = QHBoxLayout()
        size_text = QLabel(self, text="Element size:")
        size_x_text = QLabel(self, text="X:")
        size_x_input = QLineEdit(self)
        size_x_input.setText(str(w))
        size_y_text = QLabel(self, text="Y:")
        size_y_input = QLineEdit(self)
        size_y_input.setText(str(h))
        size_row.addWidget(size_text)
        size_row.addWidget(size_x_text)
        size_row.addWidget(size_x_input)
        size_row.addWidget(size_y_text)
        size_row.addWidget(size_y_input)

        dist_row = QHBoxLayout()
        dist_text = QLabel(self, text="Distance:")
        dist_x_text = QLabel(self, text="X:")
        dist_x_input = QLineEdit(self)
        dist_x_input.setText(str(dx))
        dist_y_text = QLabel(self, text="Y:")
        dist_y_input = QLineEdit(self)
        dist_y_input.setText(str(dy))
        dist_row.addWidget(dist_text)
        dist_row.addWidget(dist_x_text)
        dist_row.addWidget(dist_x_input)
        dist_row.addWidget(dist_y_text)
        dist_row.addWidget(dist_y_input)

        num_row = QHBoxLayout()
        num_text = QLabel(self, text="Number:")
        num_x_text = QLabel(self, text="X:")
        num_x_input = QLineEdit(self)
        num_x_input.setText(str(nx))
        num_y_text = QLabel(self, text="Y:")
        num_y_input = QLineEdit(self)
        num_y_input.setText(str(ny))
        num_row.addWidget(num_text)
        num_row.addWidget(num_x_text)
        num_row.addWidget(num_x_input)
        num_row.addWidget(num_y_text)
        num_row.addWidget(num_y_input)

        self.inputs = [
            size_x_input, size_y_input,
            dist_x_input, dist_y_input,
            num_x_input, num_y_input
        ]

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonbox = QDialogButtonBox(QBtn)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.vlayout = QVBoxLayout()
        self.vlayout.setSpacing(10)
        self.vlayout.addLayout(size_row)
        self.vlayout.addLayout(dist_row)
        self.vlayout.addLayout(num_row)
        self.vlayout.addWidget(self.buttonbox)

        self.setLayout(self.vlayout)
    
    def accept(self):
        """Overwritten from parent class."""
        for input in self.inputs[:4]:
            if not input.text().replace(".", "", 1).isnumeric():
                notify("Please enter a valid number.")
                return
        for input in self.inputs[4:]:
            if not input.text().isnumeric():
                notify("Please enter a whole number for the grid number.")
                return
        
        super().accept()
    
    def exec(self):
        "Run the dialog."
        confirmed = super().exec()
        if confirmed:
            response = []
            for input in self.inputs[:4]:
                response.append(float(input.text()))
            for input in self.inputs[4:]:
                response.append(int(input.text()))
            return response, True
        else:
            return None, False