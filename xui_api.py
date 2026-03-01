"""
Клиент для API 3X-UI
Создаёт/удаляет клиентов на всех серверах
"""

import json
import logging
import httpx
from config import SERVERS

logger = logging.getLogger(__name__)


class XUIClient:
    """Работа с одним сервером 3X-UI"""

    def __init__(self, server: dict):
        self.server = server
        self.base_url = server["panel_url"]
        self.username = server["panel_user"]
        self.password = server["panel_pass"]
        self.inbound_id = server["inbound_id"]
        self.cookie = None

    async def login(self) -> bool:
        """Авторизация в панели, получение cookie"""
        try:
            async with httpx.AsyncClient(verify=False, timeout=15) as client:
                resp = await client.post(
                    f"{self.base_url}/login",
                    data={"username": self.username, "password": self.password},
                )
                if resp.status_code == 200 and resp.json().get("success"):
                    self.cookie = resp.cookies
                    return True
                logger.error(f"Login failed for {self.server['name']}: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Login error for {self.server['name']}: {e}")
            return False

    async def add_client(
        self,
        vpn_uuid: str,
        email: str,
        traffic_limit_bytes: int = 0,
        expiry_time: int = 0,
    ) -> bool:
        """
        Добавляет клиента в inbound.
        email — уникальное имя клиента (обычно tg_id или uuid)
        expiry_time — timestamp в миллисекундах (0 = бессрочно)
        traffic_limit_bytes — лимит трафика в байтах (0 = безлимит)
        """
        if not self.cookie:
            if not await self.login():
                return False

        # Для Trojan протокола пароль = vpn_uuid
        client_data = {
            "id": self.inbound_id,
            "settings": json.dumps({
                "clients": [
                    {
                        "password": vpn_uuid,
                        "email": email,
                        "limitIp": 3,
                        "totalGB": traffic_limit_bytes,
                        "expiryTime": expiry_time,
                        "enable": True,
                        "tgId": "",
                        "subId": "",
                    }
                ]
            }),
        }

        try:
            async with httpx.AsyncClient(verify=False, timeout=15, cookies=self.cookie) as client:
                resp = await client.post(
                    f"{self.base_url}/panel/api/inbounds/addClient",
                    data=client_data,
                )
                result = resp.json()
                if result.get("success"):
                    logger.info(f"Client {email} added to {self.server['name']}")
                    return True
                else:
                    logger.error(f"Add client failed on {self.server['name']}: {result}")
                    return False
        except Exception as e:
            logger.error(f"Add client error on {self.server['name']}: {e}")
            return False

    async def remove_client(self, email: str) -> bool:
        """Удаляет клиента из inbound по email"""
        if not self.cookie:
            if not await self.login():
                return False

        try:
            async with httpx.AsyncClient(verify=False, timeout=15, cookies=self.cookie) as client:
                # Сначала получим UUID клиента
                resp = await client.get(
                    f"{self.base_url}/panel/api/inbounds/get/{self.inbound_id}",
                )
                inbound = resp.json().get("obj", {})
                settings = json.loads(inbound.get("settings", "{}"))
                clients = settings.get("clients", [])

                target = None
                for c in clients:
                    if c.get("email") == email:
                        target = c
                        break

                if not target:
                    logger.warning(f"Client {email} not found on {self.server['name']}")
                    return True  # Уже удалён

                # Удаляем по password (для trojan)
                resp = await client.post(
                    f"{self.base_url}/panel/api/inbounds/{self.inbound_id}/delClient/{target['password']}",
                )
                result = resp.json()
                if result.get("success"):
                    logger.info(f"Client {email} removed from {self.server['name']}")
                    return True
                else:
                    logger.error(f"Remove client failed on {self.server['name']}: {result}")
                    return False
        except Exception as e:
            logger.error(f"Remove client error on {self.server['name']}: {e}")
            return False

    async def get_client_traffic(self, email: str) -> dict | None:
        """Получает статистику трафика клиента"""
        if not self.cookie:
            if not await self.login():
                return None

        try:
            async with httpx.AsyncClient(verify=False, timeout=15, cookies=self.cookie) as client:
                resp = await client.get(
                    f"{self.base_url}/panel/api/inbounds/getClientTraffics/{email}",
                )
                result = resp.json()
                if result.get("success") and result.get("obj"):
                    obj = result["obj"]
                    return {
                        "up": obj.get("up", 0),
                        "down": obj.get("down", 0),
                        "total": obj.get("up", 0) + obj.get("down", 0),
                    }
                return None
        except Exception as e:
            logger.error(f"Get traffic error on {self.server['name']}: {e}")
            return None


# ==================
# Функции для работы со всеми серверами
# ==================

async def add_client_to_all_servers(
    vpn_uuid: str,
    email: str,
    traffic_limit_bytes: int = 0,
    expiry_time: int = 0,
) -> bool:
    """Добавляет клиента на ВСЕ серверы. Возвращает True если хотя бы один успешен."""
    results = []
    for server_config in SERVERS:
        xui = XUIClient(server_config)
        ok = await xui.add_client(vpn_uuid, email, traffic_limit_bytes, expiry_time)
        results.append(ok)
    return any(results)


async def remove_client_from_all_servers(email: str) -> bool:
    """Удаляет клиента со ВСЕХ серверов"""
    results = []
    for server_config in SERVERS:
        xui = XUIClient(server_config)
        ok = await xui.remove_client(email)
        results.append(ok)
    return any(results)


async def get_total_traffic(email: str) -> dict:
    """Суммарный трафик по всем серверам"""
    total_up = 0
    total_down = 0
    for server_config in SERVERS:
        xui = XUIClient(server_config)
        traffic = await xui.get_client_traffic(email)
        if traffic:
            total_up += traffic["up"]
            total_down += traffic["down"]
    return {
        "up": total_up,
        "down": total_down,
        "total": total_up + total_down,
    }
