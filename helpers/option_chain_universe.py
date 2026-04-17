import win32com.client as win32
import pandas as pd
import time

import datetime as dt
import numpy as np

from xbbg import blp
import os
cur_dir = os.path.dirname(__file__)
import sys
sys.path.append('Z:\\ApolloGX')
if "\\im_dev\\" in cur_dir:
    import im_dev.std_lib.common as common
    from im_dev.std_lib.bloomberg_session import *
else:
    import im_prod.std_lib.common as common
    from im_prod.std_lib.bloomberg_session import *


def ca_option_univ(ticker:str, start_date:dt.date, end_date:dt.date):
    """
    Will fail if start and end dates are too far apart, too much data
    """
    download_html = f"https://www.m-x.ca/en/trading/data/historical?symbol={ticker.lower()}&from={start_date}&to={end_date}&dnld=1#quotes"
    current_att = 0
    while current_att < 8:
        try:
            ca_option_univ = common.download_from_url(download_html)
            print(f"Downloaded option data for {ticker} from {start_date} to {end_date}")
            return ca_option_univ
        except:
            print(f"Failed to download data for {ticker} from {start_date} to {end_date}")
            return pd.DataFrame()
        
        
        
def chains_given_expiry(expiry_dt:dt.datetime, min_pct_strike:float, max_pct_strike:float, underlying_security:str, underlying_price:float, call_put_factor:float, strike_interval:float):
    output = []
    min_strike = myround(underlying_price * (1 + np.sign(call_put_factor)*min_pct_strike), strike_interval)
    max_strike = myround(underlying_price * (1 + np.sign(call_put_factor)*max_pct_strike), strike_interval)

    call_put_str = {1:' C', -1: ' P'}

    for cur_strike_100 in range(int(min_strike*100), int(max_strike*100), int(np.sign(call_put_factor)*strike_interval*100)):
        cur_strike = cur_strike_100/100
    # while cur_strike <= max_strike:
        _ticker = underlying_security + str(' ') + expiry_dt.strftime('%m/%d/%y') + call_put_str.get(int(call_put_factor)) + str(cur_strike).replace('.0', '') + str(' Equity')
        output.append(_ticker)
        cur_strike += strike_interval * call_put_factor
    return output

def gather_option_chains(rebal_date:dt.datetime, max_expiry:dt.datetime, min_pct_strike:float, max_pct_strike:float, underlying_security:str, underlying_price:float, call_put_factor:float, strike_interval:float, expiry_dt:dt.datetime=None):
    ticker_list = []
    _d = rebal_date
    if not expiry_dt is None:
        chain_per_expiry_dt = chains_given_expiry(expiry_dt, min_pct_strike, max_pct_strike, underlying_security, underlying_price, call_put_factor, strike_interval)
        ticker_list += chain_per_expiry_dt
    else:
        while _d <= max_expiry:
            chain_per_expiry_dt = chains_given_expiry(_d, min_pct_strike, max_pct_strike, underlying_security, underlying_price, call_put_factor, strike_interval)
            ticker_list += chain_per_expiry_dt
            _d+=dt.timedelta(days=7)
    return ticker_list

def us_option_univ(underlying_security:str, start_date: dt.date, end_date: dt.date, ):
   """
   Fetch option universe using excel bbg add-in
   """
   bdp = BDP_Session()
   data = bdp.bdh_request([underlying_security + " US Equity"], ['PX_LAST'], start_date=start_date, end_date=end_date)
   hist_price = data.get(underlying_security + " US Equity").get('PX_LAST')

   output_col = ["rebal_date", "ticker"]
   opt_chain = []
   # opt_chain = pd.DataFrame(columns=['trade_date', 'expiry', 'option'])
   d = date
   if d < dt.datetime.now().date():
       underlying_price = hist_price.get(d)
       if include_weekly:
           expiry_dt = None
       else:
           expiry_dt = rebalance_dates[idx+1]

       opt_chain_on_date = gather_option_chains(d, rebalance_dates[idx+2], min_pct_strike, max_pct_strike, underlying_security, underlying_price, call_put_factor, strike_interval, expiry_dt)
       opt_chain += [[d, x] for x in opt_chain_on_date]


   df_opt_chain = pd.DataFrame(opt_chain, columns=output_col)
   opt_cls = common.extract_option_ticker(df_opt_chain, 'ticker')
   df_opt_chain['expiry'] = df_opt_chain['ticker'].map(opt_cls.expiry)
   df_opt_chain = df_opt_chain[df_opt_chain['expiry'].isin(rebalance_dates)]
   df_opt_chain['underlying_price'] = df_opt_chain['rebal_date'].map(hist_price)
   
   return df_opt_chain

df = ca_option_univ('XIU', dt.date(2026,1,2), dt.date(2026,4,24))
