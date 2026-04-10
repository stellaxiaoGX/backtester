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
        self.weight = float(weight)
        self.shares = shares
        self.ticker = ticker.upper() if ticker else None
        self.country = country.upper() if country else None
        self.start_dt = start_dt
        self.end_dt = end_dt   

class Residual():
    """
    money market bond leg AKA Residual cash allocation: earns daily interest, used to secure short option legs
    - asset: "bond"
    - direction: 1 for long only
    """
    def __init__(self,
                 asset: str = "bond",
                 cash: float = None,
                 ticker: str = None,
                 country: str = None,
                 start_dt: dt.date = None,
                 end_dt: dt.date = None):
        
        self.asset = asset.lower()
        self.cash = cash
        self.ticker = ticker.upper() if ticker else None
        self.country = country.upper() if country else None
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.rates_series = self.download_rates(self.ticker, self.country, self.start_dt.strftime("%Y-%m-%d"), self.end_dt.strftime("%Y-%m-%d"))
    
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
        self.strike = None # default to None when no option chosen
        self.expiry = expiry # default to None when no option chosen
        self.multiplier = int(multiplier)
        
        self.current = None

        if self.option_type not in ["c", "p"]:
            raise ValueError(f"Option leg missing/invalid option_type: {self.__dict__}")
        if self.direction not in [1, -1]:
            raise ValueError(f"Option leg invalid direction: {self.direction}; expected 1 or -1")

    def select_option(self, ticker: str, roll_date:dt.date, holidays):
        exp_date = self._calculate_expiry(roll_date, holidays)
        option_univ = self.download_options(ticker, roll_date, roll_date)
        ul_row = option_univ.loc[option_univ['Symbol'] == ticker]
        ul_price = ul_row.loc[0, 'Last Price']
        option_univ = option_univ[option_univ['Expiry Date'] == exp_date.strftime("%Y-%m-%d")]
        option_univ = option_univ[option_univ['Call/Put'] == 0] if self.option_type == 'call' else option_univ[option_univ['Call/Put'] == 1]

        target_strike = ul_price * self.moneyness
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

    def _calculate_expiry(self, roll_date: dt.date, holidays):
        def next_friday(date):
            if date.weekday() == 4:
                candidate = common.workday(date, 5, holidays)
            else:
                candidate = common.workday(date, 4 - date.weekday(), holidays)
            while candidate in holidays or candidate.weekday() > 4:
                candidate = common.workday(candidate, -1, holidays)
            return candidate

        if self.dtm == 5:
            expiry = next_friday(roll_date)
        else:
            target = roll_date + dt.timedelta(days=self.dtm)
            weekday = target.weekday()
            days_to_friday = 4 - weekday
            expiry = target + dt.timedelta(days=days_to_friday)
            while expiry in holidays:
                expiry = expiry - dt.timedelta(days=7)
        return expiry

    def download_options(self, ticker: str, start_date:str, end_date:str):
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

def closing_prices(ticker: str, country_code:str, start_dt: str, end_dt: str):
    """ Fetches closing prices for a given ticker symbol. """
    if country_code.lower() == "cn":
        download_ticker = ticker+".TO"
    else:
        download_ticker = ticker
    try:
        # Download historical data
        ticker_obj = yf.Ticker(download_ticker)
        
        # Download historical data
        data = ticker_obj.history(start=start_dt, end=end_dt)['Close']
        #data = yf.download(download_ticker, start=start_dt, end=end_dt)['Close']
        data.rename(columns={download_ticker:ticker}, inplace=True)
        
        if data.empty:
            print(f"No data found for {ticker} in the given date range.")
            return pd.DataFrame()
        closing_prices = data.reset_index()
        return closing_prices
    
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        #return pd.DataFrame()
        manual_prices = pd.read_csv(os.path.join(cur_dir, "xiu.csv"))
        manual_prices['Date'] = pd.to_datetime(manual_prices['Date']).dt.date
        manual_prices = manual_prices[(manual_prices['Date'] >= pd.to_datetime(start_dt).date()) & (manual_prices['Date'] <= pd.to_datetime(end_dt).date())]
        return manual_prices
    
#------------------------------STRATEGY BUILDING BLOCK CLASSES---------------------------------------------------------------------------------    

