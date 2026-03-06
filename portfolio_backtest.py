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
    
# TESTING PARAMS
start_dt = dt.date(2025,1,1)
end_dt = dt.date(2025,4,30)
config = pd.read_csv(r"C:\Users\sxiao\backtester\portfolio_config\put call parity.csv")
underlying_ticker = "XIU"
country_code = "CN"


class Portfolio():
    """ 
    Every backtest is initiated by a starting portfolio. 
    The Portfolio class is for reading and parsing the configuration csv + all inputs from the user interface.
    Input: Config Dataframe csv + User Interface Inputs
    Output: Initialized Day 0 portfolio dataframe ready for backtesting
    """
    def __init__(self, config:pd.DataFrame, underlying_ticker:str, country_code:str, start_dt:dt.date(), end_dt:dt.date()):
        
        self.db = common.db_connection()
        
        port = config.set_index(config.columns[0], inplace=True)
        ul_ticker = underlying_ticker+" "+country_code
        cur = port.loc['cash', 'CUR']
        starting_cash = config['cash', 'ALLOC']
        
        if country_code == "CN":
            while start_dt in common.tsx_holidays():
                start_dt = common.workday(start_dt, 1)
        elif country_code == "US":
            while start_dt in common.nyse_holidays():
                start_dt = common.workday(start_dt, 1)
        
        self.underlying = ULAsset(ul_ticker, cur)
        self.cash = Cash(starting_cash, cur)
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.currency = cur
        self.options = []
        
        initialized = port.copy()
        initialized['DATE'] = self.start_dt
        initialized.loc['underlying', 'TICKER'] = ul_ticker+" Equity"
        
        if country_code == "CN" or cur == "CAD":
            initialized.loc['cash', 'SEC_NAME'] = "CAD"

        elif country_code == "US" or cur == "USD":
            pass
        
        if self.start_dt.toPyDate().weekday() == 4: #Friday
            pass
        else:
            days_til_fri = 4 - self.start_dt.toPyDate().weekday()
            next_fri = common.workday(self.start_dt, days_til_fri)
        
        for index, row in port.iterrows():
            if index != 'cash' and index != 'underlying':
                option = Option_Chain(index, row['SEC_TYPE'].split(" ")[0], ul_ticker, row['ALLOC'], row['DTM'], row['MONEYNESS'], row['CUR'])
                self.options.append(option)
                # first option of the option chain: nearest friday
                selected_option = option.select_option(next_fri)
                initialized.loc[index, 'SEC_NAME'] = selected_option[0]
                initialized.loc[index, 'TICKER'] = selected_option[0]
                initialized.loc[index, 'PRICE'] = selected_option[1]
                
        self.initial_positions()
        
        print(initialized)
        self.portfolio = initialized
        
        # MAIN BACKTEST LOOP
        
        while date < self.end_dt:
            return
        
    
    def initial_option_positions(self, cash_available):
        """
        Iterative algorithm that determines the optimized position for all options and the 
        """
        cash = self.cash.position
        for option in self.options:
            if option.coverage < 0: # sell options
                pass
            else: #buy optionss
                pass
            


    def overnight_rates(self, date:dt.date):
        if self.currency == "CAD":
            rates_df = pd.read_csv(r"C:\Users\sxiao\backtester\interest rates\canrates.csv")
        elif self.currency == "USD":
            rates_df = pd.read_csv(r"C:\Users\sxiao\backtester\interest rates\usrates.csv")
        rates_df['date'] = pd.to_datetime(rates_df['date'])
        rates = rates_df[(rates_df['date'] <= self.end_dt) | (rates_df['date'] >= self.start_dt)]
        return rates
    
    def daily_market_value_calc(self, today:dt.date()):
        return
    
    def run_backtest(self):
        return
    
    def visualize_backtest(self):
        return

class Option_Chain():
    def __init__(self, sec_id:str, put_call:str, underly:str, covg:float, DTM:int, moneyness:float, cur:str="CAD"):        
        self.id = sec_id
        self.put_call = put_call
        self.ticker = underly
        self.currency = cur
        self.coverage = covg
        self.dtm = DTM
        self.moneyness = moneyness
    
    def select_option(self, roll_date:dt.date):
        self.maturity = roll_date
        selected_option = None

        option_univ = self.download_options(self.ticker, roll_date, roll_date)
        for opt in option_univ:
            selected_option = None
  
        

    def is_maturity_date(self, today:dt.date:
        if today == self.mat_date:
            return True
        else:
            return False
    
    def roll_option(self, today:dt.date:
        return
        

    
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
