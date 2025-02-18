import html
from typing import Optional, List

from telegram import Message, Update, Bot, User
from telegram import ParseMode, MAX_MESSAGE_LENGTH
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown

import GroupMaster.modules.sql.userinfo_sql as sql
from GroupMaster import dispatcher, SUDO_USERS, OWNER_ID
from GroupMaster.modules.disable import DisableAbleCommandHandler
from GroupMaster.modules.helper_funcs.extraction import extract_user
from GroupMaster.modules.helper_funcs.chat_status import is_user_admin, bot_admin, user_admin_no_reply, user_admin, \
    can_restrict


@run_async
def about_me(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]
    user_id = extract_user(message, args)

    if user_id:
        user = bot.get_chat(user_id)
    else:
        user = message.from_user

    info = sql.get_user_me_info(user.id)

    if info:
        update.effective_message.reply_text("*{}*:\n{}".format(user.first_name, escape_markdown(info)),
                                            parse_mode=ParseMode.MARKDOWN)
    elif message.reply_to_message:
        username = message.reply_to_message.from_user.first_name
        update.effective_message.reply_text(username + " Chưa đặt thông điệp thông tin về bản thân!")
    else:
        update.effective_message.reply_text("Bạn chưa đặt thông báo thông tin về bản thân!")

@bot_admin
@user_admin
@run_async
def set_about_me(bot: Bot, update: Update):
    message = update.effective_message  # type: Optional[Message]
    user_id = message.from_user.id
    text = message.text
    info = text.split(None, 1)  # use python's maxsplit to only remove the cmd, hence keeping newlines.
    if len(info) == 2:
        if len(info[1]) < MAX_MESSAGE_LENGTH // 4:
            sql.set_user_me_info(user_id, info[1])
            message.reply_text("Cập nhật thông tin của bạn!")
        else:
            message.reply_text(
                "Thông tin của bạn cần phải được dưới {} characters! You have {}.".format(MAX_MESSAGE_LENGTH // 4, len(info[1])))


@run_async
def about_bio(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if user_id:
        user = bot.get_chat(user_id)
    else:
        user = message.from_user

    info = sql.get_user_bio(user.id)

    if info:
        update.effective_message.reply_text("*Thông tin về {}*:\n{}".format(user.first_name, escape_markdown(info)),
                                            parse_mode=ParseMode.MARKDOWN)
    elif message.reply_to_message:
        username = user.first_name
        update.effective_message.reply_text("{} chưa được xác minh!".format(username))
    else:
        update.effective_message.reply_text("Bạn chưa được xác minh!")

@bot_admin
@user_admin
@run_async
def set_about_bio(bot: Bot, update: Update):
    message = update.effective_message  # type: Optional[Message]
    sender = update.effective_user  # type: Optional[User]
    if message.reply_to_message:
        repl_message = message.reply_to_message
        user_id = repl_message.from_user.id
        if user_id == message.from_user.id:
            message.reply_text("Ha, bạn không thể đặt Bio của riêng bạn! Bạn đang ở sự thương xót của những người khác ở đây ...")
            return
        elif user_id == bot.id and sender.id not in SUDO_USERS:
            message.reply_text("Erm ... Ừ, tôi chỉ tin tưởng người dùng sudo để đặt bio lmao của tôi.")
            return
        elif user_id in SUDO_USERS and sender.id not in SUDO_USERS:
            message.reply_text("Erm ... yeah, tôi chỉ tin tưởng người dùng sudo để thiết lập người dùng sudo bio lmao.")
            return
        elif user_id == OWNER_ID:
            message.reply_text("Bạn không đặt bậc thầy bio lmao.")
            return

        text = message.text
        bio = text.split(None, 1)  # use python's maxsplit to only remove the cmd, hence keeping newlines.
        if len(bio) == 2:
            if len(bio[1]) < MAX_MESSAGE_LENGTH // 4:
                sql.set_user_bio(user_id, bio[1])
                message.reply_text("{} đã được xác minh thành công!".format(repl_message.from_user.first_name))
            else:
                message.reply_text(
                    "Một sinh học cần phải được dưới {} nhân vật! Bạn đã cố gắng để thiết lập {}.".format(
                        MAX_MESSAGE_LENGTH // 4, len(bio[1])))
    else:
        message.reply_text("Trả lời tin nhắn của ai đó để đặt thông tin của họ!")


def __user_info__(user_id, chat_id):
    bio = html.escape(sql.get_user_bio(user_id) or "")
    me = html.escape(sql.get_user_me_info(user_id) or "")
    if bio and me:
        return "<b>About user:</b>\n{me}\n<b>What others say:</b>\n{bio}".format(me=me, bio=bio)
    elif bio:
        return "<b>What others say:</b>\n{bio}\n".format(me=me, bio=bio)
    elif me:
        return "<b>About user:</b>\n{me}""".format(me=me, bio=bio)
    else:
        return ""


def __gdpr__(user_id):
    sql.clear_user_info(user_id)
    sql.clear_user_bio(user_id)


__help__ = """
 - /thongtin: Kiểm tra thông tin
"""

__mod_name__ = "Cài thông tin"

SET_BIO_HANDLER = DisableAbleCommandHandler("setdata", set_about_bio)
GET_BIO_HANDLER = DisableAbleCommandHandler("thongtin", about_bio, pass_args=True)

SET_ABOUT_HANDLER = DisableAbleCommandHandler("setme", set_about_me)
GET_ABOUT_HANDLER = DisableAbleCommandHandler("me", about_me, pass_args=True)

dispatcher.add_handler(SET_BIO_HANDLER)
dispatcher.add_handler(GET_BIO_HANDLER)
dispatcher.add_handler(SET_ABOUT_HANDLER)
dispatcher.add_handler(GET_ABOUT_HANDLER)

