from aiogram import Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

router = Router()


@router.callback_query(F.data == "guide")
async def guide_handler(callback: CallbackQuery):
    await callback.answer()

    text = (
        "📖 <b>Как подключиться?</b>\n\n"
        "<b>1.</b> Купи подписку или активируй пробный период\n"
        "<b>2.</b> Скопируй ссылку подписки (в разделе «Мои ключи»)\n"
        "<b>3.</b> Скачай приложение:\n\n"
        "📱 <b>Android:</b>\n"
        "• <a href='https://play.google.com/store/apps/details?id=com.v2ray.ang'>V2RayNG</a>\n"
        "• <a href='https://play.google.com/store/apps/details?id=app.hiddify.com'>Hiddify</a>\n\n"
        "🍎 <b>iOS:</b>\n"
        "• Streisand (App Store)\n"
        "• V2Box (App Store)\n\n"
        "💻 <b>Windows / macOS:</b>\n"
        "• <a href='https://github.com/hiddify/hiddify-app/releases'>Hiddify</a>\n\n"
        "<b>4.</b> В приложении: «Добавить» → «Подписка» → вставь ссылку\n"
        "<b>5.</b> Обнови подписку — появятся все серверы\n"
        "<b>6.</b> Выбери сервер и подключись! 🚀"
    )

    buttons = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_start")]]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)