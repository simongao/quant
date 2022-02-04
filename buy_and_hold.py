import backtrader as bt
from datetime import datetime
import math

class BuyAndHoldStrategy(bt.Strategy):
    params = dict(
                strategy_name='Buy and Hold',
                param='TS005',
                classname='BuyAndHoldtrategy',
                description=
                    '''
                        随机买入并设置跟踪止损单
                        买入：
                            第一天开盘价买入
                        卖出：
                            一直持有，不卖出 
                    '''
            )
    
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def next(self):
        if not self.position:
            size = math.floor(((1-0.1)*self.broker.getcash() / self.data.open[0] / 100)) * 100
            if (size > 0):
                self.buy(size=size)

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

        if order.status in [order.Canceled]:
            self.log("Order Canceled")
        if order.status in [order.Margin]:
            self.log("Order Margin")
        if order.status in [order.Rejected]:
            self.log("Order Rejected")

        # Write down: no pending order
        self.order = None

