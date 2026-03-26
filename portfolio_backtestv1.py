from allcoate_port import Equity, Leg, Portfolio
import datetime as dt
import pandas as pd
import yfinance as yf
import json
import os
from collections import defaultdict
cur_dir = os.path.dirname(__file__)
import sys
import copy
sys.path.append('Z:\\ApolloGX')
if "\\im_dev\\" in cur_dir:
    import im_dev.std_lib.common as common
else:
    import im_prod.std_lib.common as common
    

def backtest(portfolio: Portfolio):
    
    
    
    return