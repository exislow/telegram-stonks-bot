from typing import Any

from telegram import Update, ParseMode
from telegram.ext import CallbackContext

from stonks_bot.helper.media import gif_random


def reply_with_photo(update: Update, context: CallbackContext, photo: Any) -> None:
    context.bot.send_photo(update.message.chat_id, photo, reply_to_message_id=update.message.message_id)


def reply_random_gif(update: Update, search_term) -> None:
    rg = gif_random(search_term)
    rg_url = rg.data.image_original_url

    update.message.reply_animation(rg_url)


def reply_symbol_error(update: Update, symbol: str) -> None:
    reply = f'❌ Symbol *{symbol}* does not exist\.'

    update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN_V2)
