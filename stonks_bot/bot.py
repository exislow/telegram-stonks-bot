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
import json
import logging
import traceback
from datetime import datetime
from typing import Union

from telegram import Update, ParseMode, Message, Chat
from telegram.ext import Updater, CommandHandler, CallbackContext, PicklePersistence, MessageHandler, Filters

# Enable logging
from stonks_bot.helper.args import check_arg_symbol
from stonks_bot.helper.command import restricted, send_typing_action
from stonks_bot.helper.exceptions import InvalidSymbol
from stonks_bot.helper.math import round_currency_scalar
from stonks_bot.helper.message import reply_with_photo, reply_symbol_error, reply_message, send_photo
from stonks_bot.stonk import Stonk
from stonks_bot import conf

logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


def error_handler(update: Update, context: CallbackContext) -> None:
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_dict = update.to_dict() if isinstance(update, Update) else None
    message = (
        f'An exception was raised while handling an update\n'
        f'<pre>update = {html.escape(json.dumps(update_dict, indent=2, ensure_ascii=False))}'
        '</pre>\n\n'
        f'<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n'
        f'<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n'
        f'<pre>{html.escape(tb_string)}</pre>'
    )

    # Finally, send the message
    context.bot.send_message(chat_id=conf.USER_ID['master'], text=message, parse_mode=ParseMode.HTML)


def help(update: Update, context: CallbackContext) -> None:
    reply = """Hi, I am the STONKS BOT! Try to use the following commands:
- /stonk_add <SYMBOL/ISIN> (/sa) -> Add a stock to the watchlist.
- /stonk_del <SYMBOL/ISIN> (/sd) -> Delete a stock from the watchlist.
- /stonk_list (/sl) -> Show the Watchlist
- /list_price (/lp) -> List watchlist prices.
- /chart <SYMBOL> (/c) -> Plot the last trading day of a stock."""

    reply_message(update, reply)


def stonk_add(update: Update, context: CallbackContext) -> Union[None, bool]:
    symbol = check_arg_symbol(update, context.args)

    if not symbol:
        return False

    s = False

    try:
        s = Stonk(symbol)
    except InvalidSymbol:
        reply_symbol_error(update, symbol)

        return False

    reply = f"✅ {s.name} ({s.symbol}; ISIN: {s.isin}) added to watchlist."
    stonks = context.chat_data.get(conf.INTERNALS['stock'], {})
    stonks[s.symbol] = s
    context.chat_data[conf.INTERNALS['stock']] = stonks

    reply_message(update, reply)


def stonk_del(update: Update, context: CallbackContext) -> Union[None, bool]:
    symbol = check_arg_symbol(update, context.args)

    if not symbol:
        return False

    symbol: str = symbol.upper()
    stonks = context.chat_data.get(conf.INTERNALS['stock'], {})

    if symbol in stonks:
        stonks.pop(symbol, None)
        context.chat_data[conf.INTERNALS['stock']] = stonks
        reply = f'✅ Symbol *{symbol}* was removed\.'
    else:
        reply = f'⚠️ Symbol *{symbol}* is not in watchlist\.'

    reply_message(update, update, reply, parse_mode=ParseMode.MARKDOWN_V2)


@restricted
def stonk_clear(update: Update, context: CallbackContext) -> None:
    context.chat_data[conf.INTERNALS['stock']] = {}
    reply = f'🖤 Watch list purged.'

    reply_message(update, reply)


def stonk_list(update: Update, context: CallbackContext) -> None:
    stonks = context.chat_data.get(conf.INTERNALS['stock'], {})
    reply = ''

    if len(stonks) > 0:
        for k in sorted(stonks.keys()):
            reply += f'💎 {stonks[k].name} ({k})\n'

        reply = reply[0:-1]
    else:
        reply = '🧻🤲 Watch list is empty.'

    reply_message(update, reply)


# def list_price(update: Update, context: CallbackContext) -> None:
#     stonks = context.chat_data.get(STONKS, {})
#     reply = ''
#
#     if len(stonks) > 0:
#         symbols = list(stonks.keys())
#         symbols_txt = ' '.join(symbols)
#
#         yf_df = yf.download(tickers=symbols_txt, period='1d', interval='1d', group_by='ticker', prepost=True,
#                             rounding=True)
#         yf_df_eur = 1  # usd_to_eur(yf_df, rounding=4)
#
#         for k in symbols:
#             if len(symbols) == 1:
#                 t = yf_df_eur
#             else:
#                 t = yf_df_eur[k]
#             diff = round(t.Close[0] - t.Open[0], 2)
#             diff_txt = f'🚀{diff}' if diff > 0 else f'📉{diff}'
#             reply += f'📊 {k}: ⬆️{t.High[0]} ⬇️️{t.Low[0]} 🛬{t.Close[0]} {diff_txt} (EUR)\n'
#
#         reply = reply[0:-1]
#     else:
#         reply = '🧻🤲 Watch list is empty.'
#
#     reply_message(update, reply)


def list_price(update: Update, context: CallbackContext) -> None:
    stonks = context.chat_data.get(conf.INTERNALS['stock'], {})
    reply = ''

    if len(stonks) > 0:
        for k, s in stonks.items():
            pd = s.price_daily()
            diff_txt = f'🚀{pd.diff}' if pd.diff > 0 else f'📉{pd.diff}'
            reply += f"📊 {s.symbol}: ⬆️{pd.high} ⬇️️{pd.low} 🛬{pd.close} {diff_txt} ({conf.LOCAL['currency']}) " \
                     f"{pd.percent}%\n"

        reply = reply[0:-1]
    else:
        reply = '🧻🤲 Watch list is empty.'

    reply_message(update, reply)


