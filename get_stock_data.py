# -*-coding:utf-8 -*-

'''
获取股票行情
Usage:
1. 获取个股行情：
    python get_stock_data.py --code '000333.SZ' --start_date '20180104' --end_date '20211230'
2. 获取整个市场行情
    python get_stock_data.py --start_date '20211001' --end_date '20211030' --fp './data/daily/'
'''

import os, sys
import argparse
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import tushare as ts

# 显示命令行进度条
def progress_bar(iteration, total, prefix='', suffix='', decimals=1, barLength=100):
    """
    Call in a loop to create a terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        barLength   - Optional  : character length of bar (Int)
    """
    formatStr = "{0:." + str(decimals) + "f}"
    percent = formatStr.format(100 * (iteration / float(total)))
    filledLength = int(round(barLength * iteration / float(total)))
    bar = '#' * filledLength + '-' * (barLength - filledLength)
    sys.stdout.write('\r%s |%s| %s%s %s' % (prefix, bar, percent, '%', suffix)),
    if iteration == total:
        sys.stdout.write('\n')
    sys.stdout.flush()

# 获取TuShare行情接口
def get_pro():
    try:
        TOKEN_TUSHARE = os.environ.get('TOKEN_TUSHARE')
        pro = ts.pro_api(TOKEN_TUSHARE)
    except Exception as e:
        print("获取Tushare接口失败")
        print(e)
        pro = None
    return pro

# 获取交易日历
def get_trade_cal(exchange="SSE",
                  start_date="20000101",
                  end_date="20211231",
                  is_open=1
                 ):
    """
    获取各大交易所交易日历数据, 默认提取的是上交所

    Arguments:
        exchange 	str 	N 	交易所 SSE 上交所 SZSE 深交所
        start_date 	str 	N 	开始日期
        end_date 	str 	N 	结束日期
        is_open 	str 	N 	是否交易 '0' 休市 '1' 交易

    Returns:
        exchange 	str 	Y 	交易所 SSE 上交所 SZSE 深交所
        cal_date 	str 	Y 	日历日期
        is_open 	str 	Y 	是否交易 0 休市 1 交易
        pretrade_date 	str 	N 	上一个交易日
    """

    def _get_trade_cal():
        print(" 正在下载交易日历...")
        try:
            pro = get_pro()
            data = pro.trade_cal(
                start_date=start_date,
                end_date=end_date,
                exchange=exchange,
                is_open=is_open,
                fields="exchange, cal_date, is_open, pretrade_date")
            print(" 下载交易日历 TRADE_DATE {}-{} 成功 ".format(start_date, end_date))
        except Exception as e:
            print(e)
            time.sleep(1)
            data = _get_trade_cal()
        return data

    return _get_trade_cal()

# 找出最近的交易日
def nearest_date(dates, pivot, direction='backward', date_format='%Y%m%d'):
    """
    找出最近的交易日, 默认提取的交易日历是上交所

    Arguments:
        dates 	str 	N 	交易日历
        pivot 	str 	N 	特定日期
        date_formate 	str 	N 	日期格式，默认20201124

    Returns:
        nearest 	str 	Y 	最近交易日
    """
    dates = pd.to_datetime(dates)
    pivot = datetime.strptime(pivot, date_format)
    
    if(direction=='backward'):
        dates = dates.where(dates<=pivot).dropna()
    if(direction=='foreward'):
        dates = dates.where(dates>=pivot).dropna()
    
    nearest = min(dates, key=lambda x: abs(x - pivot))
    return nearest.strftime(date_format)

# 获取指数行情
def get_indexes(index_codes=[], trade_date=datetime.today().strftime('%Y%m%d')):
    
    indexes = pd.DataFrame()
    for index_code in index_codes:
        indexes = pd.concat([indexes, pro.index_daily(ts_code=index_code, trade_date=trade_date)])
    
    index_basic = pro.index_basic()
    
    indexes = pd.merge(indexes, index_basic, on=['ts_code'], how='left')

    return indexes
    
