from typing import Any

from telegram import Update, ParseMode, Message
from telegram.ext import CallbackContext

from stonks_bot.helper.media import gif_random


def reply_with_photo(update: Update, photo: Any) -> None:
    msg = get_message(update)
    msg.reply_photo(photo, quote=True)


def send_photo(update: Update, context: CallbackContext, photo: Any) -> None:
    context.bot.send_photo(update.effective_message.chat_id, photo)


def reply_random_gif(update: Update, search_term) -> None:
    rg = gif_random(search_term)
    rg_url = rg.data.image_original_url
    msg = get_message(update)

    msg.reply_animation(rg_url)


def reply_symbol_error(update: Update, symbol: str) -> None:
    reply = f'❌ Symbol *{symbol}* does not exist\.'

    reply_message(update, reply, parse_mode=ParseMode.MARKDOWN_V2)


def reply_message(update: Update, text: str, parse_mode=None) -> None:
    msg = get_message(update)

    msg.reply_text(text, parse_mode=parse_mode, quote=True)


def get_message(update: Update) -> Message:
    msg = update.effective_message

    return msg
