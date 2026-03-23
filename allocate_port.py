import datetime as dt
import pandas as pd
import yfinance as yf
import os
cur_dir = os.path.dirname(__file__)
import sys
import copy
sys.path.append('Z:\\ApolloGX')
if "\\im_dev\\" in cur_dir:
    import im_dev.std_lib.common as common
else:
    import im_prod.std_lib.common as common
    

class Leg():
    """
    back tester input class of an option leg.
    - instrument: "option"
    - side: "long" | "short"
    - ratio: integer to determine qty
    - price: option premium per share
    - option_type: "call" | "put"
    - strike: float 
    - expiry: "YYYY-MM-DD"
    - multiplier: 100 by default
    - secured: optional label parameter to specify whether a short option is naked or secured
    """
    def __init__(self,
                 instrument: str,
                 option_type: str = None,
                 pos: str = None,
                 dtm: int = 5,
                 moneyness: float = 0.0,
                 ratio: int = 1,
                 price: float = 0.0,
                 strike: float = None,
                 expiry: dt.date = None,
                 multiplier: int = 100,
                 secured: bool = False):
        
        self.instrument = instrument.lower()
        self.option_type = option_type.lower()
        self.pos = pos.lower()
        self.dtm = int(dtm)
        self.moneyness = float(moneyness)
        self.ratio = int(ratio)
        self.price = float(price)
        self.strike = float(strike)
        self.expiry = expiry
        self.multiplier = int(multiplier)
        self.secured = secured
        
        self.current = None

        if self.option_type not in ["call", "put"]:
            raise ValueError(f"Option leg missing/invalid option_type: {self.__dict__}")
        if self.expiry is None or self.strike is None:
            raise ValueError(f"Option leg must have expiry & strike: {self.__dict__}")
    
    def to_dict(self):
        return {'instrument': self.instrument,
                'option_type': self.option_type,
                'pos': self.pos,
                'dtm': self.dtm,
                'moneyness': self.moneyness,
                'ratio': self.ratio,
                'price': self.price,
                'strike': self.strike,
                'expiry': self.expiry,
                'multiplier': self.multiplier,
                'secured': self.secured,
                'current': self.current}
    
    def select_option(self, ticker: str, roll_date:dt.date, exp_date:dt.date):
        
        option_univ = self.download_options(ticker, roll_date, roll_date)
        ul_row = option_univ.loc[option_univ['Symbol'] == ticker]
        ul_price= ul_row.loc[0, 'Last Price']
        option_univ = option_univ[option_univ['Expiry Date'] == exp_date.strftime("%Y-%m-%d")]
        option_univ = option_univ[option_univ['Call/Put'] == 0] if self.option_type == 'call' else option_univ[option_univ['Call/Put'] == 1]
        
        if self.option_type == 'call':
            target_strike = ul_price*(1+self.moneyness)
        else:
            target_strike = ul_price*(1-self.moneyness)
        
        closest_strike_index = (option_univ['Strike Price'] - target_strike).abs().idxmin()
        strike = option_univ.loc[closest_strike_index, 'Strike Price']
        selected_option = option_univ.loc[closest_strike_index, 'Symbol']
        expiry = option_univ.loc[closest_strike_index, 'Expiry Date']
        bid = option_univ.loc[closest_strike_index, 'Bid Price']
        ask = option_univ.loc[closest_strike_index, 'Ask Price']
        
        self.current = selected_option
        self.price = bid if self.pos == 'long' else ask
        self.strike = strike
        self.expiry = expiry
        
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


def closing_prices(ticker: str, country_code:str, start_dt: str, end_dt: str):
    """ Fetches closing prices for a given ticker symbol. """
    if country_code == "CN":
        ticker = ticker+".TO"
    try:
        # Download historical data
        data = yf.download(ticker, start=start_dt, end=end_dt)['Close']
        
        if data.empty:
            print(f"No data found for {ticker} in the given date range.")
            return pd.DataFrame()
        closing_prices = data.reset_index()
        return closing_prices
    
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()

