from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime  # For datetime objects
import os  # To manage paths
import backtrader as bt
import pandas as pd
import math

class TrendIndicator(bt.Indicator):
    lines = ('TrendIndicator', )  
    params = dict(ma_periods=[3, 5, 10, 20, 60], )

    plotinfo = dict(plot   =True,
                    subplot=True,
                    plotname='',
               )  

    def __init__(self, *args, **kwargs):
        self.addminperiod = max(self.p.ma_periods) + 1
        super().__init__(*args, **kwargs)

    def next(self):
        smas = []
        for period in self.p.ma_periods:
            smas.append(math.fsum(self.data.close.get(size=period)) / period)
        df = pd.DataFrame(dict(x=self.p.ma_periods, y=smas))
        corr = df.corr(method='spearman')
        self.lines.TrendIndicator[0] = corr.iloc[0][1]
        
class SMAStrategy(bt.Strategy):
    params = dict(stake=10, )

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None
        self.buycomm = None

        # Add MovingAverageSimple indicators
        self.sma5 = bt.indicators.SimpleMovingAverage(self.datas[0], period=5)
        self.sma10 = bt.indicators.SimpleMovingAverage(self.datas[0], period=10)
        
        self.trend_indicator = TrendIndicator(self.data)    

        # self.smas = []
        # for period in self.p.ma_periods:
        #     self.smas.append(bt.indicators.SimpleMovingAverage(self.datas[0], period=period))
        

        self.buy_signal = bt.indicators.CrossOver(self.sma5, self.sma10)
        self.sell_signal = bt.indicators.CrossDown(self.sma5, self.sma10)
        self.buy_signal.plotinfo.plot = False
        self.sell_signal.plotinfo.plot = False

        # Indicators for the plotting show
        # bt.indicators.ExponentialMovingAverage(self.datas[0], period=25)
        # bt.indicators.WeightedMovingAverage(self.datas[0],
        #                                     period=25,
        #                                     subplot=True)
        # bt.indicators.StochasticSlow(self.datas[0])
        # bt.indicators.MACDHisto(self.datas[0])
        # rsi = bt.indicators.RSI(self.datas[0])
        # bt.indicators.SmoothedMovingAverage(rsi, period=10)
        # bt.indicators.ATR(self.datas[0], plot=False)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price, order.executed.value,
                          order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price, order.executed.value,
                          order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Check if we are in the market
        if not self.position:

            # Not yet ... we MIGHT BUY if ...
            if self.buy_signal and self.trend_indicator[0] < 0.0:
                if self.trend_indicator[0] < 0.0: size = self.p.stake * 1
                if self.trend_indicator[0] < -0.2: size = self.p.stake * 2
                if self.trend_indicator[0] < -0.4: size = self.p.stake * 4
                if self.trend_indicator[0] < -0.6: size = self.p.stake * 6
                if self.trend_indicator[0] < -0.8: size = self.p.stake * 8
                self.log('BUY CREATE, %.2f, size: %.0f' % (self.dataclose[0], size))

                # Keep track of the created order to avoid a 2nd order
                self.order = self.buy(size=size)

        else:

            if self.sell_signal:
                self.log('SELL CREATE, %.2f' % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                self.order = self.close()


if __name__ == '__main__':
    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add a strategy
    cerebro.addstrategy(SMAStrategy)

    data = bt.feeds.GenericCSVData(dataname=os.path.join('.','data','601318_SH.csv'),
                                   dtformat=('%Y-%m-%d'),
                                   datetime=0,
                                   open=1,
                                   high=2,
                                   low=3,
                                   close=4,
                                   volumn=5,
                                   openinterest=6)
    # Add the Data Feed to Cerebro
    cerebro.adddata(data)

    # Set our desired cash start
    cerebro.broker.setcash(10000.0)

    # Add a FixedSize sizer according to the stake
    cerebro.addsizer(bt.sizers.FixedSize, stake=10)

    # Set the commission
    cerebro.broker.setcommission(commission=0.001)

    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio_A)
    cerebro.addanalyzer(bt.analyzers.DrawDown)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer)

    # Run over everything
    res = cerebro.run()
    res = res[0]

    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Analyzer results
    sharpe = res.analyzers.sharperatio_a.get_analysis()
    print('Sharpe Ratio: %.2f' % sharpe['sharperatio'])

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

    print('========lost=========')
    print('lost ratio: %.2f' % (tradings['lost']['total'] / float(tradings['won']['total'] + tradings['lost']['total'])))
    print('lost hits: %.0f' % tradings['lost']['total'])
    print('lost pnl total: %.0f, avg: %.0f, max: %.0f' % 
            (tradings['lost']['pnl']['total'],
            tradings['lost']['pnl']['average'],
            tradings['lost']['pnl']['max']))

    # Plot the result
    cerebro.plot(style='candlestick',
             bardown='green',
             barup='red',
             barupfill=False,
             bardownfill=True)