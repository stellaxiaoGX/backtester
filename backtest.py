import pandas as pd
import numpy as np
import datetime as dt
import yfinance as yf
import matplotlib
from allocate_port import *
import os
cur_dir = os.path.dirname(__file__)
import sys
sys.path.append('Z:\\ApolloGX')
if "\\im_dev\\" in cur_dir:
    import im_dev.std_lib.common as common
else:
    import im_prod.std_lib.common as common
    

def download_tmx_options(ticker: str, start_date, end_date):
    """start and end dates here specify the 'as of' dates for option universe"""
    download_html = f"https://www.m-x.ca/en/trading/data/historical?symbol={ticker.lower()}&from={start_date}&to={end_date}&dnld=1#quotes"
    current_att = 0
    while current_att < 8:
        try:
            df_download = common.download_from_url(download_html)
            print(f"Downloaded option data for {ticker} from {start_date} to {end_date}")
            return df_download
        except:
            print(f"Failed to download data for {ticker} from {start_date} to {end_date}")
            return pd.DataFrame()
   

def tmx_options_pricing(ticker:str, start_date, end_date):
    
    """
    Downloads TMX option data in monthly segments.
    start_dt and end_dt define the 'as-of' dates for the option universe.
    """
    def end_of_month(d: dt.date) -> dt.date:
        if d.month == 12:
            next_month = dt.date(d.year + 1, 1, 1)
        else:
            next_month = dt.date(d.year, d.month + 1, 1)
        return next_month - dt.timedelta(days=1)

    dfs = []
    current_start = start_date

    while current_start <= end_date:
        # End of the current month segment        
        current_end = end_of_month(current_start)

        if current_end > end_date:
            current_end = end_date

        df = download_tmx_options(
            ticker=ticker,
            start_date=current_start.strftime("%Y-%m-%d"),
            end_date=current_end.strftime("%Y-%m-%d")
        )

        if not df.empty:
            df["as_of_start"] = current_start
            df["as_of_end"] = current_end
            dfs.append(df)

        # Advance to next month
        current_start = current_end + dt.timedelta(days=1)

    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)


# Global function defined in allocate_port as well
def download_rates(ticker: str, country_code:str, start_dt: str, end_dt: str):
    """ Fetches historical interest rates given time frame and country. """
    if country_code.lower() == "cn":
        rates_file_path = os.path.join(cur_dir, "interest rates", "canrates.csv")
    else:
        rates_file_path = os.path.join(cur_dir, "interest rates", "usrates.csv")
    try:
        # Load the rates CSV file
        df = pd.read_csv(rates_file_path)
        df['date'] = pd.to_datetime(df['date']).dt.date
        
        # Filter by desired time frame
        start_dt_obj = pd.to_datetime(start_dt).date()
        end_dt_obj = pd.to_datetime(end_dt).date()
        
        filtered_rates = df[(df['date'] >= start_dt_obj) & (df['date'] <= end_dt_obj)]
        
        if filtered_rates.empty:
            print(f"No rates found for {country_code} in the given date range.")
            return pd.DataFrame()
        
        rates_series = filtered_rates.reset_index(drop=True)
        return rates_series
    
    except Exception as e:
        print(f"Error fetching rates: {e}")
        return pd.DataFrame()

def date_engine(roll_date: dt.date, dtm: int, holidays):
    """
    next roll date find given the current rolling date
    """
    def next_friday(date):
        if date.weekday() == 4:
            candidate = common.workday(date, 5, holidays)
        else:
            candidate = common.workday(date, 4 - date.weekday(), holidays)
        while candidate in holidays or candidate.weekday() > 4:
            candidate = common.workday(candidate, -1, holidays)
        return candidate
    
    def third_friday(year: int, month: int) -> dt.date:
        first_day = dt.date(year, month, 1)
        first_friday_offset = (4 - first_day.weekday()) % 7
        first_friday = first_day + dt.timedelta(days=first_friday_offset)
        return first_friday + dt.timedelta(days=14)

    def next_third_friday(roll_date: dt.date, months: int) -> dt.date:
        
        # Third Friday of roll_date's month
        current_tf = third_friday(roll_date.year, roll_date.month)
        # Determine base month
        if roll_date > current_tf:
            base_month_offset = 1
        else:
            base_month_offset = 0
    
        # Convert year/month to absolute month index
        start_index = roll_date.year * 12 + (roll_date.month - 1)
        target_index = start_index + base_month_offset + months - 1
    
        year = target_index // 12
        month = target_index % 12 + 1
    
        return third_friday(year, month)

    if dtm == 5:
        expiry = next_friday(roll_date)
        
    else: # any multiple of 30 (months) will look for the 3rd friday regardless of the date we start on
        months = dtm//30
        expiry = next_third_friday(roll_date, months)
        
    while expiry in holidays:
        expiry = expiry - dt.timedelta(days=1)
            
    return expiry


def option_prices(opt_ticker:str, full_option_univ:pd.DataFrame, start_date:dt.date, end_date:dt.date):
    """specified ticker for option prices for a given time frame: buy to expiry"""
    ticker_px = full_option_univ[full_option_univ['Symbol'] == opt_ticker]
    ticker_px = ticker_px[ticker_px['Date'] >= start_date]
    ticker_px = ticker_px[ticker_px['Date'] <= end_date]
    return ticker_px


