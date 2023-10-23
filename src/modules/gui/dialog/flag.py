from PySide6.QtWidgets import (
    QWidget, 
    QDialog, 
    QDialogButtonBox, 
    QHBoxLayout, 
    QLabel, 
    QVBoxLayout, 
    QTextEdit,
    QPushButton,
    QStyle,
    QLineEdit
)

from modules.datatypes import Flag, Series

from .color_button import ColorButton

class FlagDialog(QDialog):

    def __init__(self, parent : QWidget, flag : Flag, series : Series):
        """Create a zarr dialog.
        
            Params:
                parent (QWidget): the parent widget
                flag (Flag): the flag to edit
                series (Series): the series
        """
        self.series = series

        super().__init__(parent)

        self.setWindowTitle("Flag Comments")

        self.vlayout = QVBoxLayout()
        self.vlayout.setSpacing(10)

        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel(self, text="Title:"))
        self.title_input = QLineEdit(self, text=flag.title)
        hlayout.addWidget(self.title_input)
        self.vlayout.addLayout(hlayout)

        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel(self, text="Color:"))
        self.color_bttn = ColorButton(flag.color, self)
        hlayout.addWidget(self.color_bttn)
        hlayout.addStretch()
        self.vlayout.addLayout(hlayout)

        self.vlayout.addWidget(QLabel(self, text="Comments:"))
        self.fields = {}
        for index, (user, comment) in enumerate(flag.comments):
            hlayout = self.createRow(user, comment, index)
            self.fields[index] = (hlayout, (user, comment))
            self.vlayout.addLayout(hlayout)
        
        self.vlayout.addWidget(QLabel(self, text="New Comment:"))
        self.new_comment = QTextEdit(self)
        self.new_comment.textChanged.connect(self.resizeNewComment)
        self.vlayout.addWidget(self.new_comment)
        
        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonbox = QDialogButtonBox(QBtn)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        self.vlayout.addWidget(buttonbox)

        self.setLayout(self.vlayout)

        self.show()
        self.hide()
    
    def createRow(self, user, comment, index):
        """Create a row of the dialog."""
        hlayout = QHBoxLayout()

        bttn = QPushButton(self)
        bttn.setIcon(self.style().standardIcon(
            QStyle.SP_DockWidgetCloseButton
        ))
        bttn.clicked.connect(lambda : self.removeRow(index=index))
        hlayout.addWidget(bttn)

        lbl = QLabel(self, text=user)
        hlayout.addWidget(lbl)

        te = QTextEdit(comment.replace("\n", "<br/>"), self)
        te.setEnabled(False)
        hlayout.addWidget(te)

        return hlayout

    def removeRow(self, index):
        """Remove a row from the dialog."""
        hlayout, comment = self.fields[index]
        del(self.fields[index])
        self.vlayout.removeItem(hlayout)
        for i in range(hlayout.count()):
            hlayout.itemAt(i).widget().close()
        self.resizeToContents()
    
    def resizeNewComment(self):
        """Resize the new comment field to its contents."""
        h = self.new_comment.document().size().toSize().height()
        if h == 0:
            self.new_comment.setText("X")
            h = self.new_comment.document().size().toSize().height()
            self.new_comment.setText("")
        self.new_comment.setFixedHeight(h + 3)
        self.resizeToContents()
    
    def resizeToContents(self):
        """Adjust the size of the dialog to fit its contents"""
        self.adjustSize()
        self.resize(self.width(), self.minimumHeight())       

    def exec(self):
        """Run the dialog."""
        for hlayout, comment in self.fields.values():
            te = hlayout.itemAt(2).widget()
            te.setFixedHeight(te.document().size().toSize().height() + 3)
        self.resizeNewComment()
        self.move(self.parent().rect().center() - self.rect().center())

        confirmed = super().exec()
        if confirmed:
            title = self.title_input.text()
            color = self.color_bttn.getColor()
            comments = []
            for index in sorted(self.fields.keys()):
                hlayout, comment = self.fields[index]
                comments.append(comment)
            new_comment = self.new_comment.toPlainText()
            if new_comment:
                comments.append((self.series.user, new_comment))
            return (title, color, comments), True
        else:
            return None, False
