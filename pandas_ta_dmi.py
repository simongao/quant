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

symbols = ["601318.SH", "000333.SZ", "600079.SH"]
for symbol in symbols:
    fname = os.path.join('.','data',symbol.replace('.','_')+'.csv')
    data = pd.read_csv(fname)
    data.set_index('datetime', inplace=True)
    data.ta.adx(append=True)
    adx_ind = vbt.IndicatorFactory.from_pandas_ta('ADX')
    adx = adx_ind.run(low=data['low'], high=data['high'], close=data['close'], open=data['open'])
    entries = (adx.dmp_below(10.0)) | (adx.adx_above(25.0) & adx.dmp_crossed_above(adx.dmn))
    ts = trailing_stop(data['close'], entries, discount=0.95)
    exits = data['close'] < ts

    pf_kwargs = dict(size=np.inf, fees=0.001, freq='1D')
    pf = vbt.Portfolio.from_signals(data['close'], entries, exits, **pf_kwargs)

    print(symbol)
    print('Entries')
    print(entries.where(entries).dropna().index)
    print('Exits')
    print(exits.where(exits).dropna().index)
    total_return = pf.total_return()*100
    print('Total Return: %.2f%%' % (total_return))

    fig = pf.plot()
    fig.show()