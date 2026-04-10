# Options Backtester
The main objective is to let the user be able to define the time period, underlying equity, and dynamic options portfolio to run for a backtest.

# How to Use
## 1. Inputs
1. Start Date & End Date: Time range for backtest
2. Portfolio file: csv file path for option legs.
3. Underlying Asset Ticker + Country Code
<img width="401" height="332" alt="image" src="https://github.com/user-attachments/assets/8a4ae94b-0668-47f9-a807-8ce12bc0fc25" />

### Option Blocks Overview: How to Set up Configuration csv file
There are a list of building blocks defined to set up a portfolio. You must use these identifiers to make up the portfolio and get your desired position legs.

### Supported `STRATEGY_ID` values and what they mean:

- `Single` — a single option leg (long or short) with one contract type.
- `Equity` — a pure equity position leg, used to buy or sell shares.
- `CC` — covered call: one equity leg plus one short call option leg.
- `Spread` — a two-leg option spread with one long and one short option of the same type.
- `Strangle` — two option legs: one call and one put.
- `Synthetic` — a synthetic equity position built from one long and one short option.
- `IC` — iron condor: four option legs representing a call spread and a put spread.

- (Special Case)`Residual` — a cash/bond residual leg for collateral or leftover cash (handled internally).

### Supported config columns

| Column | Meaning | Notes |
|---|---|---|
| `STRATEGY_ID` | Strategy identifier used by the backtester | Selects the strategy class |
| `SUB_STRATEGY` | Group identifier for rows that belong together | All rows with the same sub-strategy are built into one strategy object |
| `ASSET` | Asset type | `option`, `equity`, or `bond` |
| `DIRECTION` | Trade side | `1` = long, `-1` = short |
| `WEIGHT` | Relative portfolio allocation | Used to size the position from available cash |
| `OPTION TYPE` | Option type | `c` for call, `p` for put; required for option legs |
| `DTM` | Days to maturity | Used to choose which expiry date to select. Valid values are typically `5`, `30`, `60`, `90`, etc. |
| `MONEYNESS` | Moneyness ratio | Underlying price × moneyness gives the target strike |

### How config is interpreted:

- The backtester groups rows by `SUB_STRATEGY`.
- Each group is assigned one `STRATEGY_ID` strategy type.
- Option legs must include `OPTION TYPE`, `DTM`, and `MONEYNESS`.
- Equity legs use `WEIGHT` and the current underlying price to size shares.
- The `Residual` leg is allocated using all remaining cash after the portfolio has sized option, equity, and collateral requirements.


## 2. Portfolio Allocation Preview
This step prompts a check to the user to ensure that the portfolio, dependencies, and collaterals initiated by the backtester is correct before starting to backtest.


## 3. Backtest


### Outputs
