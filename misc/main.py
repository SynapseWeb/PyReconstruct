import sys
from PySide6.QtWidgets import QApplication, QApplication, QMainWindow
from series_opts import SeriesOptions


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = SeriesOptions()
        self.ui.setupUi(self)

        self.ui.stackedWidget.setCurrentWidget(self.ui.Series)

        self.ui.btn_series.clicked.connect(self.showSeriesOptions)
        self.ui.btn_rendering.clicked.connect(self.showRenderingOptions)
        self.ui.btn_interface.clicked.connect(self.showInterfaceOptions)
        self.ui.btn_navigation.clicked.connect(self.showNavigationOptions)

    def showSeriesOptions(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.Series)

    def showRenderingOptions(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.Rendering)

    def showInterfaceOptions(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.Interface)

    def showNavigationOptions(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.Navigation)
            

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
