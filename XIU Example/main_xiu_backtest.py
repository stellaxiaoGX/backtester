import pandas as pd
import numpy as np
import datetime as dt
from pandas.tseries.offsets import BDay
from xiu_data_pull import fetch_data
from portfolio_backtest import Cash, Option, Stock, Portfolio
import sys
sys.path.append('Z:\\ApolloGX')
if "\\im_dev\\" in cur_dir:
    import im_dev.std_lib.common as common
else:
    import im_prod.std_lib.common as common



def maturity(portfolio, date):
    return True


def ex(portfolio, date):
    return True



def get_div_data(equity_list=list, min_date:dt.datetime=dt.datetime.now(), max_date:dt.datetime=None):
    if equity_list == []:
        return pd.DataFrame(columns=['ticker', 'ex_date', 'payable_date', 'dvd_amount', 'currency'])
    else:
        conn = common.db_connection()
        if max_date is None:
            str_sql = f"SELECT ticker, ex_date, payable_date, dvd_amount, currency FROM dividends WHERE ex_date >= '{min_date.strftime('%Y-%m-%d')}' and ticker IN {conn.list_to_sql_str(equity_list, convert_elements=True)};"
        else:
            str_sql = f"SELECT ticker, ex_date, payable_date, dvd_amount, currency FROM dividends WHERE ex_date >= '{min_date.strftime('%Y-%m-%d')}' and ex_date <= '{max_date.strftime('%Y-%m-%d')}' and ticker IN {conn.list_to_sql_str(equity_list, convert_elements=True)};"
        return conn.query_tbl(str_sql)




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