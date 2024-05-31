from PySide6.QtWidgets import QComboBox, QCompleter

from .str_helper import sortList

class CompleterBox(QComboBox):

    def __init__(self, str_list : list, parent=None, allow_new=False):
        """Create the CompleterBox widget."""
        super().__init__(parent)
        sorted_list = sortList(str_list)
        self.addItems(sorted_list)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.completer().currentCompletion
        self.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.check_text = not allow_new
        self.current_text = self.currentText()
        self.currentTextChanged.connect(self.checkText)
    
    def checkText(self, new_text : str):
        """Ensure that text matches one of the options."""
        if not self.check_text:
            return
        
        if self.completer().currentCompletion():
            self.current_text = new_text
        else:
            self.check_text = False
            self.setCurrentText(self.current_text)
            self.check_text = True