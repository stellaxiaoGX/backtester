import pandas as pd
import numpy as np
import datetime as dt
from pandas.tseries.offsets import BDay

import faulthandler
import widget_functions as wf
from popup_messages import PopUpMsg
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QDate, QDateTime
import qtwidgets

import os
cur_dir = os.path.dirname(__file__)
import sys

# Custom popup dialog class
class PopupDialog(QDialog):
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Popup Window")
        self.setFixedSize(250, 120)

        # Layout and widgets
        layout = QVBoxLayout()
        layout.addWidget(QLabel(message))

        self.setLayout(layout)

# Main Backtest application window
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Backtester")
        self.setGeometry(0, 0, 400, 500)
        
        # Button to trigger popup
        self.button = QPushButton("Run Backtest", self)
        self.button.clicked.connect(self.popup_show_backtest_results)
        self.button.resize(120, 40)
        self.button.move(140, 440)
        
        self.dateedit1 = QDateEdit(self, calendarPopup=True)
        self.dateedit1.setDateTime(dt.datetime.today() - BDay(5))
        self.dateedit1.move(70, 10)
        
        self.dateedit2 = QDateEdit(self, calendarPopup=True)
        self.dateedit2.setDateTime(QtCore.QDateTime.currentDateTime())
        self.dateedit2.move(240, 10)
        
        self.label_start = QLabel('Start Date:', self)
        self.label_start.move(10, 10)
        self.label_end = QLabel('End Date:', self)
        self.label_end.move(180, 10)
        
        self.portfolio_csv = None
        self.otm_percentage = 0.01
        self.itm_percentage = 0.01
        
    def read_portfolio(self):
        file = self.portfolio_csv
        results = []
        return result    
        
    
    def backtest(self, portfolio):
        results = []
        return results
        
    def popup_show_backtest_results(self):
        popup = PopupDialog("Hello! Here are the backtest results.", self)
        popup.exec_()
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
