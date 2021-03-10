from io import BytesIO

import matplotlib.pyplot as plt
import mplfinance as mpf
import numpy as np
import pandas as pd
from matplotlib.ticker import MultipleLocator

from stonks_bot import conf


class PlotContext(object):
    def __enter__(self):
        self._chart_prepare()

        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._chart_finalize()

        return False

    def _add_labels_candle_high_low(self, ax, ohlc: pd.DataFrame) -> None:
        transform = ax.transData.inverted()
        # show the text 10 pixels above/below the bar
        text_pad = transform.transform((0, 30))[1] - transform.transform((0, 0))[1]
        high_low = []
        price_max = ohlc.Close.max()
        idx_price_max = ohlc.Close.index.get_loc(ohlc.Close.idxmax())
        price_min = ohlc.Close.min()
        idx_price_min = ohlc.Close.index.get_loc(ohlc.Close.idxmin())
        high_low.append({'idx': idx_price_max, 'max': price_max})
        high_low.append({'idx': idx_price_min, 'min': price_min})

        bbox_props = dict(boxstyle='circle,pad=0.3', fc='b', ec='cyan', lw=1)
        kwargs = dict(horizontalalignment='center', color='#FFFFFF', bbox=bbox_props)

        for i in high_low:
            idx = i['idx']
            if 'min' in i:
                ax.text(idx, i['min'] - text_pad, 'L', verticalalignment='bottom', **kwargs)
            elif 'max' in i:
                ax.text(idx, i['max'] + text_pad, 'H', verticalalignment='top', **kwargs)

    def _add_labels_candle_percent(self, ax, ohlc: pd.DataFrame) -> None:
        transform = ax.transData.inverted()
        # show the text 10 pixels above/below the bar
        text_pad = transform.transform((0, 10))[1] - transform.transform((0, 0))[1]
        percentages = 100. * (ohlc.Close - ohlc.Open) / ohlc.Open

        kwargs = dict(horizontalalignment='center', color='#FFFFFF')

        for i, (idx, val) in enumerate(percentages.items()):
            row = ohlc.loc[idx]
            price_open = row.Open
            price_close = row.Close
            if price_open < price_close:
                ax.text(i, row.High + text_pad, np.round(val, 1), verticalalignment='bottom', **kwargs)
            elif price_open > price_close:
                ax.text(i, row.Low - text_pad, np.round(val, 1), verticalalignment='top', **kwargs)

    def create_candle_chart(self, ohlc: pd.DataFrame, stock_name: str, symbol: str) -> BytesIO:
        mc = mpf.make_marketcolors(up='#94ED9C', down='#FE7074', inherit=True)
        s = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc)

        fig, axlist = mpf.plot(
                ohlc,
                type='candle',
                style=s,
                title=f"{stock_name} ({symbol}): {ohlc.index[0].date()}",
                ylabel=f"Price ({conf.LOCAL['currency']})",
                volume=True,
                ylabel_lower='Volume',
                returnfig=True,
                block=True,
                tz_localize=True,
                axtitle=f"Time Zone is {conf.LOCAL['tz']}.",
                datetime_format='%H:%M'
        )

        axlist[0].xaxis.set_major_locator(MultipleLocator(4))
        self._add_labels_candle_high_low(axlist[0], ohlc)
        self._add_labels_candle_percent(axlist[0], ohlc)

        return self._save_to_buffer()

    def create_bar_chart(self, bar_data: pd.DataFrame, title: str, ylabel: str) -> BytesIO:
        bar_data.plot(kind='bar')

        plt.title(title)
        plt.ylabel(ylabel)
        plt.tight_layout()
        plt.grid()

        return self._save_to_buffer()

    def _chart_prepare(self):
        plt.close('all')
        plt.style.use('dark_background')

    def _chart_finalize(self):
        plt.cla()
        plt.clf()
        plt.close()
        plt.close('all')

    def _save_to_buffer(self) -> BytesIO:
        buf = BytesIO()

        plt.savefig(buf, bbox_inches='tight')
        buf.seek(0)

        return buf
