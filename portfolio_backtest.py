import datetime as dt
import pandas as pd
import os
cur_dir = os.path.dirname(__file__)
import sys
sys.path.append('Z:\\ApolloGX')
if "\\im_dev\\" in cur_dir:
    import im_dev.std_lib.common as common
else:
    import im_prod.std_lib.common as common
    


class Portfolio():
    """ Every backtest is initiated with a portfolio. Reads and parses the configuration csv + inputs from the interface """
    
    def __init__(self, underlying_ticker:str, starting_pos:int, start_dt:dt.date(), end_dt:dt.date(), cur:str="CAD", liquid_threshold:float=0.05):
        self.underlying = ULAsset(underlying_ticker, cur)
        self.cash = Cash(starting_pos, cur)
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.currency = cur
        self.liquidity = liquid_threshold # liquidity of starting cash not allocated
        return
        
    def daily_market_value_calc(self, today:dt.date()):
        return
    
    def run_backtest(self):    
        return
    
    def visualize_backtest(self):
        return

class Option():
    def __init__(self, p_c:str, underly:str, mat_date:dt.date(), strike:float, pos:int, covg:float, DTM:int, moneyness:float, cur:str="CAD"):
        self.ticker = underly
        self.put_call = p_c
        self.maturity = mat_date
        self.strike = strike
        self.position = pos
        self.currency = cur
        self.coverage = covg
        self.dtm = DTM
        self.moneyness = moneyness
    
    def is_maturity_date(self, today:dt.date()):
        if today == self.mat_date:
            return True
        else:
            return False
    
    def roll_option(self, today:dt.date()):
        return
        
    def select_option(self, today:dt.date()):
        selected_option = None

        option_univ = self.download_options(self.ticker, today, today)
        for opt in option_univ:
            selected_option = None

        
        return selected_option
    
    def download_options(self, ticker: str, start_date:str, end_date:str):

        download_html = f"https://www.m-x.ca/en/trading/data/historical?symbol={ticker.lower()}&from={start_date}&to={end_date}&dnld=1#quotes"
        current_att = 0
        while current_att < 8:
            try:
                df_download = common.download_from_url(download_html)
                print(f"Downloaded data for {ticker} from {start_date} to {end_date}")
                return df_download
            except:
                print(f"Failed to download data for {ticker} from {start_date} to {end_date}")
                return pd.DataFrame()

    
    def option_buy_back(self):
        return
    

class ULAsset():
    def __init__(self, ticker:str, cur:str="CAD"):
        self.ticker = ticker
        self.currency = cur
        
    def fetch_ex_dates(self):
        return
    
    
    def is_ex_date(self, today:dt.date()):
        return False
    
    def next_ex_date(self, today:dt.date()):
        next_ex = dt.date(2026, 2, 27)
        return next_ex
    

class Cash():
    def __init__(self, pos, cur:str="CAD"):
        self.position = pos
        self.currency = cur
        self.overnight_rate = 0.025





today = dt.datetime.now()

start = common.workday(today, -90)
end = common.workday(today, -1)

