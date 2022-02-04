import backtrader as bt
from datetime import datetime
import math
import random

class RandomTSStrategy(bt.Strategy):
    params = dict(
                take_profit=2.0, # 止盈单比例
                stop_loss=0.95, # 止损单比例
                trail_percent=0.05, # 跟踪止损止盈百分比
                strategy_name='Random Trailing Stop Strategy',
                param='TS005',
                classname='RandomTSStrategy',
                description=
                    '''
                        随机买入并设置跟踪止损单
                        买入：
                            随机选择
                        卖出：
                            5% Trailing Stop 
                    '''
            )
    
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self, trailing_percent=0.02):
        super().__init__()
        self.p.trailing_percent = trailing_percent
        self.stop_orders = []
        self.order = None    

    def next(self):
        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        if not self.position:
            if (random.choice([0,1]) == 1):
                size = math.floor(((1-0.1)*self.broker.getcash() / self.data.close[0] / 100)) * 100
                if (size > 0):
                    self.buy(size=size)
                    stop_order = self.sell(size=size, exectype=bt.Order.StopTrail, trailpercent=self.p.trail_percent)
                    self.stop_orders.append(stop_order)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Shares: %.0f, Cash: %.0f, Value %.0f, Position: %.0f'
                    % (order.executed.price, order.executed.size,
                       self.broker.get_cash(), self.broker.get_value(),
                       self.position.size))

            else:  # Sell
                self.log(
                    'SELL EXECUTED, Price: %.2f, Shares: %.0f, Cash: %.0f, Value %.0f, Position: %.0f'
                    % (order.executed.price, order.executed.size,
                       self.broker.get_cash(), self.broker.get_value(),
                       self.position.size))
                for stop_order in self.stop_orders:
                    self.cancel(stop_order)
                    self.stop_orders.remove(stop_order)

        if order.status in [order.Canceled]:
            self.log("Order Canceled")
        if order.status in [order.Margin]:
            self.log("Order Margin")
        if order.status in [order.Rejected]:
            self.log("Order Rejected")

        # Write down: no pending order
        self.order = None

