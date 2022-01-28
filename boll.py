import backtrader as bt
from datetime import datetime


class AllInOut(bt.Sizer):
    def _getsizing(self, comminfo, cash, data, isbuy):
        if(isbuy):
            size = round((cash / data.close[0] / 100)) * 100
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

    params = (("period", 20), ("devfactor", 2), ("size", 100), ("debug", False), ("take_profit", 30.0), ("stop_loss", 0.95)) 

    def __init__(self):
        self.boll = bt.indicators.BollingerBands(period=self.p.period,
                                                 devfactor=self.p.devfactor)

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def next(self):
        if not self.position:

            if (self.data.close < self.boll.bot):
                size = round((self.broker.getcash() / data.close[0] / 100)) * 100
                if (size > 0):
                    self.buy(size=size)
                    # self.buy_bracket(limitprice=self.p.take_profit * self.boll.lines.bot,
                    #         price=self.boll.lines.bot,
                    #         stopprice=self.p.stop_loss * self.boll.lines.bot,
                    #         size=size)

        else:
            if (self.data.close > self.boll.top) and (self.position.size >= 0):
                self.sell(size=self.position.size)

            if (self.data.close < self.boll.bot) and (self.broker.get_cash() >= self.p.size*self.boll.lines.bot):
                size = round((self.broker.getcash() / data.close[0] / 100)) * 100
                if (size > 0):
                    self.buy(size=size)
                    # self.buy_bracket(limitprice=self.p.take_profit * self.boll.lines.bot,
                    #         price=self.boll.lines.bot,
                    #         stopprice=self.p.stop_loss * self.boll.lines.bot,
                    #         size=size)

        if self.p.debug:
            print(
                '---------------------------- NEXT ----------------------------------'
            )
            print("1: Data Name:                            {}".format(
                data._name))
            print("2: Bar Num:                              {}".format(
                len(data)))
            print("3: Current date:                         {}".format(
                data.datetime.datetime()))
            print('4: Open:                                 {}'.format(
                data.open[0]))
            print('5: High:                                 {}'.format(
                data.high[0]))
            print('6: Low:                                  {}'.format(
                data.low[0]))
            print('7: Close:                                {}'.format(
                data.close[0]))
            print('8: Volume:                               {}'.format(
                data.volume[0]))
            print('9: Position Size:                       {}'.format(
                self.position.size))
            print(
                '--------------------------------------------------------------------'
            )

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, Price: %.2f, Shares: %.0f, Cash: %.0f, Value %.0f, Position: %.0f' %
                         (order.executed.price, order.executed.size, self.broker.get_cash(), self.broker.get_value(), self.position.size))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Shares: %.0f, Cash: %.0f, Value %.0f, Position: %.0f' %
                         (order.executed.price, order.executed.size, self.broker.get_cash(), self.broker.get_value(), self.position.size))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # self.log("Order Canceled/Margin/Rejected")
            pass

        # Write down: no pending order
        self.order = None

    def notify_trade(self, trade):
        if trade.isclosed:
            dt = self.data.datetime.date()

            print(
                '---------------------------- TRADE ---------------------------------'
            )
            print("1: Data Name:                            {}".format(
                trade.data._name))
            print("2: Bar Num:                              {}".format(
                len(trade.data)))
            print("3: Current date:                         {}".format(dt))
            print('4: Status:                               Trade Complete')
            print('5: Ref:                                  {}'.format(
                trade.ref))
            print('6: PnL:                                  {}'.format(
                round(trade.pnl, 2)))
            print(
                '--------------------------------------------------------------------'
            )


# Variable for our starting cash
startcash = 10000

# Create an instance of cerebro
cerebro = bt.Cerebro()

# Add our strategy
cerebro.addstrategy(BOLLStrat)

data = bt.feeds.GenericCSVData(dataname='601318.csv',
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

# Run over everything
cerebro.run()

# Get final portfolio Value
portvalue = cerebro.broker.getvalue()
pnl = portvalue - startcash

# Print out the final result
print('Final Portfolio Value: ${}'.format(round(portvalue, 2)))
print('P/L: ${}'.format(round(pnl, 2)))

# Finally plot the end results
cerebro.plot(style='candlestick',
            bardown='green',
            barup='red',
            barupfill=False,
            bardownfill=True)