import html
from io import BytesIO
from typing import Optional, List

from telegram import Message, Update, Bot, User, Chat, ParseMode, InlineKeyboardMarkup
from telegram.error import BadRequest, TelegramError
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters
from telegram.utils.helpers import mention_html

import GroupMaster.modules.sql.antispam_sql as sql
from GroupMaster import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, STRICT_ANTISPAM
from GroupMaster.modules.helper_funcs.chat_status import user_admin, is_user_admin
from GroupMaster.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from GroupMaster.modules.helper_funcs.filters import CustomFilters
from GroupMaster.modules.helper_funcs.misc import send_to_list
from GroupMaster.modules.sql.users_sql import get_all_chats

from GroupMaster.modules.translations.strings import tld

GBAN_ENFORCE_GROUP = 6

GBAN_ERRORS = {
    "User is an administrator of the chat",
    "Chat not found",
    "Not enough rights to restrict/unrestrict chat member",
    "User_not_participant",
    "Peer_id_invalid",
    "Group chat was deactivated",
    "Need to be inviter of a user to kick it from a basic group",
    "Chat_admin_required",
    "Only the creator of a basic group can kick group administrators",
    "Channel_private",
    "Not in the chat"
}

UNGBAN_ERRORS = {
    "User is an administrator of the chat",
    "Chat not found",
    "Not enough rights to restrict/unrestrict chat member",
    "User_not_participant",
    "Method is available for supergroup and channel chats only",
    "Not in the chat",
    "Channel_private",
    "Chat_admin_required",
}


@run_async
def gban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bạn dường như không đề cập đến một người.")
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text("Tôi theo dõi, với con mắt nhỏ của tôi ... một cuộc chiến người dùng sudo! Tại sao các bạn đang bật nhau?")
        return

    if int(user_id) in SUPPORT_USERS:
        message.reply_text("Oooh ai đó đang cố gắng để người dùng hỗ trợ! *lấy bỏng ngô*")
        return

    if user_id == bot.id:
        message.reply_text("-_- Thật buồn cười, hãy là chính mình tại sao tôi phải không? Hãy thử tốt đẹp. Trái đất là giá của tôi!")
        return

    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        message.reply_text(excp.message)
        return

    if user_chat.type != 'private':
        message.reply_text("Đó không phải là người dùng!")
        return

    if sql.is_user_gbanned(user_id):
        if not reason:
            message.reply_text("Người này đã bị cấm toàn bộ nhóm; Tôi sẽ thay đổi lý do, nhưng bạn đã không cho tôi một ...")
            return

        old_reason = sql.update_gban_reason(user_id, user_chat.username or user_chat.first_name, reason)
        if old_reason:
            message.reply_text("Người này đã bị cấm, vì lý do sau:\n"
                               "<code>{}</code>\n"
                               "Tôi đã đi và cập nhật nó với lý do mới của bạn!".format(html.escape(old_reason)),
                               parse_mode=ParseMode.HTML)
        else:
            message.reply_text("Người này đã bị cấm, nhưng không có lý do nào; Tôi đã đi và cập nhật nó!")

        return
    
    ok123 = mention_html(user_chat.id, user_chat.first_name)


    text12 = f"⚡️Chuẩn bị đá đít súc vật {ok123}⚡️."
    update.effective_message.reply_text(text12, parse_mode=ParseMode.HTML)

    banner = update.effective_user  # type: Optional[User]
    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "<b>CẤM TOÀN BỘ NHÓM</b>" \
                 "\n#GBAN" \
                 "\n<b>Trạng thái:</b> <code>Đang cấm</code>" \
                 "\n<b>Admin:</b> {}" \
                 "\n<b>Người dùng:</b> {}" \
                 "\n<b>ID:</b> <code>{}</code>" \
                 "\n<b>Lý do:</b> {}".format(mention_html(banner.id, banner.first_name),
                                              mention_html(user_chat.id, user_chat.first_name), 
                                                           user_chat.id, reason or "Không có lí do"), 
                html=True)

    sql.gban_user(user_id, user_chat.username or user_chat.first_name, reason)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            bot.kick_chat_member(chat_id, user_id)
        except BadRequest as excp:
            if excp.message in GBAN_ERRORS:
                pass
            else:
                message.reply_text("Could not gban due to: {}".format(excp.message))
                send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "Could not gban due to: {}".format(excp.message))
                sql.ungban_user(user_id)
                return
        except TelegramError:
            pass

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                   "{} đã bị cấm thành công!".format(mention_html(user_chat.id, user_chat.first_name)),
                   html=True)
    text13 = f"Cấm {ok123} thành công, đã cấm khỏi 49 nhóm."
    update.effective_message.reply_text(text13, parse_mode=ParseMode.HTML)


