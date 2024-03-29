import json
import re
from datetime import date, timedelta
from io import BytesIO

import pandas as pd
import requests
from alpha_vantage.sectorperformance import SectorPerformances
from bs4 import BeautifulSoup
from yahoo_earnings_calendar import YahooEarningsCalendar

from stonks_bot import conf, Currency
from stonks_bot.helper.exceptions import BackendDataNotFound
from stonks_bot.helper.formatters import formatter_date, formatter_shorten_1, formatter_round_currency_scalar, \
    formatter_conditional_no_dec
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
    currency_api: str = None
    currency: Currency = None

    def __init__(self):
        self.currency_api = conf.API['finance_currency']
        self.currency = Currency()

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
        columns = ['startdatetime', 'companyshortname', 'ticker']
        result = pd_ue[columns].to_string(header=False, index=False, formatters={columns[0]: formatter_date,
                                                                                 columns[1]: '{:.15}'.format})

        return result

    def gainers(self, count: int = 15) -> str:
        url = f'https://finance.yahoo.com/gainers?offset=0&count={count}'
        result = self.get_daily_performers(url)

        return result

    def losers(self, count: int = 15) -> str:
        url = f'https://finance.yahoo.com/losers?offset=0&count={count}'
        result = self.get_daily_performers(url)

        return result

    def undervalued_large_caps(self, count: int = 15) -> str:
        url = f'https://finance.yahoo.com/screener/predefined/undervalued_large_caps?offset=0&count={count}'
        result = self.get_daily_performers(url)

        return result

    def undervalued_growth(self, count: int = 15) -> str:
        url = f'https://finance.yahoo.com/screener/predefined/undervalued_growth_stocks?offset=0&count={count}'
        result = self.get_daily_performers(url)

        return result

    def get_daily_performers(self, yf_url: str, convert_currency: bool = True) -> str:
        resp = requests.get(yf_url, headers={'User-Agent': get_user_agent()})
        regex = r'root\.App\.main = .*}\(this\)\);'
        matches = re.search(regex, resp.text, re.DOTALL)

        if not matches:
            error_msg = 'Backend data not found. Please contact an administrator.'

            raise BackendDataNotFound(error_msg)

        json_str = matches.group(0).replace('\n', '').replace('\r', '').replace('root.App.main = ', '').replace(
                ';}(this));', '')
        result = json.loads(json_str)
        columns = ['Name', 'Symbol', 'Price (Intraday)', 'Change', '% Change']
        df_data = list()

        for row in result['context']['dispatcher']['stores']['ScreenerResultsStore']['results']['rows']:
            df_data.append([
                row['shortName'], row['symbol'], row['regularMarketPrice']['raw'], row['regularMarketChange']['raw'],
                row['regularMarketChangePercent']['raw'],
            ])

        df = pd.DataFrame(df_data, columns=columns)

        if convert_currency:
            columns_to_convert = [columns[2], columns[3]]
            df = self.currency.convert_to_currency_df(self.currency_api, df, columns_to_convert)

        result = df[columns].to_string(header=['Company', 'Sym', 'Price', '±', '%'],
                                       index=False, formatters={columns[0]: '{:.9}'.format,
                                                                columns[2]: formatter_round_currency_scalar,
                                                                columns[3]: formatter_round_currency_scalar,
                                                                columns[4]: formatter_conditional_no_dec})

        return result

    def orders(self, count: int = 15) -> str:
        url = f'https://finance.yahoo.com/most-active?offset=0&count={count}'
        df = pd.read_html(url)[0]
        columns = ['Name', 'Symbol', 'Volume']
        result = df[columns].to_string(header=['Company', 'Sym', 'Volume'],
                                       index=False, formatters={columns[0]: '{:.15}'.format})

        return result

    def high_short(self, count: int = 15) -> str:
        url = 'https://www.highshortinterest.com/'
        result = self.get_short_float(url, count)

        return result

    def low_float(self, count: int = 15) -> str:
        url = 'https://www.lowfloat.com/'
        result = self.get_short_float(url, count)

        return result

    def get_short_float(self, url: str, count: int = 15) -> str:
        df = self.get_short_float_penny(url)
        columns = ['Company', 'Ticker', 'ShortInt', 'Float', 'Outstd']
        result = df[columns].head(n=count).to_string(header=['Company', 'Sym.', 'SI %', 'Float', 'Outstd'],
                                                     index=False,
                                                     formatters={columns[0]: '{:.9}'.format,
                                                                 columns[2]: formatter_shorten_1})

        return result

    def hot_pennystocks(self, count: int = 15, convert_currency: bool = True) -> str:
        url = 'https://www.pennystockflow.com/'
        df = self.get_short_float_penny(url)
        columns = ['Ticker', '# Trades', 'Price', 'Change']
        # Remove the $ symbol.
        df[columns[2]] = df['Price'].str.slice(start=1)
        df[columns[2]] = pd.to_numeric(df[columns[2]], errors='coerce')

        if convert_currency:
            columns_to_convert = [columns[2]]
            df = self.currency.convert_to_currency_df(self.currency_api, df, columns_to_convert)

        result = df[columns].head(n=count).to_string(header=['Sym.', 'Trades', 'Price', '±%'], index=False,
                                                     formatters={columns[2]: formatter_round_currency_scalar,
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
