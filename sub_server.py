"""
Subscription Server + YooKassa Webhook — SyntaxVPN
"""

import base64
import urllib.parse
import logging
import json
from datetime import datetime, timezone, timedelta

import httpx
from fastapi import FastAPI, HTTPException, Response, Request
from config import (
    SERVERS, SUB_HOST, SUB_PORT, SUB_PATH, DOMAIN,
    PLANS, ADMIN_TELEGRAM_IDS, TELEGRAM_BOT_TOKEN,
)
from database import (
    get_user_by_uuid,
    get_active_subscription,
    get_or_create_user,
    create_subscription,
    calculate_new_expiry,
    get_payment_by_yukassa_id,
    confirm_payment as db_confirm_payment,
    get_db,
    init_db,
)
from xui_api import add_client_to_all_servers, get_total_traffic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SyntaxVPN Subscription")


def utcnow() -> datetime:
    """Всегда возвращает timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def parse_dt(value: str) -> datetime:
    """
    Парсит ISO-строку из БД и гарантирует timezone-aware UTC datetime.
    Работает и со строками вида '2026-03-26T17:00:00'
    и с '2026-03-26T17:00:00+00:00'.
    """
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ───────────────────────────────────────────────
# Генерация ссылок
# ───────────────────────────────────────────────

def generate_trojan_link(server: dict, password: str) -> str:
    params = {
        "type": server["network"],
        "security": server["security"],
        "fp": server["fingerprint"],
    }

    if server["security"] == "reality":
        params["sni"] = server["sni"]
        params["pbk"] = server["public_key"]

        if server.get("short_id"):
            params["sid"] = server["short_id"]

        if server["network"] == "xhttp":
            params["path"] = server.get("path", "/")
            if server.get("host"):
                params["host"] = server["host"]
            params["mode"] = server.get("mode", "auto")

        if server.get("spx"):
            params["spx"] = server["spx"]

    elif server["security"] == "tls":
        params["sni"] = ""
        if server.get("alpn"):
            params["alpn"] = server["alpn"]
        if server["network"] == "ws":
            params["path"] = server.get("path", "/")
            params["host"] = ""

    query = urllib.parse.urlencode(params)
    name = urllib.parse.quote(server["name"])
    link = f"trojan://{password}@{server['server_ip']}:{server['server_port']}?{query}#{name}"
    return link


def generate_subscription(vpn_uuid: str) -> str:
    links = [generate_trojan_link(server, vpn_uuid) for server in SERVERS]
    raw = "\n".join(links)
    return base64.b64encode(raw.encode("utf-8")).decode("utf-8")


# ───────────────────────────────────────────────
# Startup
# ───────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    init_db()
    logger.info("Subscription server started")


# ───────────────────────────────────────────────
# Subscription endpoint
# ───────────────────────────────────────────────

@app.get(f"{SUB_PATH}/{{vpn_uuid}}")
async def subscription_endpoint(vpn_uuid: str):
    user = get_user_by_uuid(vpn_uuid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    sub = get_active_subscription(user["id"])
    if not sub:
        raise HTTPException(status_code=403, detail="No active subscription")

    # ФИХ: используем timezone-aware сравнение
    expires = parse_dt(sub["expires_at"])
    if expires < utcnow():
        raise HTTPException(status_code=403, detail="Subscription expired")

    content = generate_subscription(vpn_uuid)

    email = f"tg_{user['telegram_id']}"

    try:
        traffic = await get_total_traffic(email)   # использует кэш из xui_api
    except Exception as e:
        logger.error(f"Traffic fetch failed for {email}: {e}")
        traffic = {"up": 0, "down": 0}

    headers = {
        "Content-Type": "text/plain; charset=utf-8",
        "Content-Disposition": "inline",
        "Profile-Title": "Syntax VPN",
        "Subscription-Userinfo": (
            f"upload={traffic['up']}; download={traffic['down']}; "
            f"total=0; expire={int(expires.timestamp())}"
        ),
        "Profile-Update-Interval": "60",        # ← изменил с 2 на 60
        "Support-URL": "https://t.me/syntxvpn_bot",
    }

    return Response(content=content, headers=headers, media_type="text/plain")


# ───────────────────────────────────────────────
# Redirect в happ
# ───────────────────────────────────────────────

@app.get("/r")
async def redirect_to_happ(url: str):
    happ_url = f"happ://add/{url}"
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="0;url={happ_url}">
<title>SyntaxVPN</title>
</head>
<body>
<p>Открываю приложение...</p>
<script>window.location.href="{happ_url}";</script>
</body>
</html>"""
    return Response(content=html, media_type="text/html")


