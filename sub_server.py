"""
Subscription Server — SyntaxVPN
Отдаёт конфиги всех серверов по одной ссылке:
https://syntax-vpn.tech/sub/{vpn_uuid}

Клиент (V2RayNG, Hiddify, Streisand) вставляет эту ссылку
и получает список всех доступных серверов.
"""

import base64
import urllib.parse
import logging
from datetime import datetime

from fastapi import FastAPI, HTTPException, Response
from config import SERVERS, SUB_HOST, SUB_PORT, SUB_PATH, DOMAIN
from database import get_user_by_uuid, get_active_subscription, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SyntaxVPN Subscription")


@app.on_event("startup")
async def startup():
    init_db()
    logger.info("Subscription server started")


def generate_trojan_link(server: dict, password: str) -> str:
    """
    Генерирует trojan:// ссылку для одного сервера.
    Формат: trojan://password@host:port?params#name
    """
    params = {
        "type": server["network"],
        "security": server["security"],
        "sni": server["sni"],
        "fp": server["fingerprint"],
        "pbk": server["public_key"],
    }

    if server.get("short_id"):
        params["sid"] = server["short_id"]

    # Для Reality
    if server["security"] == "reality":
        params["flow"] = "xtls-rprx-vision"

    query = urllib.parse.urlencode(params)
    name = urllib.parse.quote(server["name"])

    link = f"trojan://{password}@{server['server_ip']}:{server['server_port']}?{query}#{name}"
    return link


def generate_subscription(vpn_uuid: str) -> str:
    """
    Генерирует полный subscription-контент (base64)
    с конфигами всех серверов для данного пользователя.
    """
    links = []
    for server in SERVERS:
        link = generate_trojan_link(server, vpn_uuid)
        links.append(link)

    # Subscription — это base64-encoded список ссылок через \n
    raw = "\n".join(links)
    encoded = base64.b64encode(raw.encode("utf-8")).decode("utf-8")
    return encoded


@app.get(f"{SUB_PATH}/{{vpn_uuid}}")
async def subscription_endpoint(vpn_uuid: str):
    """
    Главный эндпоинт подписки.
    Клиент обращается сюда, получает список серверов.
    """
    # Проверяем что пользователь существует
    user = get_user_by_uuid(vpn_uuid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Проверяем активную подписку
    sub = get_active_subscription(user["id"])
    if not sub:
        raise HTTPException(status_code=403, detail="No active subscription")

    # Проверяем срок
    expires = datetime.fromisoformat(sub["expires_at"])
    if expires < datetime.utcnow():
        raise HTTPException(status_code=403, detail="Subscription expired")

    # Генерируем контент подписки
    content = generate_subscription(vpn_uuid)

    # Возвращаем с правильными заголовками
    headers = {
        "Content-Type": "text/plain; charset=utf-8",
        "Content-Disposition": "inline",
        "Profile-Title": base64.b64encode("SyntaxVPN".encode()).decode(),
        "Subscription-Userinfo": f"upload=0; download=0; total=0; expire={int(expires.timestamp())}",
        "Profile-Update-Interval": "12",  # обновлять каждые 12 часов
    }

    return Response(content=content, headers=headers, media_type="text/plain")


@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SUB_HOST, port=SUB_PORT)
