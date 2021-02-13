from datetime import datetime
from typing import Union

import yfinance as yf

from stonks_bot.dataclasses.currency_exchange import CurrencyExchange
from stonks_bot import conf


class Currency(object):
    store: dict = dict()
    currency_local: str = conf.LOCAL['currency']

    def get_exchange_rate(self, symbol: str) -> float:
        rate_store = self.retrieve_exchange_rate_from_store(symbol)

        if not rate_store:
            result = self._fetch_exchange_rate(symbol)
            ce = CurrencyExchange(symbol=symbol)
            ce.rate = result
            self.store[symbol] = ce
        else:
            result = rate_store

        return result

    def retrieve_exchange_rate_from_store(self, symbol: str) -> Union[bool, float]:
        result = False

        if symbol in self.store:
            ce = self.store[symbol]

            if ce.fetched_at.date() == datetime.now().date():
                result = ce.rate
            else:
                result = ce.rate = self._fetch_exchange_rate(symbol)

        return result

    def _fetch_exchange_rate(self, symbol: str) -> Union[float]:
        yf_df = yf.download(tickers=f'{symbol}{self.currency_local}=X', period='1d', group_by='ticker')
        adj_close = yf_df[conf.OHLC['adj_close']]

        if len(adj_close) > 0:
            rate = adj_close[0]
        else:
            rate = 1.0

        return rate
