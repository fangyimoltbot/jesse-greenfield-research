from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils

class EMACross(Strategy):
    def hyperparameters(self):
        return [
            {'name': 'fast', 'type': int, 'min': 8, 'max': 30, 'default': 12},
            {'name': 'slow', 'type': int, 'min': 40, 'max': 120, 'default': 55},
            {'name': 'risk', 'type': float, 'min': 0.01, 'max': 0.03, 'default': 0.02},
            {'name': 'tp', 'type': float, 'min': 0.01, 'max': 0.05, 'default': 0.025},
            {'name': 'sl', 'type': float, 'min': 0.005, 'max': 0.03, 'default': 0.012},
        ]

    @property
    def fast_ema(self):
        return ta.ema(self.candles, self.hp['fast'])

    @property
    def slow_ema(self):
        return ta.ema(self.candles, self.hp['slow'])

    def should_long(self):
        return self.fast_ema > self.slow_ema

    def should_short(self):
        return self.fast_ema < self.slow_ema

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
