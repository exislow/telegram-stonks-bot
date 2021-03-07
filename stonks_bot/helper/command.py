from functools import wraps

from telegram import ChatAction, Update
from telegram.ext import CallbackContext

from stonks_bot import conf
from stonks_bot.helper.message import reply_random_gif


def restricted_command(func):
    @wraps(func)
    def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id

        if user_id not in conf.USER_ID['admins']:
            reply = f'🖕🖕🖕 You are not allowed run this command.'
            update.message.reply_text(reply)

            reply_random_gif(update, 'fuck you')

            return

        return func(update, context, *args, **kwargs)

    return wrapped


def restricted_add(func):
    @wraps(func)
    def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id

        if user_id not in conf.USER_ID['admins']:
            reply = f'🖕🖕🖕 You are not allowed to add this bot to groups.'
            update.message.reply_text(reply)

            reply_random_gif(update, 'fuck you')

            update.effective_chat.leave()

            return

        return func(update, context, *args, **kwargs)

    return wrapped


@restricted_add
def bot_added_to_group(update: Update, context: CallbackContext):
    g = context.bot_data.get(conf.INTERNALS['groups'], {})
    g[update.message.chat_id] = update.message.chat
    context.bot_data[conf.INTERNALS['groups']] = g


def send_typing_action(func):
    """Sends typing action while processing func command."""

    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)

        return func(update, context, *args, **kwargs)

    return command_func
