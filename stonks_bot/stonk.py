from datetime import datetime, timedelta
from io import BytesIO
from typing import Union

import pandas as pd
import requests
import yfinance as yf
from tabulate import tabulate, simple_separated_format

from stonks_bot import conf, Currency
from stonks_bot.dataclasses.performance import Performance
from stonks_bot.dataclasses.price_daily import PriceDaily
from stonks_bot.dataclasses.stonk_details import StonkDetails
from stonks_bot.helper.exceptions import InvalidSymbol
from stonks_bot.helper.math import round_currency_scalar, change_percent, round_percent
from stonks_bot.helper.plot import PlotContext


class Stonk(object):
    symbol: str = None
    is_valid: bool = False
    name: str = None
    isin: str = None
    currency_api: str = None
    added_at: datetime = datetime.now()
    daily_rise: Performance = Performance()
    daily_fall: Performance = Performance()
    recommendation: str = None
    current_price: float = None
    percent_change_52w: float = None
    volume: int = None
    price_52w_high: float = None
    price_52w_low: float = None
    market_capitalization: float = None

    def __init__(self, symbol: str) -> None:
        # Set global requests settings
        header = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:93.0) Gecko/20100101 Firefox/93.0',
            'Accept-Encoding': 'gzip, deflate',
            'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,'
                      '*/*;q=0.8',
            'Accept-Language': 'en-US;q=0.7,en;q=0.3',
            'Dnt': '1',
            # 'Host': 'https://query2.finance.yahoo.com',
            'Referer': 'https://query2.finance.yahoo.com',
            'Te': 'trailers',
            'Sec-Fetch-Dest': 'document'
        }
        self._req_session = requests.Session()
        self._req_session.headers.update(header)

        self._symbol_validate(symbol)

        if self.is_valid:
            self._set_currency(self.symbol)
            yf_ticker = yf.Ticker(self.symbol)
            self._populate_data(yf_ticker)

    def _set_currency(self, symbol: str) -> None:
        symbol_split = symbol.split('-')

        if len(symbol_split) > 1:
            self.currency_api = symbol_split[-1]
        else:
            self.currency_api = conf.API['finance_currency']

    def _symbol_validate(self, symbol: str) -> None:
        symbol_result = self._symbol_search(symbol)

        if symbol_result:
            self.is_valid = True
            self.symbol = symbol_result
        else:
            raise InvalidSymbol()

    def _set_name(self, yf_ticker: yf.Ticker) -> None:
        self.name = yf_ticker.info.get('longName', yf_ticker.info.get('shortName',
                                                                      yf_ticker.info.get('name',
                                                                                         'ERROR_IN_NAME_RETRIEVAL')))

    def _populate_data(self, yf_ticker: yf.Ticker) -> None:
        self._set_name(yf_ticker)
        self._set_isin(yf_ticker)
        self._set_info_data(yf_ticker)

    def _set_isin(self, yf_ticker: yf.Ticker) -> None:
        self.isin = yf_ticker.get_isin()

    def _set_info_data(self, yf_ticker: yf.Ticker) -> None:
        info = yf_ticker.get_info()
        self.recommendation = info['recommendationKey'] if 'recommendationKey' in info else 'N/A'
        self.percent_change_52w = info['52WeekChange']
        self.volume = info['volume']
        prices_to_convert = {
            'current_price': info['preMarketPrice'] if info['preMarketPrice'] else info['currentPrice'],
            'price_52w_high': info['fiftyTwoWeekHigh'],
            'price_52w_low': info['fiftyTwoWeekLow']
        }
        prices_converted = self._convert_to_local_currency(prices_to_convert)
        self.current_price = prices_converted['current_price']
        self.price_52w_high = prices_converted['price_52w_high']
        self.price_52w_low = prices_converted['price_52w_low']
        self.market_capitalization = self.volume * self.current_price

    def _convert_to_local_currency(self, values: dict) -> dict:
        result = values
        c = Currency()

        if self.currency_api != c.currency_local:
            result = c.convert_to_currency(self.currency_api, values)

        return result

    def _convert_to_local_currency_df(self, yf_df: pd.DataFrame) -> pd.DataFrame:
        result = yf_df
        c = Currency()

        if self.currency_api != c.currency_local:
            result = c.convert_to_currency_df(self.currency_api, result, ['Open', 'High', 'Low', 'Close', 'Adj Close'])

        return result

    def _symbol_search(self, needle: str) -> Union[str, bool]:
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        params = {'q': needle, 'quotesCount': 1, 'newsCount': 0}
        r = self._req_session.get(url, params=params)
        data = r.json()

        symbol = False

        if len(data['quotes']) > 0:
            symbol = data['quotes'][0]['symbol']

        return symbol

    def _financial_download(self, period: str = '1d', interval: str = '15m') -> pd.DataFrame:
        yf_df = yf.download(tickers=self.symbol, period=period, interval=interval, group_by='ticker', prepost=True)

        return yf_df

    def _convert_to_local_time(self, yf_df):
        try:
            if yf_df.index.tzinfo is not None and yf_df.index.tzinfo.utcoffset(yf_df.index) is not None:
                yf_df.index = yf_df.index.tz_convert(conf.LOCAL['tz'])
        except AttributeError as e:
            raise Exception((yf_df, f'Symbol: {self.symbol}')).with_traceback(e.__traceback__)

        return yf_df

    def _get_financials_adjusted(self, period: str = '1d', interval: str = '15m') -> pd.DataFrame:
        yf_df = self._financial_download(period, interval)
        yf_df = self._convert_to_local_currency_df(yf_df)
        yf_df = self._convert_to_local_time(yf_df)

        return yf_df

    def chart(self) -> BytesIO:
        yf_df = self._get_financials_adjusted('1d', '15m')
        with PlotContext() as pc:
            chart_buf = pc.create_candle_chart(yf_df, self.name, self.symbol)

        return chart_buf

    def price_daily(self) -> PriceDaily:
        yf_df = self._get_financials_adjusted('1d', '1d')
        pd = PriceDaily(open=round_currency_scalar(yf_df.Open[0]),
                        high=round_currency_scalar(yf_df.High[0]),
                        low=round_currency_scalar(yf_df.Low[0]),
                        close=round_currency_scalar(yf_df.Close[0]))

        return pd

    def calculate_perf_rise_fall_daily(self) -> bool:
        yf_df = self._get_financials_adjusted(period='1d', interval='1m')
        price_date = yf_df.index[0].date()
        price_open = yf_df.Open[0]
        price_max = yf_df.Close.max()
        price_min = yf_df.Open.min()
        datetime_now = datetime.now()
        date_now = datetime_now.date()

        if price_date == date_now:
            if self.daily_rise.calculated_at.date() < date_now:
                if price_max > price_open:
                    percent = (((price_max / price_open) - 1) * 100)

                    self.daily_rise.price = price_max
                    self.daily_rise.percent = percent
                    self.daily_rise.calculated_at = datetime_now

            if self.daily_fall.calculated_at.date() < date_now:
                if price_min < price_open:
                    percent = (((price_min / price_open) - 1) * 100)

                    self.daily_fall.price = price_min
                    self.daily_fall.percent = percent
                    self.daily_fall.calculated_at = datetime_now
            return True
        else:
            return False

    def upcoming_earning(self):
        t = yf.Ticker(self.symbol)
        result = False

        if t.calendar is not None:
            result = t.calendar.iloc[:, 0]['Earnings Date']

        return result

    def details_price(self) -> StonkDetails:
        yf_df_2d_hourly = self._get_financials_adjusted('2d', '1h')
        yf_df_1y_daily = self._get_financials_adjusted('1y', '1d')
        d_24h = datetime.today() - timedelta(hours=24)
        d_7d = datetime.today() - timedelta(days=7)
        d_30d = datetime.today() - timedelta(days=30)
        d_52w = datetime.today() - timedelta(weeks=52)
        d_ytd = datetime(datetime.now().year, 1, 1)

        price_24h_high = yf_df_2d_hourly.High[d_24h:].max()
        price_24h_low = yf_df_2d_hourly.Low[d_24h:].min()
        percent_change_1h = change_percent(yf_df_2d_hourly.Close[-2], self.current_price)
        percent_change_24h = change_percent(yf_df_2d_hourly.Close[:d_24h][-1], self.current_price)
        percent_change_7d = change_percent(yf_df_1y_daily.Close[:d_7d][-1], self.current_price)
        percent_change_30d = change_percent(yf_df_1y_daily.Close[:d_30d][-1], self.current_price)
        percent_change_52w = change_percent(yf_df_1y_daily.Close[:d_52w][-1], self.current_price)
        percent_change_ytd = change_percent(yf_df_1y_daily.Close[d_ytd:][1], self.current_price)

        sd = StonkDetails(price=self.current_price, price_24h_high=price_24h_high, price_24h_low=price_24h_low,
                          price_52w_high=self.price_52w_high, price_52w_low=self.price_52w_low,
                          percent_change_1h=percent_change_1h,
                          percent_change_24h=percent_change_24h, percent_change_7d=percent_change_7d,
                          percent_change_30d=percent_change_30d, percent_change_52w=percent_change_52w,
                          percent_change_ytd=percent_change_ytd, volume=self.volume,
                          market_capitalization=self.market_capitalization,
                          recommendation=self.recommendation)

        return sd

    def details_price_textual(self) -> str:
        sd = self.details_price()

        data = [{
            conf.LOCAL['currency']: round_currency_scalar(sd.price),
            '24h H': round_currency_scalar(sd.price_24h_high),
            '24h L': round_currency_scalar(sd.price_24h_low),
            '52w H': round_currency_scalar(sd.price_52w_high),
            '52w L': round_currency_scalar(sd.price_52w_low),
            '% 1h': round_percent(sd.percent_change_1h),
            '% 24h': round_percent(sd.percent_change_24h),
            '% 7d': round_percent(sd.percent_change_7d),
            '% 30d': round_percent(sd.percent_change_30d),
            '% 52w': round_percent(sd.percent_change_52w),
            '% YTD': round_percent(sd.percent_change_ytd),
            'Vol': sd.volume,
            'Cap': round_currency_scalar(sd.market_capitalization),
            # 'Recom': sd.recommendation
        }]

        # Creates pandas DataFrame by passing
        # Lists of dictionaries and row index.
        df = pd.DataFrame(data, index=[self.symbol])
        df_T = df.T
        tablefmt = simple_separated_format(': ')
        text = tabulate(df_T, tablefmt=tablefmt, colalign=('right', 'decimal'))
        text = ''.join((f'       {self.symbol}\n',
                    f'{text}\n',
                    f'Recom: {sd.recommendation}'
                    ))

        return text
