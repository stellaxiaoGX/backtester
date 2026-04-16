import pandas as pd
import numpy as np
import datetime as dt
import yfinance as yf
import matplotlib
import allocate_port
import os
cur_dir = os.path.dirname(__file__)
import sys
sys.path.append('Z:\\ApolloGX')
if "\\im_dev\\" in cur_dir:
    import im_dev.std_lib.common as common
else:
    import im_prod.std_lib.common as common


"""
Chain backtesting file Methodology:
    1. take portfolio allocation class from allocate_port.py and backtest each strategy inside while keeping portfolio structure
    2. uses the existing closest friday engine to roll and deal with holidays
"""
# Global function defined in allocate_port as well
def download_rates(self, ticker: str, country_code:str, start_dt: str, end_dt: str):
        """ Fetches historical interest rates given time frame and country. """
        if country_code.lower() == "cn":
            rates_file_path = os.path.join(cur_dir, "interest rates", "canrates.csv")
        else:
            rates_file_path = os.path.join(cur_dir, "interest rates", "usrates.csv")
        try:
            # Load the rates CSV file
            df = pd.read_csv(rates_file_path)
            df['date'] = pd.to_datetime(df['date']).dt.date
            
            # Filter by desired time frame
            start_dt_obj = pd.to_datetime(start_dt).date()
            end_dt_obj = pd.to_datetime(end_dt).date()
            
            filtered_rates = df[(df['date'] >= start_dt_obj) & (df['date'] <= end_dt_obj)]
            
            if filtered_rates.empty:
                print(f"No rates found for {country_code} in the given date range.")
                return pd.DataFrame()
            
            self.rates_series = filtered_rates.reset_index(drop=True)
            return self.rates_series
        
        except Exception as e:
            print(f"Error fetching rates: {e}")
            return pd.DataFrame()

def date_engine():
    """
    Legacy date engine to determine the next roll date friday using a +6 system
    """

    return

def run_backtest(port: allocate_port.Portfolio, start_dt, end_dt):
    """
    Reminder that after allocate_port.py, the Portfolio Object Class will have:
        - self.strategies (filled with allocated positions)
        - self.start_dt & self.end_dt adjusted for holidays already
        - self.ticker & self.country_code for identification 
        - self.holidays dictionary
        - self.
        - 
    """

    underlying = port.ticker
    country_code = port.country_code
    portfolio_allocation = port.strategies
        
    
    # MAIN ENGINE: stops at every expiry and 



    return