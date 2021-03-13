import html
import json
import logging
import traceback
from json import JSONEncoder
from typing import Union

from telegram import Update, ParseMode
from telegram.ext import CallbackContext

from stonks_bot import conf
from stonks_bot.helper.message import send_message

logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


def error_handler(update: Update, context: CallbackContext, error_message: Union[bool, str] = None) -> None:
    """Log the error and send a telegram message to notify the developer."""
    handling_type = 'an update' if update else 'a job from queue'

    # Log the error before we do anything else, so we can see it even if something breaks
    if context.error:
        logger.error(msg=f'Exception while handling {handling_type}:', exc_info=context.error)

    if not error_message:
        # traceback.format_exception returns the usual python message about an exception, but as a
        # list of strings rather than a single string, so we have to join them together.
        tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
        tb_string = ''.join(tb_list)
        additional_info = html.escape(tb_string)
        error_type = 'exception'
    else:
        additional_info = error_message
        error_type = 'error'

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_dict = update.to_dict() if isinstance(update, Update) else None
    bot_data = context.bot_data if update else context.dispatcher.bot_data
    chat_data = context.chat_data if update else context.dispatcher.chat_data
    user_data = context.user_data if update else context.dispatcher.user_data
    message = (
        f'An {error_type} was raised while handling {handling_type}.\n\n'
        f'update = {html.escape(json.dumps(update_dict, indent=2, ensure_ascii=False))}\n\n'
        f'context.bot_data = {html.escape(json.dumps(bot_data, indent=2, ensure_ascii=False, cls=TelegramEncoder))}\n\n'
        f'context.chat_data = {html.escape(json.dumps(chat_data, indent=2, ensure_ascii=False, cls=TelegramEncoder))}\n\n'
        f'context.user_data = {html.escape(json.dumps(user_data, indent=2, ensure_ascii=False, cls=TelegramEncoder))}\n\n'
        f'{additional_info}'
    )

    # Finally, send the message
    send_message(context, conf.USER_ID['master'], message, parse_mode=ParseMode.HTML, pre=True)


class TelegramEncoder(JSONEncoder):
    def default(self, o):
        return o.to_dict()
