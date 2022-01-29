# -*-coding:utf-8 -*-

import os
import argparse
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import tushare as ts

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

if __name__ == '__init__': 
    TOKEN_TUSHARE = os.environ.get('TOKEN_TUSHARE')
    ts.set_token(TOKEN_TUSHARE)

def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('--code', help='Stock Code')
    parser.add_argument('--start_date', help='Start Date example:20200301')
    parser.add_argument('--end_date', help='End Date example:20201231')

    return parser.parse_args()

if __name__ == '__main__':
    args = get_args()

    stock_data = get_stock_data(code=args.code, start_date=args.start_date, end_date=args.end_date, adj='qfq')
    fname = os.path.join('.','data',args.code.replace('.','_')+'.csv')
    stock_data.to_csv(fname)