@run_async
def ungban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Bạn dường như không đề cập đến một người.")
        return

    user_chat = bot.get_chat(user_id)
    if user_chat.type != 'private':
        message.reply_text("Đó không phải là một người!")
        return

    if not sql.is_user_gbanned(user_id):
        message.reply_text("Người này không bị cấm!")
        return

    banner = update.effective_user  # type: Optional[User]

    message.reply_text("Tô sẽ cho {} một cơ hội thứ hai, toàn cầu. Tôi không yêu cầu sự tin tưởng của bạn. Tôi chỉ yêu cầu sự vâng lời của bạn.".format(user_chat.first_name))

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "<b>GỠ CẤM TOÀN BỘ NHÓM</b>" \
                 "\n#UNGBAN" \
                 "\n<b>Status:</b> <code>Chấm dứt</code>" \
                 "\n<b>Admin:</b> {}" \
                 "\n<b>User:</b> {}" \
                 "\n<b>ID:</b> <code>{}</code>".format(mention_html(banner.id, banner.first_name),
                                                       mention_html(user_chat.id, user_chat.first_name), 
                                                                    user_chat.id),
                html=True)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status == 'kicked':
                bot.unban_chat_member(chat_id, user_id)

        except BadRequest as excp:
            if excp.message in UNGBAN_ERRORS:
                pass
            else:
                message.reply_text("Could not un-gban due to: {}".format(excp.message))
                bot.send_message(OWNER_ID, "Could not un-gban due to: {}".format(excp.message))
                return
        except TelegramError:
            pass

    sql.ungban_user(user_id)

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                  "{} đã được bỏ cấm thành công!".format(mention_html(user_chat.id,
                                                                         user_chat.first_name)),
                 html=True)

    message.reply_text("Người đã bị cấm. Lựa chọn khó nhất đòi hỏi ý chí mạnh nhất. 😐")



@run_async
def gbanlist(bot: Bot, update: Update):
    banned_users = sql.get_gban_list()

    if not banned_users:
        update.effective_message.reply_text("Không có bất kỳ người dùng bị cấm! Bạn tốt hơn tôi mong đợi ...")
        return

    banfile = 'Screw these guys.\n'
    for user in banned_users:
        banfile += "[x] {} - {}\n".format(user["name"], user["user_id"])
        if user["reason"]:
            banfile += "Reason: {}\n".format(user["reason"])

    with BytesIO(str.encode(banfile)) as output:
        output.name = "gbanlist.txt"
        update.effective_message.reply_document(document=output, filename="gbanlist.txt",
                                                caption="Here is the list of currently gbanned users.")


def check_and_ban(update, user_id, should_message=True):
    if sql.is_user_gbanned(user_id):
        update.effective_chat.kick_member(user_id)
        if should_message:
            update.effective_message.reply_text("Con súc vật này cút ra khỏi nhóm của bố ngay!")

#GMUTE

