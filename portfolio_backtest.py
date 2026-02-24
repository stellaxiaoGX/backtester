import datetime as dt
import pandas as pd
from pandas.tseries.offsets import BDay



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
        
    def option_buy_back(self):
        return
    

class ULAsset():
    def __init__(self, ticker:str, cur:str="CAD"):
        self.ticker = ticker
        self.currency = cur
        
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


class Portfolio():
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


start = dt.today() - BDay(90)
end = dt.today() - BDay(1)

