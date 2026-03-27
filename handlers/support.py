from aiogram import Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from aiogram.filters import Command

router = Router()

SUPPORT_VIDEO = "BAACAgIAAxkBAAPkabG6bCrHTuYunAN6oifN10gFV80AAoufAAJaVpBJ5f8STYZBFXQ6BA"

def has_media(message) -> bool:
    return bool(message.photo or message.video or message.animation)

@router.message(Command("help"))
async def cmd_help(message: Message):
    text = "🎧 <b>Выберите раздел, и мы поможем разобраться!</b>"
    buttons = [
        [InlineKeyboardButton(text="🔌 Как подключить VPN?", callback_data="how_to_connect")],
        [InlineKeyboardButton(text="⁉️ Часто задаваемые вопросы", callback_data="faq")],
        [InlineKeyboardButton(text="🎧 Чат с поддержкой", url="https://t.me/SyntaxSupport")],
        [InlineKeyboardButton(text="🚪 Назад", callback_data="back_start")],
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(text, reply_markup=kb)

@router.callback_query(F.data == "support")
async def support_handler(callback: CallbackQuery):
    await callback.answer()

    text = (
        
        "🎧 <b>Выберите раздел, и мы поможем разобраться!</b>"
    )

    buttons = [
        [InlineKeyboardButton(text="🔌 Как подключить VPN?", callback_data="how_to_connect")],
        [InlineKeyboardButton(text="⁉️ Часто задаваемые вопросы", callback_data="faq")],
        [InlineKeyboardButton(text="🎧 Чат с поддержкой", url="https://t.me/SyntaxSupport")],
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
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=kb)
    else:
        try:
            await callback.message.edit_text(text, reply_markup=kb)
        except Exception:
            await callback.message.answer(text, reply_markup=kb)

@router.callback_query(F.data == "how_to_connect")
async def how_to_connect_handler(callback: CallbackQuery):
    await callback.answer()

    text = (
        "📃 <b>Инструкция по подключению</b>\n\n"
        "⚖️ <b>Шаг 1. Установите приложение</b>\n"
        "Скачайте VPN-клиент:\n"
        "• <a href='https://play.google.com/store/search?q=Happ&c=apps&hl=ru'>Happ — Android</a>\n"
        "• <a href='https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973'>Happ — iOS</a>\n"
        "• <a href='https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.exe'>Happ — Windows</a>\n\n"
        "🔑 <b>Шаг 2. Импортируйте ключ</b>\n"
        "Откройте раздел «Мой ключ» и нажмите кнопку "
        "«Добавить VPN в приложение» (только если вы установили Happ), "
        "можно и вручную скопировать ключ и вставить\n\n"
        "🎉 <b>Шаг 3. Подключение</b>\n"
        "Готово! Пользуйтесь быстрым и безопасным интернетом 🚀\n\n"
        "🧾 В случае проблем с подключением помощь можно будет "
        "найти в разделе «🎧 Поддержка»"
    )

    buttons = [[InlineKeyboardButton(text="🚪 Назад", callback_data="support")]]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    if has_media(callback.message):
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=kb, disable_web_page_preview=True)
    else:
        try:
            await callback.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
        except Exception:
            await callback.message.answer(text, reply_markup=kb, disable_web_page_preview=True)

@router.callback_query(F.data == "chat_support")
async def chat_support_handler(callback: CallbackQuery):
    await callback.answer()

    buttons = [
        [InlineKeyboardButton(text="🎧 Написать в поддержку", url="https://t.me/SyntaxSupport")],
        [InlineKeyboardButton(text="🚪 Назад", callback_data="support")],
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    if has_media(callback.message):
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=kb)
    else:
        try:
            await callback.message.edit_text(text, reply_markup=kb)
        except Exception:
            await callback.message.answer(text, reply_markup=kb)