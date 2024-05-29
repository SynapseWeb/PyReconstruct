from PySide6.QtWidgets import (
    QWidget, 
    QDialog, 
    QDialogButtonBox, 
    QCheckBox, 
    QVBoxLayout, 
    QHBoxLayout,
    QPushButton,
    QStyle,
    QScrollArea
)

class TableColumnsDialog(QDialog):

    def __init__(self, parent : QWidget, columns : list):
        """Create a table column dialog.
        
            Params:
                parent (QWidget): the parent widget
        """
        super().__init__(parent)

        self.setWindowTitle("Table Columns")

        self.vlayout = QVBoxLayout()

        self.columns = columns.copy()
        self.createColumnsWidget()
        
        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonbox = QDialogButtonBox(QBtn)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        self.vlayout.addWidget(self.qsa)
        self.vlayout.addWidget(buttonbox)

        self.setLayout(self.vlayout)
    
    def createMoveButtons(self, index : int):
        """Create a pair of buttons to allow the option to be moved up and down.
        
            Params:
                index (int): the index corresponding to the buttons' place in self.columns
        """
        # create buttons layout
        bttns = QVBoxLayout()
        bttns.setSpacing(0)
        bsize = (20, 20)
        style_sheet = """
        QPushButton {background-color: transparent;}
        QPushButton:hover {border: 1px solid yellow;}
        """
        # create up button
        up_bttn = QPushButton(self.columns_widget)
        up_bttn.setStyleSheet(style_sheet)
        up_bttn.setText("▲")
        up_bttn.setFixedSize(*bsize)
        up_bttn.clicked.connect(lambda : self.moveRow(index=index, up=True))

        # create down button
        down_bttn = QPushButton(self.columns_widget)
        down_bttn.setStyleSheet(style_sheet)
        down_bttn.setText("▼")
        down_bttn.setFixedSize(*bsize)
        down_bttn.clicked.connect(lambda : self.moveRow(index=index, up=False))

        bttns.addWidget(up_bttn)
        bttns.addWidget(down_bttn)

        return bttns
    
    def createCheckbox(self, name : str, state : bool):
        """Create a checkbox with the column name.
        
            Params:
                name (str): the name of the column
                state (bool): True if column is included on the table
        """
        cb = QCheckBox(self, text=name)
        cb.setChecked(state)
        cb.stateChanged.connect(lambda : self.checkColumn(name=name))
        return cb
    
    def createColumnsWidget(self):
        """Create the widget containing all column checkboxes and buttons."""
        columns_layout = QVBoxLayout()
        columns_layout.setSpacing(0)
        self.qsa = QScrollArea(self)
        self.columns_widget = QWidget(self)

        for i, (key, b) in enumerate(self.columns):
            row = QHBoxLayout()
            row.setSpacing(10)
            row.addLayout(self.createMoveButtons(i))
            row.addWidget(self.createCheckbox(key, b))

            columns_layout.addLayout(row)
        
        self.columns_widget.setLayout(columns_layout)
        self.qsa.setWidget(self.columns_widget)
    
    def checkColumn(self, name : str):
        """Called when a column is checked.
        
            Params:
                name (str): the name of the column
        """
        for i, (key, b) in enumerate(self.columns.copy()):
            if key == name:
                n, s = self.columns[i]
                self.columns[i] = (n, not s)
                return
    
    def resetColumnsWidget(self):
        """Reset the widget containing all the columns (called when order is changed)."""
        self.columns_widget.close()
        pos = self.qsa.verticalScrollBar().value()
        self.qsa.close()
        self.createColumnsWidget()
        self.qsa.verticalScrollBar().setValue(pos)
        self.vlayout.insertWidget(0, self.qsa)
    
    def moveRow(self, index : int, up=True):
        """Move a row (checkbox and buttons) in the columns widget.
        
            Params:
                index (int): the index of the row to move
                up (bool): True if row should be moved up
        """
        if not up and index == len(self.columns) - 1:
            return
        elif up and index == 0:
            return
        item = self.columns.pop(index)
        index += (-1 if up else 1)
        self.columns.insert(index, item)
        self.resetColumnsWidget()
    
    def exec(self):
        """Run the dialog."""
        confirmed = super().exec()
        if confirmed:
            return self.columns, True
        else:
            return None, False