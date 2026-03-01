from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils

class BreakoutATR(Strategy):
    def hyperparameters(self):
        return [
            {'name': 'lookback', 'type': int, 'min': 12, 'max': 48, 'default': 24},
            {'name': 'atrp', 'type': int, 'min': 7, 'max': 21, 'default': 14},
            {'name': 'k', 'type': float, 'min': 0.8, 'max': 2.0, 'default': 1.2},
            {'name': 'risk', 'type': float, 'min': 0.01, 'max': 0.03, 'default': 0.02},
        ]

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atrp'])

    @property
    def hh(self):
        return ta.highest(self.high, self.hp['lookback'])

    @property
    def ll(self):
        return ta.lowest(self.low, self.hp['lookback'])

    def should_long(self):
        return self.price > self.hh

    def should_short(self):
        return self.price < self.ll

    def go_long(self):
        qty = utils.size_to_qty(self.balance * self.hp['risk'], self.price)
        self.buy = qty, self.price
        self.take_profit = qty, self.price + (self.atr * self.hp['k'] * 2)
        self.stop_loss = qty, self.price - (self.atr * self.hp['k'])

    def go_short(self):
        qty = utils.size_to_qty(self.balance * self.hp['risk'], self.price)
        self.sell = qty, self.price
        self.take_profit = qty, self.price - (self.atr * self.hp['k'] * 2)
        self.stop_loss = qty, self.price + (self.atr * self.hp['k'])

    def should_cancel_entry(self):
        return False
