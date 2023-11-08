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
    QLineEdit,
    QScrollArea,
    QApplication,
    QCheckBox
)

from PyReconstruct.modules.datatypes import Flag

from .color_button import ColorButton

class FlagDialog(QDialog):

    def __init__(self, parent : QWidget, flag : Flag):
        """Create a zarr dialog.
        
            Params:
                parent (QWidget): the parent widget
                flag (Flag): the flag to edit
        """

        super().__init__(parent)

        self.setWindowTitle("Flag")

        self.vlayout = QVBoxLayout()
        self.vlayout.setSpacing(10)

        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel(self, text="Name:"))
        self.name_input = QLineEdit(self, text=flag.name)
        hlayout.addWidget(self.name_input)
        self.vlayout.addLayout(hlayout)

        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel(self, text="Color:"))
        self.color_bttn = ColorButton(flag.color, self)
        hlayout.addWidget(self.color_bttn)
        hlayout.addStretch()
        self.vlayout.addLayout(hlayout)

        self.vlayout.addWidget(QLabel(self, text="Comments:"))
        vlayout = QVBoxLayout()
        self.fields = {}
        for index, comment in enumerate(flag.comments):
            hlayout = self.createRow(comment, index)
            self.fields[index] = (hlayout, comment)
            vlayout.addLayout(hlayout)
        vlayout.addStretch()
        w = QWidget(self)
        w.setLayout(vlayout)
        qsa = QScrollArea()
        self.screen_height = QApplication.primaryScreen().size().height()
        qsa.setMinimumHeight(self.screen_height / 4)
        qsa.setWidgetResizable(True)
        qsa.setWidget(w)
        self.vlayout.addWidget(qsa)
        
        self.vlayout.addWidget(QLabel(self, text="Add Comment (opt):"))
        self.new_comment = QTextEdit(self)
        self.new_comment.textChanged.connect(self.resizeNewComment)
        self.vlayout.addWidget(self.new_comment)

        self.resolved = QCheckBox(self, text="Resolved")
        self.resolved.setChecked(flag.resolved)
        self.vlayout.addWidget(self.resolved)
        
        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonbox = QDialogButtonBox(QBtn)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        self.vlayout.addWidget(buttonbox)

        self.setLayout(self.vlayout)

        self.show()
        self.hide()
    
    def createRow(self, comment, index):
        """Create a row of the dialog."""
        hlayout = QHBoxLayout()

        bttn = QPushButton(self)
        bttn.setIcon(self.style().standardIcon(
            QStyle.SP_DockWidgetCloseButton
        ))
        bttn.clicked.connect(lambda : self.removeRow(index=index))
        hlayout.addWidget(bttn)

        lbl = QLabel(self, text=comment.user + "\n" + comment.date)
        hlayout.addWidget(lbl)

        te = QTextEdit(comment.text.replace("\n", "<br/>"), self)
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
        elif h > self.screen_height / 5:
            h = self.screen_height / 5
        self.new_comment.setFixedHeight(h + 3)
        self.resizeToContents()
    
    def resizeToContents(self):
        """Adjust the size of the dialog to fit its contents"""
        self.adjustSize()
        self.resize(self.width(), self.minimumHeight())
        if self.y() + self.height() > self.screen_height:
            self.resize(self.width(), self.screen_height - self.y())

    def exec(self):
        """Run the dialog."""
        for hlayout, comment in self.fields.values():
            te = hlayout.itemAt(2).widget()
            te.setFixedHeight(te.document().size().toSize().height() + 3)
        self.resizeNewComment()

        confirmed = super().exec()
        if confirmed:
            title = self.name_input.text()
            color = self.color_bttn.getColor()
            comments = []
            for index in sorted(self.fields.keys()):
                hlayout, comment = self.fields[index]
                comments.append(comment)
            new_comment = self.new_comment.toPlainText()
            resolved = self.resolved.isChecked()
            return (title, color, comments, new_comment, resolved), True
        else:
            return None, False