# ───────────────────────────────────────────────
# YooKassa Webhook
# ───────────────────────────────────────────────

@app.post("/webhook/yookassa")
async def yookassa_webhook(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = body.get("event")
    if event_type != "payment.succeeded":
        return {"status": "ignored"}

    payment_obj = body.get("object", {})
    payment_id = payment_obj.get("id")
    if not payment_id:
        return {"status": "no payment id"}

    db_payment = get_payment_by_yukassa_id(payment_id)
    if not db_payment:
        logger.warning(f"Webhook: payment {payment_id} not found in DB")
        return {"status": "not found"}

    if db_payment["status"] == "confirmed":
        logger.info(f"Webhook: payment {payment_id} already confirmed, skipping")
        return {"status": "already confirmed"}

    plan_id = db_payment["plan_id"]
    if plan_id not in PLANS:
        logger.error(f"Webhook: unknown plan {plan_id}")
        return {"status": "unknown plan"}

    plan = PLANS[plan_id]
    user_id = db_payment["user_id"]

    with get_db() as db:
        user_row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    if not user_row:
        logger.error(f"Webhook: user {user_id} not found")
        return {"status": "user not found"}

    user = dict(user_row)
    email = f"tg_{user['telegram_id']}"

    new_expires = calculate_new_expiry(user_id, plan["duration_days"])
    expiry_ms = int(new_expires.timestamp() * 1000)
    traffic_bytes = plan["traffic_gb"] * 1024 * 1024 * 1024 if plan["traffic_gb"] > 0 else 0

    ok = await add_client_to_all_servers(
        vpn_uuid=user["vpn_uuid"],
        email=email,
        traffic_limit_bytes=traffic_bytes,
        expiry_time=expiry_ms,
    )

    if not ok:
        logger.error(
            f"Webhook: failed to add client on ALL servers for user {user['telegram_id']}"
        )
        # Не прерываем — подписку в БД всё равно создаём,
        # чтобы не потерять оплату. Можно добавить алерт админу.

    create_subscription(user_id, plan_id, plan["duration_days"], plan["traffic_gb"])
    db_confirm_payment(payment_id)

    logger.info(
        f"Webhook: payment {payment_id} confirmed for user {user['telegram_id']}, "
        f"plan {plan_id}"
    )

    await _notify_user_and_admins(user, plan)

    return {"status": "ok"}


async def _notify_user_and_admins(user: dict, plan: dict):
    """Отправляет уведомление пользователю и всем админам."""
    sub_link = f"https://{DOMAIN}{SUB_PATH}/{user['vpn_uuid']}"
    happ_redirect = f"https://{DOMAIN}/r?url={sub_link}"

    text = (
        f"<b>Готово! Оплата подтверждена ✅</b>\n\n"
        f"Спасибо, что выбрали нас — это много значит для нашей команды.\n\n"
        f"<b>С любовью, SyntaxVPN 🤍</b>\n\n"
        f"<b>Ваш ключ, нажмите чтобы скопировать:</b>\n"
        f"<code>{sub_link}</code>"
    )
    buttons = {
        "inline_keyboard": [
            [{"text": "📥 Добавить VPN в приложение", "url": happ_redirect}],
            [{"text": "📲 Скачать приложение", "callback_data": "download_app"}],
            [{"text": "🚪 Главное меню", "callback_data": "back_start"}],
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": user["telegram_id"],
                    "text": text,
                    "parse_mode": "HTML",
                    "reply_markup": buttons,
                },
            )
            if not resp.is_success:
                logger.error(
                    f"TG notify user {user['telegram_id']} failed: "
                    f"{resp.status_code} {resp.text}"
                )

            for admin_id in ADMIN_TELEGRAM_IDS:
                await client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": admin_id,
                        "text": (
                            f"💰 Новая оплата!\n"
                            f"User: {user['telegram_id']}\n"
                            f"Plan: {plan['name']} — {plan['price']}₽"
                        ),
                        "parse_mode": "HTML",
                    },
                )
    except Exception as e:
        logger.error(f"Failed to send TG notifications: {e}")


# ───────────────────────────────────────────────
# Health check
# ───────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "time": utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SUB_HOST, port=SUB_PORT)