import pandas as pd
import numpy as np
import datetime as dt
from pandas.tseries.offsets import BDay
from xiu_data_pull import fetch_data
from portfolio_backtest import Cash, Option, Stock, Portfolio

def maturity(portfolio, date):
    return True


def ex(portfolio, date):
    return True


# Date Range Input
start = dt.datetime.today() - BDay(60)
end = dt.datetime.today() - BDay(1)

# Ticker input
ticker = "XIU"

# option universe data pull
call_universe = fetch_data(ticker, (start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')), "call", 0.01)
put_universe = fetch_data(ticker, (start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')), "put", 0.01)

# read and parse portfolio input into dataframe
port = pd.read_csv(r"C:\Users\sxiao\backtester\XIU Example\XIU put call parity.csv")
port.set_index(port.columns[0], inplace=True)

starting = port.loc["cash", 'ALLOC']
mv = starting
holdings = []

for row in port.iterrows():
    if row['SEC_ID'] == 'cash':
        asset = Cash(row['ALLOC'], row['CUR'])
        
    if row['SEC_ID'] == 'underlying':
        asset = Stock(ticker, row['CUR'])

    holdings.append(asset)

holdings = [ticker, "put", "call", "cash"]
positions = [0, 0, 0, 0]




date = start
while date <= end:
    if date == start:
        positions[0] = starting
        print(date.strftime('%Y-%m-%d')+f": allocated ${starting} to {ticker}.")
    else:
        print(date.strftime('%Y-%m-%d'))
    if maturity:
    #    continue
    elif ex:
    #    continue
    portfolio_calc(portfolio)
    date = date + BDay(1)