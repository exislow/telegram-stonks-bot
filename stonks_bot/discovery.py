from datetime import date, timedelta
from io import BytesIO

import pandas as pd
from alpha_vantage.sectorperformance import SectorPerformances
from dateutil import parser
from yahoo_earnings_calendar import YahooEarningsCalendar

from stonks_bot import conf
from stonks_bot.helper.plot import PlotContext

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
        ].to_string(header=False, index=False, formatters={'startdatetime': self._formatter_date,
                                                           'companyshortname': '{:.15}'.format})

        return result

    def gainers(self, count: int = 15):
        url = f'https://finance.yahoo.com/gainers?offset=0&count={count}'
        result = self.get_daily_performers(url)

        return result

    def losers(self, count: int = 15):
        url = f'https://finance.yahoo.com/losers?offset=0&count={count}'
        result = self.get_daily_performers(url)

        return result

    def get_daily_performers(self, yf_url: str):
        df_gainers = pd.read_html(yf_url)[0]
        result = df_gainers[
            ['Name', 'Symbol', 'Price (Intraday)', 'Change', '% Change']
        ].to_string(header=['Company', 'Sym', 'Price', '+-', '%'],
                    index=False, formatters={'startdatetime': self._formatter_date,
                                             'Name': '{:.10}'.format,
                                             '% Change': self._formatter_shorten_1})

        return result

    def _formatter_date(self, datetime_str: str) -> str:
        dt = parser.isoparse(datetime_str)

        return dt.strftime('%m-%d')

    def _formatter_shorten_1(self, text):
        return text[:-1]
