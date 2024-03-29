from PySide6.QtWidgets import QDockWidget, QTextEdit, QWidget
from PySide6.QtCore import Qt, QPoint

class TextWidget(QDockWidget):

    def __init__(self, parent : QWidget, output_str : str, title=" ", html=False):
        """Create a text widget."""
        super().__init__(parent)
        self.setFloating(True)
        self.setAllowedAreas(Qt.NoDockWidgetArea)
        self.setWindowTitle(title)

        self.output = QTextEdit(self)
        if html:
            self.output.setHtml(output_str)
        else:
            self.output.setPlainText(output_str)

        self.setWidget(self.output)

        px, py = parent.x(), parent.y()
        pw, ph = parent.width(), parent.height()
        s = min(pw, ph) // 2
        self.setGeometry(
            px + (pw - s) // 2, 
            py + (ph - s) // 2, 
            s, s
        )

        # pt = parent.mapToGlobal(parent.pos())
        # px, py = pt.x(), pt.y()
        # pw, ph = parent.width(), parent.height()
        # x = px + pw // 4
        # y = py + ph // 4
        # pt = self.mapFromGlobal(QPoint(x, y))
        # x, y = pt.x(), pt.y()
        # w = pw // 2
        # h = ph // 2
        # self.setGeometry(x, y, w, h)

        self.show()