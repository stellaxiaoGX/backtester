import datetime as dt
import pandas as pd
import yfinance as yf
import os
cur_dir = os.path.dirname(__file__)
import sys
sys.path.append('Z:\\ApolloGX')
if "\\im_dev\\" in cur_dir:
    import im_dev.std_lib.common as common
else:
    import im_prod.std_lib.common as common
    
class Equity():
    """
    underlying equity leg
    - asset: "equity"
    - direction: 1 | -1 for long or short
    """
    def __init__(self,
                 asset: str = "equity",
                 direction: int = None,
                 weight: float = None,
                 shares: int = None,

                 ticker: str = None,
                 country: str = None,
                 start_dt: dt.date = None,
                 end_dt: dt.date = None):
        
        self.asset = asset.lower()
        if isinstance(direction, str):
            self.direction = 1 if direction.lower() in ("1", "+1", "long") else -1
        else:
            self.direction = int(direction) if direction is not None else None
        self.weight = weight
        self.shares = shares
        self.ticker = ticker.upper() if ticker else None
        self.country = country.upper() if country else None
        self.start_dt = start_dt
        self.end_dt = end_dt
    
    def closing_prices(ticker: str, country_code:str, start_dt: str, end_dt: str):
        """ Fetches closing prices for a given ticker symbol. """
        if country_code.lower() == "cn":
            download_ticker = ticker+".TO"
        else:
            download_ticker = ticker
        try:
            # Download historical data
            data = yf.download(download_ticker, start=start_dt, end=end_dt)['Close']
            data.rename(columns={download_ticker:ticker}, inplace=True)
            
            if data.empty:
                print(f"No data found for {ticker} in the given date range.")
                return pd.DataFrame()
            closing_prices = data.reset_index()
            return closing_prices
        
        except Exception as e:
            print(f"Error fetching data: {e}")
            return pd.DataFrame()

class Residual():
    """
    money market bond leg AKA Residual cash allocation: earns daily interest, used to secure short option legs
    - asset: "bond"
    - direction: 1 | -1 for long or short
    """
    def __init__(self,
                 asset: str = "bond",
                 direction: int = 1,
                 cash: float = None,
                 ticker: str = None,
                 country: str = None,
                 start_dt: dt.date = None,
                 end_dt: dt.date = None):
        
        self.asset = asset.lower()
        if isinstance(direction, str):
            self.direction = 1 if direction.lower() in ("1", "+1", "long") else -1
        else:
            self.direction = int(direction) if direction is not None else None
        self.cash = cash
        self.ticker = ticker.upper() if ticker else None
        self.country = country.upper() if country else None
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.rates_series = None
    
    def download_rates(self, ticker: str, country_code:str, start_dt: str, end_dt: str):
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
            
            self.rates_series = filtered_rates.reset_index(drop=True)
            return self.rates_series
        
        except Exception as e:
            print(f"Error fetching rates: {e}")
            return pd.DataFrame()
    
class OptionLeg:
    """
    General option leg.

    Inputs:
    - asset: "option"
    - option_type: "call" | "put"
    - direction: 1 | -1 for long or short
    - dtm: days to maturity (e.g., 30 for monthly options)
    - moneyness: percentage away from the money (e.g., 1.05 for 5% OTM call, 0.95 for 5% OTM put)

    Other variables:
    - price: option premium per share
    - strike: float 
    - expiry: "YYYY-MM-DD"
    - multiplier: 100 (by default, standard contract multiplier)

    """
    def __init__(self,
                 asset: str = "option",
                 option_type: str = None,
                 direction: int = 1,
                 dtm: int = 5,
                 moneyness: float = 0.0,
                 
                 price: float = 0.0,
                 strike: float = None,
                 expiry: dt.date = None,
                 multiplier: int = 100):
        
        self.asset = asset.lower()
        self.option_type = option_type.lower()
        self.direction = direction
        self.dtm = int(dtm)
        self.moneyness = float(moneyness)
        self.price = float(price)
        self.strike = float(strike)
        self.expiry = expiry
        self.multiplier = int(multiplier)
        
        self.current = None

        if self.option_type not in ["call", "put"]:
            raise ValueError(f"Option leg missing/invalid option_type: {self.__dict__}")
        if self.expiry is None or self.strike is None:
            raise ValueError(f"Option leg must have expiry & strike: {self.__dict__}")
        if self.direction not in [1, -1]:
            raise ValueError(f"Option leg invalid direction: {self.direction}; expected 1 or -1")

    def select_option(self, ticker: str, roll_date:dt.date, exp_date:dt.date):
        option_univ = self.download_options(ticker, roll_date, roll_date)
        ul_row = option_univ.loc[option_univ['Symbol'] == ticker]
        ul_price= ul_row.loc[0, 'Last Price']
        option_univ = option_univ[option_univ['Expiry Date'] == exp_date.strftime("%Y-%m-%d")]
        option_univ = option_univ[option_univ['Call/Put'] == 0] if self.option_type == 'call' else option_univ[option_univ['Call/Put'] == 1]
        
        if self.option_type == 'call':
            target_strike = ul_price*(self.moneyness)
        else:
            target_strike = ul_price*(self.moneyness)
        
        closest_strike_index = (option_univ['Strike Price'] - target_strike).abs().idxmin()
        strike = option_univ.loc[closest_strike_index, 'Strike Price']
        selected_option = option_univ.loc[closest_strike_index, 'Symbol']
        expiry = option_univ.loc[closest_strike_index, 'Expiry Date']
        bid = option_univ.loc[closest_strike_index, 'Bid Price']
        ask = option_univ.loc[closest_strike_index, 'Ask Price']
        
        self.current = selected_option
        self.price = bid if self.direction == 1 else ask
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