def group_options(legs: list[Leg]):
    """ Bucket different option legs by expiring date/dtm and option type/direction """
    buckets = {}
    for l in legs:
        if l.instrument != "option":
            continue
        key = l.expiry
        if key not in buckets:
            buckets[key] = {
                "long_calls": [],
                "short_calls": [],
                "long_puts": [],
                "short_puts": [],
            }

        if l.option_type == "call" and l.side == "long":
            buckets[key]["long_calls"].append(copy.deepcopy(l))
        elif l.option_type == "call" and l.side == "short":
            buckets[key]["short_calls"].append(copy.deepcopy(l))
        elif l.option_type == "put" and l.side == "long":
            buckets[key]["long_puts"].append(copy.deepcopy(l))
        elif l.option_type == "put" and l.side == "short":
            buckets[key]["short_puts"].append(copy.deepcopy(l))
    return buckets


class Portfolio():
    """ 
    Every backtest is initiated by a starting portfolio. 
    The portfolio class is for taking in option leg configurations and optimized allocation.
    """
    def __init__(self, config_path:str, underlying_ticker:str, country_code:str, start_dt:dt.date, end_dt:dt.date, base_cash:int=1000000):
        
        """ Inputs:
            1) Underlying Ticker + Country Code
            2) Configuration of Options file path
            3) Start Date and End Date
        """
        # Global Variables and Inputs
        self.cash = base_cash
        self.start_dt = dt.date(2025,1,1)
        self.end_dt = dt.date(2025,4,30)
        self.ticker = "XIU"
        self.country_code = "CN"
        self.option_legs = []
        
        # Inputs preprocessing: Dates
        self.holidays = None
        if self.country_code == "US":
            holidays = common.nyse_holidays()
            self.holidays = pd.to_datetime(list(holidays.keys()), format='ISO8601').date
            while self.start_dt in self.holidays:
                self.start_dt = common.workday(self.start_dt, 1, holidays)
            while end_dt in self.holidays:
                self.end_dt = common.workday(self.end_dt, -1, holidays)
        else:
            holidays = common.tsx_holidays()
            self.holidays = pd.to_datetime(list(holidays.keys()), format='ISO8601').date
            while self.start_dt in self.holidays:
                self.start_dt = common.workday(self.start_dt, 1, holidays)
            while end_dt in self.holidays:
                self.end_dt = common.workday(self.end_dt, -1, holidays)
                
        # Inputs preprocessing: Ticker + Prices Time Series
        self.equity_ticker = self.ticker+" "+self.country_code+" Equity"
        self.ul_prices = closing_prices(self.ticker, self.country_code, start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))
        
        # Inputs preprocessing: Option Legs Dataframe -> Dictionary with selected options
        config = pd.read_csv(config_path)
        cols_lst = ['SEC_ID', 'TYPE', 'POS', 'DTM', 'MONEYNESS', 'RATIO', 'PRICE', 'STRIKE', 'EXPIRY', 'SECURED']
        config = config.reindex(columns=config.columns.tolist() + [c for c in cols_lst if c not in config.columns], fill_value=None)
        
        if config.empty:
            print("Warning: Configuration dataframe is empty.") 
        config_dict = config.to_dict(orient = "records")
        
        # Find nearest next Friday for legging into options
        if self.start_dt.weekday() == 4: #Friday
            nearest_fri = common.workday(self.start_dt, 5)
        else:
            days_til_fri = 4 - self.start_dt.weekday()
            nearest_fri = common.workday(self.start_dt, days_til_fri)
        while nearest_fri in self.holidays:
            nearest_fri = common.workday(nearest_fri, -1)
        
        # Configure dictionary after selecting options
        for option in config_dict:
            option_leg = Leg(instrument=str(option.get('SEC_ID')),
                         option_type=str(option.get('TYPE')),
                         pos=str(option.get('POS')),
                         dtm=int(option.get('DTM')),
                         moneyness=float(option.get('MONEYNESS')),
                         ratio=int(option.get('RATIO')),
                         price=float(option.get('PRICE')),
                         strike=float(option.get('STRIKE')),
                         expiry=pd.to_datetime(option.get('EXPIRY')).date,
                         secured=bool(option.get('SECURED')))
            expiry_date = common.workday(nearest_fri, option_leg.dtm)
            while expiry_date in self.holidays:
                expiry_date = common.workday(expiry_date, -1)
            option_leg.select_option(self.ticker, nearest_fri, expiry_date)
            option = option_leg.to_dict()
            self.option_legs.append(option)
            
        
    def vertical_dependencies(self):
        """
        Parses through the set of option legs initialized and determine dependencies based on expiry date matches
        """
        # Expand temporary list of copied legs with new "qty" from ratio for internal math
        tmp = []
        for l in legs:
            t = copy.deepcopy(l)
            t.qty = l.ratio
            tmp.append(t)
        # uses helper to segment by expiry date and option type into buckets
        buckets = group_options(tmp)
        m_call, m_put = {}, {}
        rem_sc, rem_sp = {}, {}
        
        # sort all different option positions by moneyness
        for exp, group in buckets.items():
            scalls = sorted(group["short_calls"], key=lambda x: x.strike)
            lcalls = sorted(group["long_calls"], key=lambda x: x.strike)
            sputs  = sorted(group["short_puts"],  key=lambda x: -x.strike)
            lputs  = sorted(group["long_puts"],   key=lambda x: -x.strike)
            
            # long calls: tally up the different long call positions
            avail_lc = {}
            for lc in lcalls:
                avail_lc[lc.strike] += lc.qty
                
            # long puts: tally up the different long put positions
            avail_lp = {}
            for lp in lputs:
                avail_lp[lp.strike] += lp.qty

            # Short calls covered by long calls with strike >= short strike
            for sc in scalls:
                remain = sc.qty
                for k in sorted([k for k in avail_lc if k >= sc.strike]):
                    if remain <= 0:
                        break
                    take = min(remain, avail_lc[k])
                    if take <= 0:
                        continue
                    avail_lc[k] -= take
                    remain -= take
                    sc_leg = copy.deepcopy(sc); sc_leg.qty = take
                    lc_leg = copy.deepcopy([lc for lc in lcalls if lc.strike == k][0]); lc_leg.qty = take
                    m_call[exp].append((sc_leg, lc_leg, take))
                if remain > 0:
                    leftover = copy.deepcopy(sc); leftover.qty = remain
                    rem_sc[exp].append(leftover)

            # Short puts covered by long puts with strike <= short strike
            for sp in sputs:
                remain = sp.qty
                for k in sorted([k for k in avail_lp if k <= sp.strike], reverse=True):
                    if remain <= 0:
                        break
                    take = min(remain, avail_lp[k])
                    if take <= 0:
                        continue
                    avail_lp[k] -= take
                    remain -= take
                    sp_leg = copy.deepcopy(sp); sp_leg.qty = take
                    lp_leg = copy.deepcopy([lp for lp in lputs if lp.strike == k][0]); lp_leg.qty = take
                    m_put[exp].append((sp_leg, lp_leg, take))
                if remain > 0:
                    leftover = copy.deepcopy(sp); leftover.qty = remain
                    rem_sp[exp].append(leftover)

        return m_call, m_put, rem_sc, rem_sp
        
    
    def allocate_cash(self):
        """
        Based on initial cash amount and option leg dependencies, determine how to allocate cash into shares 
        and scale option quantities by ratio optimally without running out of cash flow
        """
        return
                
                
    
if __name__ == "__main__":
    
    """ Inputs:
        1) Underlying Ticker + Country Code
        2) Configuration of Options file path
        3) Start Date and End Date
    """
    # Global Variables
    base_cash = 1000000
    # Inputs
    start_dt = dt.date(2025,1,1)
    end_dt = dt.date(2025,4,30)
    underlying_ticker = "XIU"
    country_code = "CN"
    config_path = r"C:\Users\sxiao\backtester\portfolio_config\option_legs.csv"
    
    port = Portfolio(config_path, underlying_ticker, country_code, start_dt, end_dt, base_cash)
    legs = port.option_legs 
