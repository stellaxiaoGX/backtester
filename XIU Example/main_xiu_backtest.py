import pandas as pd
import numpy as np
import datetime as dt
from pandas.tseries.offsets import BDay
from xiu_data_pull import fetch_data

start = dt.today() - BDay(60)
end = dt.today() - BDay(1)

# initialize portfolio
ticker = "XIU"
cash = 1000000
holdings = []
positions = []

# option data pull
options_universe = fetch_data("XIU", start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'), "call", 0.05)

# read and parse portfolio input into dataframe
portfolio = pd.read_csv(r"C:\Users\sxiao\backtester\XIU Example\XIU put call parity.csv")






date = start
while date <= end:
    if date == start:
        
        return
    if date == end:
        return
    else:
        if maturity:
            return
        elif ex:
            return