@run_async
def gmute(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bạn dường như không đề cập đến một người.")
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text("Tôi theo dõi, với con mắt nhỏ của tôi ... một cuộc chiến người dùng sudo! Tại sao các bạn đang bật nhau?")
        return

    if int(user_id) in SUPPORT_USERS:
        message.reply_text("Oooh ai đó đang cố gắng gmute một người dùng hỗ trợ! *lấy bỏng ngô*")
        return

    if user_id == bot.id:
        message.reply_text("-_- Thật buồn cười, hãy tắt tiếng chính mình Tại sao phải không? Hãy thử tốt đẹp.")
        return

    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        message.reply_text(excp.message)
        return

    if user_chat.type != 'private':
        message.reply_text("Đó không phải là người dùng!")
        return

    if sql.is_user_gmuted(user_id):
        if not reason:
            message.reply_text("Người dùng này đã bị tắt tiếng; Tôi sẽ thay đổi lý do, nhưng bạn đã không cho tôi một ...")
            return

        success = sql.update_gmute_reason(user_id, user_chat.username or user_chat.first_name, reason)
        if success:
            message.reply_text("Người dùng này đã bị tắt tiếng; Tôi đã đi và cập nhật lý do GMUTE!")
        else:
            message.reply_text("Bạn có phiền thử lại không? Tôi nghĩ rằng người này đã bị tắt tiếng, nhưng sau đó họ không? "
                               "Tôi rất bối rối")

        return

    message.reply_text("*Tiểu nhị, chuẩn bị băng keo* 😉")

    muter = update.effective_user  # type: Optional[User]
    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "{} đã tắt chat {} "
                 "tại vì:\n{}".format(mention_html(muter.id, muter.first_name),
                                       mention_html(user_chat.id, user_chat.first_name), reason or "Thích"),
                 html=True)

    sql.gmute_user(user_id, user_chat.username or user_chat.first_name, reason)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gmutes
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            bot.restrict_chat_member(chat_id, user_id, can_send_messages=False)
        except BadRequest as excp:
            if excp.message == "User is an administrator of the chat":
                pass
            elif excp.message == "Chat not found":
                pass
            elif excp.message == "Not enough rights to restrict/unrestrict chat member":
                pass
            elif excp.message == "User_not_participant":
                pass
            elif excp.message == "Peer_id_invalid":  # Suspect this happens when a group is suspended by telegram.
                pass
            elif excp.message == "Group chat was deactivated":
                pass
            elif excp.message == "Need to be inviter of a user to kick it from a basic group":
                pass
            elif excp.message == "Chat_admin_required":
                pass
            elif excp.message == "Only the creator of a basic group can kick group administrators":
                pass
            elif excp.message == "Method is available only for supergroups":
                pass
            elif excp.message == "Can't demote chat creator":
                pass
            else:
                message.reply_text("Could not gmute due to: {}".format(excp.message))
                send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "Could not gmute due to: {}".format(excp.message))
                sql.ungmute_user(user_id)
                return
        except TelegramError:
            pass

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "GMUTE HOÀN THÀNH!")
    message.reply_text("Người này đã bị gmuted.")


@run_async
def ungmute(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Bạn dường như không đề cập đến một người dùng.")
        return

    user_chat = bot.get_chat(user_id)
    if user_chat.type != 'private':
        message.reply_text("Đó không phải là người dùng!")
        return

    if not sql.is_user_gmuted(user_id):
        message.reply_text("Người dùng này không bị Gmuted!")
        return

    muter = update.effective_user  # type: Optional[User]

    message.reply_text("Tôi sẽ cho phép {} chat lại, toàn cầu.".format(user_chat.first_name))

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "{} có người dùng không khéo léo {}".format(mention_html(muter.id, muter.first_name),
                                                   mention_html(user_chat.id, user_chat.first_name)),
                 html=True)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gmutes
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status == 'restricted':
                bot.restrict_chat_member(chat_id, int(user_id),
                                     can_send_messages=True,
                                     can_send_media_messages=True,
                                     can_send_other_messages=True,
                                     can_add_web_page_previews=True)

        except BadRequest as excp:
            if excp.message == "User is an administrator of the chat":
                pass
            elif excp.message == "Chat not found":
                pass
            elif excp.message == "Not enough rights to restrict/unrestrict chat member":
                pass
            elif excp.message == "User_not_participant":
                pass
            elif excp.message == "Method is available for supergroup and channel chats only":
                pass
            elif excp.message == "Not in the chat":
                pass
            elif excp.message == "Channel_private":
                pass
            elif excp.message == "Chat_admin_required":
                pass
            else:
                message.reply_text("Could not un-gmute due to: {}".format(excp.message))
                bot.send_message(OWNER_ID, "Could not un-gmute due to: {}".format(excp.message))
                return
        except TelegramError:
            pass

    sql.ungmute_user(user_id)

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "Un-gmute hoàn thành!")

    message.reply_text("Người đã không được unmute")


@run_async
def gmutelist(bot: Bot, update: Update):
    muted_users = sql.get_gmute_list()

    if not muted_users:
        update.effective_message.reply_text("Không có bất kỳ người dùng Gmuted nào! Bạn tốt hơn tôi mong đợi ...")
        return

    mutefile = 'Screw these guys.\n'
    for user in muted_users:
        mutefile += "[x] {} - {}\n".format(user["name"], user["user_id"])
        if user["reason"]:
            mutefile += "Reason: {}\n".format(user["reason"])

    with BytesIO(str.encode(mutefile)) as output:
        output.name = "gmutelist.txt"
        update.effective_message.reply_document(document=output, filename="gmutelist.txt",
                                                caption="Dưới đây là danh sách những người dùng hiện đang được Gmuted.")


