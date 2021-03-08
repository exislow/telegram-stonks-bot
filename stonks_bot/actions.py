from telegram import Update
from telegram.ext import CallbackContext

from stonks_bot import conf
from stonks_bot.helper.command import restricted_add
from stonks_bot.helper.handler import error_handler


@restricted_add(error_handler, 'Add to group forbidden.')
def bot_added_to_group(update: Update, context: CallbackContext) -> bool:
    g = context.bot_data.get(conf.INTERNALS['groups'], {})
    g[update.message.chat_id] = update.message.chat
    context.bot_data[conf.INTERNALS['groups']] = g

    return True
