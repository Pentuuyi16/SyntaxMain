from aiogram import Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

router = Router()


def has_media(message) -> bool:
    return bool(message.photo or message.video or message.animation)


@router.callback_query(F.data == "referral")
async def referral_handler(callback: CallbackQuery):
    await callback.answer()

    text = (
        "👾 <b>Реферальная система</b>\n\n"
        "🚧 Раздел в разработке.\n\n"
        "Скоро ты сможешь приглашать друзей и "
        "получать бонусы к подписке!"
    )

    buttons = [[InlineKeyboardButton(text="🚪 Назад", callback_data="back_start")]]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    if has_media(callback.message):
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=kb)
    else:
        await callback.message.edit_text(text, reply_markup=kb)