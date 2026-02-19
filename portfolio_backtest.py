class Option():
    def __init__(self, p_c, underly, cur, alloc, DTM, moneyness):
        self.ticker = underly
        self.put_call = p_c
        self.currency = cur
        self.alloc = alloc
        self.dtm = DTM
        self.mnyness = moneyness

class Stock():
    def __init__(self, ticker, cur):
        self.ticker = ticker
        self.currency = cur

class Cash():
    def __init__(self, pos, cur):
        self.position = pos
        self.currency = cur

class Portfolio():
    def __init__(self, starting, underlying, cur):
        self.underlying = Stock(underlying, cur)
        self.cash = Cash(starting, cur)
        return

    def run_backtest(self):
        return