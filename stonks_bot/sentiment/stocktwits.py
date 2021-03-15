import math
from typing import Union, List

import pandas as pd
import requests

from stonks_bot.helper.formatters import formatter_brackets, formatter_to_percent
from stonks_bot.helper.web import get_user_agent


class Stocktwits(object):
    count_per_request: int = 30

    def _get_data(self, url_suffix: str, params: Union[dict, None] = None) -> Union[dict, bool]:
        # TODO: Implement rate limit tracking accoding to https://api.stocktwits.com/developers/docs/rate_limiting
        headers = {
            'User-Agent': get_user_agent()
        }
        params = params if params else {}
        req_result = requests.get(f'https://api.stocktwits.com/api/2{url_suffix}', headers=headers, params=params)
        result = False

        if req_result.status_code < 500:
            resp = req_result.json()

            return resp

        return result

    def bullbear(self, symbols: List[Union[str, None]], count: int = 300) -> str:
        result = False
        columns = ['Company', 'Symbol', 'Count Total', 'Count Bull', 'Count Bear', 'Ratio Bull', 'Ratio Bear', 'Icon']
        data = []
        iters = math.ceil(count / self.count_per_request)

        for s in symbols:
            url_suffix = f'/streams/symbol/{s}.json'
            req_result = []

            for i in range(iters):
                tmp_res = self._get_data(url_suffix)

                if tmp_res['response']['status'] != 200:
                    break

                req_result.append(tmp_res)

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
