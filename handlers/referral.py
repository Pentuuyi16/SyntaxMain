from aiogram import Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

router = Router()


@router.callback_query(F.data == "referral")
async def referral_handler(callback: CallbackQuery):
    await callback.answer()

    text = (
        "👾 <b>Реферальная система</b>\n\n"
        "🚧 Раздел в разработке.\n\n"
        "Скоро ты сможешь приглашать друзей и "
        "получать бонусы к подписке!"
    )

    buttons = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_start")]]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb)