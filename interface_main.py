import datetime as dt
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QFont

import os
cur_dir = os.path.dirname(__file__)
import sys
sys.path.append('Z:\\ApolloGX')
if "\\im_dev\\" in cur_dir:
    import im_dev.std_lib.common as common
else:
    import im_prod.std_lib.common as common

import allocate_port
import confirmation_popup
    
    
# Backtest Popup after running on all inputs
class BackTestResults(QDialog):
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Backtest Results Window")
        self.setFixedSize(900, 700)

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
        
        # Validated input lists
        self.valid_list = ["XIU"]
        self.valid_country_codes = ["CN", "US"]

        # Final Bottom Button to trigger Backtesting Screen Popup
        self.button = QPushButton("Run Backtest", self)
        self.button.clicked.connect(self.popup_show_preview)
        self.button.resize(120, 40)
        self.button.move(140, 245)
        
        # Date Range Selection
        self.dateedit1 = QDateEdit(self, calendarPopup=True)
        self.dateedit1.setDateTime(common.workday(dt.datetime.today(), -40))
        self.dateedit1.setMaximumDate(common.workday(dt.datetime.today(), -1))
        self.dateedit1.dateChanged.connect(self.update_label)
        self.dateedit1.move(80, 10)
        
        self.dateedit2 = QDateEdit(self, calendarPopup=True)
        self.dateedit2.setDateTime(QtCore.QDateTime.currentDateTime())
        self.dateedit2.setMaximumDate(common.workday(dt.datetime.today(), -1))
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
        self.portfolio_path = 0
        
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
    
    def popup_show_preview(self):

        ticker = self.input_box.text()
        country = self.region_input_box.text()
        # Warnings:
        if self.start_date > self.end_date:
            QMessageBox.warning(self, "Invalid Date Range", "Start Date must be before End Date.")
            return
        if not os.path.isfile(self.portfolio_path):
            QMessageBox.warning(self, "Invalid Portfolio Path", "Invalid portfolio configuration file path.")
            return
        if ticker not in self.valid_list:
            QMessageBox.warning(self, "Invalid Identifier", "Ticker not valid.")
            return
        if country not in self.valid_country_codes:
            QMessageBox.warning(self, "Invalid Country Identifier", "Country Code not valid.")
            return
                
        # Create the portfolio
        start_dt = self.start_date.toPyDate()
        end_dt = self.end_date.toPyDate()
        try:
            portfolio = allocate_port.Portfolio(self.portfolio_path, ticker, country, start_dt, end_dt, base_cash=1000000)
        except Exception as e:
            QMessageBox.critical(self, "Portfolio Creation Error", f"Failed to create portfolio:\n{str(e)}")
            return
        
        # Show confirmation dialog
        if confirmation_popup.ConfirmationDialog.confirm_portfolio(portfolio, ticker):
            # Proceed with backtest
            QMessageBox.information(self, "Backtest Started", "Portfolio confirmed. Proceeding with backtest...")
            # TODO: Implement actual backtest logic here
        else:
            QMessageBox.information(self, "Backtest Cancelled", "Portfolio not confirmed. Backtest cancelled.")

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
        self.dateedit1.setMaximumDate(common.workday(self.dateedit2.date().toPyDate(), -1))
        
        self.start_date = self.dateedit1.date()
        self.end_date = self.dateedit2.date()
        if common.workday(self.dateedit1.date().toPyDate(), 20) > self.dateedit2.date():
            self.check_dates_label.setText("Please choose a longer backtest period for best results.")
            self.check_dates_label.setStyleSheet("color: red;")
        else:
            formatted_start_date = self.dateedit1.date().toString("yyyy-MM-dd")
            formatted_end_date = self.dateedit2.date().toString("yyyy-MM-dd")
            self.check_dates_label.setText(f"Selected Date Range: {formatted_start_date} to {formatted_end_date}")
            self.check_dates_label.setStyleSheet("color: black;")
        
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
