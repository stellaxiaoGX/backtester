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

# Backtest Popup after running on all inputs
class BackTestResults(QDialog):
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Results Window")
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
        
        # Final Bottom Button to trigger Backtesting Screen Popup
        self.button = QPushButton("Run Backtest", self)
        self.button.clicked.connect(self.popup_show_backtest_results)
        self.button.resize(120, 40)
        self.button.move(140, 440)
        
        # Date Range Selection
        self.dateedit1 = QDateEdit(self, calendarPopup=True)
        self.dateedit1.setDateTime(dt.datetime.today() - BDay(5))
        self.dateedit1.setMaximumDate(dt.datetime.today() - BDay(1))
        self.dateedit1.dateChanged.connect(self.update_label)
        self.dateedit1.move(70, 10)
        
        self.dateedit2 = QDateEdit(self, calendarPopup=True)
        self.dateedit2.setDateTime(QtCore.QDateTime.currentDateTime())
        self.dateedit2.setMaximumDate(dt.datetime.today() - BDay(1))
        self.dateedit2.dateChanged.connect(self.update_label)
        self.dateedit2.move(240, 10)
        
        self.label_start = QLabel('Start Date:', self)
        self.label_start.move(10, 10)
        self.label_end = QLabel('End Date:', self)
        self.label_end.move(180, 10)
        self.check_dates_label = QLabel("", self)
        self.check_dates_label.resize(300, 30)
        self.check_dates_label.move(10, 40)
        self.update_label()
        
        # Portfolio File Input
        
        
        # Backtest Inputs
        
        
        
    def update_label(self):
        if self.dateedit1.date() > self.dateedit2.date():
            self.check_dates_label.setText("Warning: start date must be before end date.")
            self.check_dates_label.setStyleSheet("color: red;")
        else:
            formatted_start_date = self.dateedit1.date().toString("yyyy-dd-MM")
            formatted_end_date = self.dateedit2.date().toString("yyyy-dd-MM")
            self.check_dates_label.setText(f"Selected Date Range: {formatted_start_date} to {formatted_end_date}")
            self.check_dates_label.setStyleSheet("color: black;")
        
        
    def read_portfolio(self):
        file = self.portfolio_csv
        results = []
        return result    
        
    
    def backtest(self, portfolio):
        results = []
        return results
        
    def popup_show_backtest_results(self):
        popup = BackTestResults("Hello! Here are the backtest results.", self)
        popup.exec_()
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
