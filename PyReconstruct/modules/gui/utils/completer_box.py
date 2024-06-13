from PySide6.QtWidgets import QComboBox, QCompleter
from PySide6.QtCore import Qt

from .str_helper import sortList

class CompleterBox(QComboBox):

    def __init__(self, parent=None, str_list : list = [], allow_new=False):
        """Create the CompleterBox widget."""
        super().__init__(parent)
        sorted_list = sortList(str_list)
        self.addItems(sorted_list)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        completer = self.completer()
        completer.setCompletionMode(QCompleter.PopupCompletion)
        completer.setCaseSensitivity(Qt.CaseSensitive)
        self.check_text = not allow_new
        self.current_text = self.currentText()
        self.currentTextChanged.connect(self.checkText)
    
    def checkText(self, new_text : str):
        """Ensure that text matches one of the options."""
        if not self.check_text:
            return
        
        if self.completer().currentCompletion() or self.findText(new_text) != -1:
            self.current_text = new_text
        else:
            self.check_text = False
            self.setCurrentText(self.current_text)
            self.check_text = True
    
    def focusOutEvent(self, event):
        if self.check_text and self.findText(self.currentText()) == -1:
            t = self.completer().currentCompletion()
            if t:
                self.setCurrentText(self.completer().currentCompletion())
            else:
                self.setCurrentText(self.itemText(0))
        super().focusOutEvent(event)