def check_and_mute(bot, update, user_id, should_message=True):
    if sql.is_user_gmuted(user_id):
        bot.restrict_chat_member(update.effective_chat.id, user_id, can_send_messages=False)
        if should_message:
            update.effective_message.reply_text("This is a bad person, I'll silence them for you!")


@run_async
def enforce_gmute(bot: Bot, update: Update):
    # Not using @restrict handler to avoid spamming - just ignore if cant gmute.
    if sql.does_chat_gban(update.effective_chat.id) and update.effective_chat.get_member(bot.id).can_restrict_members:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        msg = update.effective_message  # type: Optional[Message]

        if user and not is_user_admin(chat, user.id):
            check_and_mute(bot, update, user.id, should_message=True)
        if msg.new_chat_members:
            new_members = update.effective_message.new_chat_members
            for mem in new_members:
                check_and_mute(bot, update, mem.id, should_message=True)
        if msg.reply_to_message:
            user = msg.reply_to_message.from_user  # type: Optional[User]
            if user and not is_user_admin(chat, user.id):
                check_and_mute(bot, update, user.id, should_message=True)


@run_async
def enforce_gban(bot: Bot, update: Update):
    # Not using @restrict handler to avoid spamming - just ignore if cant gban.
    if sql.does_chat_gban(update.effective_chat.id) and update.effective_chat.get_member(bot.id).can_restrict_members:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        msg = update.effective_message  # type: Optional[Message]

        if user and not is_user_admin(chat, user.id):
            check_and_ban(update, user.id)

        if msg.new_chat_members:
            new_members = update.effective_message.new_chat_members
            for mem in new_members:
                check_and_ban(update, mem.id)

        if msg.reply_to_message:
            user = msg.reply_to_message.from_user  # type: Optional[User]
            if user and not is_user_admin(chat, user.id):
                check_and_ban(update, user.id, should_message=False)


