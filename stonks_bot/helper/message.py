from typing import Any, List, Union

from telegram import Update, ParseMode
from telegram.ext import CallbackContext

from stonks_bot import conf
from stonks_bot.helper.media import gif_random


def reply_with_photo(update: Update, photo: Any) -> None:
    update.effective_message.reply_photo(photo, quote=True)


def send_photo(context: CallbackContext, chat_id: int, photo: Any) -> None:
    context.bot.send_photo(chat_id=chat_id, photo=photo)


def reply_random_gif(update: Update, search_term) -> None:
    rg = gif_random(search_term)
    rg_url = rg.data.image_original_url

    update.effective_message.reply_animation(rg_url)


def reply_symbol_error(update: Update, symbol: str) -> None:
    reply = f'❌ Symbol *{symbol}* does not exist\.'

    reply_message(update, reply, parse_mode=ParseMode.MARKDOWN_V2)


def reply_message(update: Update, text: str, parse_mode: str = None, pre: bool = False) -> None:
    text_list = split_long_message(text)

    for t in text_list:
        msg = t if not pre else f'<pre>{t}</pre>'

        update.effective_message.reply_text(msg, parse_mode=parse_mode, quote=True)


def send_message(context: CallbackContext, chat_id: int, text: str, parse_mode: str = None, pre: bool = False) -> None:
    text_list = split_long_message(text)

    for t in text_list:
        msg = t if not pre else f'<pre>{t}</pre>'

        context.bot.send_message(chat_id=chat_id, text=msg, parse_mode=parse_mode)


def reply_command_unknown(update: Update):
    reply = f'❌ This command does not exist.'

    reply_message(update, reply)
    reply_random_gif(update, 'what')


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
        result.append(split_long_message(text[split_pos:], result))

        return result
