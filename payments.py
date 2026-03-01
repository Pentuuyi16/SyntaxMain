"""
Интеграция с ЮKassa (YooKassa)
Создание и проверка платежей
"""

import uuid
import logging
from yookassa import Configuration, Payment
from config import YUKASSA_SHOP_ID, YUKASSA_SECRET_KEY, DOMAIN

logger = logging.getLogger(__name__)

# Инициализация ЮKassa
Configuration.account_id = YUKASSA_SHOP_ID
Configuration.secret_key = YUKASSA_SECRET_KEY


def create_payment(amount: float, plan_id: str, telegram_id: int, description: str = "VPN подписка") -> dict | None:
    """
    Создаёт платёж в ЮKassa.
    Возвращает dict с confirmation_url и payment_id.
    """
    try:
        idempotence_key = str(uuid.uuid4())
        payment = Payment.create(
            {
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": "RUB",
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": f"https://t.me/SyntaxVPNBot",  # Замени на username бота
                },
                "capture": True,
                "description": description,
                "metadata": {
                    "plan_id": plan_id,
                    "telegram_id": str(telegram_id),
                },
            },
            idempotence_key,
        )

        return {
            "payment_id": payment.id,
            "confirmation_url": payment.confirmation.confirmation_url,
            "status": payment.status,
        }
    except Exception as e:
        logger.error(f"YooKassa create payment error: {e}")
        return None


def check_payment(payment_id: str) -> dict:
    """
    Проверяет статус платежа.
    Возвращает dict со статусом и metadata.
    """
    try:
        payment = Payment.find_one(payment_id)
        return {
            "status": payment.status,  # pending, waiting_for_capture, succeeded, canceled
            "paid": payment.paid,
            "metadata": payment.metadata,
        }
    except Exception as e:
        logger.error(f"YooKassa check payment error: {e}")
        return {"status": "error", "paid": False, "metadata": {}}