@send_typing_action
def chart(update: Update, context: CallbackContext, reply=True) -> Union[None, bool]:
    symbol = check_arg_symbol(update, context.args)

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
        send_photo(update, context, c_buf)


def check_rise_fall_day(context: CallbackContext) -> None:
    chat_data = context.job.context['chat_data']
    datetime_now = datetime.now()
    date_now = datetime_now.date()
    datetime_zero = datetime.fromtimestamp(0)

    for c_id, cd in chat_data.items():
        stonks = cd.get(conf.INTERNALS['stock'], {})
        chat_custom = Chat(c_id, 'group')
        message_custom = Message(0, datetime_now, chat=chat_custom)
        update_custom = Update(0, message=message_custom)

        for symbol, stonk in stonks.items():
            # TODO: I need a better solution to track chat based values.
            key_msg_last_rise = conf.JOBS['check_rise_fall_day']['prefix']['msg_last_rise'] + symbol
            key_msg_last_fall = conf.JOBS['check_rise_fall_day']['prefix']['msg_last_rise'] + symbol
            msg_last_rise_at = cd.get(key_msg_last_rise, datetime_zero)
            msg_last_fall_at = cd.get(key_msg_last_fall, datetime_zero)
            context.args = [symbol]

            if msg_last_rise_at.date() == date_now and msg_last_fall_at.date() == date_now:
                continue

            res_calc = stonk.calculate_perf_rise_fall_daily()

            if res_calc:
                if stonk.daily_rise.calculated_at.date() == date_now:
                    if stonk.daily_rise.percent >= conf.JOBS['check_rise_fall_day']['threshold_perc_rise']:
                        reply = f"🚀🚀🚀 {stonk.name} ({stonk.symbol}) is rocketing to {round_currency_scalar(stonk.daily_rise.price)} " \
                                f"{conf.LOCAL['currency']} (+{stonk.daily_rise.percent.round(2)}%)"
                        context.bot.send_message(c_id, text=reply)
                        chart(update_custom, context, reply=False)

                        cd.update({key_msg_last_rise: datetime_now})

                if stonk.daily_fall.calculated_at.date() == date_now:
                    if stonk.daily_fall.percent <= conf.JOBS['check_rise_fall_day']['threshold_perc_fall']:
                        reply = f"📉📉📉 {stonk.name} ({stonk.symbol}) is drowning to {round_currency_scalar(stonk.daily_fall.price)} " \
                                f"{conf.LOCAL['currency']} ({stonk.daily_fall.percent.round(2)}%)"
                        context.bot.send_message(c_id, text=reply)
                        chart(update_custom, context, reply=False)

                        cd.update({key_msg_last_fall + symbol: datetime_now})


def added_to_group(update: Update, context: CallbackContext):
    if context.bot.bot in update.message.new_chat_members or update.message.group_chat_created:
        g = context.bot_data.get(conf.INTERNALS['groups'], {})
        g[update.message.chat_id] = update.message.chat
        context.bot_data[conf.INTERNALS['groups']] = g


def removed_from_group(update: Update, context: CallbackContext):
    if context.bot.bot == update.message.left_chat_member:
        g = context.bot_data.get(conf.INTERNALS['groups'], {})
        g.pop(update.message.chat_id, None)
        context.bot_data[conf.INTERNALS['groups']] = g


def main():
    """Run bot."""
    persist = PicklePersistence(filename=f'{conf.PERSISTENCE_NAME}.pickle')
    # Create the Updater and pass it your bot's token.
    updater = Updater(f"{conf.API['telegram_bot_id']}", persistence=persist, use_context=True)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler('help', help))
    dispatcher.add_handler(CommandHandler('stonk_add', stonk_add))
    dispatcher.add_handler(CommandHandler('sa', stonk_add))
    dispatcher.add_handler(CommandHandler('stonk_del', stonk_del))
    dispatcher.add_handler(CommandHandler('sd', stonk_del))
    dispatcher.add_handler(CommandHandler('stonk_clear', stonk_clear))
    dispatcher.add_handler(CommandHandler('sc', stonk_clear))
    dispatcher.add_handler(CommandHandler('stonk_list', stonk_list))
    dispatcher.add_handler(CommandHandler('sl', stonk_list))
    dispatcher.add_handler(CommandHandler('list_price', list_price))
    dispatcher.add_handler(CommandHandler('lp', list_price))
    dispatcher.add_handler(CommandHandler('chart', chart))
    dispatcher.add_handler(CommandHandler('c', chart))

    # ...and the error handler
    dispatcher.add_error_handler(error_handler)

    # Message handler
    dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members |
                                          Filters.status_update.chat_created, added_to_group))
    dispatcher.add_handler(MessageHandler(Filters.status_update.left_chat_member, removed_from_group))

    # Job queue stuff
    job_queue = updater.job_queue
    job_queue.run_repeating(check_rise_fall_day, conf.JOBS['check_rise_fall_day']['interval_sec'],
                            context={'chat_data': updater.dispatcher.chat_data})

    # Start the Bot
    updater.start_polling()

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()
