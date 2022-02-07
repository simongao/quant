from datetime import datetime
import random
import argparse
import numpy as np
import dataloader
import pandas as pd

import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sb

def contrarian_strategy(start_week, s, h, loser=True):
    weeks = pd.date_range("20210101","20221231", freq='W-MON')
    weeks = list(weeks.strftime('%Y%m%d'))
    scan_start_date = weeks[start_week]
    scan_end_date = weeks[start_week+s]
    hold_start_date = weeks[start_week+s]
    hold_end_date = weeks[start_week+s+h]
    # print(f"{scan_start_date}-{scan_end_date}, {hold_start_date}-{hold_end_date}")

    try:
        scan = dataloader.calc_growth_from_local(start_date=scan_start_date, end_date=scan_end_date)
        scan = dataloader.filter_stock(dataset=scan, method='ALL')
        scan.sort_values(by='total_growth', ascending=loser, inplace=True)
        selected = scan.head(20)

        hold = dataloader.calc_growth_from_local(start_date=hold_start_date, end_date=hold_end_date)
        hold = dataloader.filter_stock(dataset=hold, method='ALL')

        result = pd.merge(selected[['ts_code']], hold, on='ts_code', how='left')
        rtn = np.average(result['total_growth'])
    except:
        rtn = 1.0
        
    return rtn

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

    start_date = args.start_date if args.start_date else '20210101'
    end_date = args.end_date if args.end_date else '20220128'
    fp = args.fp if args.fp else './data/daily/'
    method = args.scope if args.scope else 'ALL'


    results = np.ones([52,52])
    i = 0
    l = 49*50*0.5
    for s in np.arange(1,49):
        for h in np.arange(1,50-s):
            start_week = random.choice(np.arange(0, 50-s-h))
            results[s][h] = contrarian_strategy(start_week,s,h)

            i += 1
            dataloader.progress_bar(i, l, prefix='Progress:', suffix='Complete', barLength=50)

    results = np.nan_to_num(results, nan=1.0)
    vmin = np.min(results)
    vmax = np.max(results)

    # 画图
    mpl.rcParams['font.family']= 'Microsoft YaHei UI' # 指定字体，实际上相当于修改 matplotlibrc 文件　只不过这样做是暂时的　下次失效
    mpl.rcParams['axes.unicode_minus']=False # 正确显示负号，防止变成方框

    fig, ax = plt.subplots(figsize=(11, 9))
    ax.set_xlim(1,50)
    ax.set_ylim(1,50)
    ax.set_xlabel('Holding Period (Weeks)')
    ax.set_ylabel('Watch Period (Weeks)')
    cmap = sb.diverging_palette(220,20,sep=3, as_cmap=True)
    sb.heatmap(results, cmap=cmap, center=1.0, vmin=vmin, vmax=vmax,
                linewidth=0.3, ax=ax, square=True,
                cbar_kws={"shrink": .8})
    plt.title('Contrarian Strategy', loc='left')
    plt.show()