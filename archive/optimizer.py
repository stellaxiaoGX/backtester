import numpy as np
import pandas as pd
import linprog

# Allocation Optimizer

def optimize_positions(self, liquid_buffer:float=0.05):
    """
    Linear Program to find optimized initial starting positions for all share and option allocations 
    """
    cash = self.cash
    df = self.init_portfolio
    ul_price = df.loc['underlying', 'PRICE']
    spending_per_share = ul_price
    for option in self.options:
        spending_per_share -= option.coverage*option.option_mid
            
    # Example: Allocate cash to maximize shares bought while meeting liquidity buffer limit
    # Maximize: X (shares)
    # Subject to:
    #   (price_per_share + 50%*call_price - 50%*put_price)X <= 950000
    #   X >= 0
    
    c = [1]
    c = np.array(c, dtype=float)
    A_ub = [[(spending_per_share)]] # Spending equation for every share, need to include every option in the portfolio
    b_ub = [cash*(1-liquid_buffer)]
    bounds = [(0, None)]

    # linprog minimizes, so we negate c to maximize
    result = linprog(-c, A_ub=A_ub, b_ub=b_ub, A_eq=None, b_eq=None, bounds=bounds, method='highs')
    
    print(result)
    if result.success:
        return {
            "status": "Optimal solution found",
            "optimal_value": -result.fun,  # Negate back to get max value
            "allocations": result.x
        }
    else:
        return {
            "status": "Optimization failed",
            "message": result.message
        }