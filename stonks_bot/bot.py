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
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Union, NoReturn

import pandas as pd
from telegram import Update, ParseMode, Message, Chat, error
from telegram.ext import Updater, CommandHandler, CallbackContext, PicklePersistence, MessageHandler, Filters

from stonks_bot import conf
from stonks_bot.actions import bot_added_to_group
from stonks_bot.discovery import Discovery
from stonks_bot.helper.args import parse_symbol, parse_daily_perf_count
from stonks_bot.helper.command import restricted_command, send_typing_action, check_symbol_limit, log_error, \
    restricted_group_command
from stonks_bot.helper.data import factory_defaultdict
from stonks_bot.helper.exceptions import InvalidSymbol
from stonks_bot.helper.formatters import formatter_conditional_no_dec
from stonks_bot.helper.handler import error_handler
from stonks_bot.helper.math import round_currency_scalar
from stonks_bot.helper.message import reply_with_photo, reply_symbol_error, reply_message, send_photo, \
    reply_command_unknown, send_message, reply_random_gif
from stonks_bot.stonk import Stonk


@log_error(error_handler, 'Command does not exist.')
def command_unknown(update: Update, context: CallbackContext) -> NoReturn:
    reply_command_unknown(update)


def start(update: Update, context: CallbackContext) -> NoReturn:
    help(update, context)


def help(update: Update, context: CallbackContext) -> NoReturn:
    reply = """Hi, I am the STONKS BOT! Try to use the following commands:
* /stonk_add <SYMBOL/ISIN> | /sa -> Add a stock to the watchlist.
* /stonk_del <SYMBOL/ISIN> | /sd -> Delete a stock from the watchlist.
* /stonk_list | /sl -> Show the Watchlist
* /list_price | /lp -> List watchlist prices.
* /chart <SYMBOL> | /c -> Plot the last trading day of a stock.
* /discovery | /d -> Useful infos to find hot stocks.
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
"""

    reply_message(update, reply)


@check_symbol_limit
def stonk_add(update: Update, context: CallbackContext) -> Union[None, bool]:
    symbol = parse_symbol(update, context.args)

    if not symbol:
        return False

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
    symbol = parse_symbol(update, context.args)

    if not symbol:
        return False

    symbol: str = symbol.upper()
    stonks = context.chat_data.get(conf.INTERNALS['stock'], {})

    if symbol in stonks:
        stonks.pop(symbol, None)
        context.chat_data[conf.INTERNALS['stock']] = stonks
        msg_daily = get_daily_dict(context.chat_data)
        msg_daily[conf.JOBS['check_rise_fall_day']['dict']['rise']].pop(symbol, None)
        msg_daily[conf.JOBS['check_rise_fall_day']['dict']['fall']].pop(symbol, None)
        reply = f'✅ Symbol *{symbol}* was removed\.'
    else:
        reply = f'⚠️ Symbol *{symbol}* is not in watchlist\.'

    reply_message(update, reply, parse_mode=ParseMode.MARKDOWN_V2)


@restricted_group_command(error_handler, 'Execution of this command in a group chat is forbidden (restricted access).')
def stonk_clear(update: Update, context: CallbackContext) -> NoReturn:
    context.chat_data[conf.INTERNALS['stock']] = {}
    #clear_daily_dict(context.chat_data)
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
        reply = '🖤 Your watch list had to be purged due to maintenance reasons. ' \
                'All symbols need to be re-added by you again. Sorry for inconvenience.'
        send_message(context, chat_id, reply)


