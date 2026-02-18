class Option():
    def __init__(self):
        self.ticker = None
        self.put_call = "call"

class Stock():
    def __init__(self):
        self.ticker = None

class Cash():
    def __init__(self):
        self.position = 0
        self.currency = "CAD"

class Portfolio():
    def __init__(self):
        self.holdings = []
        self.positions = []
    
class Backtest():
    def __init__(self, portfolio):
        self.portfolio = portfolio
        return
        
        
    def run(self):
        return