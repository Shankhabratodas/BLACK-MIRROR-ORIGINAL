import random
import string
from threading import Thread
import pytz

from datetime import datetime
from telegram.ext import CommandHandler
from telegram import ParseMode
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import auto_delete_message, sendMessage, sendMarkup, deleteMessage, delete_all_messages, update_all_messages, sendStatusMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.mirror_utils.status_utils.clone_status import CloneStatus
from bot import PM_LOG, bot, dispatcher, LOGGER, CLONE_LIMIT, STOP_DUPLICATE, LOGS_CHATS, download_dict, download_dict_lock, Interval, TIMEZONE
from bot.helper.ext_utils.bot_utils import get_readable_file_size, is_appdrive_link, is_gdrive_link, is_gdtot_link, new_thread, secondsToText
from bot.helper.mirror_utils.download_utils.direct_link_generator import appdrive, gdtot
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException

@new_thread
def cloneNode(update, context):
    if PM_LOG:
        try:
            sent_msg = bot.copy_message(
                chat_id=update.message.from_user.id,
                from_chat_id=update.message.chat.id,
                message_id=update.message.message_id
            )
            deleteMessage(update.message.from_user.id, sent_msg.message_id)
        except Exception as ex:
            print(ex)
            help_msg = 'šš­šš«š­ šš”š ššØš­ šš¬š¢š§š  šš”š šš¢š§š¤,\n\nšš­ šššššš ššØš« šš¢š«š¬š­ šš¢š¦š\n\nššØ ššØš­ ššš§ šš¢šÆš ššØš® šš¢š«š«šØš« šš¢š„šš¬ šš§ ššØš®š« šš \nššš«š šš¬ šš”š šš¢š§š¤: https://t.me/' + bot.get_me().username + '?start=start'
            return sendMessage(help_msg, context.bot, update.message)
    args = update.message.text.split(" ", maxsplit=1)
    reply_to = update.message.reply_to_message
    link = ''
    if len(args) > 1:
        link = args[1]
        if update.message.from_user.username:
            tag = f"@{update.message.from_user.username}"
        else:
            tag = update.message.from_user.mention_html(update.message.from_user.first_name)
    if reply_to is not None:
        if len(link) == 0:
            link = reply_to.text
        if reply_to.from_user.username:
            tag = f"@{reply_to.from_user.username}"
        else:
            tag = reply_to.from_user.mention_html(reply_to.from_user.first_name)
    is_appdrive = is_appdrive_link(link)
    if is_appdrive:
        try:
            msg = sendMessage(f"PŹį“į“į“ssÉŖÉ“É¢ Aį“į“į“ŹÉŖį“ į“ LÉŖÉ“į“:- \n<code>{link}</code>", context.bot, update.message)
            link = appdrive(link)
            deleteMessage(context.bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(context.bot, msg)
            return sendMessage(str(e), context.bot, update)
    is_gdtot = is_gdtot_link(link)
    if is_gdtot:
        try:
            msg = sendMessage(f"ššššššššš ššššš šššš ā <code>{link}</code>", context.bot, update.message)
            link = gdtot(link)
            deleteMessage(context.bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(context.bot, msg)
            return sendMessage(str(e), context.bot, update.message)
    if is_gdrive_link(link):
        autodel = secondsToText()
        msg1 = f'<b> I have sent files in PM & <a href="https://t.me/reflectionmir_logs"><b>LOG CHANNEL</b></a>\n This message will auto deleted in {autodel} </b>' if PM_LOG else ''
        gd = GoogleDriveHelper()
        res, size, name, files = gd.helper(link)
        if res != "":
            return sendMessage(res, context.bot, update.message)
        if STOP_DUPLICATE:
            LOGGER.info('Checking File/Folder if already in Drive...')
            smsg, button = gd.drive_list(name, True, True)
            if smsg:
                msg3 = "š šš¢š„š/ššØš„ššš« š¢š¬ šš„š«šššš² ššÆšš¢š„ššš„š š¢š§ šš«š¢šÆš.\nššš«š šš«š š­š”š š¬ššš«šš” š«šš¬š®š„š­š¬ ā“"
                return sendMarkup(msg3, context.bot, update.message, button)
        if CLONE_LIMIT is not None:
            LOGGER.info('Checking File/Folder Size...')
            if size > CLONE_LIMIT * 1024**3:
                msg2 = f'ššš¢š„šš, šš„šØš§š š„š¢š¦š¢š­ š¢š¬ {CLONE_LIMIT}GB.\nYour File/Folder size is {get_readable_file_size(size)}.'
                return sendMessage(msg2, context.bot, update.message)
        if files <= 20:
            msg = sendMessage(f"āļø šš„šØš§š¢š§š  ššØš®š« šš¢š„š/ššØš„ššš« šš§š­šØ šš² šš«š¢šÆš !! ššØš®š« šš¢š§š¤ ā <code>{link}</code>", context.bot, update.message)
            result, button = gd.clone(link)
            deleteMessage(context.bot, msg)
        else:
            drive = GoogleDriveHelper(name)
            gid = ''.join(random.SystemRandom().choices(string.ascii_letters + string.digits, k=12))
            clone_status = CloneStatus(drive, size, update.message, gid)
            with download_dict_lock:
                download_dict[update.message.message_id] = clone_status
            sendStatusMessage(update.message, context.bot)
            result, button = drive.clone(link)
            with download_dict_lock:
                del download_dict[update.message.message_id]
                count = len(download_dict)
            try:
                if count == 0:
                    Interval[0].cancel()
                    del Interval[0]
                    delete_all_messages()
                else:
                    update_all_messages()
            except IndexError:
                pass
        result += f'\nā°āš¬ šš² ā¢ {tag}\n\n'
        if button in ["cancelled", ""]:
            reply_message = sendMessage(f"{tag} {result}", context.bot, update.message)
        else:
            reply_message = sendMarkup(result + msg1, context.bot, update.message, button)
            if PM_LOG:
                Thread(target=auto_delete_message, args=(context.bot, update.message, reply_message, True)).start()
                bot.sendMessage(chat_id=update.message.from_user.id, text=result, reply_markup=button, parse_mode=ParseMode.HTML) 
        if LOGS_CHATS:
            try:
                for i in LOGS_CHATS:
                    kie = datetime.now(pytz.timezone(f'{TIMEZONE}'))
                    jam = kie.strftime('\n šš®šš² : %d/%m/%Y\n š§š¶šŗš²: %I:%M:%S %P')
                    msg1 = f'{jam}'
                    msg1 += f'\nā­āš šš¢š„šš§šš¦š ā¢ <code>{name}</code>'
                    msg1 += f'\nāāš¹ļø Size ā¢ {get_readable_file_size(size)}'
                    msg1 += f'\nā°āš¬ šš² ā¢ {tag}\n\n'
                    bot.sendMessage(chat_id=i, text=msg1, reply_markup=button, parse_mode=ParseMode.HTML)
            except Exception as e:
                LOGGER.warning(e)
        if is_gdtot:
            gd.deletefile(link)
        if is_appdrive:
            gd.deletefile(link)
    else:
        sendMessage('šš¢šÆš ššš«š¢šÆš šØš« ššš«š¢šÆš site š„š¢š§š¤ šš„šØš§š  š°š¢š­š” ššØš¦š¦šš§š šØš« šš² š«šš©š„š²š¢š§š  š­šØ š­š”š š„š¢š§š¤ šš² ššØš¦š¦šš§š', context.bot, update.message)

clone_handler = CommandHandler(BotCommands.CloneCommand, cloneNode, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
dispatcher.add_handler(clone_handler)