def clear_chat_data_stonk(chat_data: defaultdict) -> bool:
    stonks = chat_data.get(conf.INTERNALS['stock'], None)
    daily = chat_data.get(conf.JOBS['check_rise_fall_day']['dict']['daily'], None)
    cleared = False

    if stonks and len(stonks) > 0:
        chat_data[conf.INTERNALS['stock']] = factory_defaultdict()
        cleared = True

    if daily and len(daily) > 0:
        rise = daily.get(conf.JOBS['check_rise_fall_day']['dict']['rise'], None)
        fall = daily.get(conf.JOBS['check_rise_fall_day']['dict']['fall'], None)

        if rise and len(rise) > 0:
            chat_data[conf.JOBS['check_rise_fall_day']['dict']['daily']][conf.JOBS['check_rise_fall_day']['dict']['rise']] = factory_defaultdict()
            cleared = True

        if fall and len(fall) > 0:
            chat_data[conf.JOBS['check_rise_fall_day']['dict']['daily']][conf.JOBS['check_rise_fall_day']['dict']['fall']] = factory_defaultdict()
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
def chart(update: Update, context: CallbackContext, reply: bool = True, symbol: Union[bool, str] = False) -> Union[
    None, bool]:
    if not symbol:
        symbol = parse_symbol(update, context.args)

    if not symbol:
        return False

    try:
        s = Stonk(symbol)
    except InvalidSymbol:
        reply_symbol_error(update, symbol)

        return False

    c_buf = s.chart()

    if reply:
        reply_with_photo(update, c_buf)
    else:
        send_photo(context, update.effective_message.chat_id, c_buf)


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
                        chart(update_custom, context, reply=False, symbol=stonk.symbol)
                    except error.Unauthorized:
                        error_message = f'Rise/Fall check: User ID {c_id} blocked our bot. Thus, this user was will ' \
                                        f'be removed from chat_data.'
                        error_handler(update_custom, context, error_message)

                        del context.job.context.dispatcher.chat_data[c_id]

                        break


def added_to_group(update: Update, context: CallbackContext):
    if context.bot.bot in update.message.new_chat_members or update.message.group_chat_created:
        bot_added_to_group(update, context)


def removed_from_group(update: Update, context: CallbackContext):
    if context.bot.bot == update.message.left_chat_member:
        g = context.bot_data.get(conf.INTERNALS['groups'], {})
        g.pop(update.message.chat_id, None)
        context.bot_data[conf.INTERNALS['groups']] = g


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
    text = f"""🚀 🚀 🚀 ({conf.LOCAL['currency']})\n\n{text}\n\n<a href="https://finance.yahoo.com/gainers">Source</a>"""

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
    text = f"""👼 🐖 🐖 ({conf.LOCAL['currency']})\n\n{text}\n\n<a href="https://finance.yahoo.com/screener/predefined/undervalued_large_caps">Source</a>"""

    reply_message(update, text, parse_mode=ParseMode.HTML, pre=True)


@send_typing_action
def underval_growth(update: Update, context: CallbackContext):
    count = parse_daily_perf_count(update, context.args)

    d = Discovery()
    text = d.undervalued_growth(count)
    text = f"""👼 🕺 🕺 ({conf.LOCAL['currency']})\n\n{text}\n\n<a href="https://finance.yahoo.com/screener/predefined/undervalued_growth_stocks">Source</a>"""

    reply_message(update, text, parse_mode=ParseMode.HTML, pre=True)


@restricted_command(error_handler, 'Command execution forbidden (restricted access).')
def exec_job_check_rise_fall(update: Update, context: CallbackContext):
    context.job_queue.run_once(check_rise_fall_day, timedelta(seconds=1), context=context)


def main():
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
    dispatcher.add_handler(CommandHandler('chart', chart, run_async=True))
    dispatcher.add_handler(CommandHandler('c', chart, run_async=True))
    dispatcher.add_handler(CommandHandler('discovery', discovery_websites, run_async=True))
    dispatcher.add_handler(CommandHandler('d', discovery_websites, run_async=True))
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

    # ...and the error handler
    dispatcher.add_error_handler(error_handler, run_async=True)

    # Message handler
    dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members |
                                          Filters.status_update.chat_created, added_to_group, run_async=True))
    dispatcher.add_handler(MessageHandler(Filters.status_update.left_chat_member, removed_from_group, run_async=True))

    # Unknown command. this handler must be added last.
    dispatcher.add_handler(MessageHandler(Filters.command, command_unknown, run_async=True))

    # Job queue stuff
    job_queue = updater.job_queue
    job_queue.run_repeating(check_rise_fall_day, conf.JOBS['check_rise_fall_day']['interval_sec'],
                            context=updater)

    bot_init(updater)

    # Start the Bot
    updater.start_polling()

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()
