import backtrader as bt
from datetime import datetime
import os, time
import math
import argparse
import numpy as np
import dataloader
import pandas as pd
from buy_and_hold import BuyAndHoldStrategy

strategy = dict(
                name='Buy and Hold',
                param='',
                classname='BuyAndHoldStrategy',
            )

class AllInOut(bt.Sizer):
    def _getsizing(self, comminfo, cash, data, isbuy):
        if (isbuy):
            size = math.floor((cash / data.close[0] / 100)) * 100
        else:
            size = self.broker.getposition(data)
        return size

def generate_report(res):
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

    print('========lost========')
    print('lost ratio: %.2f' % (tradings['lost']['total'] / float(tradings['won']['total'] + tradings['lost']['total'])))
    print('lost hits: %.0f' % tradings['lost']['total'])
    print('lost pnl total: %.0f, avg: %.0f, max: %.0f' % 
            (tradings['lost']['pnl']['total'],
            tradings['lost']['pnl']['average'],
            tradings['lost']['pnl']['max']))

def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('--start_date', help='Start Date, example:20200301')
    parser.add_argument('--end_date', help='End Date, example:20201231')
    parser.add_argument('--fp', help='File Path Prefix for daily prices')
    parser.add_argument('--scope', help='Back test data scope: RANDOM, HS300, ZZ500, ZZ1000')
    parser.add_argument('--plot', help='Plot the result: True or False')

    return parser.parse_args()

if __name__ == '__main__':
    args = get_args()

    t1 = time.time()

    start_date = args.start_date if args.start_date else '20210101'
    end_date = args.end_date if args.end_date else '20220128'
    fp = args.fp if args.fp else './data/daily/'
    method = args.scope if args.scope else 'RANDOM'
    dataset = dataloader.get_daily_from_local(start_date=start_date, end_date=end_date, fp=fp)
    dataset = dataloader.filter_stock(dataset=dataset, method=method)
    dataset.sort_values(by='datetime', ascending=True, inplace=True)

    accumulated_pnl = 0.0
    summary = pd.DataFrame(columns=['code', 'PnL', 'Trades', 'Wins', 'Win_Ratio', 'Losts', 'Lost_Ratio', 'Win_Value', 'Win_Avg', 'Win_Max', 'Lost_Value', 'Lost_Avg', 'Lost_Max'])
    stocks = dataset.groupby('code')
    for code, stock in stocks:
        stock = stock[['datetime','open','high','low','close','volume']].copy()
        stock['datetime'] = pd.to_datetime(stock['datetime'], format='%Y%m%d')
        stock['openinterest'] = 0.0
        stock.set_index('datetime', inplace=True)

        # Variable for our starting cash
        startcash = 10000

        # Create an instance of cerebro
        cerebro = bt.Cerebro()

        # Add strategy
        cerebro.addstrategy(eval(strategy['classname'])) 

        data = bt.feeds.PandasData(dataname=stock)
        cerebro.adddata(data)

        # Add a sizer
        cerebro.addsizer(AllInOut)

        # Set our desired cash start
        cerebro.broker.set_cash(startcash)

        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio_A)
        cerebro.addanalyzer(bt.analyzers.SharpeRatio)
        cerebro.addanalyzer(bt.analyzers.DrawDown)
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer)

        # Run over everything
        res = cerebro.run()
        res = res[0]

        # Get final portfolio Value
        portvalue = cerebro.broker.getvalue()
        pnl = portvalue - startcash

        accumulated_pnl += pnl

        # Print out the final result
        print(f'Symbol: {code}')
        print('Final Portfolio Value: ${}'.format(round(portvalue, 2)))
        print('P/L: ${}'.format(round(pnl, 2)))
        print('==============================================')

        tradings = res.analyzers.tradeanalyzer.get_analysis()
        if tradings['total']['total']==0: 
            pass
        else:
            try: 
                row = pd.DataFrame(dict(
                            code=[code],
                            PnL=[pnl], 
                            Trades=[tradings['won']['total'] + tradings['lost']['total']], 
                            Wins=[tradings['won']['total']],
                            Win_Ratio=[tradings['won']['total'] / float(tradings['won']['total'] + tradings['lost']['total'])], 
                            Losts = [tradings['lost']['total']], 
                            Lost_Ratio = [tradings['lost']['total'] / float(tradings['won']['total'] + tradings['lost']['total'])], 
                            Win_Value = [tradings['won']['pnl']['total']], 
                            Win_Avg = [tradings['won']['pnl']['average']], 
                            Win_Max = [tradings['won']['pnl']['max']], 
                            Lost_Value = [tradings['lost']['pnl']['total']], 
                            Lost_Avg = [tradings['lost']['pnl']['average']], 
                            Lost_Max = [tradings['lost']['pnl']['max']]
                ))
                summary = summary.append(row, ignore_index=True)
            except:
                pass

        plot = args.plot if args.plot else False
        if (plot):
            # Finally plot the end results
            cerebro.plot(style='candlestick',
                        bardown='green',
                        barup='red',
                        barupfill=False,
                        bardownfill=True)

    print(f"Accumulated Profit & Loss: {accumulated_pnl :.2f}.")

    if (len(summary) > 0):
        summary_pvt = pd.pivot_table(summary, index=['code'], 
                                    values=['PnL', 'Trades', 'Wins', 'Win_Ratio', 'Losts', 'Lost_Ratio', 'Win_Value', 'Win_Avg', 'Win_Max', 'Lost_Value', 'Lost_Avg', 'Lost_Max'], 
                                    aggfunc={'PnL':np.sum, 'Trades':np.sum, 'Wins':np.sum, 'Win_Ratio':np.average, 
                                            'Losts':np.sum, 'Lost_Ratio':np.average, 'Win_Value':np.sum, 'Win_Avg':np.average, 
                                            'Win_Max':np.max, 'Lost_Value':np.sum, 'Lost_Avg':np.average, 'Lost_Max':np.min}, 
                                            margins=True, margins_name='Total') 
        summary_pvt = summary_pvt[['PnL', 'Trades', 'Wins', 'Win_Ratio', 'Losts', 'Lost_Ratio', 'Win_Value', 'Win_Avg', 'Win_Max', 'Lost_Value', 'Lost_Avg', 'Lost_Max']]
        summary_pvt = np.round(summary_pvt,2)
        print(summary_pvt)
        summary_pvt.to_csv(f"./result/{strategy['name']}_{strategy['param']}.csv")
    t2 = time.time()
    print('共处理%.0f个股票，总计耗时:%.2f 秒, 平均%.2f 秒' % (len(stocks), (t2 - t1), (t2 - t1)/len(stocks)))
