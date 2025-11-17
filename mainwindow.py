# This Python file uses the following encoding: utf-8
import os
import sys

from PySide6 import QtCore
from PySide6.QtWidgets import QApplication, QMainWindow

# Important:
# You need to run the following command to generate the ui_form.py file
#     pyside6-uic form.ui -o ui_form.py, or
#     pyside2-uic form.ui -o ui_form.py
from ui_form import Ui_MainWindow

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.date_select.setDate(QtCore.QDate.currentDate())
        self.ui.start_date.setDate(QtCore.QDate.currentDate().addDays(-7))
        self.ui.finish_date.setDate(QtCore.QDate.currentDate())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())
