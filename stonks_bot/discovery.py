from io import BytesIO

import matplotlib.pyplot as plt
import pandas as pd
import requests
from alpha_vantage.sectorperformance import SectorPerformances
from bs4 import BeautifulSoup

from stonks_bot import conf
from stonks_bot.helper.web import get_user_agent

PERFORMANCE_SECTORS_SP500_TIMESPAN = {
    'realtime': 'Rank A: Real-Time Performance',
    '1d': 'Rank B: 1 Day Performance',
    '5d': 'Rank C: 5 Day Performance',
    '1m': 'Rank D: 1 Month Performance',
    '3m': 'Rank E: 3 Month Performance',
    'ytd': 'Rank F: Year-to-Date (YTD) Performance',
    '1y': 'Rank G: 1 Year Performance',
    '3y': 'Rank H: 3 Year Performance',
    '5y': 'Rank I: 5 Year Performance',
    '10y': 'Rank J: 10 Year Performance'
}


class Discovery(object):
    websites = [
        {'url': 'https://finviz.com/map.ashx?t=geo', 'description': 'FinViz Map'},
        {'url': 'https://simplywall.st/stocks/us/any?page=1', 'description': 'Simply Wall St. Research Data'},
        {'url': 'https://www.spachero.com', 'description': 'SPAC Hero Research'},
        {'url': 'https://unusualwhales.com/spacs', 'description': 'UnusualWhales SPAC Research'}
    ]

    def __init(self):
        pass

    def performance_sectors_sp500(self, timespan: str = 'realtime'):
        plt.close('all')
        plt.style.use('dark_background')

        buf = BytesIO()

        sp = SectorPerformances(key=conf.API['alphavantage_api_key'], output_format='pandas')
        df_sectors, _ = sp.get_sector()
        timespan_desc = PERFORMANCE_SECTORS_SP500_TIMESPAN[timespan]
        df_sectors[timespan_desc].plot(kind='bar')
        plt.title(f'S&P500 Sectors: {timespan_desc[8:]}')
        plt.ylabel('%')
        plt.tight_layout()
        plt.grid()

        plt.savefig(buf, bbox_inches='tight')
        plt.cla()
        plt.clf()
        plt.close()
        plt.close('all')

        buf.seek(0)

        return buf

    def upcoming_earnings(self):
        pages = 3
        days = 3

        earnings = list()
        for idx in range(0, pages):
            if idx == 0:
                url_next_earnings = ('https://seekingalpha.com/earnings/earnings-calendar')
            else:
                url_next_earnings = (f'https://seekingalpha.com/earnings/earnings-calendar/{idx + 1}')
            text_soup_earnings = BeautifulSoup(
                    requests.get(url_next_earnings, headers={'User-Agent': get_user_agent()}).text, 'lxml',
            )

            for bs_stock in text_soup_earnings.findAll('tr', {'data-exchange': 'NASDAQ'}):
                stock = list()

                for stock in bs_stock.contents[:3]:
                    stock.append(stock.text)

                earnings.append(stock)

        df_earnings = pd.DataFrame(earnings, columns=['Ticker', 'Name', 'Date'])
        df_earnings['Date'] = pd.to_datetime(df_earnings['Date'])
        df_earnings = df_earnings.set_index('Date')

        pd.set_option('display.max_colwidth', -1)

        for n_days, earning_date in enumerate(df_earnings.index.unique()):
            if n_days > (days - 1):
                break

            print(f'Earning Release on {earning_date.date()}')
            print('----------------------------------------------')
            print(
                    df_earnings[earning_date == df_earnings.index][['Ticker', 'Name']].to_string(index=False, header=False)
            )
