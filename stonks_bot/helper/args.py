from typing import Union

from telegram import Update

from stonks_bot.helper.message import reply_random_gif


def check_arg_symbol(update: Update, args: list) -> Union[bool, str]:
    if len(args) == 0:
        reply = f'Provide a SYMBOL you 🧻🤲🐩.'
        update.message.reply_text(reply)

        reply_random_gif(update, 'fail')

        result = False
    else:
        result = args[0]

    return result