#------------------------------STRATEGY BUILDING BLOCK CLASSES---------------------------------------------------------------------------------    

class OptionStrategy:
    def __init__(self, strategy_id="Generic", name=None, underlying=None):
        self.strategy_id = strategy_id
        self.name = name or strategy_id
        self.underlying = underlying
        self.legs = []

    def add_leg(self, leg):
        self.legs.append(leg)

    def total_notional(self):
        return sum((leg.price * leg.multiplier * abs(leg.direction)) for leg in self.legs if hasattr(leg, 'price') and leg.price is not None)

    def __str__(self):
        legs_desc = ", ".join(
            [f"{('Long' if leg.direction == 1 else 'Short')} {getattr(leg, 'option_type', getattr(leg, 'asset', 'leg')).capitalize()} @{getattr(leg, 'strike', 'n/a')} exp {getattr(leg, 'expiry', 'n/a')}" for leg in self.legs]
        )
        return f"{self.name} ({self.strategy_id}): {legs_desc}"

class Single(OptionStrategy):
    """A single option leg."""
    def __init__(self, leg: OptionLeg):
        super().__init__(strategy_id="Single", name="Single Option")
        self.add_leg(leg)

class CoveredCall(OptionStrategy):
    """A covered call strategy with 1 equity leg and 1 short call leg."""
    def __init__(self, equity_leg: Equity, call_leg: OptionLeg):
        super().__init__(strategy_id="CC", name="Covered Call", underlying=equity_leg.ticker)
        self.add_leg(equity_leg)
        self.add_leg(call_leg)

class Spread(OptionStrategy):
    """A spread strategy with 2 option legs."""
    def __init__(self, long_leg: OptionLeg, short_leg: OptionLeg):
        super().__init__(strategy_id="Spread", name="Spread")
        self.add_leg(long_leg)
        self.add_leg(short_leg)

class Strangle(OptionStrategy):
    """A strangle strategy with 2 option legs."""
    def __init__(self, call_leg: OptionLeg, put_leg: OptionLeg):
        super().__init__(strategy_id="Strangle", name="Strangle")
        self.add_leg(call_leg)
        self.add_leg(put_leg)

class Synthetic(OptionStrategy):
    """A synthetic position using an equity leg plus an option leg."""
    def __init__(self, equity_leg: Equity, option_leg: OptionLeg):
        super().__init__(strategy_id="Synthetic", name="Synthetic", underlying=equity_leg.ticker)
        self.add_leg(equity_leg)
        self.add_leg(option_leg)

class IronCondor(OptionStrategy):
    """An iron condor strategy with 4 option legs: call spread + put spread."""
    def __init__(self, long_call: OptionLeg, short_call: OptionLeg, short_put: OptionLeg, long_put: OptionLeg):
        super().__init__(strategy_id="IC", name="Iron Condor")
        self.add_leg(long_call)
        self.add_leg(short_call)
        self.add_leg(short_put)
        self.add_leg(long_put)


#------------------------------STRATEGY BUILDING BLOCK CLASSES---------------------------------------------------------------------------------    


class Portfolio():
    """ 
    Every backtest needs to have a starting initiated portfolio determined by the configuration file and inputs. 
    The portfolio class:
        1. reads configurations,
        2. identifies option universe, selects options based on user input parameters (DTM, moneyness),
        3. matches strategies to building blocks (e.g., long call, short put secured by bond, etc.),
        4. determines net collateral of all strategies and,
        5. allocates capital to each leg accordingly.
    The output is shown to the user to be reviewed and confirmed before the backtest is run.
    """
    def __init__(self, config_path:str, ticker:str, country_code:str, start_dt:dt.date, end_dt:dt.date, base_cash:int=1000000):
        
        """ Inputs:
            1) Underlying Ticker + Country Code
            2) Configuration dataframe file path
            3) Start Date and End Date
        """
        # Global Variables and Inputs
        self.cash = base_cash
        self.start_dt = dt.date(2025,1,1)
        self.end_dt = dt.date(2025,4,30)
        self.ticker = ticker.upper()
        self.country_code = country_code.upper()
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
        self.ul_prices = closing_prices(self.ticker, self.country_code, start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")).set_index('Date')
        
        # Inputs preprocessing: Option OptionLegs Dataframe -> dictionary with selected options
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

if __name__ == "__main__":
    
    """ Inputs:
        1) Underlying Ticker + Country Code
        2) Configuration of Options file path
        3) Start Date and End Date
    """
    # Global Variables
    base_cash = 1000000
    # User Inputs
    start_dt = dt.date(2025,1,1)
    end_dt = dt.date(2025,4,30)
    ticker = "XIU"
    country_code = "CN"
    config_path = r"C:\Users\sxiao\backtester\portfolio_config\config.csv"

    portfolio = Portfolio(config_path, ticker, country_code, start_dt, end_dt, base_cash)
    