from functools import wraps
from typing import Callable, Union

from telegram import ChatAction, Update
from telegram.ext import CallbackContext

from stonks_bot import conf
from stonks_bot.helper.message import reply_random_gif


class Any(object):
    pass


def log_error(func_error_handler: Callable[..., Any], error_message: str) -> Union[Callable, bool]:
    def decorator(func: Callable[..., Any]) -> Union[Callable, bool]:
        @wraps(func)
        def wrapped(update: Update, context: CallbackContext, *args, **kwargs) -> Union[Callable[..., Any], bool]:
            func_error_handler(update, context, error_message)

            return func(update, context, *args, **kwargs)

        return wrapped

    return decorator


def restricted_command(func_error_handler: Callable[..., Any], error_message: str) -> Union[Callable, bool]:
    def decorator(func: Callable[..., Any]) -> Union[Callable[..., Any], bool]:
        @wraps(func)
        def wrapped(update: Update, context: CallbackContext, *args, **kwargs) -> Union[Callable[..., Any], bool]:
            user_id = update.effective_user.id

            if user_id not in conf.USER_ID['admins']:
                func_error_handler(update, context, error_message)

                reply = f'🖕🖕🖕 You are not allowed run this command.'
                update.message.reply_text(reply)

                reply_random_gif(update, 'fuck you')

                return
            return func(update, context, *args, **kwargs)

        return wrapped

    return decorator


def restricted_group_command(func_error_handler: Callable[..., Any], error_message: str) -> Union[
    Callable[..., Any], bool]:
    def decorator(func: Callable[..., Any]) -> Union[Callable[..., Any], bool]:
        @wraps(func)
        def wrapped(update: Update, context: CallbackContext, *args, **kwargs) -> Union[Callable[..., Any], bool]:
            user_id = update.effective_user.id

            if user_id not in conf.USER_ID['admins'] and update.effective_chat.id < 0:
                func_error_handler(update, context, error_message)

                reply = f'🖕🖕🖕 You are not allowed run this command.'
                update.message.reply_text(reply)

                reply_random_gif(update, 'fuck you')

                return
            return func(update, context, *args, **kwargs)

        return wrapped

    return decorator


def restricted_add(func_error_handler: Callable[..., Any], error_message: str) -> Union[Callable[..., Any], bool]:
    def decorator(func: Callable[..., Any]) -> Union[Callable[..., Any], bool]:
        @wraps(func)
        def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
            user_id = update.effective_user.id

            if user_id not in conf.USER_ID['admins']:
                func_error_handler(update, context, error_message)

                reply = f'🖕🖕🖕 You are not allowed to add this bot to groups.'
                update.message.reply_text(reply)

                reply_random_gif(update, 'fuck you')

                update.effective_chat.leave()

                return
            return func(update, context, *args, **kwargs)

        return wrapped

    return decorator


def check_symbol_limit(func: Callable[..., Any]) -> Union[Callable[..., Any], bool]:
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


def send_typing_action(func: Callable[..., Any]) -> Callable[..., Any]:
    """Sends typing action while processing func command."""

    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)

        return func(update, context, *args, **kwargs)

    return command_func
