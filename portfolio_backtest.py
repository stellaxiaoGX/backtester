import datetime as dt
import pandas as pd
import numpy as np
from scipy.optimize import linprog
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
        port = config.set_index(config.columns[0], inplace=True)
        ul_ticker = underlying_ticker+" "+country_code
        cur = port.loc['cash', 'CUR']
        starting_cash = config['cash', 'ALLOC']
        
        if country_code == "US":
            holidays = common.nyse_holidays()
            while start_dt in holidays:
                start_dt = common.workday(start_dt, 1, holidays)
            while end_dt in holidays:
                end_dt = common.workday(end_dt, -1, holidays)
        else:
            holidays = common.tsx_holidays()
            while start_dt in holidays:
                start_dt = common.workday(start_dt, 1)
            while end_dt in holidays:
                end_dt = common.workday(end_dt, -1)
        
        self.db = common.db_connection()
        self.underlying = ULAsset(ul_ticker, cur)
        self.cash = starting_cash
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.currency = cur
        self.country_code = country_code
        self.rates = self.overnight_rate()
        self.options = []
        
        initialized = port.copy()
        initialized['DATE'] = self.start_dt
        initialized.loc['underlying', 'TICKER'] = ul_ticker+" Equity"
        
        if self.country_code == "CN" or self.currency == "CAD":
            initialized.loc['cash', 'SEC_NAME'] = "CAD"

        elif country_code == "US" or cur == "USD":
            pass
        
        # NEED TO ACCOUNT FOR FRIDAY HOLIDAY
        if self.start_dt.toPyDate().weekday() == 4: #Friday
            next_fri = common.workday(self.start_dt, 5)
        else:
            days_til_fri = 4 - self.start_dt.toPyDate().weekday()
            next_fri = common.workday(self.start_dt, days_til_fri)
        
        # Iterate options and initialize each option chain
        # Select the first option of the chain
        for index, row in port.iterrows():
            if index != 'cash' and index != 'underlying':
                option = Option_Chain(index, row['SEC_TYPE'].split(" ")[0].lower(), underlying_ticker, row['ALLOC'], row['DTM'], row['MONEYNESS'], row['CUR'])
                # first option of the option chain: nearest friday
                selected_option = option.select_option(self.start_dt, next_fri)
                initialized.loc[index, 'SEC_NAME'] = selected_option[0]
                initialized.loc[index, 'TICKER'] = selected_option[0]
                initialized.loc[index, 'PRICE'] = selected_option[1]
                self.options.append(option)
        
        day_0_pos = self.initial_positions()


        self.portfolio = initialized
        
        
        
        
        
        # MAIN BACKTEST LOOP
        iter_date = self.start_dt

        while iter_date < self.end_dt:
            
            
            iter_date = common.workday(iter_date, 1, holidays)
        
    
    def initial_positions(self):
        """
        Linear Program to find optimized initial starting positions for all share and option allocations 
        """
        cash = self.cash
        ul_price = self.underlying.price(self.start_dt)
        liquid_buffer = 0.05
        
        # Example: Allocate cash to maximize shares bought while meeting liquidity buffer limit
        # Maximize: X (shares)
        # Subject to:
        #   (price_per_share + 50%*call_price - 50%*put_price)X <= 950000
        #   X >= 0
        c = [1]
        c = np.array(c, dtype=float)
        A_ub = [[(ul_price)]] # Spending equation for every share, need to include every option in the portfolio
        b_ub = [cash*(1-liquid_buffer)]
        bounds = [(0, None)]

        # linprog minimizes, so we negate c to maximize
        result = linprog(-c, A_ub=A_ub, b_ub=b_ub, A_eq=None, b_eq=None, bounds=bounds, method='highs')

        if result.success:
            return {
                "status": "Optimal solution found",
                "optimal_value": -result.fun,  # Negate back to get max value
                "allocations": result.x
            }
        else:
            return {
                "status": "Optimization failed",
                "message": result.message
            }
        
        print(result)


    def overnight_rates(self):
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
        self.put_call = 0 if put_call == 'call' else 1
        self.ticker = underly
        self.currency = cur
        self.coverage = covg
        self.buy_sell = 1 if covg > 0 else -1 # 1 for buy -1 for sell
        self.dtm = DTM
        self.moneyness = moneyness
        
        # Indiv Option Variables that change
        self.maturity = None
        self.cur_option = None
        self.strike = None
        self.option_bid = None
        self.option_ask = None
        self.option_last = None
    
    def select_option(self, roll_date:dt.date, exp_date:dt.date):
        selected_option = None
        strike = None
        maturity = None
        bid = None
        ask = None
        last = None
        
        option_univ = self.download_options(self.ticker, self.put_call, roll_date, roll_date)
        option_univ = option_univ[option_univ['Expiry Date'] == exp_date.strftime("%Y-%m-%d")]
        ul_price = option_univ.set_index(option_univ['Symbol'], inplace=True).iloc[self.ticker, 'Last Price']

        option_univ = option_univ[option_univ['Call/Put'] == self.put_call]
        
        if self.put_call == 0:
            target_strike = ul_price*(1+self.moneyness)
        else:
            target_strike = ul_price*(1-self.moneyness)
        
        closest_strike_index = (option_univ['Strike Price'] - target_strike).abs().idxmin()
        strike = option_univ.loc[closest_strike_index, 'Strike Price']
        selected_option = option_univ.loc[closest_strike_index, 'Symbol']
        maturity = option_univ.loc[closest_strike_index, 'Expiry Date']
        bid = option_univ.loc[closest_strike_index, 'Bid Price']
        ask = option_univ.loc[closest_strike_index, 'Ask Price']
        last = option_univ.loc[closest_strike_index, 'Last Price']
        
        self.maturity = maturity
        self.cur_option = selected_option
        self.strike = strike
        self.option_bid = bid
        self.option_ask = ask
        self.option_last = last
        return [selected_option, bid if self.buy_sell == -1 else ask]
    

    def is_maturity_date(self, date:dt.date):
        if date == self.maturity:
            return True
        else:
            return False
    
    def roll_option(self, date:dt.date):
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
    