class OptionStrategy:
    def __init__(self, strategy_id="Generic", name=None, underlying=None):
        self.strategy_id = strategy_id
        self.name = name or strategy_id
        self.underlying = underlying
        self.legs = []

    def add_leg(self, leg):
        self.legs.append(leg)

    def __str__(self):
        legs_desc = []
        for leg in self.legs:
            if leg.asset.lower() == "option":
                contracts = getattr(self, 'contracts', 'n/a')
                option_type_full = 'Call' if getattr(leg, 'option_type', '').lower() == 'c' else 'Put'
                desc = f"{('Long' if leg.direction == 1 else 'Short')} {option_type_full} {contracts} contracts @{getattr(leg, 'strike', 'n/a')} expiring {getattr(leg, 'expiry', 'n/a')}"
            elif leg.asset.lower() == "equity":
                shares = getattr(self, 'shares', 'n/a')
                price = getattr(self, 'underlying_spot', 'n/a')
                price_str = f"{price:.2f}" if price != 'n/a' else 'n/a'
                desc = f"{('Long' if leg.direction == 1 else 'Short')} {shares} shares of {leg.ticker} @{price_str}"
            elif leg.asset.lower() == "bond":
                ticker = getattr(leg, 'ticker', 'Money Market')
                cash = getattr(leg, 'cash', None)
                cash_str = f"{cash:.2f}" if cash is not None else 'n/a'
                desc = f"{ticker} ${cash_str}"
            legs_desc.append(desc)
            
        return f"{self.name} ({self.strategy_id}): {', '.join(legs_desc)}"

class Single(OptionStrategy):
    """A single option leg. Expects only one line"""
    def __init__(self, leg: OptionLeg, weight: float = None, underlying_spot: float = None, base_cash: int = 1000000):
        super().__init__(strategy_id="Single", name="Single Option")
        self.add_leg(leg)
        self.weight = weight
        self.underlying_spot = underlying_spot
        if self.weight is not None:
            target_notional = self.weight * base_cash  # Default base_cash
        self.contracts = target_notional / (self.underlying_spot * self.legs[0].multiplier)
        self.contracts = int(self.contracts)  # Round down to nearest whole contract

    def notional_value(self):
        """Determine number of contracts using weight.Calculate notional value: spot * multiplier * contracts."""
        option_leg = self.legs[0]
        return self.underlying_spot * option_leg.multiplier * self.contracts

    def collateral_required(self):
        """Collateral for short options: strike * multiplier * contracts for short call/put."""
        option_leg = self.legs[0]
        if option_leg.direction == -1:
            return option_leg.strike * option_leg.multiplier * self.contracts
        return 0

    def cash_flow(self):
        """Calculate total premiums paid/received for the option leg."""
        option_leg = self.legs[0]
        return option_leg.price * self.contracts * option_leg.direction * -1 # Premiums paid are negative cash flow, received are positive cash flow

class EquityStrategy(OptionStrategy):
    """A pure equity position strategy. Determine number of shares using weight and underlying spot price."""
    def __init__(self, equity_leg: Equity, weight: float = None, underlying_spot: float = None, base_cash: int = 1000000):
        super().__init__(strategy_id="Equity", name="Equity Shares", underlying=equity_leg.ticker)
        self.add_leg(equity_leg)
        self.weight = weight
        self.underlying_spot = underlying_spot
        self.shares = (self.weight * base_cash) / self.underlying_spot if self.weight is not None else None
        self.shares = int(self.shares)  # Round down to nearest whole share

    def notional_value(self):
        """Notional value: weight * base_cash (+ allocated to shares)."""
        if self.weight:
            return self.shares * self.underlying_spot
        return 0

    def collateral_required(self):
        """Equity positions require no collateral."""
        return 0
    
    def cash_flow(self):
        """Calculate total cash flow for the equity leg."""
        equity_leg = self.legs[0]
        return self.shares * self.underlying_spot * equity_leg.direction * -1 # Buying shares is negative cash flow, selling shares is positive cash flow

class BondStrategy(OptionStrategy):
    """Residual is leftover cash at the end of allocation, in which case everything is put into money market."""
    def __init__(self, residual_leg: Residual):
        name = "Collateral" if residual_leg.ticker is None else f"{residual_leg.ticker} Cash"
        super().__init__(strategy_id="Residual", name=name)
        self.add_leg(residual_leg)

    def notional_value(self):
        """Notional value: cash amount allocated."""
        residual_leg = self.legs[0]
        if residual_leg.cash:
            return residual_leg.cash
        return 0

    def collateral_required(self):
        """Residual cash requires no collateral."""
        return 0

    def cash_flow(self):
        """Calculate total cash flow for the residual leg."""
        residual_leg = self.legs[0]
        return residual_leg.cash * -1 # Allocating cash is negative cash flow

class CoveredCall(OptionStrategy):
    """A covered call strategy expecting 1 equity leg and 1 short call leg."""
    def __init__(self, equity_leg: Equity, call_leg: OptionLeg, weight: float = None, underlying_spot: float = None, base_cash: int = 1000000):
        super().__init__(strategy_id="CC", name="Covered Call", underlying=equity_leg.ticker)
        self.add_leg(equity_leg)
        self.add_leg(call_leg)
        self.weight = weight
        self.underlying_spot = underlying_spot
        if self.weight is not None:
            target_notional = self.weight * base_cash  # Default base_cash
            self.shares = target_notional / call_leg.strike
            self.shares = int(self.shares)  # Round down to nearest whole share
            self.contracts = self.shares / call_leg.multiplier
            self.contracts = int(self.contracts)  # Round down to nearest whole contract

    def notional_value(self):
        """Notional value is the strike * multiplier * contracts."""
        call_leg = next(l for l in self.legs if isinstance(l, OptionLeg) and l.direction == -1)
        if call_leg:
            return call_leg.strike * call_leg.multiplier * self.contracts
        return 0

    def collateral_required(self):
        """Covered call has no collateral requirement (short call covered by equity)."""
        return 0
    
    def cash_flow(self):
        """Calculate total cash flow for the covered call strategy. Earn premiums from short call, pay for equity shares."""
        equity_leg = next(l for l in self.legs if isinstance(l, Equity))
        call_leg = next(l for l in self.legs if isinstance(l, OptionLeg) and l.direction == -1)
        equity_cash_flow = self.shares * self.underlying_spot * equity_leg.direction * -1 # Buying shares is negative cash flow
        call_cash_flow = call_leg.price * self.contracts * call_leg.direction * -1 # Premiums received from short call are positive cash flow
        return equity_cash_flow + call_cash_flow

class Spread(OptionStrategy):
    """A spread strategy with 2 option legs. Expects 1 long leg and 1 short leg of the same option type."""
    def __init__(self, long_leg: OptionLeg, short_leg: OptionLeg, weight: float = None, underlying_spot: float = None, base_cash: int = 1000000):
        super().__init__(strategy_id="Spread", name="Spread")
        self.add_leg(long_leg)
        self.add_leg(short_leg)
        self.spread_type = f"{long_leg.option_type.upper()} Spread"
        self.weight = weight
        self.underlying_spot = underlying_spot
        if self.weight is not None:
            target_notional = self.weight * base_cash  # Default base_cash
            self.contracts = target_notional / (self.underlying_spot * short_leg.multiplier)
            self.contracts = int(self.contracts)  # Round down to nearest whole contract

    def notional_value(self):
        """Notional value based on underlying spot price * multiplier * contracts."""
        return self.underlying_spot * self.short_leg.multiplier * self.contracts

    def collateral_required(self):
        """Collateral for spread: max_loss = |short_strike - long_strike| * multiplier."""
        long_leg = next(l for l in self.legs if l.direction == 1)
        short_leg = next(l for l in self.legs if l.direction == -1)
        strike_diff = abs(short_leg.strike - long_leg.strike)
        return strike_diff * long_leg.multiplier * self.contracts
    
    def cash_flow(self):
        """Calculate total cash flow for the spread strategy. Pay premium for long leg, receive premium for short leg."""
        long_leg = next(l for l in self.legs if l.direction == 1)
        short_leg = next(l for l in self.legs if l.direction == -1)
        long_cash_flow = long_leg.price * self.contracts * long_leg.direction * -1 # Premium paid for long leg is negative cash flow
        short_cash_flow = short_leg.price * self.contracts * short_leg.direction * -1 # Premium received from short leg is positive cash flow
        return long_cash_flow + short_cash_flow

class Strangle(OptionStrategy):
    """A strangle strategy with 1 long (short) call leg and 1 long (short) put leg."""
    def __init__(self, call_leg: OptionLeg, put_leg: OptionLeg, weight: float = None, underlying_spot: float = None, base_cash: int = 1000000):
        super().__init__(strategy_id="Strangle", name="Strangle")
        self.add_leg(call_leg)
        self.add_leg(put_leg)
        self.weight = weight
        self.underlying_spot = underlying_spot
        if self.weight is not None:
            target_notional = self.weight * base_cash  # Default base_cash
            self.contracts = target_notional / (self.underlying_spot * call_leg.multiplier)
            self.contracts = int(self.contracts)

    def notional_value(self):
        """Notional value: spot * multiplier * contracts."""         
        return self.underlying_spot * self.call_leg.multiplier * self.contracts

    def collateral_required(self):
        """Collateral for strangles: max of two strikes * multiplier * contracts."""
        collateral = 0
        call_leg = next((l for l in self.legs if l.option_type == "c"), None)
        put_leg = next((l for l in self.legs if l.option_type == "p"), None)
        collateral = max(call_leg.strike if call_leg else 0, put_leg.strike if put_leg else 0) * call_leg.multiplier * self.contracts
        return collateral

    def cash_flow(self):
        """Calculate total cash flow for the strangle strategy. Pay premiums for long legs, receive premiums for short legs."""
        call_leg = next((l for l in self.legs if l.option_type == "c"), None)
        put_leg = next((l for l in self.legs if l.option_type == "p"), None)
        call_cash_flow = call_leg.price * self.contracts * call_leg.direction * -1 if call_leg else 0
        put_cash_flow = put_leg.price * self.contracts * put_leg.direction * -1 if put_leg else 0
        return call_cash_flow + put_cash_flow
    
class Synthetic(OptionStrategy):
    """A synthetic equity position using two option legs (1 long, 1 short & 1 call, 1 put)."""
    def __init__(self, long_leg: OptionLeg, short_leg: OptionLeg, weight: float = None, underlying_spot: float = None, base_cash: int = 1000000):
        super().__init__(strategy_id="Synthetic", name="Synthetic", underlying=long_leg.underlying)
        self.add_leg(long_leg)
        self.add_leg(short_leg)
        self.weight = weight
        self.underlying_spot = underlying_spot
        if self.weight is not None:
            target_notional = self.weight * base_cash
            self.contracts = target_notional / (self.underlying_spot * long_leg.multiplier)
            self.contracts = int(self.contracts)

    def notional_value(self):
        """Notional value: spot * multiplier * contracts."""
        return self.underlying_spot * self.legs[0].multiplier * self.contracts

    def collateral_required(self):
        """Collateral for synthetic: strike * multiplier * contracts for the short leg."""
        short_leg = next((l for l in self.legs if l.direction == -1), None)
        if short_leg:
            return short_leg.strike * short_leg.multiplier * self.contracts
        return 0
    
    def cash_flow(self):
        """Calculate total cash flow for the synthetic strategy. Pay premium for long leg, receive premium for short leg."""
        long_leg = next((l for l in self.legs if l.direction == 1), None)
        short_leg = next((l for l in self.legs if l.direction == -1), None)
        long_cash_flow = long_leg.price * self.contracts * long_leg.direction * -1 if long_leg else 0
        short_cash_flow = short_leg.price * self.contracts * short_leg.direction * -1 if short_leg else 0
        return long_cash_flow + short_cash_flow

