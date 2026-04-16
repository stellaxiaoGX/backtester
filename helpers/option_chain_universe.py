import pandas as pd
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



def us_option_univ(ticker:str, start_date:dt.date, end_date:dt.date):

   """
   Fetch option universe using bloomberg session
   """
   underlying_security = ticker.upper()+" US"
   bbg_ticker_format = " Equity"
   try:
       # Retrieve option chain
       bdp = BDP_Session()

       
       if data.empty:
           print("No options found for given parameters.")
           return None
       
       return data, hist_price
   
   except Exception as e:
       print(f"Error fetching option universe: {e}")
       return None




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
        


start_dt = dt.date(2025,2,20)
end_dt = dt.date(2025,3,20)

sstr = start_dt.strftime('%Y-%m-%d')
estr = end_dt.strftime('%Y-%m-%d')

#ca = ca_option_univ('XIU', start_dt, end_dt)

us_data, us_hist = us_option_univ('SPY', start_dt, end_dt)

