import os
import datetime as dt
import csv
try:
    import pandas as pd
except ImportError:
    pd = None
try:
    import yfinance as yf
except ImportError:
    yf = None
cur_dir = os.path.dirname(__file__)
import sys
sys.path.append('Z:\\ApolloGX')
common = None
if "\\im_dev\\" in cur_dir:
    try:
        import im_dev.std_lib.common as common
    except Exception:
        common = None
else:
    try:
        import im_prod.std_lib.common as common
    except Exception:
        common = None

"""
    Class-based allocation script using working/building_blocks.csv and config.csv example.
    Supports config.csv file format and identifies option strategies from the lookups in working/building_blocks.csv.
    Building Blocks:
        1. Equity: Long | Short {ticker}
        2. Residal: Long {bond}
        3. Options:
            - Single Leg: Long | Short , Call | Put
            - Covered Call: Long Equity + Short Call
            - Synthetic: : Long | Short + Call | Put
            - Strangle: Long | Short, Call + Put
            - IC: Long + Short, Call + Put
            - Spread: Bull | Bear, Call | Put
"""

class OptionLeg:
    """
    General option leg.

    Inputs:
    - asset: "option"
    - option_type: "call" | "put"
    - direction: 1 | -1 (long or short position)
    - dtm: days to maturity (e.g., 30 for monthly options)
    - moneyness: percentage away from the money (e.g., 1.05 for 5% OTM call, 0.95 for 5% OTM put)

    Other variables:
    - price: option premium per share
    - strike: float 
    - expiry: "YYYY-MM-DD"
    - multiplier: 100 (by default, standard contract multiplier)

    """
    def __init__(self,
                 asset="option",
                 option_type=None,
                 direction=None,
                 dtm=5,
                 moneyness=0.0,
                 price=0.0,
                 strike=None,
                 expiry=None,
                 multiplier=100):
        
        self.asset = asset.lower()
        self.option_type = option_type.lower() if option_type else None
        self.direction = direction
        self.dtm = int(dtm)
        self.moneyness = float(moneyness)
        self.price = float(price)
        self.strike = float(strike) if strike is not None else None
        self.expiry = expiry
        self.multiplier = int(multiplier)
        
        self.current = None

        if self.option_type not in ["call", "put"]:
            raise ValueError(f"Option leg missing/invalid option_type: {self.__dict__}")
        if self.expiry is None:
            raise ValueError(f"Option leg must have expiry: {self.__dict__}")
        if self.direction not in [1, -1]:
            raise ValueError(f"Invalid direction: {self.direction}; expected 1 (long) or -1 (short)")

    def __str__(self):
        direction_str = "Long" if self.direction == 1 else "Short"
        strike_str = f" @ {self.strike}" if self.strike else ""
        expiry_str = f" exp {self.expiry}" if self.expiry else ""
        return f"{direction_str} {self.option_type.capitalize()}{strike_str}{expiry_str}"

class EquityLeg:
    def __init__(self, quantity=1, ticker=None, start_dt=None, end_dt=None, country_code=None):
        self.quantity = int(quantity)
        self.ticker = ticker
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.country_code = country_code
        self.price_data = None
        self.current_price = None
    
    def fetch_pricing_data(self):
        """Fetch pricing data from yfinance for the given ticker and date range."""
        if not self.ticker or yf is None:
            return None
        try:
            data = yf.download(self.ticker, start=self.start_dt, end=self.end_dt, progress=False)
            self.price_data = data
            if len(data) > 0:
                self.current_price = data['Close'].iloc[-1]
            return data
        except Exception as e:
            print(f"Error fetching pricing for {self.ticker}: {e}")
            return None
    
    def get_current_price(self):
        """Get current or latest price."""
        if self.current_price is None:
            self.fetch_pricing_data()
        return self.current_price
    
    def __str__(self):
        price_str = f" @ {self.current_price}" if self.current_price else ""
        return f"Equity {self.quantity}x {self.ticker}{price_str}"


