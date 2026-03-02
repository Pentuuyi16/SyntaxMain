from aiogram import Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

router = Router()


@router.callback_query(F.data == "support")
async def support_handler(callback: CallbackQuery):
    await callback.answer()

    text = (
        "🎧 <b>Поддержка Syntax VPN</b>\n\n"
        "Если у тебя возникли вопросы или проблемы, "
        "напиши нам — мы поможем!\n\n"
        "📩 Написать в поддержку: @syntax_vpn_support\n"
        "📢 Канал: @AllenVPN"
    )

    buttons = [
        [InlineKeyboardButton(text="📩 Написать в поддержку", url="https://t.me/syntax_vpn_support")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_start")],
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb)