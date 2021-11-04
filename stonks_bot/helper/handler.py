import html
import logging
import traceback
from typing import Union, Optional, Tuple

from telegram import Update, ParseMode, ChatMemberUpdated, ChatMember, Chat
from telegram.ext import CallbackContext

from stonks_bot import conf
from stonks_bot.dataclasses.data_chat import DataChat
from stonks_bot.dataclasses.data_user import DataUser
from stonks_bot.dataclasses.tracking_chats import TrackingChat
from stonks_bot.helper.command import restricted_add
from stonks_bot.helper.formatters import formatter_to_json
from stonks_bot.helper.message import send_message, reply_random_gif

logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


def log_message_handler(context: CallbackContext, message: str) -> None:
    """Send any logging message to the master user."""

    # Finally, send the message
    send_message(context, conf.USER_ID['master'], message, parse_mode=ParseMode.HTML, pre=True)


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
        f'update = {html.escape(formatter_to_json(update_dict))}\n\n'
        f'context.bot_data = {html.escape(formatter_to_json(bot_data))}\n\n'
        f'context.chat_data = {html.escape(formatter_to_json(chat_data))}\n\n'
        f'context.user_data = {html.escape(formatter_to_json(user_data))}\n\n'
        f'{additional_info}'
    )

    # Finally, send the message
    log_message_handler(context, message)


def extract_status_change(chat_member_update: ChatMemberUpdated) -> Optional[Tuple[bool, bool]]:
    """Takes a ChatMemberUpdated instance and extracts whether the 'old_chat_member' was a member
    of the chat and whether the 'new_chat_member' is a member of the chat. Returns None, if
    the status didn't change."""
    status_change = chat_member_update.difference().get("status")
    old_is_member, new_is_member = chat_member_update.difference().get("is_member", (None, None))

    if status_change is None:
        return None
    # We first check if the bot was a chat member before and if it it now
    old_status, new_status = status_change
    was_member = (
            old_status
            in [
                ChatMember.MEMBER,
                ChatMember.CREATOR,
                ChatMember.ADMINISTRATOR,
            ]
            or (old_status == ChatMember.RESTRICTED and old_is_member is True)
    )
    is_member = (
            new_status
            in [
                ChatMember.MEMBER,
                ChatMember.CREATOR,
                ChatMember.ADMINISTRATOR,
            ]
            or (new_status == ChatMember.RESTRICTED and new_is_member is True)
    )

    return was_member, is_member


def track_chats(update: Update, context: CallbackContext) -> None:
    """Tracks the chats the bot is in."""
    result = extract_status_change(update.my_chat_member)
    if result is None:
        return
    was_member, is_member = result

    # Let's check how is responsible for the change
    cause_name = update.effective_user.full_name

    # Handle chat types differently:
    chat = update.effective_chat
    if chat.type == Chat.PRIVATE:
        if not was_member and is_member:
            bot_added_to(update, context, conf.INTERNALS['users'])
            log_message_handler(context, f'"{cause_name}" started the bot.')
        elif was_member and not is_member:
            bot_removed_from(update, context, conf.INTERNALS['users'])
            log_message_handler(context, f'"{cause_name}" blocked the bot.')
    elif chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        if not was_member and is_member:
            log_message_handler(context, f'"{cause_name}" added the bot to the group "{chat.title}".')
            bot_added_to_group(update, context)
        elif was_member and not is_member:
            log_message_handler(context, f'"{cause_name}" removed the bot from the group "{chat.title}".')
            bot_removed_from(update, context, conf.INTERNALS['groups'])
    else:
        if not was_member and is_member:
            log_message_handler(context, f'"{cause_name}" added the bot to the channel "{chat.title}".')
            bot_added_to_channel(update, context)
        elif was_member and not is_member:
            log_message_handler(context, f'"{cause_name}" removed the bot from the channel "{chat.title}".')
            bot_removed_from(update, context, conf.INTERNALS['channels'])


def greet_chat_members(update: Update, _: CallbackContext) -> None:
    """Greets new users in chats and announce if someone leaves"""
    result = extract_status_change(update.chat_member)

    if result is None:
        return

    was_member, is_member = result
    cause_name = update.chat_member.from_user.mention_html()
    member_name = update.chat_member.new_chat_member.user.mention_html()

    if not was_member and is_member:
        update.effective_chat.send_message(
                f'🎲 {member_name} was added by {cause_name}. Welcome! Please type /help to see the my commands.',
                parse_mode=ParseMode.HTML,
        )
        search = 'money'
        reply_random_gif(update, search)
    elif was_member and not is_member:
        update.effective_chat.send_message(
                f'🏃 {member_name} is no longer with us, loooser. Thanks {cause_name} ...',
                parse_mode=ParseMode.HTML,
        )
        search = 'loser'
        reply_random_gif(update, search)


@restricted_add(error_handler, 'Add to group forbidden.')
def bot_added_to_group(update: Update, context: CallbackContext) -> bool:
    bot_added_to(update, context, conf.INTERNALS['groups'])

    return True


@restricted_add(error_handler, 'Add to channel forbidden.')
def bot_added_to_channel(update: Update, context: CallbackContext) -> bool:
    bot_added_to(update, context, conf.INTERNALS['channels'])

    return True


def bot_added_to(update: Update, context: CallbackContext, key: str) -> bool:
    g = context.bot_data.get(key, {})
    effective_chat = update.effective_chat.to_dict()
    dc = DataChat(**effective_chat)
    cause_user = update.effective_user.to_dict()
    du = DataUser(**cause_user)
    tc = TrackingChat(chat=dc, cause_user=du)
    g[effective_chat['id']] = tc
    context.bot_data[key] = g

    return True


def bot_removed_from(update: Update, context: CallbackContext, chat_type: str, chat_id: int = 0) -> bool:
    g = context.bot_data.get(chat_type, {})
    chat_id_remove = chat_id if chat_id != 0 else update.effective_chat.id
    g.pop(chat_id_remove, None)
    context.bot_data[chat_type] = g

    return True
