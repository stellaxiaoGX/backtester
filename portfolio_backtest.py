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
    

config = pd.read_csv(r"C:\Users\sxiao\backtester\portfolio_config\put call parity.csv")

class Portfolio():
    """ 
    Every backtest is initiated by a starting portfolio. 
    The Portfolio class is for reading and parsing the configuration csv + all inputs from the user interface.
    Input: Config Dataframe csv + User Interface Inputs
    Output: Initialized Day 0 portfolio dataframe ready for backtesting
    """
    def __init__(self, config:pd.DataFrame, underlying_ticker:str, country_code:str, start_dt:dt.date(), end_dt:dt.date()):
        
        self.db = common.db_connectio()
        
        port = config.set_index(config.columns[0], inplace=True)
        ul_ticker = underlying_ticker+" "+country_code+" Equity"
        cur = port.loc['cash', 'CUR']
        starting = config['cash', 'ALLOC']
        while start_dt in common.tsx_holidays():
            start_dt = common.workday(start_dt, 1)
        
        self.underlying = ULAsset(ul_ticker, cur)
        self.cash = Cash(starting, cur)
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.currency = cur
        initialized = port.copy()
        initialized['DATE'] = self.start_dt
        initialized.loc['underlying', 'TICKER'] = ul_ticker
        initialized.loc['cash', 'SEC NAME'] = "CAD"
        initialized['RATE'] = 0.0225
        
        self.portfolio = initialized
        
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