def eod_log(port: Portfolio, date:pd.date, ul_prices: pd.DataFrame, results_df: pd.DataFrame):
    """
    Note: columns are "Date", "Id", "Ticker", "Direction", "Qty", "Price", "Strike", "Expiration", "MV"
    """
    for strgy, strategy_id in port.strategies:
        if strategy_id == 'Equity':
            results_df.loc[len(results_df)] = [d, strategy_id, port.ticker.upper()+port.country_code.upper()+" Equity", 1, strgy.shares, ul_prices[d], None, None, strgy.shares*ul_prices[d]]
        elif strategy_id == 'Residual':
            results_df.loc[len(results_df)] = [d, strategy_id, None, 1, strgy.legs[0].cash, 1, None, None, strgy.legs[0].cash]
        elif strategy_id == 'CC':
            equity_leg = next(l for l in strgy.legs if isinstance(l, Equity))
            call_leg = next(l for l in strgy.legs if isinstance(l, OptionLeg))
            results_df.loc[len(results_df)] = [d, strategy_id, port.ticker.upper()+port.country_code.upper()+" Equity", 1, strgy.shares, ul_prices[d], None, None, strgy.shares*ul_prices[d]]
            results_df.loc[len(results_df)] = [d, strategy_id, call_leg.current, call_leg.direction, strgy.contracts, call_leg.price, call_leg.strike, call_leg.expiry, call_leg.direction*strgy.contracts*call_leg.price*call_leg.multiplier]
        else:
            option_legs = [l for l in strgy.legs if isinstance(l, OptionLeg)]
            for option in option_legs:
                results_df.loc[len(results_df)] = [d, strategy_id, option.current, option.direction, strgy.contracts, option.price, option.strike, option.expiry, option.direction*strgy.contracts*option.price*option.multiplier]
                
"""
Backtesting Methodology:
    1. take portfolio allocation class result from allocate_port.py
    2. drill down to every strategy in the allocated portfolio
    3. On every looped date:
        A. For each strategy: Check for expiry and transact + rebalance
        B. money market cash accrues daily interest
"""
    
def run_backtest(port: Portfolio):
    """
    Reminder that after allocate_port.py, the Portfolio Object Class will have:
        - self.strategies (filled with allocated positions)
        - self.start_dt & self.end_dt adjusted for holidays already
        - self.ticker & self.country_code for identification 
        - self.holidays dictionary
    """
    # Assign needed data
    underlying_prices = port.ul_prices
    rates = download_rates(port.ticker, port.country_code, port.start_dt.strftime("%Y-%m-%d"), port.end_dt.strftime("%Y-%m-%d"))
    full_options_universe = None
    if port.country_code.lower() == 'cn':
        full_options_universe = tmx_options_pricing(port.ticker, port.start_dt, port.end_dt)
    else:
        pass

    last_d = None
    d = port.start_dt
    
    columns = ["Date", "Id", "Ticker", "Direction", "Qty", "Price", "Strike", "Expiration", "MV"]
    backtest_results = pd.DataFrame(columns = columns)

    # day 0: portfolio just allocated need to get option price by dates until expiry
    for strgy, strategy_id in port.strategies:
        # allocation = bought at closing of day 0: nothing has accrued/prices have not changed, append to results dataframe
        if strategy_id == 'Equity' or strategy_id == 'Residual':
            continue
        # make sure options have correct and future premiums for each ticker
        else:
            option_legs = [l for l in strgy.legs if isinstance(l, OptionLeg)]
            expiry_date = option_legs[0].expiry
            for option in option_legs:
                ticker = option.current
                qty = strgy.contracts
                
                # determine prices of options and validate
                option.price_series = option_prices(ticker, full_options_universe, d, expiry_date)
                price = option.price_series[d]
                option.price = price

    eod_log(port, d, underlying_prices, backtest_results)

    # MAIN ENGINE: date loop that stops at every expiry and rolls the position/strategy
    while port.start_dt <= d <= port.end_dt:
        ir = rates[d.strftime("%Y-%m-%d")]
        spot = underlying_prices[d.strftime("%Y-%m-%d")]
        for strgy in port.strategies:
            s_id = strgy.strategy_id
            
            if s_id == 'Equity': # EQUITY: don't need to do anything
                continue
            
            elif s_id == 'Residual': # RESIDUAL or COLLATERAL: accrue daily interest
                days = (last_d - d).days
                strgy.legs[0].cash = strgy.legs[0].cash * (1+ir/365)
                continue
            
            else: # REST BUILDING BLOCKS: Check for expiry, only make any action if expiring ('Single', 'Spread', 'Synthetic', 'Strangle', 'IC', 'CC')
                if s_id == 'CC': # Covered Call is the only strategy with equity leg, need to check differently
                    call_leg = next(l for l in strgy.legs if isinstance(l, OptionLeg))
                    
                    if call_leg.expiry == d:
                        # Determine action needed at Expiration: ITM or OTM?
                        strgy.expiry_action(d, spot)
                        # Roll for next position
                        strgy.roll(d, spot)
                    else:
                        continue
                    
                elif strgy.legs[0].expiry == d:
                    # Take action on expiry
                    strgy.expiry_action(d, spot)
                    # Roll position
                    strgy.roll(d, spot)
                    
        # Compute daily value
        eod_log(port, d, underlying_prices, backtest_results)
        # GO TO NEXT DATE (save previous)
        last_d = d
        d = common.workday(d, 1, port.holidays)
        
    return backtest_results
    

def plot_backtest(results: pd.DataFrame):
    """
    Plots the results of the backtest using matplotlib
    """

    return    