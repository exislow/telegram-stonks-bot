from datetime import date, timedelta
from io import BytesIO

import pandas as pd
import requests
from alpha_vantage.sectorperformance import SectorPerformances
from bs4 import BeautifulSoup
from yahoo_earnings_calendar import YahooEarningsCalendar

from stonks_bot import conf
from stonks_bot.helper.formatters import formatter_date, formatter_shorten_1, formatter_offset_1
from stonks_bot.helper.plot import PlotContext
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

    def performance_sectors_sp500(self, timespan: str = 'realtime') -> BytesIO:
        sp = SectorPerformances(key=conf.API['alphavantage_api_key'], output_format='pandas')
        df_sectors, _ = sp.get_sector()
        timespan_desc = PERFORMANCE_SECTORS_SP500_TIMESPAN[timespan]
        df_data = df_sectors[timespan_desc]
        title = f'S&P500 Sectors: {timespan_desc[8:]}'
        ylabel = '%'

        with PlotContext() as pc:
            buf = pc.create_bar_chart(df_data, title, ylabel)

        return buf

    def upcoming_earnings(self, days: int = 2) -> str:
        result = ''
        date_from = date.today()
        date_to = date_from + timedelta(days=days)

        yec = YahooEarningsCalendar()
        ue = yec.earnings_between(date_from, date_to)
        pd_ue = pd.DataFrame(ue)
        pd_ue = pd_ue.drop_duplicates(subset=['ticker'])
        result = pd_ue[
            ['startdatetime', 'companyshortname', 'ticker']
        ].to_string(header=False, index=False, formatters={'startdatetime': formatter_date,
                                                           'companyshortname': '{:.15}'.format})

        return result

    def gainers(self, count: int = 15) -> str:
        url = f'https://finance.yahoo.com/gainers?offset=0&count={count}'
        result = self.get_daily_performers(url)

        return result

    def losers(self, count: int = 15) -> str:
        url = f'https://finance.yahoo.com/losers?offset=0&count={count}'
        result = self.get_daily_performers(url)

        return result

    def get_daily_performers(self, yf_url: str) -> str:
        df_perf = pd.read_html(yf_url)[0]
        result = df_perf[
            ['Name', 'Symbol', 'Price (Intraday)', 'Change', '% Change']
        ].to_string(header=['Company', 'Sym', 'Price', '±', '%'],
                    index=False, formatters={'Name': '{:.10}'.format,
                                             '% Change': formatter_shorten_1})

        return result

    def orders(self, count: int = 15) -> str:
        url = f'https://finance.yahoo.com/most-active?offset=0&count={count}'
        df_orders = pd.read_html(url)[0]
        result = df_orders[
            ['Name', 'Symbol', 'Volume']
        ].to_string(header=['Company', 'Sym', 'Volume'],
                    index=False, formatters={'Name': '{:.15}'.format})

        return result

    def high_short(self, count: int = 15) -> str:
        url = 'https://www.highshortinterest.com/'
        result = self.get_short_float(url, count)

        return result

        df = self.get_short_float_penny(url)

    def low_float(self, count: int = 15) -> str:
        url = 'https://www.lowfloat.com/'
        result = self.get_short_float(url, count)

        return result

    def get_short_float(self, url: str, count: int = 15):
        df = self.get_short_float_penny(url)
        columns = ['Company', 'Ticker', 'ShortInt', 'Float', 'Outstd']
        result = df[columns].head(n=count).to_string(header=['Company', 'Sym.', 'SI %', 'Float', 'Outstd'],
                                                     index=False,
                                                     formatters={columns[0]: '{:.9}'.format,
                                                                 columns[2]: formatter_shorten_1})

        return result

    def hot_pennystocks(self, count: int = 15) -> str:
        url = 'https://www.pennystockflow.com/'
        df = self.get_short_float_penny(url)
        columns = ['Ticker', '# Trades', 'Price', 'Change']
        result = df[columns].head(n=count).to_string(header=['Sym.', 'Trades', 'Price', '±%'], index=False,
                                                     formatters={columns[2]: formatter_offset_1,
                                                                 columns[3]: formatter_shorten_1})

        return result

    def get_short_float_penny(self, url: str) -> pd.DataFrame:
        soup_text = BeautifulSoup(requests.get(url, headers={'User-Agent': get_user_agent()}).text, 'lxml')

        columns = list()
        for header_cell in soup_text.findAll('td', {'class': 'tblhdr'}):
            columns.append(header_cell.text.strip('\n').split('\n')[0])

        row_stock = soup_text.find_all('tr')

        len_columns = len(columns)
        data = []

        for row in row_stock:
            stock_text = row.text

            if stock_text == '':
                continue

            a_stock = stock_text.split('\n')

            if (len(a_stock) - 1) == len_columns:
                data.append(a_stock[:-1])

            del a_stock

        df = pd.DataFrame(data, columns=columns)

        return df
