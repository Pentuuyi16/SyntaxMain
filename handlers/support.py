from aiogram import Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

router = Router()

SUPPORT_VIDEO = "BAACAgIAAxkBAAPkabG6bCrHTuYunAN6oifN10gFV80AAoufAAJaVpBJ5f8STYZBFXQ6BA"


def has_media(message) -> bool:
    return bool(message.photo or message.video or message.animation)


@router.callback_query(F.data == "support")
async def support_handler(callback: CallbackQuery):
    await callback.answer()

    buttons = [
        [InlineKeyboardButton(text="🔌 Как подключить VPN?", callback_data="how_to_connect")],
        [InlineKeyboardButton(text="⁉️ Часто задаваемые вопросы", callback_data="faq")],
        [InlineKeyboardButton(text="🎧 Чат с поддержкой", callback_data="chat_support")],
        [InlineKeyboardButton(text="🚪 Назад", callback_data="back_start")],
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    if has_media(callback.message):
        await callback.message.delete()
    else:
        try:
            await callback.message.delete()
        except Exception:
            pass

    await callback.message.answer_video(video=SUPPORT_VIDEO, caption=text, reply_markup=kb)


@router.callback_query(F.data == "faq")
async def faq_handler(callback: CallbackQuery):
    await callback.answer()

    text = (
        "♟ Здесь собраны ответы на самые популярные вопросы.\n\n"
        "<b>Мои данные в безопасности?</b>\n"
        "— Да. Ваша информация под надёжной защитой. "
        "Мы применяем современные протоколы шифрования, "
        "благодаря которым доступ к трафику для третьих лиц исключён.\n\n"
        "<b>Говорят, что VPN может передавать или красть данные.</b>\n"
        "— Такое возможно у недобросовестных сервисов. "
        "Мы работаем на репутацию и долгосрочное сотрудничество, "
        "поэтому не имеем доступа к вашему зашифрованному трафику "
        "и не собираем личную информацию.\n\n"
        "<b>Есть ли ограничения по подписке?</b>\n"
        "— Да, предусмотрены лимиты: до 2 устройств на один ключ."
    )

    buttons = [[InlineKeyboardButton(text="🚪 Назад", callback_data="support")]]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    if has_media(callback.message):
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=kb)
    else:
        await callback.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "how_to_connect")
async def how_to_connect_handler(callback: CallbackQuery):
    await callback.answer()

    text = "🔌 <b>Как подключить VPN?</b>\n\n🚧 Раздел в разработке."

    buttons = [[InlineKeyboardButton(text="🚪 Назад", callback_data="support")]]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    if has_media(callback.message):
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=kb)
    else:
        await callback.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "chat_support")
async def chat_support_handler(callback: CallbackQuery):
    await callback.answer()

    text = "🎧 <b>Чат с поддержкой</b>\n\n🚧 Раздел в разработке."

    buttons = [[InlineKeyboardButton(text="🚪 Назад", callback_data="support")]]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    if has_media(callback.message):
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=kb)
    else:
        await callback.message.edit_text(text, reply_markup=kb)