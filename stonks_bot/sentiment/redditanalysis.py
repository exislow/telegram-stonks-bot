import re
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import List, Union

import pandas as pd
import pytz
import yfinance as yf
from praw import Reddit
from praw.models import Submission
from psaw import PushshiftAPI
from telegram import Update
from telegram.ext import CallbackContext

from stonks_bot import conf, Currency
from stonks_bot.config import Config
from stonks_bot.helper.formatters import formatter_round_currency_scalar, formatter_date, formatter_conditional_no_dec
from stonks_bot.helper.message import reply_message, reply_random_gif


class RedditAnalysis(object):
    conf: Config = None
    context: CallbackContext = None
    update: Update = None
    currency: Currency = None
    currency_api: str = None

    def __init__(self, context: CallbackContext, update: Union[Update, bool] = False):
        self.conf = conf
        self.context = context
        self.update = update
        self.currency = Currency()
        self.currency_api = conf.API['finance_currency']

    def _get_reddit_client(self) -> Reddit:
        client = Reddit(
                client_id=conf.API['reddit']['client_id'],
                client_secret=conf.API['reddit']['client_secret'],
                username=conf.API['reddit']['username'],
                user_agent=conf.API['reddit']['user_agent'],
                password=conf.API['reddit']['password']
        )

        return client

    def wallstreetbets(self, sort: str = 'hot', count: int = 15):
        result = self._posts('wallstreetbets', ['DD', 'News'], sort, count)

        return result

    def mauerstrassenwetten(self, sort: str = 'hot', count: int = 15):
        result = self._posts('mauerstrassenwetten', ['Information', '"Fällige Sorgfalt (DD)"', 'Presse'], sort,
                             count)

        return result

    def investing(self, sort: str = 'hot', count: int = 15):
        result = self._posts('investing', [], sort, count)

        return result

    def stocks(self, sort: str = 'hot', count: int = 15):
        result = self._posts('stocks', ['Advice', 'Resources', '"Company Analysis"', '"Industry News"'], sort, count)

        return result

    def gamestop(self, sort: str = 'hot', count: int = 15):
        result = self._posts('gamestop', [], sort,
                             count)

        return result

    def spielstopp(self, sort: str = 'hot', count: int = 15):
        result = self._posts('spielstopp', ['DD', 'Diskussion'], sort, count)

        return result

    def stockmarket(self, sort: str = 'hot', count: int = 15):
        result = self._posts('StockMarket', ['News', '"Technical Analysis"', '"Fundamentals/DD"', 'Crypto',
                                             '"Education/Lessons Learned"'], sort, count)

        return result

    def daytrading(self, sort: str = 'hot', count: int = 15):
        result = self._posts('Daytrading', [], sort, count)

        return result

    def pennystocks(self, sort: str = 'hot', count: int = 15):
        result = self._posts('pennystocks', ['"Stock Info"', 'DD', '"Tip & Tricks"'], sort, count)

        return result

    def cryptomarkets(self, sort: str = 'hot', count: int = 15):
        result = self._posts('CryptoMarkets', ['NEWS', '"NEW COIN"', 'TECHNICALS', 'WARNING'], sort, count)

        return result

    def satoshistreetbets(self, sort: str = 'hot', count: int = 15):
        result = self._posts('SatoshiStreetBets', ['Moonshot', 'Fundamentals', 'Discussion'], sort, count)

        return result

    def samoyedcoin(self, sort: str = 'hot', count: int = 15):
        result = self._posts('SamoyedCoin', [], sort, count)

        return result

    def _posts(self, sub: str, flair: List[Union[str, None]], sort: str = 'hot', limit: int = 15) -> str:
        praw_api = self._get_reddit_client()
        flair_str = 'flair:'
        flair_str += f"({' OR '.join(flair)})" if len(
            flair) > 0 else '(NOT asdfghdfdafsgdhfffdsgh)'  # Something never occurs
        submissions = praw_api.subreddit(sub).search(flair_str, sort=sort, limit=limit)
        columns = ['created_utc', 'subreddit', 'title', 'link', 'flair', 'score', 'comments_count',
                   'upvote_ratio']
        posts = []

        for s in submissions:
            # Ensure that the post hasn't been removed  by moderator in the meanwhile,
            # that there is a description and it's not just an image, that the flair is
            # meaningful, and that we aren't re-considering same author's watchlist
            if not s.removed_by_category:
                # Refactor date
                datetime_creation = datetime.fromtimestamp(s.created_utc, tz=timezone.utc).astimezone(
                        pytz.timezone('Europe/Berlin'))
                link = f'https://www.reddit.com{s.permalink}'

                # Create dictionary with data to construct dataframe allows to save data
                posts.append([datetime_creation, s.subreddit, s.title, link, s.link_flair_text, s.score, s.num_comments,
                              s.upvote_ratio])

        df = pd.DataFrame(posts, columns=columns)
        df = df.sort_values(by=columns[5], ascending=False)
        result_html = ''

        for idx, r in df.iterrows():
            result_html += f'* <a href="{r[columns[3]]}">{r[columns[2]].replace("<", "&lt;").replace(">", "&gt;")}</a>\n -> <b>{r[columns[4]]}</b>; Score:'
            result_html += f'{r[columns[5]]}; # Com.: {r[columns[6]]}; UpV Ratio: {r[columns[-1]]}\n'

        return result_html

    def popular_symbols(self, days: int = 1, limit: int = 30, convert_currency: bool = True) -> str:
        subs = ['pennystocks', 'Daytrading', 'StockMarket', 'stocks', 'investing', 'wallstreetbets',
                'mauerstrassenwetten']
        columns = ['Company', 'Symbol', 'Mentions', 'Price', '% 1mo.', 'Earnings Date', 'Earnings Days Left']
        data = []
        timestamp_after = int((datetime.today() - timedelta(days=days)).timestamp())
        psaw_api = PushshiftAPI()
        praw_api = self._get_reddit_client()
        tickers = []

        for sub in subs:
            comments = psaw_api.search_submissions(after=timestamp_after, subreddit=sub, limit=limit, filter=['id'])

            for c in comments:
                try:
                    t = praw_api.submission(id=c.id)

                    if not t.removed_by_category and (t.selftext or t.title):
                        tickers += self._find_tickers(t)
                except Exception as e:
                    # TODO: If HTTP 5xx save datetime to bot_data and do not execute for x minutes.
                    msg = '💔 The remote data source is having issues or has blocked me. Try again MUCH later.'

                    if self.update:
                        reply_message(self.update, msg)
                        reply_random_gif(self.update, 'bot broken')

                    raise e

        if len(tickers) > 0:
            now = datetime.now()
            tickers_stats = dict(Counter(tickers))
            tickers_dedup = list(tickers_stats.keys())

            # TODO: Refactor to own method.
            blacklist = ['YOLO', 'LMAO', 'LOL', 'MOFO', 'HAHA', 'DFV', 'WSB', 'MSW', 'CEO', 'CTO', 'CFO', 'CIO', 'USER']
            tickers_clean = [t for t in tickers_dedup if t not in blacklist]

            history = yf.download(' '.join(tickers_clean), period='1mo', prepost=True, actions=False, progress=False,
                                  group_by='ticker')
            tickers_not_existing = list(yf.shared._ERRORS.keys())
            tickers_existing = [t for t in tickers_clean if t not in tickers_not_existing]
            tickers = yf.Tickers(' '.join(tickers_existing))

            for symbol in tickers_existing:
                try:
                    t = getattr(tickers.tickers, symbol)
                    t_info = t.info
                except:
                    continue

                earnings_date = None
                earnings_days_left = None

                if t.calendar is not None:
                    if len(t.calendar.T) > 0:
                        earnings_date = t.calendar.iloc[:, 0]['Earnings Date']
                        earnings_days_left = (earnings_date - now).days

                price = history[symbol]['Close'][-1]
                perf_1mo = (price / history[symbol]['Open'][0]) - 1
                # TODO: Refactor with stonk.py (extract method or something like this).
                name = t_info.get('longName', t_info.get('shortName', t_info.get('name', 'ERROR_IN_NAME_RETRIEVAL')))

                data.append([name, symbol, tickers_stats[symbol], price, perf_1mo, earnings_date, earnings_days_left])

            df = pd.DataFrame(data, columns=columns)

            if convert_currency:
                columns_to_convert = [columns[3]]
                df = self.currency.convert_to_currency_df(self.currency_api, df, columns_to_convert)

            df = df.sort_values(by=columns[2], ascending=False)
            result = df[columns[:-1]].to_string(header=['Company', 'Sym', '#', 'Price', '% 1mo', 'Earn.📅'],
                                                index=False, formatters={columns[0]: '{:.9}'.format,
                                                                         columns[3]: formatter_round_currency_scalar,
                                                                         columns[4]: formatter_conditional_no_dec,
                                                                         columns[5]: formatter_date})
        else:
            result = 'No symbols could be found. Try again later.'

        return result

    def _find_tickers(self, submission: Submission) -> List[str]:
        tickers = list()
        text_extracted = list()
        text_extracted.append(submission.selftext)
        text_extracted.append(submission.title)

        submission.comments.replace_more(limit=0)

        for comment in submission.comments.list():
            text_extracted.append(comment.body)

        for t in text_extracted:
            for ticker in set(re.findall(r'([A-Z]{3,5})(\.[A-Z]{1,2})?\s', t)):
                tickers.append(''.join(ticker).strip())

        return tickers

    def a(self):
        pass
