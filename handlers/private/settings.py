import typing as p

from aiogram import types as t
from aiogram.dispatcher import FSMContext
from aiogram.utils.callback_data import CallbackData

import handlers.all
from bot import dp
from handlers.private import alias_form
from libs import filters as f
from libs.classes import Utils as u
from libs.classes.Chat import Chat
from libs.classes.Errors import EmptyOwns
from libs.classes.Settings import Property, SettingsType
from libs.classes.User import User
from libs.objects import MessageData
from libs.src import buttons, text, any

s = buttons.private.settings
alias_data = CallbackData("delete_alias", "key")
lang_data = CallbackData("change_lang", "lang")


@dp.message_handler(u.write_action, f.message.is_private, commands=["settings"])
async def settings_cmd(msg: t.Message):
    await buttons.private.settings.settings.send()


@s.private_settings(f.message.is_private)
async def private_settings(clb: t.CallbackQuery):
    user = await User.create()
    await buttons.private.settings.private.settings.menu(user.settings.row).edit()


@s.chat_settings(f.message.is_private)
async def chat_settings(clb: t.CallbackQuery):
    user = await User.create()
    await clb.message.edit_text(text.private.settings.chat_loading)
    chats = await user.get_owns()

    if not chats:
        await EmptyOwns().answer()
        await clb.message.delete()
        await buttons.private.settings.settings.send()

    menu = buttons.private.settings.chat_list.copy
    for chat in chats:
        s = chat.settings.row
        settings = buttons.private.settings.chat.settings.menu(s, text=chat.title, callback_data=chat.id)
        settings.storage["chat"] = chat
        menu.add(settings)
    await menu.edit()


@s.chat.add_alias(f.message.is_private)
async def add_alias(clb: t.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data["settings_message"] = clb.message
    with await MessageData.data(clb.message) as data:
        prop: Property = data.property

    if prop.key == "sticker_alias":
        await alias_form.start_sticker(clb)
    elif prop.key == "text_alias":
        await alias_form.start_text(clb)


@dp.callback_query_handler(f.message.is_private, alias_data.filter())
async def delete_alias(clb: t.CallbackQuery, callback_data: p.Dict[str, str]):
    with await MessageData.data(clb.message) as data:
        data.key = callback_data["key"]
    await buttons.private.settings.chat.delete.edit()


@s.chat.delete_yes(f.message.is_private)
async def delete_yes(clb: t.CallbackQuery):
    with await MessageData.data(clb.message) as data:
        settings: SettingsType = data.settings
        chat: Chat = data.chat
        prop: Property = data.property
        key = data.key
    settings.pop(key)
    await prop.menu(settings).edit(False)
    chat.chat.settings = chat.settings.row


@dp.callback_query_handler(f.message.is_private, lang_data.filter())
async def delete_alias(clb: t.CallbackQuery, callback_data: p.Dict[str, str]):
    user = await User.create()
    user.settings.lang = callback_data["lang"]
    await handlers.all.back(clb)
