import html
import logging
import json
import traceback
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
    # Log the error before we do anything else, so we can see it even if something breaks.
    if context.error:
        logger.error(msg='Exception while handling an update:', exc_info=context.error)

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
    message = (
        f'An {error_type} was raised while handling an update.\n\n'
        f'update = {html.escape(json.dumps(update_dict, indent=2, ensure_ascii=False))}\n\n'
        f'context.bot_data = {html.escape(str(context.bot_data))}\n\n'
        f'context.chat_data = {html.escape(str(context.chat_data))}\n\n'
        f'context.user_data = {html.escape(str(context.user_data))}\n\n'
        f'{additional_info}'
    )

    # Finally, send the message
    send_message(context, conf.USER_ID['master'], message, parse_mode=ParseMode.HTML, pre=True)
