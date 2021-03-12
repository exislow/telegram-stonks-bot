from datetime import datetime
from io import BytesIO
from typing import Union

import pandas as pd
import requests
import yfinance as yf

from stonks_bot import c, conf, Currency
from stonks_bot.dataclasses.performance import Performance
from stonks_bot.dataclasses.price_daily import PriceDaily
from stonks_bot.helper.exceptions import InvalidSymbol
from stonks_bot.helper.math import round_currency_scalar
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

    def __init__(self, symbol: str) -> None:
        self._symbol_validate(symbol)

        if self.is_valid:
            self._set_currency(self.symbol)
            yf_ticker = yf.Ticker(self.symbol)
            self._set_name(yf_ticker)
            self._set_isin(yf_ticker)

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

    def _set_isin(self, yf_ticker: yf.Ticker) -> None:
        self.isin = yf_ticker.isin

    def _convert_to_local_currency(self, yf_df: pd.DataFrame) -> pd.DataFrame:
        result = yf_df
        c = Currency()

        if self.currency_api != c.currency_local:
            result = c.convert_to_currency(self.currency_api, result, ['Open', 'High', 'Low', 'Close', 'Adj Close'])

        return result

    def _symbol_search(self, needle: str) -> Union[str, bool]:
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        params = {'q': needle, 'quotesCount': 1, 'newsCount': 0}
        r = requests.get(url, params=params)
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
            # TODO: Log it / send it to master
            raise Exception(yf_df).with_traceback(e.__traceback__)

        return yf_df

    def _get_financials_adjusted(self, period: str = '1d', interval: str = '15m') -> pd.DataFrame:
        yf_df = self._financial_download(period, interval)
        yf_df = self._convert_to_local_currency(yf_df)
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
