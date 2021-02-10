from functools import wraps

from telegram import ChatAction

from stonks_bot.helper.message import reply_random_gif

LIST_OF_ADMINS = [27891180]


def restricted(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id

        if user_id not in LIST_OF_ADMINS:
            reply = f'🖕🖕🖕'
            update.message.reply_text(reply)

            reply_random_gif(update, 'fuck you')

            return

        return func(update, context, *args, **kwargs)

    return wrapped


def send_typing_action(func):
    """Sends typing action while processing func command."""

    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)

        return func(update, context, *args, **kwargs)

    return command_func
