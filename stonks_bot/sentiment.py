from datetime import datetime

from praw import Reddit

from stonks_bot.config import Config
from stonks_bot import conf


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

    def wsb_community(self):
        praw_api = self._get_reddit_client()

        d_submission = {}
        l_watchlist_links = list()


        if False:
            submissions = praw_api.subreddit('wallstreetbets').new(
                    limit=15
            )
        else:
            submissions = praw_api.subreddit('wallstreetbets').hot(
                    limit=15
            )

        submissions = praw_api.subreddit('wallstreetbets').search('flair:dd', sort='hot')

        for s in submissions:
            # Get more information about post using PRAW api

            # Ensure that the post hasn't been removed  by moderator in the meanwhile,
            # that there is a description and it's not just an image, that the flair is
            # meaningful, and that we aren't re-considering same author's watchlist
            if not s.removed_by_category:

                l_watchlist_links.append(
                        f'https://www.reddit.com{s.permalink}'
                )

                # Refactor data
                s_datetime = datetime.utcfromtimestamp(
                        s.created_utc
                ).strftime('%d/%m/%Y %H:%M:%S')
                s_link = f'https://www.reddit.com{s.permalink}'
                s_all_awards = ''
                for award in s.all_awardings:
                    s_all_awards += f"{award['count']} {award['name']}\n"
                s_all_awards = s_all_awards[:-2]

                # Create dictionary with data to construct dataframe allows to save data
                d_submission[s.id] = {
                    'created_utc': s_datetime,
                    'subreddit': s.subreddit,
                    'link_flair_text': s.link_flair_text,
                    'title': s.title,
                    'score': s.score,
                    'link': s_link,
                    'num_comments': s.num_comments,
                    'upvote_ratio': s.upvote_ratio,
                    'awards': s_all_awards,
                }

                # Print post data collected so far
                print(f'{s_datetime} - {s.title}')
                print(f'{s_link}')
                # t_post = PrettyTable(
                #         [
                #             'Subreddit',
                #             'Flair',
                #             'Score',
                #             '# Comments',
                #             'Upvote %',
                #             'Awards',
                #         ]
                # )
                # t_post.add_row(
                #         [
                #             submission.subreddit,
                #             submission.link_flair_text,
                #             submission.score,
                #             submission.num_comments,
                #             f'{round(100*submission.upvote_ratio)}%',
                #             s_all_awards,
                #         ]
                # )
                # print(t_post)
                # print('')
        # Check if search_submissions didn't get anymore posts
