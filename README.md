# Options Backtester
Interface for backtesting dynamic option portfolios.

## User Interface : Inputs
1. Start Date & End Date: Time range for backtest
2. Portfolio file: csv file path for option legs.
3. Underlying Asset Ticker + Country Code
<img width="401" height="332" alt="image" src="https://github.com/user-attachments/assets/8a4ae94b-0668-47f9-a807-8ce12bc0fc25" />

## Option Set Configuration
Set of option legs defined in a csv file, read in step 2 from above.
1. SEC_ID: "option"
2. TYPE: "call" | "put"
3. POS: "long" | "short"
4. DTM: int
5. MONEYNESS: float
6. RATIO: float
7. SECURED: bool
Instead of using user-defined quantities, the backtester:
* first parses through all option legs and matches same expiry date options to determine dependencies (put/call spreads)
* defines needed shares and cash reserve for each option
* then allocates default cash amount of 1000000 (unless defined otherwise) based on constraints 

## Allocation


## Backtest


## Outputs
