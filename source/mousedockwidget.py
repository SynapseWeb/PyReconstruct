from PySide2.QtWidgets import QWidget, QDockWidget, QPushButton
from PySide2.QtGui import QIcon, QPixmap, QPainter, QPen, QColor
from PySide2.QtCore import QSize, Qt

class MouseDockWidget(QDockWidget):

    def __init__(self, parent, button_size=30):
        super().__init__(parent)
        self.setFloating(True)
        self.setFeatures(QDockWidget.DockWidgetFloatable |
                         QDockWidget.DockWidgetMovable)
        self.setAllowedAreas(Qt.NoDockWidgetArea)
        self.setWindowTitle(" ")
        self.bsize = button_size
        self.central_widget = QWidget()
        self.setFixedSize(self.bsize*5, self.bsize*2)

        self.buttons = {}

        self.createButton("pointer", 0, 0, parent.toPointer)
        self.createButton("panzoom", 1, 0, parent.toPanzoom)
        self.createButton("pencil", 0, 1, parent.toPencil)
        #self.createButton("color", 1, 1, parent.setPencilColor)
        #self.createButton("name", 2, 1, parent.setPencilName)

        self.highlight_pixmap = QPixmap(self.bsize, self.bsize)
        self.highlight_pixmap.fill(Qt.transparent)
        painter = QPainter(self.highlight_pixmap)
        painter.setPen(QPen(QColor(0, 0, 0), 5))
        painter.drawLine(0, 0, 0, self.bsize)
        painter.drawLine(0, self.bsize, self.bsize, self.bsize)
        painter.drawLine(self.bsize, self.bsize, self.bsize, 0)
        painter.drawLine(self.bsize, 0, 0, 0)
        painter.end()

        self.setWidget(self.central_widget)
        self.show()
    
    def buttonClicked(self):
        sender = self.sender()
        for name, button in self.buttons.items():
            if button[0] == sender:
                button[0].setChecked(True)
                button[1]()
            else:
                button[0].setChecked(False)      

    def createButton(self, name, row, col, func):
        b = QPushButton(self.central_widget)
        pixmap = QPixmap(name + ".png").scaled(self.bsize, self.bsize)
        #pixmap = changePixmapOpacity(pixmap, 0.5)
        b.setIcon(QIcon(pixmap))
        b.setIconSize(QSize(self.bsize, self.bsize))
        b.setGeometry(row*self.bsize, col*self.bsize, self.bsize, self.bsize)
        b.setCheckable(True)
        if (row, col) == (0, 0):
            b.setChecked(True)
        b.clicked.connect(self.buttonClicked)
        self.buttons[name] = (b, func)
        