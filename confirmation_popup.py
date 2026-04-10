import sys
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QPushButton, QHeaderView
from PyQt5.QtCore import Qt
import datetime as dt

class ConfirmationDialog(QDialog):
    def __init__(self, portfolio, underlying_ticker=None, parent=None):
        super().__init__(parent)
        self.portfolio = portfolio
        self.underlying_ticker = underlying_ticker
        self.setWindowTitle("Portfolio Confirmation")
        self.setModal(True)
        self.resize(1500, 900)

        # Layout
        layout = QVBoxLayout()

        # Title
        title_label = QLabel("Portfolio Allocation Confirmation ($1,000,000)")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)

        # Table for portfolio details
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels(["Strategy", "Leg Type", "Direction", "Ticker", "Quantity", "Strike", "Option Type", "Unit Price", "Cash Flow", "Expiry", "Notional"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("alternate-background-color: #f0f0f0;")
        layout.addWidget(self.table)

        # Populate table
        self.populate_table()

        # Summary labels
        summary_layout = QVBoxLayout()
        net_cash_label = QLabel(f"Net Cash Flow on Allocation: ${-1*self.portfolio.net_cash_spend:.2f}")
        net_cash_label.setStyleSheet("font-weight: bold; color: blue;")
        summary_layout.addWidget(net_cash_label)
        
        collateral_label = QLabel(f"Total Collateral Held: ${self.portfolio.bond_cash:.2f}")
        collateral_label.setStyleSheet("font-weight: bold; color: green;")
        summary_layout.addWidget(collateral_label)
        
        residual_label = QLabel(f"Residual Cash in Money Market: ${self.portfolio.residual_cash:.2f}")
        residual_label.setStyleSheet("font-weight: bold; color: purple;")
        summary_layout.addWidget(residual_label)
        
        layout.addLayout(summary_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.yes_button = QPushButton("Proceed with Backtest")
        self.yes_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 10px; font-size: 14px; }")
        self.yes_button.clicked.connect(self.accept)
        self.no_button = QPushButton("Cancel")
        self.no_button.setStyleSheet("QPushButton { background-color: #f44336; color: white; padding: 10px; font-size: 14px; }")
        self.no_button.clicked.connect(self.reject)
        button_layout.addWidget(self.yes_button)
        button_layout.addWidget(self.no_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def populate_table(self):
        row = 0
        for strategy in self.portfolio.strategies:
            if hasattr(strategy, 'legs') and strategy.legs:
                for leg in strategy.legs:
                    self.table.insertRow(row)
                    
                    # Strategy name
                    strategy_item = QTableWidgetItem(strategy.name)
                    strategy_item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, 0, strategy_item)
                    
                    # Leg type
                    if hasattr(leg, 'asset'):
                        leg_type = leg.asset.title()
                    else:
                        leg_type = "Unknown"
                    leg_type_item = QTableWidgetItem(leg_type)
                    leg_type_item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, 1, leg_type_item)
                    
                    # Direction
                    if hasattr(leg, 'direction') and leg.direction is not None:
                        direction = "Long" if leg.direction == 1 else "Short"
                    else:
                        direction = "N/A"
                    direction_item = QTableWidgetItem(direction)
                    direction_item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, 2, direction_item)
                    
                    # Ticker (Full Option Ticker or Equity Ticker)
                    ticker_display = "N/A"
                    if hasattr(leg, 'option_type') and leg.option_type:
                        # Build full option ticker: UNDERLYING EXPIRY STRIKE CALLPUT
                        underlying = self.underlying_ticker if self.underlying_ticker else 'N/A'
                        if hasattr(leg, 'expiry') and leg.expiry:
                            expiry_str = leg.expiry.strftime("%d%b%y").upper() if isinstance(leg.expiry, (dt.date, dt.datetime)) else str(leg.expiry)
                        else:
                            expiry_str = "N/A"
                        strike_str = f"{leg.strike:.2f}" if (hasattr(leg, 'strike') and leg.strike) else "N/A"
                        call_put_str = "C" if (hasattr(leg, 'option_type') and leg.option_type.lower() == 'c') else "P"
                        ticker_display = f"{underlying} {expiry_str} {strike_str}{call_put_str}"
                    elif hasattr(leg, 'asset') and leg.asset.lower() == 'equity' and hasattr(leg, 'ticker'):
                        # Show equity ticker in Bloomberg format
                        country = leg.country if hasattr(leg, 'country') else 'N/A'
                        ticker_display = f"{leg.ticker} {country} Equity"
                    ticker_item = QTableWidgetItem(ticker_display)
                    ticker_item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, 3, ticker_item)
                    
                    # Quantity
                    if hasattr(leg, 'cash') and leg.cash:
                        quantity = f"${leg.cash:.2f}"
                    elif hasattr(strategy, 'contracts') and strategy.contracts:
                        quantity = f"{strategy.contracts}"
                    elif hasattr(strategy, 'shares') and strategy.shares:
                        quantity = f"{strategy.shares}"
                    else:
                        quantity = "N/A"
                    quantity_item = QTableWidgetItem(quantity)
                    quantity_item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, 4, quantity_item)
                    
                    # Strike
                    if hasattr(leg, 'strike') and leg.strike:
                        strike = f"${leg.strike:.2f}"
                    else:
                        strike = "N/A"
                    strike_item = QTableWidgetItem(strike)
                    strike_item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, 5, strike_item)
                    
                    # Option Type (Call or Put)
                    option_type_display = "N/A"
                    if hasattr(leg, 'option_type') and leg.option_type:
                        option_type_display = "Call" if leg.option_type.lower() == 'c' else "Put"
                    option_type_item = QTableWidgetItem(option_type_display)
                    option_type_item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, 6, option_type_item)
                    
                    # Unit Price (premium for options, price for equity)
                    unit_price = "N/A"
                    if hasattr(leg, 'option_type') and leg.option_type:
                        # This is an option leg - use the option premium price
                        if hasattr(leg, 'price'):
                            unit_price = f"${leg.price:.2f}"
                    elif hasattr(leg, 'asset') and leg.asset.lower() == 'equity':
                        # This is an equity leg - use the underlying spot price
                        if hasattr(strategy, 'underlying_spot') and strategy.underlying_spot:
                            unit_price = f"${strategy.underlying_spot:.2f}"
                    elif hasattr(leg, 'price') and leg.price:
                        # Fallback for other leg types
                        unit_price = f"${leg.price:.2f}"
                    unit_price_item = QTableWidgetItem(unit_price)
                    unit_price_item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, 7, unit_price_item)
                    
                    # Cash Flow (combines premium for options and transaction for shares/bonds)
                    cash_flow = "N/A"
                    if hasattr(leg, 'price') and leg.price and hasattr(leg, 'option_type'):
                        # This is an option leg
                        if hasattr(strategy, 'contracts') and strategy.contracts:
                            premium_total = leg.price * strategy.contracts * 100  # 100 multiplier for options
                            if leg.direction == -1:
                                cash_flow = f"${premium_total:.2f} (Earned)"
                            else:
                                cash_flow = f"-${premium_total:.2f} (Paid)"
                    elif hasattr(leg, 'asset') and leg.asset.lower() == 'equity' and hasattr(strategy, 'shares') and strategy.shares:
                        if hasattr(strategy, 'underlying_spot') and strategy.underlying_spot:
                            transaction_amt = strategy.shares * strategy.underlying_spot
                            cash_flow = f"-${transaction_amt:.2f}" if leg.direction == 1 else f"${transaction_amt:.2f}"
                    elif hasattr(leg, 'cash') and leg.cash:
                        cash_flow = f"${leg.cash:.2f}"
                    cash_flow_item = QTableWidgetItem(cash_flow)
                    cash_flow_item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, 8, cash_flow_item)
                    
                    # Expiry
                    if hasattr(leg, 'expiry') and leg.expiry:
                        expiry = leg.expiry.strftime("%Y-%m-%d") if isinstance(leg.expiry, (dt.date, dt.datetime)) else str(leg.expiry)
                    else:
                        expiry = "N/A"
                    expiry_item = QTableWidgetItem(expiry)
                    expiry_item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, 9, expiry_item)
                    
                    # Notional
                    if hasattr(strategy, 'notional_value'):
                        notional = f"${strategy.notional_value():.2f}"
                    elif hasattr(leg, 'cash'):
                        notional = f"${leg.cash:.2f}"
                    else:
                        notional = "N/A"
                    notional_item = QTableWidgetItem(notional)
                    notional_item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, 10, notional_item)
                    
                    row += 1

    @staticmethod
    def confirm_portfolio(portfolio, underlying_ticker=None):
        """
        Static method to show the confirmation dialog.
        Returns True if user clicks Proceed, False otherwise.
        """
        dialog = ConfirmationDialog(portfolio, underlying_ticker)
        result = dialog.exec_()
        return result == QDialog.Accepted

if __name__ == "__main__":
    # Example usage - would need a real portfolio object
    print("Run interface_main.py to test the confirmation dialog")