class IronCondor(OptionStrategy):
    """An iron condor strategy with 4 option legs: call spread + put spread. All with different strikes but same expiry."""
    def __init__(self, long_call: OptionLeg, short_call: OptionLeg, short_put: OptionLeg, long_put: OptionLeg, weight: float = None, underlying_spot: float = None, base_cash: int = 1000000):
        super().__init__(strategy_id="IC", name="Iron Condor")
        self.add_leg(long_call)
        self.add_leg(short_call)
        self.add_leg(short_put)
        self.add_leg(long_put)
        self.weight = weight
        self.underlying_spot = underlying_spot
        if self.weight is not None:
            target_notional = self.weight * base_cash  # Default base_cash
            self.contracts = target_notional / (self.underlying_spot * short_call.multiplier)
            self.contracts = int(self.contracts)
        
    def notional_value(self):
        """Notional value: spot * multiplier * contracts."""
        return self.underlying_spot * self.legs[0].multiplier * self.contracts

    def collateral_required(self):
        """Collateral for iron condor: max width of two spreads * multiplier * contracts."""
        calls = [l for l in self.legs if l.option_type == "call"]
        puts = [l for l in self.legs if l.option_type == "put"]
        call_width = abs(calls[0].strike - calls[1].strike) if len(calls) == 2 else 0
        put_width = abs(puts[0].strike - puts[1].strike) if len(puts) == 2 else 0
        return max(call_width, put_width) * self.legs[0].multiplier * self.contracts
    
    def cash_flow(self):
        """Calculate total cash flow for the iron condor strategy. Pay premiums for long legs, receive premiums for short legs."""
        call_legs = [l for l in self.legs if l.option_type == "call"]
        put_legs = [l for l in self.legs if l.option_type == "put"]
        call_cash_flow = sum(leg.price * self.contracts * leg.direction * -1 for leg in call_legs)
        put_cash_flow = sum(leg.price * self.contracts * leg.direction * -1 for leg in put_legs)
        return call_cash_flow + put_cash_flow