class BondLeg:
    def __init__(self, quantity=1, start_dt=None, end_dt=None, country_code=None):
        self.quantity = int(quantity)
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.country_code = country_code or "US"
        self.rates_data = None
        self.average_rate = None
    
    def fetch_interest_rates(self, base_path="interest rates"):
        """Fetch interest rates from CSV files based on country code and date range."""
        country_map = {
            "CN": "canrates.csv",
            "US": "usrates.csv",
            "CA": "canrates.csv"
        }
        
        filename = country_map.get(self.country_code.upper(), "usrates.csv")
        file_path = os.path.join(base_path, filename)
        
        if not os.path.exists(file_path):
            print(f"Rate file not found: {file_path}")
            return None
        
        try:
            rates = []
            with open(file_path, newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    try:
                        row_date = dt.datetime.strptime(row['date'], '%Y-%m-%d').date()
                        if self.start_dt and row_date < self.start_dt:
                            continue
                        if self.end_dt and row_date > self.end_dt:
                            continue
                        rate = float(row['rate'])
                        rates.append({'date': row_date, 'rate': rate})
                    except (ValueError, KeyError):
                        continue
            
            self.rates_data = rates
            if rates:
                self.average_rate = sum(r['rate'] for r in rates) / len(rates)
            return rates
        except Exception as e:
            print(f"Error reading rates from {file_path}: {e}")
            return None
    
    def get_average_rate(self):
        """Get average interest rate for the period."""
        if self.average_rate is None:
            self.fetch_interest_rates()
        return self.average_rate
    
    def __str__(self):
        rate_str = f" @ {self.average_rate}%" if self.average_rate else ""
        return f"Bond {self.quantity}x {self.country_code}{rate_str}"




#------------------------------BUILDING BLOCKS---------------------------------------------------------------------------------

class OptionStrategy:
    def __init__(self, strategy_id, name=None, description="", underlying=None):
        self.strategy_id = strategy_id
        self.name = name or strategy_id
        self.description = description
        self.underlying = underlying
        self.legs = []

    def add_leg(self, leg: OptionLeg):
        self.legs.append(leg)

    def total_quantity(self):
        return sum((leg.quantity if hasattr(leg, "quantity") else 1) for leg in self.legs)

    def __str__(self):
        legs_desc = ", ".join(str(leg) for leg in self.legs)
        return f"{self.strategy_id} ({self.name}) -> {legs_desc}"


class SingleOptionStrategy(OptionStrategy):
    def __init__(self, direction, option_type, quantity=1, strike=None, expiry=None, underlying=None):
        direction_val = 1 if str(direction).lower() in ("1", "+1", "long") else -1
        super().__init__(strategy_id="Single", name=f"{direction.capitalize()} {option_type.capitalize()}", underlying=underlying)
        dtm = self._extract_dtm(expiry)
        self.add_leg(OptionLeg(direction=direction_val, option_type=option_type.lower(), strike=strike, expiry=expiry, dtm=dtm))
    
    def _extract_dtm(self, expiry):
        if isinstance(expiry, str) and 'd' in expiry.lower():
            return int(expiry.lower().replace('d', ''))
        return 30  # default


class CoveredCallStrategy(OptionStrategy):
    def __init__(self, underlying, equity_qty=1, call_qty=1, strike=None, expiry=None, start_dt=None, end_dt=None, country_code=None):
        super().__init__(strategy_id="CC", name="Covered Call", underlying=underlying)
        self.add_leg(EquityLeg(quantity=equity_qty, ticker=underlying, start_dt=start_dt, end_dt=end_dt, country_code=country_code))
        dtm = self._extract_dtm(expiry)
        self.add_leg(OptionLeg(direction=-1, option_type="call", strike=strike, expiry=expiry, dtm=dtm))
    
    def _extract_dtm(self, expiry):
        if isinstance(expiry, str) and 'd' in expiry.lower():
            return int(expiry.lower().replace('d', ''))
        return 30  # default


class StrangleStrategy(OptionStrategy):
    def __init__(self, underlying, call_qty=1, put_qty=1, call_strike=None, put_strike=None, expiry=None, start_dt=None, end_dt=None, country_code=None):
        super().__init__(strategy_id="Strangle", name="Strangle", underlying=underlying)
        dtm = self._extract_dtm(expiry)
        self.add_leg(OptionLeg(direction=1, option_type="call", strike=call_strike, expiry=expiry, dtm=dtm))
        self.add_leg(OptionLeg(direction=1, option_type="put", strike=put_strike, expiry=expiry, dtm=dtm))
    
    def _extract_dtm(self, expiry):
        if isinstance(expiry, str) and 'd' in expiry.lower():
            return int(expiry.lower().replace('d', ''))
        return 30  # default


class SyntheticStrategy(OptionStrategy):
    def __init__(self, underlying, direction="Long", quantity=1, strike=None, expiry=None, start_dt=None, end_dt=None, country_code=None):
        direction_val = 1 if str(direction).lower() in ("1", "+1", "long") else -1
        super().__init__(strategy_id="Synthetic", name=f"Synthetic {direction}", underlying=underlying)
        self.add_leg(EquityLeg(quantity=quantity, ticker=underlying, start_dt=start_dt, end_dt=end_dt, country_code=country_code))
        dtm = self._extract_dtm(expiry)
        self.add_leg(OptionLeg(direction=direction_val, option_type="put", strike=strike, expiry=expiry, dtm=dtm))
    
    def _extract_dtm(self, expiry):
        if isinstance(expiry, str) and 'd' in expiry.lower():
            return int(expiry.lower().replace('d', ''))
        return 30  # default


class IronCondorStrategy(OptionStrategy):
    def __init__(self, underlying, long_call_strike=None, short_call_strike=None, short_put_strike=None, long_put_strike=None, expiry=None, start_dt=None, end_dt=None, country_code=None):
        super().__init__(strategy_id="IC", name="Iron Condor", underlying=underlying)
        dtm = self._extract_dtm(expiry)
        self.add_leg(OptionLeg(direction=1, option_type="call", strike=long_call_strike, expiry=expiry, dtm=dtm))
        self.add_leg(OptionLeg(direction=-1, option_type="call", strike=short_call_strike, expiry=expiry, dtm=dtm))
        self.add_leg(OptionLeg(direction=-1, option_type="put", strike=short_put_strike, expiry=expiry, dtm=dtm))
        self.add_leg(OptionLeg(direction=1, option_type="put", strike=long_put_strike, expiry=expiry, dtm=dtm))
    
    def _extract_dtm(self, expiry):
        if isinstance(expiry, str) and 'd' in expiry.lower():
            return int(expiry.lower().replace('d', ''))
        return 30  # default


class SpreadStrategy(OptionStrategy):
    def __init__(self, underlying, direction="Bull", option_type="Call", long_strike=None, short_strike=None, expiry=None, start_dt=None, end_dt=None, country_code=None):
        super().__init__(strategy_id="Spread", name=f"{direction} {option_type} Spread", underlying=underlying)
        dtm = self._extract_dtm(expiry)
        if direction.lower() == "bull":
            self.add_leg(OptionLeg(direction=1, option_type=option_type.lower(), strike=long_strike, expiry=expiry, dtm=dtm))
            self.add_leg(OptionLeg(direction=-1, option_type=option_type.lower(), strike=short_strike, expiry=expiry, dtm=dtm))
        else:
            self.add_leg(OptionLeg(direction=-1, option_type=option_type.lower(), strike=long_strike, expiry=expiry, dtm=dtm))
            self.add_leg(OptionLeg(direction=1, option_type=option_type.lower(), strike=short_strike, expiry=expiry, dtm=dtm))
    
    def _extract_dtm(self, expiry):
        if isinstance(expiry, str) and 'd' in expiry.lower():
            return int(expiry.lower().replace('d', ''))
        return 30  # default

#------------------------------BUILDING BLOCKS---------------------------------------------------------------------------------




class StrategyFactory:
    def __init__(
        self,
        default_cash=1000000,
        ticker="XIU",
        country_code="CN",
        start_dt=dt.date(2025, 1, 1),
        end_dt=dt.date(2025, 4, 30),
    ):
        self.default_cash = default_cash
        self.ticker = ticker
        self.country_code = country_code
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.blocks = []  # no external building blocks CSV dependency

    def get_strategy_template(self, strategy_id):
        strategy_id_upper = str(strategy_id).strip().upper()
        if strategy_id_upper == "CC":
            return ["Equity", "Short Call"]
        if strategy_id_upper == "STRANGLE":
            return ["Long Call", "Long Put"]
        if strategy_id_upper == "SYNTHETIC":
            return ["Equity", "Long/Short Put"]
        if strategy_id_upper == "IC":
            return ["Long Call", "Short Call", "Short Put", "Long Put"]
        if strategy_id_upper == "SPREAD":
            return ["Long Call/Put", "Short Call/Put"]
        if strategy_id_upper == "SINGLE" or strategy_id_upper == "SINGLE LEG":
            return ["Long/Short Call/Put"]
        return ["Generic"]

    def match_option_strategies(self, config_csv_path):
        with open(config_csv_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = [r for r in reader]

        groups = {}
        for row in rows:
            strategy_id = str(row.get("STRATEGY ID", "")).strip()
            sub_strategy = str(row.get("SUB STRATEGY", "")).strip()
            key = (strategy_id, sub_strategy)
            groups.setdefault(key, []).append(row)

        strategies = []
        dependency_rows = []

        for (strategy_id, sub_strategy), group in groups.items():
            strategy_id = str(strategy_id).strip()
            sub_strategy = str(sub_strategy).strip()
            strategy = None

            if strategy_id.upper() == "CC":
                equities = [r for r in group if str(r.get("ASSET", "")).strip().lower() == "equity"]
                options = [r for r in group if str(r.get("ASSET", "")).strip().lower() == "option"]
                eq_qty = int(str(equities[0].get("WEIGHT", "1")).replace("%", "")) if equities else 1
                call_rows = [r for r in options if str(r.get("OPTION TYPE", "")).strip().upper() == "C"]
                call_row = call_rows[0] if call_rows else {}
                call_qty = 1
                strike = None
                expiry = None
                if call_row and str(call_row.get("DTM", "")).strip().isdigit():
                    expiry = f"{int(float(call_row['DTM']))}d"
                strategy = CoveredCallStrategy(
                    underlying=self.ticker,
                    equity_qty=eq_qty,
                    call_qty=call_qty,
                    strike=strike,
                    expiry=expiry,
                    start_dt=self.start_dt,
                    end_dt=self.end_dt,
                    country_code=self.country_code,
                )

            elif strategy_id.upper() == "STRANGLE":
                call_leg = next((r for r in group if str(r.get("OPTION TYPE", "")).strip().upper() == "C"), None)
                put_leg = next((r for r in group if str(r.get("OPTION TYPE", "")).strip().upper() == "P"), None)
                strategy = StrangleStrategy(
                    underlying=self.ticker,
                    call_qty=int(str(call_leg.get("WEIGHT", "1")).replace("%", "")) if call_leg else 1,
                    put_qty=int(str(put_leg.get("WEIGHT", "1")).replace("%", "")) if put_leg else 1,
                    call_strike=float(str(call_leg.get("MONEYNESS", "")).replace("%", "")) if call_leg and str(call_leg.get("MONEYNESS", "")).strip() != "" else None,
                    put_strike=float(str(put_leg.get("MONEYNESS", "")).replace("%", "")) if put_leg and str(put_leg.get("MONEYNESS", "")).strip() != "" else None,
                    expiry=f"{int(float(call_leg['DTM']))}d" if call_leg and str(call_leg.get("DTM", "")).strip().replace('.','',1).isdigit() else None,
                    start_dt=self.start_dt,
                    end_dt=self.end_dt,
                    country_code=self.country_code,
                )

            elif strategy_id.upper() == "SYNTHETIC":
                call_leg = next((r for r in group if str(r.get("OPTION TYPE", "")).strip().upper() == "C"), None)
                put_leg = next((r for r in group if str(r.get("OPTION TYPE", "")).strip().upper() == "P"), None)
                direction = "Long"
                if put_leg and str(put_leg.get("DIRECTION", "")).strip().lower() in ("-1", "short"):
                    direction = "Short"
                strike = float(str(put_leg.get("MONEYNESS", "")).replace("%", "")) if put_leg and str(put_leg.get("MONEYNESS", "")).strip() != "" else None
                expiry = f"{int(float(put_leg['DTM']))}d" if put_leg and str(put_leg.get("DTM", "")).strip().replace('.','',1).isdigit() else None
                strategy = SyntheticStrategy(
                    underlying=self.ticker,
                    direction=direction,
                    quantity=1,
                    strike=strike,
                    expiry=expiry,
                    start_dt=self.start_dt,
                    end_dt=self.end_dt,
                    country_code=self.country_code,
                )

            elif strategy_id.upper() == "IC":
                call_legs = [r for r in group if str(r.get("OPTION TYPE", "")).strip().upper() == "C"]
                put_legs = [r for r in group if str(r.get("OPTION TYPE", "")).strip().upper() == "P"]
                long_call = next((r for r in call_legs if str(r.get("DIRECTION", "")).strip().lower() in ("1", "+1", "long")), None)
                short_call = next((r for r in call_legs if str(r.get("DIRECTION", "")).strip().lower() in ("-1", "short")), None)
                short_put = next((r for r in put_legs if str(r.get("DIRECTION", "")).strip().lower() in ("-1", "short")), None)
                long_put = next((r for r in put_legs if str(r.get("DIRECTION", "")).strip().lower() in ("1", "+1", "long")), None)
                expiry = f"{int(float(long_call['DTM']))}d" if long_call and str(long_call.get("DTM", "")).strip().replace('.','',1).isdigit() else None
                strategy = IronCondorStrategy(
                    underlying=self.ticker,
                    long_call_strike=float(str(long_call.get("MONEYNESS", "")).replace("%", "")) if long_call and str(long_call.get("MONEYNESS", "")).strip() != "" else None,
                    short_call_strike=float(str(short_call.get("MONEYNESS", "")).replace("%", "")) if short_call and str(short_call.get("MONEYNESS", "")).strip() != "" else None,
                    short_put_strike=float(str(short_put.get("MONEYNESS", "")).replace("%", "")) if short_put and str(short_put.get("MONEYNESS", "")).strip() != "" else None,
                    long_put_strike=float(str(long_put.get("MONEYNESS", "")).replace("%", "")) if long_put and str(long_put.get("MONEYNESS", "")).strip() != "" else None,
                    expiry=expiry,
                )

            elif strategy_id.upper() == "SPREAD":
                call_legs = [r for r in group if str(r.get("OPTION TYPE", "")).strip().upper() == "C"]
                put_legs = [r for r in group if str(r.get("OPTION TYPE", "")).strip().upper() == "P"]
                option_type = "Call" if call_legs else "Put"
                legs = call_legs if call_legs else put_legs
                long_leg = next((r for r in legs if str(r.get("DIRECTION", "")).strip().lower() in ("1", "+1", "long")), legs[0] if legs else None)
                short_leg = next((r for r in legs if str(r.get("DIRECTION", "")).strip().lower() in ("-1", "short")), legs[-1] if len(legs) > 1 else None)
                direction = "Bull"
                if long_leg and short_leg:
                    long_strike = float(str(long_leg.get("MONEYNESS", "")).replace("%", "")) if str(long_leg.get("MONEYNESS", "")).strip() != "" else None
                    short_strike = float(str(short_leg.get("MONEYNESS", "")).replace("%", "")) if str(short_leg.get("MONEYNESS", "")).strip() != "" else None
                    if long_strike and short_strike and long_strike > short_strike:
                        direction = "Bear"
                expiry = f"{int(float(long_leg['DTM']))}d" if long_leg and str(long_leg.get("DTM", "")).strip().replace('.','',1).isdigit() else None
                strategy = SpreadStrategy(
                    underlying=self.ticker,
                    direction=direction,
                    option_type=option_type,
                    long_strike=float(str(long_leg.get("MONEYNESS", "")).replace("%", "")) if long_leg and str(long_leg.get("MONEYNESS", "")).strip() != "" else None,
                    short_strike=float(str(short_leg.get("MONEYNESS", "")).replace("%", "")) if short_leg and str(short_leg.get("MONEYNESS", "")).strip() != "" else None,
                    expiry=expiry,
                )

            else:
                strategy = OptionStrategy(strategy_id=strategy_id, name=f"{strategy_id} - {sub_strategy}", underlying=self.ticker)
                for row in group:
                    asset = str(row.get("ASSET", "")).strip().lower()
                    if asset == "equity":
                        strategy.add_leg(EquityLeg(quantity=1, ticker=self.ticker, start_dt=self.start_dt, end_dt=self.end_dt, country_code=self.country_code))
                    elif asset == "bond":
                        strategy.add_leg(BondLeg(quantity=1, start_dt=self.start_dt, end_dt=self.end_dt, country_code=self.country_code))
                    elif asset == "option":
                        direction = row.get("DIRECTION", 1)
                        direction_val = 1 if str(direction).lower() in ("1", "+1", "long") else -1
                        option_type = row.get("OPTION TYPE", "C").lower()
                        strike = row.get("MONEYNESS", None)
                        expiry = None
                        if str(row.get("DTM", "")).strip().replace('.','',1).isdigit():
                            expiry = f"{int(float(row['DTM']))}d"
                        strategy.add_leg(
                            OptionLeg(
                                direction=direction_val,
                                option_type=option_type,
                                strike=float(str(strike).replace("%", "")) if strike is not None and str(strike).strip() != "" else None,
                                expiry=expiry,
                            )
                        )

            strategies.append(strategy)

            for row in group:
                dep = dict(row)
                dep["MATCHED_STRATEGY_ID"] = strategy.strategy_id
                dep["MATCHED_STRATEGY_NAME"] = strategy.name
                dep["MATCHED_SUB_STRATEGY"] = sub_strategy
                dependency_rows.append(dep)

        if pd is not None:
            dependencies_df = pd.DataFrame(dependency_rows)
        else:
            dependencies_df = dependency_rows

        return strategies, dependencies_df

    def load_portfolio_config(self, config_csv_path):
        strategies, _ = self.match_option_strategies(config_csv_path)
        return strategies

    def build_single_option(self, direction, option_type, quantity=1, strike=None, expiry=None):
        direction_val = 1 if str(direction).lower() in ("1", "+1", "long") else -1
        return OptionLeg(direction=direction_val, option_type=option_type.lower(), strike=strike, expiry=expiry)
   
if __name__ == "__main__":
    
    #----------INPUTS FROM USER INTERFACE & DEFAULT CASH------------
    DEFAULT_CASH = 1000000
    ticker = "XIU"
    country_code = "CN"
    start_dt = dt.date(2025, 1, 1)
    end_dt = dt.date(2025, 4, 30)
    #---------------------------------------------------------------
    
    # EXAMPLE MAIN
    strategies = StrategyFactory(default_cash=DEFAULT_CASH, ticker=ticker, country_code=country_code, start_dt=start_dt, end_dt=end_dt)
    config = strategies.load_portfolio_config(os.path.join("portfolio_config", "config.csv"))

    for strategy in config:
        print(strategy)
        
        
        