import numpy as np
import pandas as pd
import vectorbt as vbt
import os

symbols = ["601318.SH", "000333.SZ", "600079.SH"]
for symbol in symbols:
    fname = os.path.join('.','data',symbol.replace('.','_')+'.csv')
    data = pd.read_csv(fname)
    data.set_index('datetime', inplace=True)
    boll = vbt.BBANDS.run(data['close'])
    # boll_mid, boll_upper, boll_lower = vbt.BBANDS.run(data.close)
    entries = boll.close_crossed_above(boll.lower)
    exits = boll.close_crossed_below(boll.upper)

    pf_kwargs = dict(size=np.inf, fees=0.001, freq='1D')
    pf = vbt.Portfolio.from_signals(data['close'], entries, exits, **pf_kwargs)

    print(symbol)
    total_return = pf.total_return()*100
    print('Total Return: %.2f%%' % (total_return))

    fig = pf.plot()
    boll.plot(fig=fig)
    fig.show()

# fast_ma, slow_ma = vbt.MA.run_combs(price, window=windows, r=2, short_names=['fast', 'slow'])
# entries = fast_ma.ma_crossed_above(slow_ma)
# exits = fast_ma.ma_crossed_below(slow_ma)

# pf_kwargs = dict(size=np.inf, fees=0.001, freq='1D')
# pf = vbt.Portfolio.from_signals(price, entries, exits, **pf_kwargs)

# fig = pf.total_return().vbt.heatmap(
#     x_level='fast_window', y_level='slow_window', slider_level='symbol', symmetric=True,
#     trace_kwargs=dict(colorbar=dict(title='Total return', tickformat='%')))
# fig.show()