#------------------------------END OF STRATEGY BUILDING BLOCK CLASSES---------------------------------------------------------------------------------    

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
        self.strategies = []
        self.start_dt = dt.date(2025,1,1)
        self.end_dt = dt.date(2025,4,30)
        self.ticker = ticker.upper()
        self.country_code = country_code.upper()

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
        holidays_dict = dict(enumerate(self.holidays.flatten(), 1))

        # Inputs preprocessing: Ticker + Prices Time Series
        self.equity_ticker = self.ticker+" "+self.country_code+" Equity"
        self.ul_prices = closing_prices(self.ticker, self.country_code, start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))
        
        # Inputs preprocessing: Option OptionLegs Dataframe -> dictionary with selected options
        config = pd.read_csv(config_path)
        cols_lst = ['STRATEGY_ID',	'SUB_STRATEGY',	'ASSET',	'DIRECTION',	'WEIGHT',	'OPTION TYPE',	'DTM',	'MONEYNESS']
        config = config.reindex(columns=config.columns.tolist() + [c for c in cols_lst if c not in config.columns], fill_value=None)
        
        if config.empty:
            print("Warning: Configuration dataframe is empty.")

        #---------------------------------------ERROR CHECKING: VALIDATE CONFIG FILE--------------------------------------------------

        required_cols = ['STRATEGY_ID', 'SUB_STRATEGY', 'ASSET', 'DIRECTION']
        for col in required_cols:
            if col not in config.columns:
                raise ValueError(f"Configuration dataframe is missing required column: {col}")
        if not all(config['ASSET'].str.lower().isin(['option', 'equity', 'bond'])):
            raise ValueError("Configuration dataframe has invalid ASSET values; expected 'option', 'equity', or 'bond'.")
        if not all(config['DIRECTION'].isin([1, -1])):
            raise ValueError("Configuration dataframe has invalid DIRECTION values; expected 1, -1")
        if 'OPTION TYPE' in config.columns and not all(config['OPTION TYPE'].str.lower().isin(['c', 'p', None])):
            raise ValueError("Configuration dataframe has invalid OPTION TYPE values; expected 'c', 'p', or None.")
        if 'DTM' in config.columns and not all(config['DTM'].apply(lambda x: isinstance(x, (int, float)) or pd.isna(x))):
            raise ValueError("Configuration dataframe has invalid DTM values; expected numeric or NaN.")
        if 'MONEYNESS' in config.columns and not all(config['MONEYNESS'].apply(lambda x: isinstance(x, (int, float)) or pd.isna(x))):
            raise ValueError("Configuration dataframe has invalid MONEYNESS values; expected numeric or NaN.")
        if 'DTM' in config.columns and not all(config['DTM'].isin([5, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330, 360, 450, 540, 630, 720, 810, 900, 990, 1080, 1170, 1260]) | config['DTM'].isna()):
            raise ValueError("Configuration dataframe has invalid DTM values; expected 5, 30, 60, 90, 120... etc. Monthly values (multiple of 30) within a year and quarterly values (multiple of 90) up to 3 years, or NaN.")
        for sub_id, sub_df in config.groupby('SUB_STRATEGY'):
            # check that weight are all the same within the sub strategy
            if 'WEIGHT' in sub_df.columns and not sub_df['WEIGHT'].isna().all() and len(sub_df['WEIGHT'].dropna().unique()) > 1:
                raise ValueError(f"Sub-strategy {sub_id} has inconsistent weight values.")
            # check that option legs have option type, DTM, and moneyness specified
            option_legs = sub_df[sub_df['ASSET'].str.lower() == 'option']
            if not option_legs.empty:
                if option_legs['OPTION TYPE'].isna().any():
                    raise ValueError(f"Sub-strategy {sub_id} has option legs with missing OPTION TYPE.")
                if option_legs['DTM'].isna().any():
                    raise ValueError(f"Sub-strategy {sub_id} has option legs with missing DTM.")
                if option_legs['MONEYNESS'].isna().any():
                    raise ValueError(f"Sub-strategy {sub_id} has option legs with missing MONEYNESS.")
        #---------------------------------------ERROR CHECKING: VALIDATE CONFIG FILE--------------------------------------------------


        # Find nearest next Friday for legging into options: First Roll Date
        if self.start_dt.weekday() == 4: #Friday
            nearest_fri = common.workday(self.start_dt, 5)
        else:
            days_til_fri = 4 - self.start_dt.weekday()
            nearest_fri = common.workday(self.start_dt, days_til_fri)
        while nearest_fri in self.holidays:
            nearest_fri = common.workday(nearest_fri, -1)
        underlying_price_on_roll = self.ul_prices[self.ul_prices['Date'] == nearest_fri]['Close'].iloc[0]
                
        # Identify unique sub-strategies loop an`d select options for each leg based on user input parameters (DTM, moneyness)
        sub_strat_iter = config['SUB_STRATEGY'].unique() # How many sub-strategies are in the config? Iterate through each one, select options, and build strategy objects accordingly
        # for sub strategies 1, 2, ... in config:
        for sub in sub_strat_iter:
            sub_df = config[config['SUB_STRATEGY'] == sub] # filter table for the sub strategy
            sub_id = sub_df['STRATEGY_ID'].iloc[0] # find id
            weight = sub_df['WEIGHT'].iloc[0] if 'WEIGHT' in sub_df.columns else None # find weight for the sub strategy if specified, otherwise None
            # collect and initiate leg objects for all in the sub strategy
            legs = []
            for _, row in sub_df.iterrows():
                if row['ASSET'].lower() == "option":
                    leg = OptionLeg(
                        asset=row['ASSET'],
                        option_type=row['OPTION TYPE'],
                        direction=row['DIRECTION'],
                        dtm=row['DTM'],
                        moneyness=row['MONEYNESS']
                    )
                    # select expiration and strike based on DTM, moneyness, and nearest next Friday, and update leg attributes accordingly
                    # this needs to be done before strategy matching because the selected option (strike and expiry) will impact the strategy type (e.g., single leg vs spread) and collateral requirement
                    leg.select_option(self.ticker, nearest_fri, holidays_dict)
                    legs.append(leg)
                elif row['ASSET'].lower() == "equity":
                    leg = Equity(
                        asset=row['ASSET'],
                        direction=row['DIRECTION'],
                        weight=row['WEIGHT'],
                        ticker=self.ticker,
                        country=self.country_code,
                        start_dt=self.start_dt,
                        end_dt=self.end_dt
                    )
                    legs.append(leg)
                elif row['ASSET'].lower() == "bond":
                    leg = Residual(
                        asset=row['ASSET'],
                        cash=row['WEIGHT']*self.cash if row['WEIGHT'] is not None else None,
                        ticker="Money Market",
                        country=self.country_code,
                        start_dt=self.start_dt,
                        end_dt=self.end_dt
                    )
                    legs.append(leg)

            # STRATEGY MATCHING: initiate classes for each identified strategy and calculate notional value and collateral requirement for each strategy
            if sub_id == "Single":
                # Single option: expect 1 option leg
                leg = legs[0]
                strategy = Single(leg, weight=weight, underlying_spot=underlying_price_on_roll, base_cash=self.cash)
                self.strategies.append(strategy)
            
            elif sub_id == "Equity":
                # Pure equity leg: expect 1 equity leg
                leg = legs[0]
                strategy = EquityStrategy(leg, weight=weight, underlying_spot=underlying_price_on_roll, base_cash=self.cash)
                self.strategies.append(strategy)
            
            # Removing Residual leg because it won't be input as a strategy by the user; instead default last leg for remaining cash unallocated to other strategies after collateral is secured, and put it into money market as a bond strategy.
            #elif sub_id == "Residual":
                # Residual cash leg: expect 1 bond leg
                #leg = legs[0]
                #strategy = BondStrategy(leg)
                #self.strategies.append(strategy)
                
            elif sub_id == "CC":
                # Covered Call: expect 1 equity leg + 1 short call leg
                equity_leg = next(l for l in legs if isinstance(l, Equity))
                call_leg = next(l for l in legs if isinstance(l, OptionLeg) and l.option_type == "c")
                strategy = CoveredCall(equity_leg, call_leg, weight=weight, underlying_spot=underlying_price_on_roll, base_cash=self.cash)
                self.strategies.append(strategy)

            elif sub_id == "Spread":
                # Spread: expect 2 option legs (long and short) of the same option type
                long_leg = next(l for l in legs if l.direction == 1)
                short_leg = next(l for l in legs if l.direction == -1)
                strategy = Spread(long_leg, short_leg, weight=weight, underlying_spot=underlying_price_on_roll, base_cash=self.cash)
                self.strategies.append(strategy)

            elif sub_id == "Strangle":
                # Strangle: expect 2 option legs (1 call, 1 put)
                call_leg = next(l for l in legs if l.option_type == "c")
                put_leg = next(l for l in legs if l.option_type == "p")
                strategy = Strangle(call_leg, put_leg, weight=weight, underlying_spot=underlying_price_on_roll, base_cash=self.cash)
                self.strategies.append(strategy)

            elif sub_id == "Synthetic":
                # Synthetic: expect 2 options legs (1 long, 1 short)
                long_leg = next(l for l in legs if l.direction == 1)
                short_leg = next(l for l in legs if l.direction == -1)
                strategy = Synthetic(long_leg, short_leg, weight=weight, underlying_spot=underlying_price_on_roll, base_cash=self.cash)
                self.strategies.append(strategy)

            elif sub_id == "IC":
                # Iron Condor: expect 4 option legs (a put spread and a call spread), identify by different strikes but same expiry
                long_call = next(l for l in legs if l.option_type == "c" and l.direction == 1)
                short_call = next(l for l in legs if l.option_type == "c" and l.direction == -1)
                short_put = next(l for l in legs if l.option_type == "p" and l.direction == -1)
                long_put = next(l for l in legs if l.option_type == "p" and l.direction == 1)
                strategy = IronCondor(long_call, short_call, short_put, long_put, weight=weight, underlying_spot=underlying_price_on_roll, base_cash=self.cash)
                self.strategies.append(strategy)

        # Calculate Total Allocation Cash flow (Paid/Earned Premiums and long shares paid)
        self.net_cash_spend = sum(strategy.cash_flow() for strategy in self.strategies)
        # Also Secure collateral cash for every strategy: amount is held and sits in money market
        self.bond_cash = sum(strategy.collateral_required() for strategy in self.strategies if strategy.collateral_required() > 0)

        # Scale down allocations proportionally if overallocation (total cash allocated exceeds available cash)
        self.residual_cash = self.cash + self.net_cash_spend - self.bond_cash
        self.scale_if_overallocated()

        # Add collateral as a separate cash position
        if self.bond_cash > 0:
            collateral_leg = Residual(asset="bond", cash=self.bond_cash, ticker="Collateral", country=self.country_code, start_dt=self.start_dt, end_dt=self.end_dt)
            collateral_strategy = BondStrategy(collateral_leg)
            self.strategies.append(collateral_strategy)

        # Residual cash leg: remaining cash in money market if there is leftover after allocating to other legs.
        leftover = self.cash + self.net_cash_spend - self.bond_cash
        if leftover > 0:
            residual_cash = leftover
            residual_leg = Residual(asset="bond", cash=residual_cash, ticker="Money Market", country=self.country_code, start_dt=self.start_dt, end_dt=self.end_dt)
            residual_strategy = BondStrategy(residual_leg)
            self.strategies.append(residual_strategy)
            
    def scale_if_overallocated(self):
        """ If total cash allocated exceeds available cash, scale down contracts/shares proportionally. """
        if self.residual_cash < 0:
            total_allocated = -1*self.net_cash_spend + self.bond_cash
            print(f"Overallocation detected: Total Allocated (${total_allocated:.2f}) exceeds Available Cash (${self.cash:.2f}). Scaling down allocations proportionally.")
            scale_factor = self.cash / total_allocated
            for strategy in self.strategies:
                if isinstance(strategy, Single):
                    strategy.contracts = int(strategy.contracts * scale_factor)
                    # Update weight proportionally
                    if strategy.weight is not None:
                        strategy.weight *= scale_factor
                elif isinstance(strategy, EquityStrategy):
                    strategy.shares = int(strategy.shares * scale_factor)
                    # Update weight proportionally
                    if strategy.weight is not None:
                        strategy.weight *= scale_factor
                elif isinstance(strategy, CoveredCall):
                    strategy.shares = int(strategy.shares * scale_factor)
                    strategy.contracts = int(strategy.contracts * scale_factor)
                    # Update weight proportionally
                    if strategy.weight is not None:
                        strategy.weight *= scale_factor
                elif isinstance(strategy, Spread):
                    strategy.contracts = int(strategy.contracts * scale_factor)
                    # Update weight proportionally
                    if strategy.weight is not None:
                        strategy.weight *= scale_factor
                elif isinstance(strategy, Strangle):
                    strategy.contracts = int(strategy.contracts * scale_factor)
                    # Update weight proportionally
                    if strategy.weight is not None:
                        strategy.weight *= scale_factor
                elif isinstance(strategy, Synthetic):
                    strategy.contracts = int(strategy.contracts * scale_factor)
                    # Update weight proportionally
                    if strategy.weight is not None:
                        strategy.weight *= scale_factor
                elif isinstance(strategy, IronCondor):
                    strategy.contracts = int(strategy.contracts * scale_factor)
                    # Update weight proportionally
                    if strategy.weight is not None:
                        strategy.weight *= scale_factor
            # Recalculate net cash spend, bond cash, and residual cash after scaling
            self.net_cash_spend = sum(strategy.cash_flow() for strategy in self.strategies)
            self.bond_cash = sum(strategy.collateral_required() for strategy in self.strategies if strategy.collateral_required() > 0)
            leftover = self.cash + self.net_cash_spend - self.bond_cash
            self.residual_cash = leftover
            print(f"Scaling complete. New Total Allocated: ${-1*self.net_cash_spend + self.bond_cash:.2f}, New Residual Cash: ${self.residual_cash:.2f}")

    def __str__(self):
        strategy_descriptions = [str(strategy) for strategy in self.strategies]
        return f"Portfolio Composition:\n" + "\n".join(strategy_descriptions) + f"\n\nNet Cash Flow on Allocation: ${-1*self.net_cash_spend:.2f}\n" + f"Total Collateral Held: ${self.bond_cash:.2f}\n" + f"Residual Cash in Money Market: ${self.residual_cash:.2f}"
    

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

    # Initialize Portfolio
    portfolio = Portfolio(config_path, ticker, country_code, start_dt, end_dt, base_cash)

    # Output portfolio composition for user review
    print(f"\nStarting Cash Balance: ${base_cash}\n")
    print(portfolio)

    # total allocation check
    print(f"\nTotal Cash Allocated (Cash Flow + Collateral + Residual): ${-1*portfolio.net_cash_spend + portfolio.bond_cash + portfolio.residual_cash:.2f}")
    
    # Popup Screen: Ask user to confirm the portfolio in order to proceed with the backtest
    proceed = input("\nIs this portfolio correct? (y/n):")
    if proceed.lower() != 'y':
        print("Please review and update the configuration file, then re-run the script.")
    else:
        print("Portfolio confirmed. Proceeding with backtest...")