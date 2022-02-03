import numpy as np
import pandas as pd
import pandas_ta as ta 
import vectorbt as vbt
import os

def trailing_stop(price, entries, discount=0.95):
    
    if len(price) != len(entries): 
        print('price and entries length mismatch')
        return 0
    
    ts = price.copy(deep=True)
    for i in range(1, len(price)):
        if entries.iloc[i] == True:
            ts.iloc[i] = price.iloc[i]
        else: 
            ts.iloc[i] = max(ts.iloc[i-1], price.iloc[i])
    return ts * discount

def combine_stats(pf: vbt.portfolio.base.Portfolio, ticker: str, strategy: str, mode: int = 0):
    header = pd.Series({
        "Run Time": ta.get_time(full=False, to_string=True),
        "Mode": "LIVE" if mode else "TEST",
        "Strategy": strategy,
        "Direction": vbt.settings.portfolio["signal_direction"],
        "Symbol": ticker.upper(),
        "Fees [%]": 100 * vbt.settings.portfolio["fees"],
        "Slippage [%]": 100 * vbt.settings.portfolio["slippage"],
        "Accumulate": vbt.settings.portfolio["accumulate"],
    })
    rstats = pf.returns_stats().dropna(axis=0).T
    stats = pf.stats().dropna(axis=0).T
    joint = pd.concat([header, stats, rstats])
    return joint[~joint.index.duplicated(keep="first")]

# VectorBT setting
vbt.settings.portfolio['freq'] = '1D'
vbt.settings.portfolio['fees'] = 0.001
vbt.settings.portfolio['slippage'] = 0.001

symbols = ["601318.SH", "000333.SZ", "600079.SH"]
for symbol in symbols:
    fname = os.path.join('.','data',symbol.replace('.','_')+'.csv')
    data = pd.read_csv(fname)
    data.set_index('datetime', inplace=True)
    adx_ind = vbt.IndicatorFactory.from_pandas_ta('ADX')
    adx = adx_ind.run(low=data['low'], high=data['high'], close=data['close'], open=data['open'])
    entries = (adx.dmp_below(10.0)) | (adx.adx_above(25.0) & adx.dmp_crossed_above(adx.dmn))
    ts = trailing_stop(data['close'], entries, discount=0.95)
    exits = data['close'] < ts

    pf_kwargs = dict(size=np.inf, fees=0.001, freq='1D')
    pf = vbt.Portfolio.from_signals(data['close'], entries, exits, **pf_kwargs)

    print("===================={:^12}====================".format(symbol))
    print(pf.trades.records)
    print(combine_stats(pf, ticker=symbol, strategy='DMI'))

    fig = pf.plot()
    fig.show()