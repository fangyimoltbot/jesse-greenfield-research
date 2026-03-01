from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils

class RSIReversion(Strategy):
    def hyperparameters(self):
        return [
            {'name': 'rsi', 'type': int, 'min': 8, 'max': 21, 'default': 14},
            {'name': 'low', 'type': int, 'min': 20, 'max': 35, 'default': 28},
            {'name': 'high', 'type': int, 'min': 65, 'max': 80, 'default': 72},
            {'name': 'risk', 'type': float, 'min': 0.01, 'max': 0.03, 'default': 0.02},
            {'name': 'tp', 'type': float, 'min': 0.01, 'max': 0.04, 'default': 0.018},
            {'name': 'sl', 'type': float, 'min': 0.005, 'max': 0.03, 'default': 0.010},
        ]

    @property
    def rsi(self):
        return ta.rsi(self.candles, self.hp['rsi'])

    def should_long(self):
        return self.rsi < self.hp['low']

    def should_short(self):
        return self.rsi > self.hp['high']

    def go_long(self):
        qty = utils.size_to_qty(self.balance * self.hp['risk'], self.price)
        self.buy = qty, self.price
        self.take_profit = qty, self.price * (1 + self.hp['tp'])
        self.stop_loss = qty, self.price * (1 - self.hp['sl'])

    def go_short(self):
        qty = utils.size_to_qty(self.balance * self.hp['risk'], self.price)
        self.sell = qty, self.price
        self.take_profit = qty, self.price * (1 - self.hp['tp'])
        self.stop_loss = qty, self.price * (1 + self.hp['sl'])

    def should_cancel_entry(self):
        return False
