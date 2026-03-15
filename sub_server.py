"""
Subscription Server + YooKassa Webhook — SyntaxVPN
"""

import base64
import urllib.parse
import logging
import json
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Response, Request
from config import SERVERS, SUB_HOST, SUB_PORT, SUB_PATH, DOMAIN, PLANS, ADMIN_TELEGRAM_IDS, TELEGRAM_BOT_TOKEN
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
from xui_api import add_client_to_all_servers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SyntaxVPN Subscription")


@app.on_event("startup")
async def startup():
    init_db()
    logger.info("Subscription server started")


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

        if server["network"] == "tcp":
            params["flow"] = "xtls-rprx-vision"

        if server["network"] == "xhttp":
            params["path"] = server.get("path", "/")
            params["host"] = ""
            params["mode"] = "auto"

        if server.get("spx"):
            params["spx"] = server["spx"]

    elif server["security"] == "tls":
        params["sni"] = ""
        if server.get("alpn"):
            params["alpn"] = server["alpn"]

    query = urllib.parse.urlencode(params)
    name = urllib.parse.quote(server["name"])

    link = f"trojan://{password}@{server['server_ip']}:{server['server_port']}?{query}#{name}"
    return link


def generate_subscription(vpn_uuid: str) -> str:
    links = []
    for server in SERVERS:
        link = generate_trojan_link(server, vpn_uuid)
        links.append(link)

    raw = "\n".join(links)
    encoded = base64.b64encode(raw.encode("utf-8")).decode("utf-8")
    return encoded


@app.get(f"{SUB_PATH}/{{vpn_uuid}}")
async def subscription_endpoint(vpn_uuid: str):
    user = get_user_by_uuid(vpn_uuid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    sub = get_active_subscription(user["id"])
    if not sub:
        raise HTTPException(status_code=403, detail="No active subscription")

    expires = datetime.fromisoformat(sub["expires_at"])
    if expires < datetime.utcnow():
        raise HTTPException(status_code=403, detail="Subscription expired")

    content = generate_subscription(vpn_uuid)

    headers = {
        "Content-Type": "text/plain; charset=utf-8",
        "Content-Disposition": "inline",
        "Profile-Title": base64.b64encode("SyntaxVPN".encode()).decode(),
        "Subscription-Userinfo": f"upload=0; download=0; total=0; expire={int(expires.timestamp())}",
        "Profile-Update-Interval": "12",
    }

    return Response(content=content, headers=headers, media_type="text/plain")


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

    # Считаем expiry с учётом текущей подписки
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
        logger.error(f"Webhook: failed to add client for user {user['telegram_id']}")

    create_subscription(user_id, plan_id, plan["duration_days"], plan["traffic_gb"])
    db_confirm_payment(payment_id)

    logger.info(f"Webhook: payment {payment_id} confirmed for user {user['telegram_id']}, plan {plan_id}")

    try:
        import httpx
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
                [{"text": "Добавить VPN в приложение", "url": happ_redirect}],
                [{"text": "Скачать приложение", "callback_data": "download_app"}],
                [{"text": "🚪 Главное меню", "callback_data": "back_start"}],
            ]
        }
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": user["telegram_id"],
                    "text": text,
                    "parse_mode": "HTML",
                    "reply_markup": buttons,
                },
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
        logger.error(f"Webhook: failed to send TG notification: {e}")

    return {"status": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SUB_HOST, port=SUB_PORT)