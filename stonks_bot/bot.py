#!/usr/bin/env python
# pylint: disable=W0613, C0116
# type: ignore[union-attr]

"""
Simple Bot to send timed Telegram messages.
This Bot uses the Updater class to handle the bot and the JobQueue to send
timed messages.
First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Basic Alarm Bot example, sends a message after a set time.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""
import html
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Union, NoReturn, List

import pandas as pd
from telegram import Message, error, Update, Chat, ParseMode
from telegram.ext import (
    Updater, CommandHandler, CallbackContext, ChatMemberHandler, PicklePersistence, MessageHandler, Filters
)

from stonks_bot import conf
from stonks_bot.discovery import Discovery
from stonks_bot.helper.args import parse_symbols, parse_daily_perf_count, parse_reddit
from stonks_bot.helper.command import restricted_command, send_typing_action, check_symbol_limit, log_error
from stonks_bot.helper.data import factory_defaultdict
from stonks_bot.helper.exceptions import InvalidSymbol
from stonks_bot.helper.formatters import formatter_conditional_no_dec, formatter_to_json
from stonks_bot.helper.handler import error_handler, track_chats, greet_chat_members, log_message_handler, \
    bot_removed_from
from stonks_bot.helper.math import round_currency_scalar
from stonks_bot.helper.message import reply_with_photo, reply_symbol_error, reply_message, send_photo, \
    reply_command_unknown, send_message, reply_random_gif
from stonks_bot.sentiment.redditanalysis import RedditAnalysis
from stonks_bot.sentiment.stocktwits import Stocktwits
from stonks_bot.stonk import Stonk

# General logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
log_level = logging.DEBUG if conf.DEBUG else logging.ERROR
logger.setLevel(log_level)


@log_error(error_handler, 'Command does not exist.')
def command_unknown(update: Update, context: CallbackContext) -> NoReturn:
    reply_command_unknown(update)


def start(update: Update, context: CallbackContext) -> NoReturn:
    help(update, context)


def help(update: Update, context: CallbackContext) -> NoReturn:
    reply = """Hi ape, I am the STONKS BOT! Try to use the following commands:
* /help | /h -> This help.
Fundamental:
* /chart [<SYMBOLs/ISINs>] | /c -> Plot the last trading day of a stock.
* /price | /p [<SYMBOLs/ISINs>] -> Get details about the stonk price
* /details | /d [<SYMBOLs/ISINs>] -> Shortcut for /chart & /price.
* /stonk_add [<SYMBOLs/ISINs>] | /sa -> Add a stock to the watchlist.
* /stonk_del [<SYMBOLs/ISINs>] | /sd -> Delete a stock from the watchlist.
* /stonk_list | /sl -> Show the watchlist.
* /stonk_clear | /sc -> Clears the watchlist (not allowed in group chats).
* /list_price | /lp -> List watchlist prices.

Discovery:
* /discovery | /di -> Useful infos to find hot stocks.
* /sector_performance | /sp -> Show sector daily performance.
* /upcoming_earnings | /ue -> Show upcoming earning dates.
* /stonk_upcoming_earnings | /sue -> Show upcoming earning dates for watched stonks.
* /gainers (<count>) | /g -> Show daily gainers.
* /losers (<count>) | /l -> Show daily losers.
* /orders (<count>) | /o -> Show daily high volume stonks.
* /high_short (<count>) | /hs -> Show stonks with high short interest.
* /low_float (<count>) | /lf -> Show stonks with low float.
* /hot_penny (<count>) | /hp -> Show hot penny stonks.
* /underval_large (<count>) | /ul -> Show undervalued large cap stonks.
* /underval_growth (<count>) | /ug -> Show undervalued growth stonks.

Sentiment:
* /wallstreetbets (<sort={hot, rising, new} count>) | /wsb -> Show relevant r/wallstreetbets posts.
* /mauerstrassenwetten (<sort={hot, rising, new} count>) | /msw -> Zeige relevante r/mauerstrassenwetten Einträge.
* /investing (<sort={hot, rising, new} count>) | /ri -> Show relevant r/investing posts.
* /rstocks (<sort={hot, rising, new} count>) | /rs -> Show relevant r/stocks posts.
* /gamestop (<sort={hot, rising, new} count>) | /gme -> Show relevant r/gamestop posts.
* /spielstopp (<sort={hot, rising, new} count>) | /rss -> Show relevant r/spielstopp posts.
* /stockmarket (<sort={hot, rising, new} count>) | /rsm -> Show relevant r/stockmarket posts.
* /daytrading (<sort={hot, rising, new} count>) | /rdt -> Show relevant r/daytrading posts.
* /pennystocks (<sort={hot, rising, new} count>) | /rps -> Show relevant r/pennystocks posts.
* /cryptomarkets (<sort={hot, rising, new} count>) | /rcm -> Show relevant r/cryptomarkets posts.
* /satoshistreetbets (<sort={hot, rising, new} count>) | /ssb -> Show relevant r/satoshistreetbets posts.
* /rsamoyedcoin (<sort={hot, rising, new} count>) | /rsc -> Show relevant r/samoyedcoin posts.
* /popular_symbols (<sort={hot, rising, new} count>) | /ps -> Show popular symbols from Reddit.
* /bullbear [<SYMBOLs>] | /bb -> Bull / Bear analysis for chosen symbols.
* /stock_messages [<SYMBOLs>] | /sm -> Get the latest TwitStock messages for chosen symbols.
* /trending_symbols | /ts -> Get the latest trending symbols from TwitStock.
"""

    reply_message(update, reply)


@restricted_command(error_handler, 'Command execution forbidden (restricted access).')
def help_admin(update: Update, context: CallbackContext) -> NoReturn:
    reply = """Hi admin, I am the STONKS BOT! You are allowed to use the following commands:
* /stonk_clear | /sc -> Clears the watchlist.
* /all_stonk_clear | /asc -> Clears the watchlist of every user.
* /exec_job_check_rise_fall | /ejcrf -> Executes check_rise_fall immediately.
* /all_stonk_clear | /asc -> Clears all stonk lists of all chats.
* /bot_list_all_data | /blad -> Lists internal data storage.
* /show_chats -> Lists all chats.
* /chat_data_reset | /acdr -> Clear all chat data in `bot_data`.
"""

    reply_message(update, reply)


@restricted_command(error_handler, 'Command execution forbidden (restricted access).')
def show_chats(update: Update, context: CallbackContext) -> None:
    """Shows which chats the bot is in"""
    users = ''
    groups = ''
    channels = ''

    for key, user in context.bot_data.setdefault(conf.INTERNALS['users'], {}).items():
        users += f'{user.chat.username} ({user.chat.id}),'
    users = users[:-1] if users != '' else 'N/A'

    for key, group in context.bot_data.setdefault(conf.INTERNALS['groups'], {}).items():
        groups += f'{group.chat.title} ({group.chat.id}) by {group.cause_user.username} ({group.cause_user.id}),'
    groups = groups[:-1] if groups != '' else 'N/A'

    for key, channel in context.bot_data.setdefault(conf.INTERNALS['channels'], {}).items():
        channels += f'{channel.chat.title} ({channel.chat.id}) by {channel.cause_user.username} (' \
                    f'{channel.cause_user.id}),'
    channels = channels[:-1] if channels != '' else 'N/A'
    text = (
        f'Users: {users}.\n\n'
        f'Groups: {groups}.\n\n'
        f'Channels: {channels}.'
    )

    reply_message(update, text, parse_mode=ParseMode.HTML, pre=True)


@restricted_command(error_handler, 'Command execution forbidden (restricted access).')
def chat_data_reset(update: Update, context: CallbackContext) -> None:
    """Removes all chat data, e.g. in case of data structure changes. Tries to leave the chats in advance."""
    bot = context.bot

    keys_groups = list(context.bot_data.setdefault(conf.INTERNALS['groups'], {}).keys())
    keys_channels = list(context.bot_data.setdefault(conf.INTERNALS['channels'], {}).keys())
    keys_users = list(context.bot_data.setdefault(conf.INTERNALS['users'], {}).keys())

    for key in keys_groups:
        try:
            bot.leave_chat(key)
        except Exception as e:
            raise e
        bot_removed_from(update, context, conf.INTERNALS['groups'], key)

    for key in keys_channels:
        try:
            bot.leave_chat(key)
        except Exception as e:
            raise e
        bot_removed_from(update, context, conf.INTERNALS['channels'], key)

    for key in keys_users:
        bot_removed_from(update, context, conf.INTERNALS['users'], key)

    msg = ''.join(('Chat data was successfully reset.\n\n',
           f'Group IDs left: {", ".join(keys_groups)}\n\n',
           f'Channel IDs left: {", ".join(keys_channels)}\n\n',
           f'User IDs (cannot leave/block them): {", ".join(keys_users)}\n\n'
           ))
    log_message_handler(context, msg)


@check_symbol_limit
def stonk_add(update: Update, context: CallbackContext) -> Union[None, bool]:
    symbols = parse_symbols(update, context.args)

    if len(symbols) == 0:
        return False

    for symbol in symbols:
        s = False

        try:
            s = Stonk(symbol)
        except InvalidSymbol:
            reply_symbol_error(update, symbol)

            return False

        stonks = context.chat_data.get(conf.INTERNALS['stock'], {})

        if s.symbol not in stonks:
            stonks[s.symbol] = s
            context.chat_data[conf.INTERNALS['stock']] = stonks

            reply = f"✅ {s.name} ({s.symbol}; ISIN: {s.isin}) added to watchlist."
        else:
            stonk_list(update, context)
            reply_random_gif(update, 'boring')

            reply = f"⚠️ {s.name} ({s.symbol}; ISIN: {s.isin}) is already in the watchlist."

        reply_message(update, reply)


def stonk_del(update: Update, context: CallbackContext) -> Union[None, bool]:
    symbols = parse_symbols(update, context.args)

    if len(symbols) == 0:
        return False

    for symbol in symbols:
        symbol: str = symbol.upper()
        stonks = context.chat_data.get(conf.INTERNALS['stock'], {})

        if symbol in stonks:
            stonks.pop(symbol, None)
            context.chat_data[conf.INTERNALS['stock']] = stonks
            msg_daily = get_daily_dict(context.chat_data)

            rise = msg_daily.get(conf.JOBS['check_rise_fall_day']['dict']['rise'], factory_defaultdict())
            fall = msg_daily.get(conf.JOBS['check_rise_fall_day']['dict']['fall'], factory_defaultdict())

            if rise and len(rise) > 0:
                msg_daily[conf.JOBS['check_rise_fall_day']['dict']['rise']].pop(symbol, None)

            if fall and len(fall) > 0:
                msg_daily[conf.JOBS['check_rise_fall_day']['dict']['fall']].pop(symbol, None)

            reply = f'✅ Symbol <b>{symbol}</b> was removed.'
        else:
            reply = f'⚠️ Symbol <b>{symbol}</b> is not in watchlist.'

        reply_message(update, reply, parse_mode=ParseMode.HTML)


@restricted_command(error_handler, 'Execution of this command in a group chat is forbidden (restricted access).',
                    in_private=False)
def stonk_clear(update: Update, context: CallbackContext) -> NoReturn:
    context.chat_data[conf.INTERNALS['stock']] = {}
    # clear_daily_dict(context.chat_data)
    reply = f'🖤 Watch list purged.'

    reply_message(update, reply)


@restricted_command(error_handler, 'Command execution forbidden (restricted access).')
def all_stonk_clear(update: Update, context: CallbackContext) -> NoReturn:
    # TODO: Maybe send the stick_list to the chat first before clearing.
    global_chat_data = context.dispatcher.chat_data
    cleared_chats = []

    for chat_id, chat_dict in global_chat_data.items():
        result_clear = clear_chat_data_stonk(chat_dict)

        if result_clear:
            cleared_chats.append(chat_id)

    for chat_id in cleared_chats:
        try:
            reply = '🖤 Your watch list had to be purged due to maintenance reasons. ' \
                    'All symbols need to be re-added by you again. Sorry for inconvenience.'
            send_message(context, chat_id, reply)
        except error.Unauthorized:
            error_message = f'All stonk clear: User ID {chat_id} blocked our bot. Thus, this user was will ' \
                            f'be removed from chat_data.'
            error_handler(update, context, error_message)
            global_chat_data.pop(chat_id, None)


def clear_chat_data_stonk(chat_data: defaultdict) -> bool:
    stonks = chat_data.get(conf.INTERNALS['stock'], None)
    daily = get_daily_dict(chat_data)
    cleared = False

    if stonks and len(stonks) > 0:
        chat_data[conf.INTERNALS['stock']] = factory_defaultdict()
        cleared = True

    if daily and len(daily) > 0:
        rise = daily.get(conf.JOBS['check_rise_fall_day']['dict']['rise'], None)
        fall = daily.get(conf.JOBS['check_rise_fall_day']['dict']['fall'], None)

        if rise:
            if len(rise) > 0:
                chat_data[conf.JOBS['check_rise_fall_day']['dict']['daily']][
                    conf.JOBS['check_rise_fall_day']['dict']['rise']] = factory_defaultdict()
                cleared = True

        if fall:
            if len(fall) > 0:
                chat_data[conf.JOBS['check_rise_fall_day']['dict']['daily']][
                    conf.JOBS['check_rise_fall_day']['dict']['fall']] = factory_defaultdict()
                cleared = True

    return cleared


def stonk_list(update: Update, context: CallbackContext) -> NoReturn:
    stonks = context.chat_data.get(conf.INTERNALS['stock'], {})
    reply = ''

    if len(stonks) > 0:
        for k in sorted(stonks.keys()):
            reply += f'💎 {stonks[k].name} ({k})\n'

        reply = reply[0:-1]
    else:
        reply = '🧻🤲 Watch list is empty.'

    reply_message(update, reply)


@send_typing_action
def list_price(update: Update, context: CallbackContext) -> NoReturn:
    stonks = context.chat_data.get(conf.INTERNALS['stock'], {})
    columns = ['Sym.', '⬆️ H', '⬇️️ L', '🛬 C', f"±{conf.LOCAL['currency']}", '±%']
    data = []

    if len(stonks) > 0:
        for k, s in sorted(stonks.items()):
            dp = s.price_daily()

            data.append([s.symbol, dp.high, dp.low, dp.close, dp.diff, dp.percent])

        df = pd.DataFrame(data, columns=columns)
        reply = df.to_string(index=False, formatters={
            columns[1]: formatter_conditional_no_dec,
            columns[2]: formatter_conditional_no_dec,
            columns[3]: formatter_conditional_no_dec,
            columns[4]: formatter_conditional_no_dec,
            columns[5]: formatter_conditional_no_dec
        })
        reply = f'🚀 🚀 🚀 📉 📉 📉\n\n{reply}'
    else:
        reply = '🧻🤲 Watch list is empty.'

    reply_message(update, reply, parse_mode=ParseMode.HTML, pre=True)


@send_typing_action
def chart(update: Update, context: CallbackContext, reply: bool = True,
          symbols: Union[bool, List[Union[None, str]]] = False, caption: str = '', pre: bool = True) -> NoReturn:
    if not symbols:
        symbols = parse_symbols(update, context.args)

    if len(symbols) == 0:
        return False

    for symbol in symbols:
        try:
            s = Stonk(symbol)
        except InvalidSymbol:
            reply_symbol_error(update, symbol)

            continue

        c_buf = s.chart()

        if reply:
            reply_with_photo(update, c_buf, caption=caption, pre=pre)
        else:
            send_photo(context, update.effective_message.chat_id, c_buf, caption=caption, pre=pre)


def check_rise_fall_day(context: CallbackContext) -> NoReturn:
    chat_data = context.job.context.dispatcher.chat_data
    datetime_now = datetime.now()
    date_now = datetime_now.date()
    datetime_zero = datetime.fromtimestamp(0)

    for c_id, cd in chat_data.items():
        stonks = cd.get(conf.INTERNALS['stock'], {})
        chat_custom = Chat(c_id, 'group')
        message_custom = Message(0, datetime_now, chat=chat_custom)
        update_custom = Update(0, message=message_custom)
        msg_daily = get_daily_dict(cd)
        daily_rise = msg_daily[conf.JOBS['check_rise_fall_day']['dict']['rise']]
        daily_fall = msg_daily[conf.JOBS['check_rise_fall_day']['dict']['fall']]

        for symbol, stonk in stonks.items():
            msg_last_rise_at = daily_rise.get(symbol, datetime_zero).date()
            msg_last_fall_at = daily_fall.get(symbol, datetime_zero).date()
            context.args = [symbol]

            if msg_last_rise_at == date_now and msg_last_fall_at == date_now:
                continue

            res_calc = stonk.calculate_perf_rise_fall_daily()
            to_send_message = []

            if res_calc:
                if stonk.daily_rise.calculated_at.date() == date_now and msg_last_rise_at < date_now:
                    if stonk.daily_rise.percent >= conf.JOBS['check_rise_fall_day']['threshold_perc_rise']:
                        text = f"🚀🚀🚀 {stonk.name} ({stonk.symbol}) is rocketing to " \
                               f"{round_currency_scalar(stonk.daily_rise.price)} " \
                               f"{conf.LOCAL['currency']} (+{stonk.daily_rise.percent.round(2)}%)"
                        to_send_message.append(text)
                        daily_rise[symbol] = datetime_now

                if stonk.daily_fall.calculated_at.date() == date_now and msg_last_fall_at < date_now:
                    if stonk.daily_fall.percent <= conf.JOBS['check_rise_fall_day']['threshold_perc_fall']:
                        text = f"📉📉📉 {stonk.name} ({stonk.symbol}) is drow" \
                               f"ning to {round_currency_scalar(stonk.daily_fall.price)} " \
                               f"{conf.LOCAL['currency']} ({stonk.daily_fall.percent.round(2)}%)"
                        to_send_message.append(text)
                        daily_fall[symbol] = datetime_now

                for message in to_send_message:
                    try:
                        send_message(context, c_id, message)
                        chart(update_custom, context, reply=False, symbols=[stonk.symbol])
                    except error.Unauthorized:
                        error_message = f'Rise/Fall check: User ID {c_id} blocked our bot. Thus, this user was will ' \
                                        f'be removed from chat_data.'
                        error_handler(update_custom, context, error_message)

                        del context.job.context.dispatcher.chat_data[c_id]

                        break


def bot_init(updater: Updater) -> NoReturn:
    pass


def get_daily_dict(chat_data: dict) -> defaultdict:
    d = chat_data.get(conf.JOBS['check_rise_fall_day']['dict']['daily'], factory_defaultdict())
    chat_data[conf.JOBS['check_rise_fall_day']['dict']['daily']] = d

    return chat_data[conf.JOBS['check_rise_fall_day']['dict']['daily']]


def discovery_websites(update: Update, context: CallbackContext):
    d = Discovery()
    message_html = '🔍 Useful discovery sources:\n'

    for item in d.websites:
        message_html += f"* <a href=\"{item['url']}\">{item['description']}</>\n"

    reply_message(update, message_html, parse_mode=ParseMode.HTML)


@send_typing_action
def sector_performance(update: Update, context: CallbackContext):
    d = Discovery()
    c_buf = d.performance_sectors_sp500()

    reply_with_photo(update, c_buf)


@send_typing_action
def upcoming_earnings(update: Update, context: CallbackContext):
    d = Discovery()
    text = d.upcoming_earnings()
    text = f'🗓️ 🗓️ 🗓️\n\n{text}'

    reply_message(update, text, parse_mode=ParseMode.HTML, pre=True)


@send_typing_action
def stonk_upcoming_earnings(update: Update, context: CallbackContext):
    # TODO: Optimize this to load all symbols for event lookup in one go instead of per symbol.
    stonks = context.chat_data.get(conf.INTERNALS['stock'], {})
    columns = ['Company', 'Sym.', 'Date', '-days']
    data = []

    if len(stonks) > 0:
        now = datetime.now()

        for k, s in sorted(stonks.items()):
            ue = s.upcoming_earning()
            date = 'N/A'
            days_left = 'N/A'

            if ue:
                date = ue.strftime('%Y-%m-%d')
                days_left = (ue - now).days

            data.append([s.name, s.symbol, date, days_left])

        df = pd.DataFrame(data, columns=columns)
        reply = df.to_string(index=False, formatters={'Company': '{:.10}'.format})
        reply = f'📅 📅 📅\n\n{reply}'
    else:
        reply = '🧻🤲 Watch list is empty.'

    reply_message(update, reply, parse_mode=ParseMode.HTML, pre=True)


@send_typing_action
def gainers(update: Update, context: CallbackContext):
    count = parse_daily_perf_count(update, context.args)

    d = Discovery()
    text = d.gainers(count)
    text = f"""🚀 🚀 🚀 ({conf.LOCAL['currency']})\n\n{text}\n\n<a
    href="https://finance.yahoo.com/gainers">Source</a>"""

    reply_message(update, text, parse_mode=ParseMode.HTML, pre=True)


@send_typing_action
def losers(update: Update, context: CallbackContext):
    count = parse_daily_perf_count(update, context.args)

    d = Discovery()
    text = d.losers(count)
    text = f"""📉 📉 📉 ({conf.LOCAL['currency']})\n\n{text}\n\n<a href="https://finance.yahoo.com/losers">Source</a>"""

    reply_message(update, text, parse_mode=ParseMode.HTML, pre=True)


@send_typing_action
def orders(update: Update, context: CallbackContext):
    count = parse_daily_perf_count(update, context.args)

    d = Discovery()
    text = d.orders(count)
    text = f'📖 📖 📖\n\n{text}\n\n<a href="https://finance.yahoo.com/most-active">Source</a>'

    reply_message(update, text, parse_mode=ParseMode.HTML, pre=True)


@send_typing_action
def high_short(update: Update, context: CallbackContext):
    count = parse_daily_perf_count(update, context.args)

    d = Discovery()
    text = d.high_short(count)
    text = f'🩳 🩳 🩳\n\n{text}\n\n<a href="https://www.highshortinterest.com/">Source</a>'

    reply_message(update, text, parse_mode=ParseMode.HTML, pre=True)


@send_typing_action
def low_float(update: Update, context: CallbackContext):
    count = parse_daily_perf_count(update, context.args)

    d = Discovery()
    text = d.low_float(count)
    text = f'🤲 🤲 🤲\n\n{text}\n\n<a href="https://www.lowfloat.com/">Source</a>'

    reply_message(update, text, parse_mode=ParseMode.HTML, pre=True)


@send_typing_action
def hot_penny(update: Update, context: CallbackContext):
    count = parse_daily_perf_count(update, context.args)

    d = Discovery()
    text = d.hot_pennystocks(count)
    text = f"""🔥 👼 💰 ({conf.LOCAL['currency']})\n\n{text}\n\n<a href="https://www.pennystockflow.com/">Source</a>"""

    reply_message(update, text, parse_mode=ParseMode.HTML, pre=True)


@send_typing_action
def underval_large(update: Update, context: CallbackContext):
    count = parse_daily_perf_count(update, context.args)

    d = Discovery()
    text = d.undervalued_large_caps(count)
    text = f"""👼 🐖 🐖 ({conf.LOCAL['currency']})\n\n{text}\n\n<a
    href="https://finance.yahoo.com/screener/predefined/undervalued_large_caps">Source</a>"""

    reply_message(update, text, parse_mode=ParseMode.HTML, pre=True)


@send_typing_action
def underval_growth(update: Update, context: CallbackContext):
    count = parse_daily_perf_count(update, context.args)

    d = Discovery()
    text = d.undervalued_growth(count)
    text = f"""👼 🕺 🕺 ({conf.LOCAL['currency']})\n\n{text}\n\n<a
    href="https://finance.yahoo.com/screener/predefined/undervalued_growth_stocks">Source</a>"""

    reply_message(update, text, parse_mode=ParseMode.HTML, pre=True)


@restricted_command(error_handler, 'Command execution forbidden (restricted access).')
def exec_job_check_rise_fall(update: Update, context: CallbackContext):
    context.job_queue.run_once(check_rise_fall_day, timedelta(seconds=1), context=context)


@restricted_command(error_handler, 'Command execution forbidden (restricted access).')
def bot_list_all_data(update: Update, context: CallbackContext):
    user_data = context.dispatcher.user_data
    chat_data = context.dispatcher.chat_data
    bot_data = context.dispatcher.bot_data
    chat_ids = list(
            set(list(user_data.keys()) + list(chat_data.keys()) + list(
                    bot_data.get(conf.INTERNALS['groups'], {}).keys())))
    bot = context.bot
    result = 'User Info:\n'

    for c_id in chat_ids:
        user_info = bot.get_chat(c_id).to_dict()
        user_info.pop('photo', None)
        user_info = html.escape(formatter_to_json(user_info))

        result += f'{user_info}\n'

    result += f'\nBot Data:\n{formatter_to_json(bot_data)}\n\n'
    result += f'\nChat Data:\n{formatter_to_json(chat_data)}\n\n'
    result += f'\nUser Data:\n{formatter_to_json(user_data)}'

    reply_message(update, result, parse_mode=ParseMode.HTML, pre=True)


@send_typing_action
def wallstreetbets(update: Update, context: CallbackContext):
    args = parse_reddit(update, context.args)

    if not args:
        return False

    s = RedditAnalysis(context, update)
    result = s.wallstreetbets(args['sort'], args['count'])

    reply_message(update, result, parse_mode=ParseMode.HTML)


@send_typing_action
def mauerstrassenwetten(update: Update, context: CallbackContext):
    args = parse_reddit(update, context.args)

    if not args:
        return False

    s = RedditAnalysis(context, update)
    result = s.mauerstrassenwetten(args['sort'], args['count'])

    reply_message(update, result, parse_mode=ParseMode.HTML)


@send_typing_action
def investing(update: Update, context: CallbackContext):
    args = parse_reddit(update, context.args)

    if not args:
        return False

    s = RedditAnalysis(context, update)
    result = s.investing(args['sort'], args['count'])

    reply_message(update, result, parse_mode=ParseMode.HTML)


@send_typing_action
def stocks(update: Update, context: CallbackContext):
    args = parse_reddit(update, context.args)

    if not args:
        return False

    s = RedditAnalysis(context, update)
    result = s.stocks(args['sort'], args['count'])

    reply_message(update, result, parse_mode=ParseMode.HTML)


@send_typing_action
def gamestop(update: Update, context: CallbackContext):
    args = parse_reddit(update, context.args)

    if not args:
        return False

    s = RedditAnalysis(context, update)
    result = s.gamestop(args['sort'], args['count'])

    reply_message(update, result, parse_mode=ParseMode.HTML)


@send_typing_action
def spielstopp(update: Update, context: CallbackContext):
    args = parse_reddit(update, context.args)

    if not args:
        return False

    s = RedditAnalysis(context, update)
    result = s.spielstopp(args['sort'], args['count'])

    reply_message(update, result, parse_mode=ParseMode.HTML)


@send_typing_action
def stockmarket(update: Update, context: CallbackContext):
    args = parse_reddit(update, context.args)

    if not args:
        return False

    s = RedditAnalysis(context, update)
    result = s.stockmarket(args['sort'], args['count'])

    reply_message(update, result, parse_mode=ParseMode.HTML)


@send_typing_action
def daytrading(update: Update, context: CallbackContext):
    args = parse_reddit(update, context.args)

    if not args:
        return False

    s = RedditAnalysis(context, update)
    result = s.daytrading(args['sort'], args['count'])

    reply_message(update, result, parse_mode=ParseMode.HTML)


@send_typing_action
def pennystocks(update: Update, context: CallbackContext):
    args = parse_reddit(update, context.args)

    if not args:
        return False

    s = RedditAnalysis(context, update)
    result = s.pennystocks(args['sort'], args['count'])

    reply_message(update, result, parse_mode=ParseMode.HTML)


@send_typing_action
def cryptomarkets(update: Update, context: CallbackContext):
    args = parse_reddit(update, context.args)

    if not args:
        return False

    s = RedditAnalysis(context, update)
    result = s.cryptomarkets(args['sort'], args['count'])

    reply_message(update, result, parse_mode=ParseMode.HTML)


@send_typing_action
def satoshistreetbets(update: Update, context: CallbackContext):
    args = parse_reddit(update, context.args)

    if not args:
        return False

    s = RedditAnalysis(context, update)
    result = s.satoshistreetbets(args['sort'], args['count'])

    reply_message(update, result, parse_mode=ParseMode.HTML)


@send_typing_action
def popular_symbols(update: Update, context: CallbackContext):
    s = RedditAnalysis(context, update)
    text = s.popular_symbols()
    result = f"💁 💁 💁 ({conf.LOCAL['currency']})\n\n{text}"

    reply_message(update, result, parse_mode=ParseMode.HTML, pre=True)


@send_typing_action
def bullbear(update: Update, context: CallbackContext):
    symbols = parse_symbols(update, context.args)

    if len(symbols) == 0:
        return False

    st = Stocktwits()
    text = st.bullbear(symbols)
    result = f'🐣 Stocktwits Analysis 🔍\n\n{text}'

    reply_message(update, result, parse_mode=ParseMode.HTML, pre=True)


@send_typing_action
def stock_messages(update: Update, context: CallbackContext):
    symbols = parse_symbols(update, context.args)

    if len(symbols) == 0:
        return False

    st = Stocktwits()
    text = st.messages_ticker(symbols)
    result = f'🐣 Stocktwits Messages 💬\n\n{text}'

    reply_message(update, result, parse_mode=ParseMode.HTML)


@send_typing_action
def trending_symbols(update: Update, context: CallbackContext):
    st = Stocktwits()
    text = st.trending()
    result = f'🐣 Stocktwits Trending 🚀\n\n{text}'

    reply_message(update, result, parse_mode=ParseMode.HTML, pre=True)


@send_typing_action
def price(update: Update, context: CallbackContext, reply: bool = True,
          symbols: Union[bool, List[Union[None, str]]] = False):
    if not symbols:
        symbols = parse_symbols(update, context.args)

    if len(symbols) == 0:
        return False

    for symbol in symbols:
        try:
            s = Stonk(symbol)
        except InvalidSymbol:
            reply_symbol_error(update, symbol)

            continue

        p_text = s.details_price_textual()

        if reply:
            reply_message(update, p_text, parse_mode=ParseMode.HTML, pre=True)
        else:
            send_message(context, update.effective_message.chat_id, p_text, parse_mode=ParseMode.HTML, pre=True)


@send_typing_action
def details(update: Update, context: CallbackContext, reply: bool = True,
          symbols: Union[bool, List[Union[None, str]]] = False):
    if not symbols:
        symbols = parse_symbols(update, context.args)

    if len(symbols) == 0:
        return False

    for symbol in symbols:
        try:
            s = Stonk(symbol)
        except InvalidSymbol:
            reply_symbol_error(update, symbol)

            continue

        p_text = s.details_price_textual()

        if reply:
            chart(update, context, symbols=[symbol], caption=p_text, pre=True)
        else:
            chart(update, context, reply=reply, pre=True)


@send_typing_action
def r_samoyed_coin(update: Update, context: CallbackContext):
    args = parse_reddit(update, context.args)

    if not args:
        return False

    s = RedditAnalysis(context, update)
    result = s.samoyedcoin(args['sort'], args['count'])

    reply_message(update, result, parse_mode=ParseMode.HTML)


def main() -> NoReturn:
    """Run bot."""
    persist = PicklePersistence(filename=f'{conf.PERSISTENCE_NAME}.pickle')
    # Create the Updater and pass it your bot's token.
    updater = Updater(f"{conf.API['telegram_bot_token']}", persistence=persist, use_context=True, workers=conf.WORKERS)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler('start', start, run_async=True))
    dispatcher.add_handler(CommandHandler('help', help, run_async=True))
    dispatcher.add_handler(CommandHandler('h', help, run_async=True))
    dispatcher.add_handler(CommandHandler('help_admin', help_admin, run_async=True))
    dispatcher.add_handler(CommandHandler('ha', help_admin, run_async=True))
    dispatcher.add_handler(CommandHandler('show_chats', show_chats, run_async=True))
    dispatcher.add_handler(CommandHandler('chat_data_reset', chat_data_reset, run_async=True))
    dispatcher.add_handler(CommandHandler('acdr', chat_data_reset, run_async=True))
    dispatcher.add_handler(CommandHandler('stonk_add', stonk_add))
    dispatcher.add_handler(CommandHandler('sa', stonk_add))
    dispatcher.add_handler(CommandHandler('stonk_del', stonk_del))
    dispatcher.add_handler(CommandHandler('sd', stonk_del))
    dispatcher.add_handler(CommandHandler('stonk_clear', stonk_clear))
    dispatcher.add_handler(CommandHandler('sc', stonk_clear))
    dispatcher.add_handler(CommandHandler('stonk_list', stonk_list, run_async=True))
    dispatcher.add_handler(CommandHandler('sl', stonk_list, run_async=True))
    dispatcher.add_handler(CommandHandler('list_price', list_price, run_async=True))
    dispatcher.add_handler(CommandHandler('lp', list_price, run_async=True))
    dispatcher.add_handler(CommandHandler('chart', chart, run_async=False))
    dispatcher.add_handler(CommandHandler('c', chart, run_async=False))
    dispatcher.add_handler(CommandHandler('discovery', discovery_websites, run_async=True))
    dispatcher.add_handler(CommandHandler('di', discovery_websites, run_async=True))
    dispatcher.add_handler(CommandHandler('sector_performance', sector_performance, run_async=True))
    dispatcher.add_handler(CommandHandler('sp', sector_performance, run_async=True))
    dispatcher.add_handler(CommandHandler('upcoming_earnings', upcoming_earnings, run_async=True))
    dispatcher.add_handler(CommandHandler('ue', upcoming_earnings, run_async=True))
    dispatcher.add_handler(CommandHandler('stonk_upcoming_earnings', stonk_upcoming_earnings, run_async=True))
    dispatcher.add_handler(CommandHandler('sue', stonk_upcoming_earnings, run_async=True))
    dispatcher.add_handler(CommandHandler('gainers', gainers, run_async=True))
    dispatcher.add_handler(CommandHandler('g', gainers, run_async=True))
    dispatcher.add_handler(CommandHandler('losers', losers, run_async=True))
    dispatcher.add_handler(CommandHandler('l', losers, run_async=True))
    dispatcher.add_handler(CommandHandler('orders', orders, run_async=True))
    dispatcher.add_handler(CommandHandler('o', orders, run_async=True))
    dispatcher.add_handler(CommandHandler('high_short', high_short, run_async=True))
    dispatcher.add_handler(CommandHandler('hs', high_short, run_async=True))
    dispatcher.add_handler(CommandHandler('low_float', low_float, run_async=True))
    dispatcher.add_handler(CommandHandler('lf', low_float, run_async=True))
    dispatcher.add_handler(CommandHandler('hot_penny', hot_penny, run_async=True))
    dispatcher.add_handler(CommandHandler('hp', hot_penny, run_async=True))
    dispatcher.add_handler(CommandHandler('underval_large', underval_large, run_async=True))
    dispatcher.add_handler(CommandHandler('ul', underval_large, run_async=True))
    dispatcher.add_handler(CommandHandler('underval_growth', underval_growth, run_async=True))
    dispatcher.add_handler(CommandHandler('ug', underval_growth, run_async=True))
    dispatcher.add_handler(CommandHandler('exec_job_check_rise_fall', exec_job_check_rise_fall))
    dispatcher.add_handler(CommandHandler('ejcrf', exec_job_check_rise_fall))
    dispatcher.add_handler(CommandHandler('all_stonk_clear', all_stonk_clear))
    dispatcher.add_handler(CommandHandler('asc', all_stonk_clear))
    dispatcher.add_handler(CommandHandler('bot_list_all_data', bot_list_all_data, run_async=True))
    dispatcher.add_handler(CommandHandler('blad', bot_list_all_data, run_async=True))
    dispatcher.add_handler(CommandHandler('wallstreetbets', wallstreetbets, run_async=True))
    dispatcher.add_handler(CommandHandler('wsb', wallstreetbets, run_async=True))
    dispatcher.add_handler(CommandHandler('mauerstrassenwetten', mauerstrassenwetten, run_async=True))
    dispatcher.add_handler(CommandHandler('msw', mauerstrassenwetten, run_async=True))
    dispatcher.add_handler(CommandHandler('investing', investing, run_async=True))
    dispatcher.add_handler(CommandHandler('ri', investing, run_async=True))
    dispatcher.add_handler(CommandHandler('rstocks', stocks, run_async=True))
    dispatcher.add_handler(CommandHandler('rs', stocks, run_async=True))
    dispatcher.add_handler(CommandHandler('gamestop', gamestop, run_async=True))
    dispatcher.add_handler(CommandHandler('gme', gamestop, run_async=True))
    dispatcher.add_handler(CommandHandler('spielstopp', spielstopp, run_async=True))
    dispatcher.add_handler(CommandHandler('rss', spielstopp, run_async=True))
    dispatcher.add_handler(CommandHandler('stockmarket', stockmarket, run_async=True))
    dispatcher.add_handler(CommandHandler('rsm', stockmarket, run_async=True))
    dispatcher.add_handler(CommandHandler('daytrading', daytrading, run_async=True))
    dispatcher.add_handler(CommandHandler('rdt', daytrading, run_async=True))
    dispatcher.add_handler(CommandHandler('pennystocks', pennystocks, run_async=True))
    dispatcher.add_handler(CommandHandler('rps', pennystocks, run_async=True))
    dispatcher.add_handler(CommandHandler('cryptomarkets', cryptomarkets, run_async=True))
    dispatcher.add_handler(CommandHandler('rcm', cryptomarkets, run_async=True))
    dispatcher.add_handler(CommandHandler('satoshistreetbets', satoshistreetbets, run_async=True))
    dispatcher.add_handler(CommandHandler('ssb', satoshistreetbets, run_async=True))
    dispatcher.add_handler(CommandHandler('popular_symbols', popular_symbols, run_async=True))
    dispatcher.add_handler(CommandHandler('ps', popular_symbols, run_async=True))
    dispatcher.add_handler(CommandHandler('bullbear', bullbear, run_async=True))
    dispatcher.add_handler(CommandHandler('bb', bullbear, run_async=True))
    dispatcher.add_handler(CommandHandler('stock_messages', stock_messages, run_async=True))
    dispatcher.add_handler(CommandHandler('sm', stock_messages, run_async=True))
    dispatcher.add_handler(CommandHandler('trending_symbols', trending_symbols, run_async=True))
    dispatcher.add_handler(CommandHandler('ts', trending_symbols, run_async=True))
    dispatcher.add_handler(CommandHandler('price', price, run_async=True))
    dispatcher.add_handler(CommandHandler('p', price, run_async=True))
    dispatcher.add_handler(CommandHandler('details', details, run_async=False))
    dispatcher.add_handler(CommandHandler('d', details, run_async=False))
    dispatcher.add_handler(CommandHandler('rsamoyedcoin', r_samoyed_coin, run_async=True))
    dispatcher.add_handler(CommandHandler('rsc', r_samoyed_coin, run_async=True))

    # ...and the error handler
    dispatcher.add_error_handler(error_handler, run_async=True)

    # Message handler
    # Keep track of which chats the bot is in
    dispatcher.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
    # Handle members joining/leaving chats.
    dispatcher.add_handler(ChatMemberHandler(greet_chat_members, ChatMemberHandler.CHAT_MEMBER))

    # Unknown command. this handler must be added last.
    dispatcher.add_handler(MessageHandler(Filters.command, command_unknown, run_async=True))

    # Job queue stuff
    job_queue = updater.job_queue
    job_queue.run_repeating(check_rise_fall_day, conf.JOBS['check_rise_fall_day']['interval_sec'],
                            context=updater)

    bot_init(updater)

    # Start the Bot
    updater.start_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()
