# -*-coding:utf-8 -*-

'''
每日复盘程序，具备以下功能；
    * 市场回顾
        * 主要股指强弱
        * 当日个股涨跌榜
        * 交易信号
    * 交易信号
        - 趋势交易信号
        - 逆向交易信号（）
        - 套利交易

Usage:
    python daily_scan.py --window '3m' 
'''

import pandas as pd
import numpy as np
import tushare as ts
from datetime import datetime, timedelta
import os
import pandas_ta as ta

settings = dict(
            freq = '1D',
            look_back_window = 90,
            index_codes = ['000001.SH','000016.SH','000300.SH','000905.SH','000688.SH','399001.SZ','399006.SZ'],
            ignore_newly_IPO = True,
            ignore_ST = True,
            )

def get_pro():
    try:
        if not TOKEN_TUSHARE: 
            TOKEN_TUSHARE = os.environ.get('TOKEN_TUSHARE')
        pro = ts.pro_api(TOKEN_TUSHARE)
    except Exception as e:
        print("获取Tushare接口失败")
        print(e)
        pro = None
    return pro

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

# 涨跌幅最大的前N只
def get_top_changers(df, direction="up", n=20):
    if direction=="down":
        return df.sort_values("change%", ascending=True).head(n)
    else:
        return df.sort_values("change%", ascending=False).head(n)

# 计算最大回撤
def drawdown(timeseries):
    timeseries = pd.Series(timeseries)
    # 回撤结束时间点
    j = (np.maximum.accumulate(timeseries) - timeseries).idxmax()
    # 回撤开始的时间点
    i = (timeseries[:j]).idxmax()
    dd = (float(timeseries[j]) / timeseries[i]) - 1.0
    return dd

# 计算夏普比率 (日均收益率*250-3%) / (日均波动率*squareroot(250))
def sharpe(rets, rf=0.03, days=250):
    rets = rets - 1.0
    return (rets.mean()*days - rf) / (rets.std() * np.sqrt(days))

# 计算年度统计数据
def calc_yearly_stats(df):
    df['trade_date'] = pd.to_datetime(df['trade_date'],format='%Y%m%d')
    df.set_index('trade_date', inplace=True)
    df['pct_chg'] = df['pct_chg']*0.01 + 1.0
    
    # 计算年化收益率
    yearly_return = (df.resample('A')['pct_chg'].prod())
    avg_3y = np.power(yearly_return.rolling(window=3).apply(np.prod), 1.0/3.0)
    avg_5y = np.power(yearly_return.rolling(window=5).apply(np.prod), 1.0/5.0)
    avg_10y = np.power(yearly_return.rolling(window=10).apply(np.prod), 1.0/10.0)
    L = len(yearly_return)
    avg_max = np.power(yearly_return.rolling(window=L).apply(np.prod), 1.0/L)
    
    # 计算最大回撤
    yearly_drawdown = df.resample('A')['pct_chg'].apply(drawdown)
    
    # 计算夏普比率
    sharpe_ratio = df.resample('A')['pct_chg'].apply(sharpe)
    
    # 组装年度统计数据
    yearly_statistic = pd.DataFrame({'1Y' : yearly_return, 'Avg_3Y' : avg_3y, 'Avg_5Y' : avg_5y, 'Avg_10Y' : avg_10y, 'Avg_Max' : avg_max, 'Drawdown' : yearly_drawdown, 'Sharpe Ratio' : sharpe_ratio })
    yearly_statistic.index = yearly_statistic.index.year
    
    return yearly_statistic

# 获取指数行情
def get_indexes(index_codes=[], mode='all'):
    indexes = pd.DataFrame()
    for index_code in index_codes:
        if mode=='recent_day': # 最近交易日
            recent_trade_date = nearest_date(dates=trade_cal['cal_date'], pivot=datetime.today().strftime('%Y%m%d'))
            indexes = pd.concat([indexes, pro.index_daily(ts_code=index_code, trade_date=recent_trade_date)])
        else: # 所有交易日
            indexes = pd.concat([indexes, pro.index_daily(ts_code=index_code)])
    
    index_basic = pro.index_basic()
    indexes = pd.merge(indexes, index_basic, on=['ts_code'], how='left')

    return indexes

def calc_growth(start_date, end_date, ignore_ST=True, ignore_IPO=True):
    daily1 = pro.daily(trade_date=start_date)
    daily2 = pro.daily(trade_date=end_date)
    
    adj_factor1 = pro.adj_factor(trade_date=start_date)
    adj_factor2 = pro.adj_factor(trade_date=end_date)
    
    daily1 = pd.merge(daily1, adj_factor1, on=['ts_code'], how='left')
    daily2 = pd.merge(daily2, adj_factor2, on=['ts_code'], how='left')
    
    daily1['adj_price1'] = daily1['close'] * daily1['adj_factor']
    daily2['adj_price2'] = daily2['close'] * daily2['adj_factor']
    
    growth = pd.merge(daily1[['ts_code','adj_price1']], daily2[['ts_code','adj_price2']], on=['ts_code'], how='left', suffixes=('_1','_2'))
    
    date1 = datetime.strptime(start_date,'%Y%m%d')
    date2 = datetime.strptime(end_date,'%Y%m%d')
    delta = (date2 - date1) 
    delta_years = delta.days / 365.0 
    
    growth['total_growth'] = growth['adj_price2'] / growth['adj_price1']

    growth['annual_growth'] = np.round((np.power(10, np.log10(growth['total_growth']) / delta_years) - 1.0) * 100, 2)
    
    growth.sort_values(by='annual_growth', ascending=False, inplace=True)
    
    # 获得股票基本信息
    stock_basic = pro.stock_basic()
    growth = pd.merge(growth, stock_basic, on=['ts_code'], how='left')
    
    growth = growth.dropna()
    
    if(ignore_ST):
        growth = growth[~growth['name'].str.contains('ST', na=False)]
    
    if(ignore_IPO):
        cutoff_date = (date2-timedelta(days=365)).strftime('%Y%m%d')
        growth = growth[growth['list_date'] < cutoff_date]
        
    
    return growth

def analyze_indexes(index_codes):
    if not index_codes:
        index_codes = settings['index_codes']
    indexes_recent_day = get_indexes(index_codes=index_codes, mode='recent_day')

    indexes_all = get_indexes(index_codes=index_codes, mode='all')
    indexes_all.set_index('ts_code', inplace=True)
    indexes_stats = []
    for index_code in index_codes:
        indexes_stats.append(calc_yearly_stats(indexes_all.iloc[index_code]))

    return indexes_recent_day, indexes_stats    

def analyze_top_winners_losers(ignore_ST=True, ignore_IPO=True):
    return top_winners, top_losers

def identify_opptunities(ignore_ST=True, ignore_IPO=True):
    return opptunities

def generate_reports(*args, **kwargs):
    pass

if __name__ == __init__:
    TOKEN_TUSHARE = os.environ.get('TOKEN_TUSHARE')
    pro = get_pro()

if __name__ == __main__:
    # 获取开始时间和结束时间
    today = datetime.today().strftime('%Y%m%d')
    start_date = (datetime.today()-timedelta(days=settings['look_back_window'])).strftime('%Y%m%d')
    end_date = today

    trade_cal = get_trade_cal(start_date=start_date, end_date=end_date)

    analyze_indexes(index_codes=settings['index_codes'])

    analyze_top_winners_losers()

    identify_opptunities()

    generate_reports()

    pass