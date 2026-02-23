import pandas as pd
import numpy as np
import datetime as dt
from pandas.tseries.offsets import BDay
from pathlib import Path

import faulthandler
import widget_functions as wf
from popup_messages import PopUpMsg
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QDate, QDateTime
from PyQt5.QtGui import QFont
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
        self.setFixedSize(400, 300)
        self.setGeometry(200, 200, 400, 300)
        layout = QVBoxLayout()

        # Fonts
        big_font = QFont()
        big_font.setPointSize(11)
        small_font = QFont()
        small_font.setPointSize(10)

        # Final Bottom Button to trigger Backtesting Screen Popup
        self.button = QPushButton("Run Backtest", self)
        self.button.clicked.connect(self.popup_show_backtest_results)
        self.button.resize(120, 40)
        self.button.move(140, 245)
        
        # Date Range Selection
        self.dateedit1 = QDateEdit(self, calendarPopup=True)
        self.dateedit1.setDateTime(dt.datetime.today() - BDay(5))
        self.dateedit1.setMaximumDate(dt.datetime.today() - BDay(1))
        self.dateedit1.dateChanged.connect(self.update_label)
        self.dateedit1.move(80, 10)
        
        self.dateedit2 = QDateEdit(self, calendarPopup=True)
        self.dateedit2.setDateTime(QtCore.QDateTime.currentDateTime())
        self.dateedit2.setMaximumDate(dt.datetime.today() - BDay(1))
        self.dateedit2.dateChanged.connect(self.update_label)
        self.dateedit2.move(260, 10)
        
        self.label_start = QLabel('Start Date:', self)
        self.label_start.setFont(small_font)
        self.label_start.move(10, 10)
        self.label_end = QLabel('  End Date:', self)
        self.label_end.setFont(small_font)
        self.label_end.move(190, 10)
        self.check_dates_label = QLabel("", self)
        self.check_dates_label.resize(300, 30)
        self.check_dates_label.move(10, 40)
        self.update_label()
        
        self.start_date = self.dateedit1.date()
        self.end_date = self.dateedit2.date()
        
        # Portfolio File Input
        self.portfolio_input = QLineEdit(self)
        self.portfolio_input.move(10, 80)
        self.portfolio_input.resize(260, 30)
        self.portfolio_input.setPlaceholderText("Select a portfolio file (csv)...")
        
        self.browse_button = QPushButton("Select Portfolio", self)
        self.browse_button.move(280, 80)
        self.browse_button.clicked.connect(self.select_portfolio_folder)
        
        # Underlying Input
        self.underly_label = QLabel("Define Underlying Asset", self)
        self.underly_label.setFont(big_font)
        self.underly_label.resize(200, 40)
        self.underly_label.move(10, 120)

        self.ticker = QLabel("Stock / ETF:", self)
        self.ticker.move(50, 160)
        self.ticker.setFont(small_font)
        self.ticker.resize(100, 30)
        self.input_box = QLineEdit(self)
        self.input_box.move(140, 160)
        self.input_box.setFont(small_font)
        self.input_box.resize(240, 30)
        self.input_box.setPlaceholderText(f" Enter ticker for Stock or ETF ...")
        
        self.region_ticker = QLabel("Country Code:", self)
        self.region_ticker.move(50, 200)
        self.region_ticker.setFont(small_font)
        self.region_ticker.resize(100, 30)
        self.region_input_box = QLineEdit(self)
        self.region_input_box.move(140, 200)
        self.region_input_box.setFont(small_font)
        self.region_input_box.resize(240, 30)
        self.region_input_box.setPlaceholderText(f" Enter Bloomberg country code ...")
    
    def popup_show_backtest_results(self):
        
        portfolio_path = self.portfolio_path
        ticker = self.input_box.text()
        country = self.region_input_box.text()
        # Warnings:
        if self.start_date > self.end_date:
            QMessageBox.warning(self, "Invalid Date Range", "Start Date must be before End Date.")
            return
        if not os.path.isfile(self.portfolio_path):
            QMessageBox.warning(self, "Invalid Portfolio Path", "Invalid portfolio configuration file path.")
            return
        #if ticker not in valid_list:
        #    QMessageBox.warning(self, "Invalid Identifier", "Ticker not valid, please revise.")
        #    return
        #if country not in valid_country_codes:
        #    QMessageBox.warning(self, "Invalid Country Identifier", "Country Code not valid, please revise.")
        #    return
        
        popup = BackTestResults(f"Hello! Here are the backtest results for {ticker}.", self)
        popup.exec_()

    def select_portfolio_folder(self):
        """Open a folder selection dialog and update label."""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select File",
                "",  # Start directory ("" means OS default)
                "Csv Files (*.csv)"
            )
    
            if file_path:  # If user selected a folder
                self.portfolio_input.setText(file_path)
                self.portfolio_path = file_path
            else:
                self.portfolio_input.setText("No portfolio selected")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred:\n{str(e)}")

    def update_label(self):
        self.start_date = self.dateedit1.date()
        self.end_date = self.dateedit2.date()
        if self.dateedit1.date() > self.dateedit2.date():
            self.check_dates_label.setText("Warning: start date must be before end date.")
            self.check_dates_label.setStyleSheet("color: red;")
        else:
            formatted_start_date = self.dateedit1.date().toString("yyyy-dd-MM")
            formatted_end_date = self.dateedit2.date().toString("yyyy-dd-MM")
            self.check_dates_label.setText(f"Selected Date Range: {formatted_start_date} to {formatted_end_date}")
            self.check_dates_label.setStyleSheet("color: black;")
        
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
