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
    


class Portfolio():
    """ 
    Every backtest is initiated by a starting portfolio.
    The Portfolio class is for reading and parsing the configuration csv + all inputs from the user interface.
    Input: Config Dataframe csv + User Interface Inputs
    Output: Initialized Day 0 portfolio dataframe ready for backtesting
    """
    def __init__(self, config:pd.DataFrame, underlying_ticker:str, country_code:str, start_dt:dt.date, end_dt:dt.date):
        config.set_index(config.columns[0], inplace=True)
        ul_ticker = underlying_ticker
        cur = config.loc['cash', 'CUR']
        starting_cash = config.loc['cash', 'ALLOC']
        
        if country_code == "US":
            holidays = common.nyse_holidays()
            self.holidays = pd.to_datetime(list(holidays.keys()), format='ISO8601').date
            while start_dt in self.holidays:
                start_dt = common.workday(start_dt, 1, holidays)
            while end_dt in self.holidays:
                end_dt = common.workday(end_dt, -1, holidays)
        else:
            holidays = common.tsx_holidays()
            self.holidays = pd.to_datetime(list(holidays.keys()), format='ISO8601').date
            while start_dt in self.holidays:
                start_dt = common.workday(start_dt, 1)
            while end_dt in self.holidays:
                end_dt = common.workday(end_dt, -1)
        
        self.cash = starting_cash
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.currency = cur
        self.underlying = ULAsset(ul_ticker+" "+country_code, start_dt, end_dt, cur)
        self.country_code = country_code
        self.rates = self.overnight_rates()
        self.options = []
        
        initialized = config.copy()
        initialized['DATE'] = self.start_dt
        initialized.loc['underlying', 'TICKER'] = ul_ticker+" "+country_code+" Equity"
        initialized.loc['cash', 'SEC_NAME'] = self.currency
        
        # NEED TO ACCOUNT FOR FRIDAY HOLIDAY
        if self.start_dt.weekday() == 4: #Friday
            next_fri = common.workday(self.start_dt, 5)
        else:
            days_til_fri = 4 - self.start_dt.weekday()
            next_fri = common.workday(self.start_dt, days_til_fri)
        
        # Iterate options and initialize each option chain
        # Select the first option of the chain
        for index, row in config.iterrows():
            if index != 'cash' and index != 'underlying':
                option = Option_Chain(index, row['SEC_TYPE'].split(" ")[0].lower(), underlying_ticker, row['ALLOC'], row['DTM'], row['MONEYNESS'], row['CUR'])
                # first option of the option chain: nearest friday
                selected_option = option.select_option(self.start_dt, next_fri)
                initialized.loc[index, 'SEC_NAME'] = selected_option[0]
                initialized.loc[index, 'TICKER'] = selected_option[0]
                initialized.loc[index, 'PRICE'] = option.option_mid
                initialized.loc['underlying', 'PRICE'] = selected_option[1]
                self.options.append(option)
        
        initialized.loc['cash', 'PRICE'] = 1
        initialized.loc['cash', 'TICKER'] = self.currency
        initialized.loc['underlying', 'SEC_NAME'] = ul_ticker
        initialized = initialized.drop(["DTM", "MONEYNESS", "ALLOC"], axis='columns')
        self.init_portfolio = initialized

        # DAY 0 TRADES + QTY & MV Columns + SUMMARY ROW
        day0_alloc = self.initial_positions()
        if day0_alloc['status'] == "Optimization failed":
            shares = round(self.cash*0.9/initialized.loc['underlying', 'PRICE'], -2)
        else:
            shares = round(day0_alloc['allocations'][0], -2)
        self.shares = shares
        
        initialized['QTY'] = None
        initialized['MV'] = None
        
        initialized.loc['underlying', 'QTY'] = shares
        ul_price = initialized.loc['underlying', 'PRICE']
        self.cash -= shares*ul_price
        for option in self.options:
            option_qty = round(option.coverage*shares, -2)
            initialized.loc[option.id, 'QTY'] = option_qty
            self.cash -= option_qty*option.option_mid
        
        initialized.loc['cash', 'QTY'] = self.cash
        initialized['MV'] = initialized['QTY']*initialized['PRICE']
        
        initialized.loc['summary'] = {'SEC_TYPE': 'total portfolio', 
                                      'CUR': self.currency,
                                      'DATE': self.start_dt,
                                      'MV': initialized['MV'].sum()}
        self.portfolio = initialized
        self.backtest()
        
        
    def backtest(self):
        trade_log = self.portfolio
        
        # MAIN BACKTEST LOOP: Start at Day 1
        iter_date = common.workday(self.start_dt, 1)
        while iter_date < self.end_dt:
            self.portfolio['DATE'] = iter_date
            # Fetch data for the iterated date and update portfolio
            self.portfolio.loc['underlying', 'PRICE'] = self.underlying.prices[iter_date]
            # CHECKS:
            # Dividend Pay check: Reinvested in underlying security
            
            # Options expiring check: Roll option if true
            # Account for in the money and out the money changes
                
            for option in self.options:
                if option.is_maturity_date(iter_date):
                    if option.itm():
                        pass
                    else:
                        pass
                    
                    # SELL (-1) CALL (0)
                    
                    # BUY (1) CALL (0)
                    
                    # SELL (-1) PUT (1)
                    
                    # BUY (1) PUT (1)
                    next_roll_date = common.workday(iter_date, option.map_maturity(option.dtm))
                    while next_roll_date in self.holidays:
                        next_roll_date = common.workday(next_roll_date, -1)
                    roll_option = option.roll_option(iter_date, next_roll_date)
                    self.portfolio.loc[option.id, 'SEC_NAME'] = roll_option[0]
                    self.portfolio.loc[option.id, 'TICKER'] = roll_option[0]
                    self.portfolio.loc[option.id, 'PRICE'] = option.option_mid
                    self.portfolio.loc['underlying', 'PRICE'] = roll_option[1]
                    option_qty = round(option.coverage*self.shares, -2)
                    self.portfolio.loc[option.id, 'QTY'] = option_qty
                    self.cash -= option_qty*option.option_mid
                    
                else:
                    continue
            # Ex Date Check
            if self.ex_date(iter_date):
                pass
            
            # Calculate EOD MV and append new table.
            self.portfolio.loc['summary']
            
            trade_log = pd.concat([trade_log, self.portfolio], axis=0)            
            # Move to next business day
            iter_date = common.workday(iter_date, 1)
        
    
    def initial_positions(self, liquid_buffer:float=0.05):
        """
        Linear Program to find optimized initial starting positions for all share and option allocations 
        """
        cash = self.cash
        df = self.init_portfolio
        ul_price = df.loc['underlying', 'PRICE']
        spending_per_share = ul_price
        for option in self.options:
            spending_per_share -= option.coverage*option.option_mid
                
        # Example: Allocate cash to maximize shares bought while meeting liquidity buffer limit
        # Maximize: X (shares)
        # Subject to:
        #   (price_per_share + 50%*call_price - 50%*put_price)X <= 950000
        #   X >= 0
        
        c = [1]
        c = np.array(c, dtype=float)
        A_ub = [[(spending_per_share)]] # Spending equation for every share, need to include every option in the portfolio
        b_ub = [cash*(1-liquid_buffer)]
        bounds = [(0, None)]

        # linprog minimizes, so we negate c to maximize
        result = linprog(-c, A_ub=A_ub, b_ub=b_ub, A_eq=None, b_eq=None, bounds=bounds, method='highs')
        
        print(result)
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

    def overnight_rates(self):
        if self.currency == "CAD":
            rates_df = pd.read_csv(r"C:\Users\sxiao\backtester\interest rates\canrates.csv")
        elif self.currency == "USD":
            rates_df = pd.read_csv(r"C:\Users\sxiao\backtester\interest rates\usrates.csv")
        rates_df['date'] = pd.to_datetime(rates_df['date'], format='ISO8601').dt.date
        rates = rates_df[(rates_df['date'] <= self.end_dt) & (rates_df['date'] >= self.start_dt)]
        return rates

