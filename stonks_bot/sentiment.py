from datetime import datetime, timezone
from typing import List, Union

import pytz
import pandas as pd
from praw import Reddit

from stonks_bot import conf
from stonks_bot.config import Config


class Sentiment(object):
    conf: Config

    def __init__(self):
        self.conf = conf

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
        result = self.reddit('wallstreetbets', ['DD', 'News'], sort, count)

        return result

    def mauerstrassenwetten(self, sort: str = 'hot', count: int = 15):
        result = self.reddit('mauerstrassenwetten', ['Information', 'Fällige Sorgfalt (DD)', 'Presse'], sort, count)

        return result

    def reddit(self, sub: str, flair: List[Union[str, None]], sort: str = 'hot', limit: int = 15) -> str:
        praw_api = self._get_reddit_client()
        submissions = praw_api.subreddit(sub).search(f"flair:{' OR '.join(flair)}", sort=sort, limit=limit)
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
                print (datetime_creation)
                link = f'https://www.reddit.com{s.permalink}'

                # Create dictionary with data to construct dataframe allows to save data
                posts.append([datetime_creation, s.subreddit, s.title, link, s.link_flair_text, s.score, s.num_comments,
                              s.upvote_ratio])

        df = pd.DataFrame(posts, columns=columns)
        df = df.sort_values(by=columns[5], ascending=False)
        result_html = ''

        for idx, r in df.iterrows():
            result_html += f"""* <a href="{r[columns[3]]}">{r[columns[2]]}</a>\n -> <b>{r[columns[4]]}</b>; Score: {r[columns[5]]}; # Com.: {r[columns[6]]}; UpV Ratio: {r[columns[-1]]}\n"""

        return result_html
