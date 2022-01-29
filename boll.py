import backtrader as bt
from datetime import datetime
import os
import math


class AllInOut(bt.Sizer):

    def _getsizing(self, comminfo, cash, data, isbuy):
        if (isbuy):
            size = math.floor((cash / data.close[0] / 100)) * 100
        else:
            size = self.broker.getposition(data)
        return size


class BOLLStrat(bt.Strategy):
    '''
    This is a simple mean reversion bollinger band strategy.

    Entry Critria:
        - Long:
            - Price closes below the lower band
            - Stop Order entry when price crosses back above the lower band
        - Short:
            - Price closes above the upper band
            - Stop order entry when price crosses back below the upper band
    Exit Critria
        - Long/Short: Price touching the median line
    '''

    params = dict(
                period=20, 
                devfactor=2, 
                size=100,
                debug=False, 
                take_profit=30.0,
                stop_loss=0.95,
                trail_percent=0.05,)

    def __init__(self):
        self.boll = bt.indicators.BollingerBands(period=self.p.period,
                                                 devfactor=self.p.devfactor)
        self.stop_orders = []
        self.buy_orders = []
        self.order = None

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def next(self):
        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        if not self.position:
            if (self.data.close < self.boll.bot):
                size = math.floor(
                    (self.broker.getcash() / data.close[0] / 100)) * 100
                if (size > 0):
                    buy_order = self.buy(size=size)
                    stop_order = self.sell(size=size, exectype=bt.Order.StopTrail, trailpercent=self.p.trail_percent)
                    self.stop_orders.append(stop_order)

        else: # in market
            if (self.data.close > self.boll.top) and (self.position.size >= 0):
                self.close()
                for stop_order in self.stop_orders:
                    self.cancel(stop_order)

            if (self.data.close <
                    self.boll.bot) and (self.broker.get_cash() >=
                                        self.p.size * self.boll.lines.bot):
                size = math.floor(
                    (self.broker.getcash() / data.close[0] / 100)) * 100
                if (size > 0):
                    buy_order = self.buy(size=size)
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

            # self.bar_executed = len(self)

        if order.status in [order.Canceled]:
            self.log("Order Canceled")
        if order.status in [order.Margin]:
            self.log("Order Margin")
        if order.status in [order.Rejected]:
            self.log("Order Rejected")

        # Write down: no pending order
        self.order = None

    def notify_trade(self, trade):
        if trade.isclosed:
            dt = self.data.datetime.date()

            # print(
            #     '---------------------------- TRADE ---------------------------------'
            # )
            # print("1: Data Name:                            {}".format(
            #     trade.data._name))
            # print("2: Bar Num:                              {}".format(
            #     len(trade.data)))
            # print("3: Current date:                         {}".format(dt))
            # print('4: Status:                               Trade Complete')
            # print('5: Ref:                                  {}'.format(
            #     trade.ref))
            # print('6: PnL:                                  {}'.format(
            #     round(trade.pnl, 2)))
            # print(
            #     '--------------------------------------------------------------------'
            # )


# Variable for our starting cash
startcash = 10000

# Create an instance of cerebro
cerebro = bt.Cerebro()

# Add our strategy
cerebro.addstrategy(BOLLStrat)

data = bt.feeds.GenericCSVData(dataname=os.path.join('.','data','601318_SH.csv'),
                               dtformat=('%Y-%m-%d'),
                               datetime=0,
                               open=1,
                               high=2,
                               low=3,
                               close=4,
                               volumn=5,
                               openinterest=6)

# Add the data to Cerebro
cerebro.adddata(data)

# Add a sizer
cerebro.addsizer(AllInOut)

# Set our desired cash start
cerebro.broker.set_cash(startcash)

# Add analyzers
cerebro.addanalyzer(bt.analyzers.SharpeRatio)
cerebro.addanalyzer(bt.analyzers.DrawDown)
cerebro.addanalyzer(bt.analyzers.TradeAnalyzer)

# Run over everything
res = cerebro.run()
res = res[0]

# Get final portfolio Value
portvalue = cerebro.broker.getvalue()
pnl = portvalue - startcash

# Print out the final result
print('Final Portfolio Value: ${}'.format(round(portvalue, 2)))
print('P/L: ${}'.format(round(pnl, 2)))

# Analyzer results
drawdown = res.analyzers.drawdown.get_analysis()
print('Max drawdown percent: %.2f' % drawdown['max']['drawdown'])
print('Max drawdown money: %.0f' % drawdown['max']['moneydown'])

tradings = res.analyzers.tradeanalyzer.get_analysis()
print('=================Trading Analysis=================')
print('========won=========')
print('won ratio: %.2f' % (tradings['won']['total'] / float(tradings['won']['total'] + tradings['lost']['total'])))
print('won hits: %.0f' % tradings['won']['total'])
print('won pnl total: %.0f, avg: %.0f, max: %.0f' % 
        (tradings['won']['pnl']['total'],
        tradings['won']['pnl']['average'],
        tradings['won']['pnl']['max']))

print('========lost========')
print('lost ratio: %.2f' % (tradings['lost']['total'] / float(tradings['lost']['total'] + tradings['lost']['total'])))
print('lost hits: %.0f' % tradings['lost']['total'])
print('lost pnl total: %.0f, avg: %.0f, max: %.0f' % 
        (tradings['lost']['pnl']['total'],
        tradings['lost']['pnl']['average'],
        tradings['lost']['pnl']['max']))


# Finally plot the end results
cerebro.plot(style='candlestick',
             bardown='green',
             barup='red',
             barupfill=False,
             bardownfill=True)