class covered_call():
    def __init__(self, sec_id):
        self.id = sec_id
        
        
        
        
class naked_put():
    def __init__(self, sec_id):
        self.id = sec_id



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
        self.option_mid = None
    
    def select_option(self, roll_date:dt.date, exp_date:dt.date):
        selected_option = None
        strike = None
        maturity = None
        bid = None
        ask = None
        last = None
        
        option_univ = self.download_options(self.ticker, roll_date, roll_date)
        ul_row = option_univ.loc[option_univ['Symbol'] == self.ticker]
        ul_price= ul_row.loc[0, 'Last Price']
        
        option_univ = option_univ[option_univ['Expiry Date'] == exp_date.strftime("%Y-%m-%d")]
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
        self.option_mid = (bid + ask)/2
        return [selected_option, ul_price]
    

    def is_maturity_date(self, date:dt.date):
        if date == self.maturity:
            return True
        else:
            return False
    
    def roll_option(self, roll_date:dt.date, exp_date:dt.date):
        selected_option = self.select_option(roll_date, exp_date)
        return selected_option
    
    def map_maturity(self, dtm:str):
        dtm_map = {'W': 5,
                   'M': 20,
                   'Q': 60,
                   'S': 120,
                   'Y': 240}
        return dtm_map[dtm]
    
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

class ULAsset():
    def __init__(self, ticker:str, start_dt:dt.date, end_dt:dt.date, cur:str="CAD"):
        self.ticker = ticker
        self.currency = cur
        self.ex_dates = self.ex_dates(start_dt, end_dt)
        self.price_data = self.prices(start_dt, end_dt)
        self.div_dates = self.divid_dates(start_dt, end_dt)
        
        
    def is_ex_date(self, today:dt.date):
        return False
        
    def prices(self, start_dt:dt.date, end_d:dt.date):
        pass
        
    def ex_dates(self, start_dt:dt.date, end_dt:dt.date):
        return
    
    def divid_dates(self, start_dt:dt.date, end_dt:dt.date):
        pass


    
    
# EXAMPLE PARAMS - PUT CALL PARITY FOR XIU
start_dt = dt.date(2025,1,1)
end_dt = dt.date(2025,4,30)
config = pd.read_csv(r"C:\Users\sxiao\backtester\portfolio_config\put call parity.csv")
underlying_ticker = "XIU"
country_code = "CN"

test = Portfolio(config, underlying_ticker, country_code, start_dt, end_dt)
    