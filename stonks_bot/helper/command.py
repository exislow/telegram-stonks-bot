from functools import wraps
from typing import Callable, Union
import html
import json

from telegram import ChatAction, Update, ParseMode
from telegram.ext import CallbackContext

from stonks_bot import conf
from stonks_bot.helper.message import reply_random_gif


def error_handler(update: Update, context: CallbackContext, error_message: str) -> None:
    # TODO: Move somehwere else (logging file?).
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    #logger.error(msg='Exception while handling an update:', exc_info=context.error)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_dict = update.to_dict() if isinstance(update, Update) else None
    message = (
        f'An error occurred while handling an update.\n'
        f'<pre>update = {html.escape(json.dumps(update_dict, indent=2, ensure_ascii=False))}</pre>\n\n'
        f'<pre>context.bot_data = {html.escape(str(context.bot_data))}</pre>\n\n'
        f'<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n'
        f'<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n'
        f'<pre>{error_message}</pre>'
    )

    # Finally, send the message
    context.bot.send_message(chat_id=conf.USER_ID['master'], text=message, parse_mode=ParseMode.HTML)


def restricted_command(func: Callable) -> Union[Callable, bool]:
    @wraps(func)
    def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id

        if user_id not in conf.USER_ID['admins']:
            error_message = 'Command execution forbidden (restricted access).'
            error_handler(update, context, error_message)

            reply = f'🖕🖕🖕 You are not allowed run this command.'
            update.message.reply_text(reply)

            reply_random_gif(update, 'fuck you')

            return

        return func(update, context, *args, **kwargs)

    return wrapped


def restricted_add(func: Callable) -> Union[Callable, bool]:
    @wraps(func)
    def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id

        if user_id not in conf.USER_ID['admins']:
            error_message = 'Add to group forbidden.'
            error_handler(update, context, error_message)

            reply = f'🖕🖕🖕 You are not allowed to add this bot to groups.'
            update.message.reply_text(reply)

            reply_random_gif(update, 'fuck you')

            update.effective_chat.leave()

            return

        return func(update, context, *args, **kwargs)

    return wrapped


def check_symbol_limit(func: Callable) -> Union[Callable, bool]:
    @wraps(func)
    def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        len_stonks = len(context.chat_data.get(conf.INTERNALS['stock'], {}))
        chat_type = update.effective_chat.type
        symbols_max = conf.LIMITS['default'][chat_type]['symbols_max']
        user_id = update.effective_user.id

        if len_stonks >= symbols_max and user_id not in conf.USER_ID['admins']:
            reply = f'❌ You are only allowed to watch {symbols_max} symbol(s). Please delete symbols from the watch ' \
                    f'list first.'
            update.message.reply_text(reply)

            reply_random_gif(update, 'too fat')

            return

        return func(update, context, *args, **kwargs)

    return wrapped


def send_typing_action(func: Callable) -> Callable:
    """Sends typing action while processing func command."""

    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)

        return func(update, context, *args, **kwargs)

    return command_func
