import backtrader as bt
from datetime import datetime


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

    params = (("period", 20), ("devfactor", 2), ("size", 100), ("debug", False), ("take_profit", 2.0), ("stop_loss", 0.95))

    def __init__(self):
        self.boll = bt.indicators.BollingerBands(period=self.p.period,
                                                 devfactor=self.p.devfactor)


    def next(self):


        if not self.position:

            if (self.data.close < self.boll.bot):
                self.buy_bracket(limitprice=self.p.take_profit * self.boll.lines.bot,
                         price=self.boll.lines.bot,
                         stopprice=self.p.stop_loss * self.boll.lines.bot,
                         size=self.p.size)
            

        else:

            if (self.data.close > self.boll.top) and (self.position.size >= self.p.size):
                self.sell(exectype=bt.Order.Limit,
                          price=self.boll.lines.top,
                          size=self.p.size)

            if (self.data.close < self.boll.bot) and (self.broker.get_cash() >= self.p.size*self.boll.lines.bot):
                self.buy_bracket(limitprice=self.p.take_profit * self.boll.lines.bot,
                         price=self.boll.lines.bot,
                         stopprice=self.p.stop_loss * self.boll.lines.bot,
                         size=self.p.size)

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
cerebro.addsizer(bt.sizers.FixedReverser, stake=100)

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
cerebro.plot(style='candlestick')