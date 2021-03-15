import math
from typing import Union, List

import pandas as pd
import requests

from stonks_bot.helper.formatters import formatter_brackets, formatter_to_percent
from stonks_bot.helper.web import get_user_agent


class Stocktwits(object):
    count_per_request: int = 30

    def _get_data(self, url_suffix: str, params: Union[dict, None] = None, headers: Union[dict, bool] = False) -> Union[
        dict, bool]:
        # TODO: Implement rate limit tracking accoding to https://api.stocktwits.com/developers/docs/rate_limiting
        header_ua = {
            'User-Agent': get_user_agent()
        }
        headers = {**header_ua, **headers} if headers else header_ua
        params = params if params else {}
        req_result = requests.get(f'https://api.stocktwits.com/api/2{url_suffix}', params=params, headers=headers)
        result = False

        if req_result.status_code < 500:
            resp = req_result.json()

            return resp

        return result

    def _get_symbol_data(self, symbol: str, count: int = 30) -> List[Union[dict, None]]:
        url_suffix = f'/streams/symbol/{symbol}.json'
        iters = math.ceil(count / self.count_per_request)
        result = []
        max_id = False

        for i in range(iters):
            params = {'max': max_id} if max_id else {}
            tmp_res = self._get_data(url_suffix, params)

            if tmp_res['response']['status'] != 200:
                break

            max_id = tmp_res['cursor']['max']
            result.append(tmp_res)

        return result

    def bullbear(self, symbols: List[str], count: int = 300) -> str:
        columns = ['Company', 'Symbol', 'Count Total', 'Count Bull', 'Count Bear', 'Ratio Bull', 'Ratio Bear', 'Icon']
        data = []

        for s in symbols:
            req_result = self._get_symbol_data(s, count)

            count = 0
            bull = 0
            bear = 0

            for d in req_result:
                for m in d['messages']:
                    if m['entities']['sentiment']:
                        count += 1

                        if m['entities']['sentiment']['basic'] == 'Bullish':
                            bull += 1
                        else:
                            bear += 1

            ratio_bull = bull / count
            ratio_bear = bear / count
            icon = '🚀' if ratio_bull >= 0.5 else '🌈🐻'
            data.append([d['symbol']['title'], d['symbol']['symbol'], count, bull, bear, ratio_bull, ratio_bear, icon])

        df = pd.DataFrame(data, columns=columns)
        df = df.sort_values(columns[0])
        columns_selected = [columns[0], columns[1], columns[-1], columns[5], columns[3]]
        result = df[columns_selected].to_string(header=['Company', 'Sym', '', '% Bull', '#'], index=False,
                                                formatters={columns[0]: '{:.9}'.format,
                                                            columns[5]: formatter_to_percent,
                                                            columns[3]: formatter_brackets})

        return result

    def messages_ticker(self, symbols: List[Union[str, None]], count: int = 30) -> str:
        result = ''
        columns = ['Company', 'Symbol', 'Message']
        data = []

        for s in symbols:
            req_result = self._get_symbol_data(s, count)

            for rr in req_result:
                for m in rr['messages']:
                    data.append([rr['symbol']['title'], rr['symbol']['symbol'], m['body']])

        df = pd.DataFrame(data, columns=columns)
        symbols_unique = df['Symbol'].unique()

        for su in symbols_unique:
            df_sym = df[df[columns[1]] == su]
            company = df_sym.iloc[0][0]
            result += f'<b>{company} ({su})</b>:\n'

            for index, row in df_sym.iterrows():
                result += f"* {row[columns[-1]]}\n---\n"

            result += '\n'

        return result

    def trending(self, count: int = 30) -> str:
        columns = ['Company', 'Symbol', 'Watchlist Count']
        data = []
        url_suffix = '/trending/symbols.json'
        params = {'count': count}

        req_result = self._get_data(url_suffix, params=params)

        for s in req_result['symbols']:
            data.append([s['title'], s['symbol'], s['watchlist_count']])

        df = pd.DataFrame(data, columns=columns)
        df = df.sort_values(columns[-1], ascending=False)

        result = df.head(count).to_string(header=[columns[0], 'Sym', '# Watchl.'], index=False,
                                          formatters={columns[0]: '{:.14}'.format})

        return result
