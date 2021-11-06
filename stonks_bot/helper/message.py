from typing import Any, List, Union

from telegram import Update, ParseMode
from telegram.ext import CallbackContext

from stonks_bot import conf
from stonks_bot.helper.formatters import text_pre
from stonks_bot.helper.media import gif_random


def reply_with_photo(update: Update, photo: Any, caption: str = '', pre: bool = False,
                     parse_mode: ParseMode = ParseMode.HTML) -> None:
    caption = caption if not pre else text_pre(caption)

    update.effective_message.reply_photo(photo, quote=True, caption=caption, parse_mode=parse_mode)


def send_photo(context: CallbackContext, chat_id: int, photo: Any, caption: str = '', pre: bool = False,
               parse_mode: ParseMode = ParseMode.HTML) -> None:
    caption = caption if not pre else text_pre(caption)

    context.bot.send_photo(chat_id=chat_id, photo=photo, caption=caption, parse_mode=parse_mode)


def reply_random_gif(update: Update, search_term) -> None:
    rg = gif_random(search_term)
    # TODO: Uncomment if Giphy SDK is fixed again.
    #rg_url = rg.data.image_original_url
    rg_url = rg['data']['images']['original']['url']

    update.effective_message.reply_animation(rg_url)


def reply_symbol_error(update: Update, symbol: str) -> None:
    reply = f'❌ Symbol <b>{symbol}</b> does not exist.'

    reply_message(update, reply, parse_mode=ParseMode.HTML)


def reply_message(update: Update, text: str, parse_mode: str = None, pre: bool = False) -> None:
    text_list = split_long_message(text)

    for t in text_list:
        msg = t if not pre else text_pre(t)

        update.effective_message.reply_text(msg, parse_mode=parse_mode, quote=True)


def send_message(context: CallbackContext, chat_id: int, text: str, parse_mode: str = None, pre: bool = False) -> None:
    text_list = split_long_message(text)

    for t in text_list:
        msg = t if not pre else text_pre(t)

        context.bot.send_message(chat_id=chat_id, text=msg, parse_mode=parse_mode)


def reply_command_unknown(update: Update):
    reply = '❌ This command does not exist.'
    search = 'what'

    reply_error_message_gif(update, reply, search)


def reply_error_message_gif(update: Update, message: str, search_term: str):
    reply_message(update, message)
    reply_random_gif(update, search_term)


def reply_gif_fail_message(update: Update, message: str):
    search = 'fail'

    reply_error_message_gif(update, message, search)


def reply_gif_wrong_arg_help(update: Update):
    message = '❌ Wrong argument. Read /help again.'

    reply_gif_fail_message(update, message)


def reply_gif_symbol_missing(update: Update):
    message = f'Provide a SYMBOL you 🧻🤲🐩.'

    reply_gif_fail_message(update, message)


def split_long_message(text: str, result: Union[None, List[str]] = None) -> List[str]:
    # This is necessary, since a list in Python is mutable.
    if result is None:
        result = []

    text_len = len(text)

    if text_len < conf.MAX_LEN_MSG:
        result.append(text)

        return result
    else:
        try:
            split_pos = text[:conf.MAX_LEN_MSG].rindex('\n')
        except:
            split_pos = conf.MAX_LEN_MSG

        result.append(text[:split_pos])
        result = split_long_message(text[split_pos:], result)

        return result
