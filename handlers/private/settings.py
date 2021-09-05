import typing as p

from aiogram import types as t
from aiogram.dispatcher import FSMContext
from aiogram.utils.callback_data import CallbackData

import handlers.all
from bot import dp
from handlers.private import alias_form, report_form
from libs.buttons import Submenu
from libs.chat import Chat
from libs.errors import EmptyOwns
from libs.settings import Property, SettingsType
from libs.user import User
from src.objects import MessageData
from src import buttons, text, filters as f, utils as u

s = buttons.private.settings
alias_data = CallbackData("delete_alias", "key")
lang_data = CallbackData("change_lang", "lang")
statistic_data = CallbackData("statistic", "mode")
set_report_delta = CallbackData("set_report_delta", "delta")


@dp.message_handler(u.write_action, f.message.is_private, commands=["settings"])
async def settings_cmd(msg: t.Message):
    await buttons.private.settings.settings.send()


@s.private_settings(f.message.is_private)
async def private_settings(clb: t.CallbackQuery):
    user = await User.create(clb.from_user)
    with MessageData.data() as data:
        data.user = user
    await buttons.private.settings.private.settings.menu(user.settings).edit()


@s.chat_settings(f.message.is_private)
async def chat_settings(clb: t.CallbackQuery):
    user = await User.create(clb.from_user)
    await clb.message.edit_text(text.private.settings.chat_loading)
    chats = await user.get_owns()

    if not chats:
        await EmptyOwns().answer()
        await clb.message.delete()
        await buttons.private.settings.settings.send()
        return

    menu = buttons.private.settings.chat_list.copy
    for chat in chats:
        s = chat.settings
        settings = buttons.private.settings.chat.settings.menu(s, text=chat.title, callback_data=chat.id)
        settings.storage["chat"] = chat
        settings.storage["test"] = s
        menu.add(settings, )
    await menu.edit()


@s.chat.add_alias(f.message.is_private)
async def add_alias(clb: t.CallbackQuery, state: FSMContext):
    with MessageData.data() as data:
        prop: Property = data.property

    if prop.key == "sticker_alias":
        await alias_form.start_sticker(clb, state)
    elif prop.key == "text_alias":
        await alias_form.start_text(clb, state)


@s.chat.set_report_count(f.message.is_private)
@s.chat.set_report_command(f.message.is_private)
@s.chat.set_report_delta(f.message.is_private)
async def start_report_form(clb: t.CallbackQuery, state: FSMContext):
    type = clb.data
    if type == "set_report_command":
        await report_form.start_command(clb, state)
    elif type == "set_report_count":
        await report_form.start_count(clb, state)
    elif type == "set_report_delta":
        await report_form.start_delta(clb, state)


@dp.callback_query_handler(f.message.is_private, alias_data.filter())
async def delete_alias(clb: t.CallbackQuery, callback_data: p.Dict[str, str]):
    with MessageData.data() as data:
        data.key = callback_data["key"]
    await buttons.private.settings.chat.delete.edit()


@s.chat.delete_yes(f.message.is_private)
async def delete_yes(clb: t.CallbackQuery):
    with MessageData.data() as data:
        settings: SettingsType = data.settings
        chat: Chat = data.chat
        prop: Property = data.property
        menu: Submenu = data.menu
        key = data.key
    settings.pop(key)
    menu.update(prop.menu(settings))
    await menu.edit(False)
    chat.chatOBJ.settings = chat.settings


@dp.callback_query_handler(f.message.is_private, lang_data.filter())
async def edit_lang(clb: t.CallbackQuery, callback_data: p.Dict[str, str]):
    with MessageData.data() as data:
        settings: SettingsType = data.settings
        user: User = data.user
    settings["lang"] = callback_data["lang"]
    user.userOBJ.settings = user.settings
    await handlers.all.back(clb)


@dp.callback_query_handler(f.message.is_private, statistic_data.filter())
async def statistic_change(clb: t.CallbackQuery, callback_data: p.Dict[str, str]):
    with MessageData.data() as data:
        settings: SettingsType = data.settings
        target: p.Union[Chat, User] = data.chat or data.user
        menu: Submenu = data.menu

    settings["mode"] = int(callback_data["mode"])
    if isinstance(target, Chat):
        target.chatOBJ.settings = target.settings
    else:
        target.userOBJ.settings = target.settings

    await menu.edit(False)
    await clb.answer(text.private.settings.statistic_mode_changed)


@buttons.statistic_title.format_callback()
@text.private.settings.statistic_mode_changed.format_callback()
def format_callback(t: str):
    with MessageData.data() as data:
        target: p.Union[Chat, User] = data.chat or data.user
    return t.format(mode=str(text.statistic_modes[target.statistic_mode]))