@run_async
@user_admin
def antispam(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    if len(args) > 0:
        if args[0].lower() in ["on", "yes"]:
            sql.enable_antispam(chat.id)
            update.effective_message.reply_text(tld(chat.id, "Tôi đã kích hoạt an ninh Antispam trong nhóm này. Điều này sẽ giúp bảo vệ bạn "
                                                "từ những kẻ gửi thư rác, nhân vật không đáng kính và những con troll lớn nhất."))
        elif args[0].lower() in ["off", "no"]:
            sql.disable_antispam(chat.id)
            update.effective_message.reply_text(tld(chat.id, "Tôi đã vô hiệu hóa an ninh Antispam trong nhóm này. GBANS sẽ không ảnh hưởng đến người dùng của bạn "
                                                "nữa không. Bạn sẽ ít được bảo vệ khỏi bất kỳ troll và kẻ gửi thư rác "
                                                "mặc dù! Và tôi hơi thất vọng quá. 😶"))
    else:
        update.effective_message.reply_text(tld(chat.id, "Hãy cho tôi một số đối số để chọn một thiết lập! on/off, yes/no!\n\n"
                                            "Cài đặt hiện tại của bạn là: {}\n"
                                            "Khi True, Bất kỳ GBAN nào xảy ra cũng sẽ xảy ra trong nhóm của bạn. "
                                            "Khi False, họ sẽ không, để lại cho bạn sự thương xót có thể "
                                            "spammers.").format(sql.does_chat_gban(chat.id)))

#Gkick

GKICK_ERRORS = {
    "User is an administrator of the chat",
    "Chat not found",
    "Not enough rights to restrict/unrestrict chat member",
    "User_not_participant",
    "Peer_id_invalid",
    "Group chat was deactivated",
    "Need to be inviter of a user to kick it from a basic group",
    "Chat_admin_required",
    "Only the creator of a basic group can kick group administrators",
    "Channel_private",
    "Not in the chat",
    "Method is available for supergroup and channel chats only",
    "Reply message not found"
}

@run_async
def gkick(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    user_id = extract_user(message, args)
    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        if excp.message in GKICK_ERRORS:
            pass
        else:
            message.reply_text("Người dùng không thể bị đá trên toàn cầu vì: {}".format(excp.message))
            return
    except TelegramError:
            pass

    if not user_id:
        message.reply_text("Bạn dường như không được đề cập đến một người")
        return
    if int(user_id) in SUDO_USERS or int(user_id) in SUPPORT_USERS:
        message.reply_text("OHHH! Someone's trying to gkick a sudo/support user! *Grabs popcorn*")
        return
    if int(user_id) == OWNER_ID:
        message.reply_text("Wow! Some's trying to gkick my owner! *Grabs Potato Chips*")
        return
        
    if user_id == bot.id:
        message.reply_text("Chà, tôi sẽ không tự Gkick!")
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text("")
        return

    chats = get_all_chats()
    message.reply_text("Đá @{} khỏi toàn bộ nhóm".format(user_chat.username))
    for chat in chats:
        try:
            bot.unban_chat_member(chat.chat_id, user_id)  # Unban_member = kick (and not ban)
        except BadRequest as excp:
            if excp.message in GKICK_ERRORS:
                pass
            else:
                message.reply_text("Người không thể bị đá trên toàn cầu vì: {}".format(excp.message))
                return
        except TelegramError:
            pass


def __stats__():
    return "{} cấm toàn cầu.\n{} tắt chát toàn cầu.".format(sql.num_gbanned_users(), sql.num_gmuted_users())
    


def __user_info__(user_id, chat_id):
    is_gbanned = sql.is_user_gbanned(user_id)
    is_gmuted = sql.is_user_gmuted(user_id)

    if not user_id in SUDO_USERS:

        text = tld(chat_id, "Cấm toàn cầu: <b>{}</b>")
        if is_gbanned:
            text = text.format(tld(chat_id, "Yes"))
            user = sql.get_gbanned_user(user_id)
            if user.reason:
                text += tld(chat_id, "\nLý do: {}").format(html.escape(user.reason))
        else:
            text = text.format(tld(chat_id, "No"))
        
        text += tld(chat_id, "\nTắt chat toàn cầu: <b>{}</b>")
        if is_gmuted:
            text = text.format(tld(chat_id, "Yes"))
            user = sql.get_gmuted_user(user_id)
            if user.reason:
                text += tld(chat_id, "\nLý do: {}").format(html.escape(user.reason))
        else:
            text = text.format(tld(chat_id, "No"))

        return text
    else:
        return ""


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(bot, update, chat, chatP, user):
    chat_id = chat.id
    return "Trò chuyện này đang thực thi *GBAN*: `{}`.".format(sql.does_chat_gban(chat_id))


__help__ = """
*Admin only:*
 - /antispam <on/off/yes/no>: Sẽ vô hiệu hóa an ninh Antispam trong nhóm hoặc trả về cài đặt hiện tại của bạn.

Antispam được sử dụng bởi các chủ sở hữu bot để cấm những kẻ gửi thư rác trên tất cả các nhóm. Điều này giúp bảo vệ \
Bạn và các nhóm của bạn bằng cách loại bỏ lũ spam càng nhanh càng tốt. Họ có thể bị vô hiệu hóa cho nhóm bạn bằng cách gọi \
/antispam
"""

__mod_name__ = "Antispam 👿"

ANTISPAM_STATUS = CommandHandler("antispam", antispam, pass_args=True, filters=Filters.group)

GBAN_HANDLER = CommandHandler("gban", gban, pass_args=True,
                              filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
UNGBAN_HANDLER = CommandHandler("ungban", ungban, pass_args=True,
                                filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
GBAN_LIST = CommandHandler("gbanlist", gbanlist,
                           filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
GBAN_ENFORCER = MessageHandler(Filters.all & Filters.group, enforce_gban)


GMUTE_HANDLER = CommandHandler("gmute", gmute, pass_args=True,
                              filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
UNGMUTE_HANDLER = CommandHandler("ungmute", ungmute, pass_args=True,
                                filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
GMUTE_LIST = CommandHandler("gmutelist", gmutelist,
                           filters=CustomFilters.sudo_filter | CustomFilters.support_filter)


GKICK_HANDLER = CommandHandler("gkick", gkick, pass_args=True,
                              filters=CustomFilters.sudo_filter | CustomFilters.support_filter)

dispatcher.add_handler(ANTISPAM_STATUS)

dispatcher.add_handler(GBAN_HANDLER)
dispatcher.add_handler(UNGBAN_HANDLER)
dispatcher.add_handler(GBAN_LIST)

dispatcher.add_handler(GMUTE_HANDLER)
dispatcher.add_handler(UNGMUTE_HANDLER)
dispatcher.add_handler(GMUTE_LIST)

dispatcher.add_handler(GKICK_HANDLER)


if STRICT_ANTISPAM:  # enforce GBANS if this is set
    dispatcher.add_handler(GBAN_ENFORCER, GBAN_ENFORCE_GROUP)