# 获取个股行情
def get_stock_data(code, start_date, end_date, adj='qfq'):
    data = ts.pro_bar(ts_code=code, asset='E', start_date=start_date, end_date=end_date, adj=adj)
    data = data[['trade_date', 'open', 'high', 'low', 'close', 'vol']]
    data.columns = ['datetime', 'open', 'high', 'low', 'close', 'volumn']
    data['datetime'] = pd.to_datetime(data['datetime'])
    data.set_index('datetime', inplace=True)
    data.sort_values(by='datetime', ascending=True, inplace=True)
    data['openinterest'] = 0.0
    data = data.dropna()
    data = data.fillna(0)

    return data

# 获取整个市场每日行情
def get_daily(start_date='20180101', end_date='20211231', exchange='China', fp=None):
    trade_cal = get_trade_cal(start_date=start_date, end_date=end_date)
    trade_cal.sort_values(by='cal_date', ascending=True, inplace=True)
    start_date = nearest_date(trade_cal['cal_date'], start_date, direction='foreward')
    end_date = nearest_date(trade_cal['cal_date'], end_date, direction='backward')

    trade_dates = trade_cal.query(f'cal_date>="{start_date}" and cal_date<="{end_date}" and is_open==1')
    trade_dates = trade_dates['cal_date']

    print('正在下载每日行情数据...')
    pro = get_pro()
    datas = pd.DataFrame()
    adj_factors = pd.DataFrame()
    adj_datas = pd.DataFrame()
    i = 0
    l = len(trade_dates)
    for trade_date in trade_dates:
        # 获取每日行情
        data = pro.daily(trade_date=trade_date)
        if fp: # 存储到本地
            fname1 = os.path.join(fp,trade_date+'.csv')
            if not os.path.exists(fname1): 
                data.to_csv(fname1)
        datas = pd.concat([datas, data])
        
        # 获取除权系数
        adj_factor = pro.adj_factor(trade_date=trade_date)
        if fp: # 存储到本地
            fname2 = os.path.join(fp,'adj_factor_'+trade_date+'.csv')
            if not os.path.exists(fname2): 
                adj_factor.to_csv(fname2)
        adj_factors = pd.concat([adj_factors, adj_factor])

        adj_data = pd.merge(data, adj_factor, on=['ts_code'], how='left', suffixes=('','_y'))
        adj_data['adj_open'] = adj_data['open'] * adj_data['adj_factor']
        adj_data['adj_high'] = adj_data['high'] * adj_data['adj_factor']
        adj_data['adj_low'] = adj_data['low'] * adj_data['adj_factor']
        adj_data['adj_close'] = adj_data['close'] * adj_data['adj_factor']
        adj_datas = pd.concat([adj_datas, adj_data])

        i += 1
        progress_bar(i, l, prefix='Progress:', suffix='Complete', barLength=50)

    adj_datas = adj_datas[['ts_code', 'trade_date', 'adj_open', 'adj_high', 'adj_low', 'adj_close', 'vol']]
    adj_datas.columns = ['code', 'datetime', 'open', 'high', 'low', 'close', 'volumn']
    adj_datas['datetime'] = pd.to_datetime(adj_datas['datetime'])
    adj_datas.sort_values(by='datetime', ascending=True, inplace=True)
    adj_datas.set_index(['code', 'datetime'], inplace=True)
    adj_datas['openinterest'] = 0.0
    adj_datas = adj_datas.dropna()
    adj_datas = adj_datas.fillna(0)

    print('下载完毕')


    return adj_datas

if __name__ == '__init__': 
    TOKEN_TUSHARE = os.environ.get('TOKEN_TUSHARE')
    ts.set_token(TOKEN_TUSHARE)

def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('--code', help='Stock Code')
    parser.add_argument('--start_date', help='Start Date, example:20200301')
    parser.add_argument('--end_date', help='End Date, example:20201231')
    parser.add_argument('--fp', help='File Path Prefix for daily prices')

    return parser.parse_args()

if __name__ == '__main__':
    args = get_args()

    if args.code: # 个股行情
        stock_data = get_stock_data(code=args.code, start_date=args.start_date, end_date=args.end_date, adj='qfq')
        fname = os.path.join('.','data',args.code.replace('.','_')+'.csv')
        stock_data.to_csv(fname)
    else: # 整体市场行情
        data = get_daily(start_date=args.start_date, end_date=args.end_date, fp=args.fp)
        print(data)
        fname = os.path.join('.','data',args.start_date+'_'+args.end_date+'.csv')
        data.to_csv(fname)
