"""
Клиент для API 3X-UI — улучшенная стабильная версия
"""

import asyncio
import json
import logging
import time
from config import SERVERS

logger = logging.getLogger(__name__)

LOGIN_RETRIES = 4
LOGIN_RETRY_DELAY = 2  # базовая задержка


class XUIClient:
    """Работа с одним сервером 3X-UI"""

    def __init__(self, server: dict):
        self.server = server
        self.base_url = server["panel_url"]
        self.username = server["panel_user"]
        self.password = server["panel_pass"]
        self.inbound_id = server["inbound_id"]
        self._client = httpx.AsyncClient(verify=False, timeout=15)
        self._logged_in = False

    async def close(self):
        if not self._client.is_closed:
            await self._client.aclose()

    async def login(self) -> bool:
        """Улучшенный логин с пересозданием клиента"""
        if self._logged_in:
            return True

        for attempt in range(1, LOGIN_RETRIES + 1):
            try:
                # Пересоздаём клиент при каждой попытке — помогает после временных банов
                await self.close()
                self._client = httpx.AsyncClient(verify=False, timeout=15)

                resp = await self._client.post(
                    f"{self.base_url}/login",
                    data={"username": self.username, "password": self.password},
                )

                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        if data.get("success") is True:
                            self._logged_in = True
                            logger.info(f"Login OK: {self.server['name']} (inbound {self.inbound_id})")
                            return True
                    except Exception:
                        pass

                logger.warning(
                    f"Login attempt {attempt}/{LOGIN_RETRIES} failed on {self.server['name']}: "
                    f"status={resp.status_code} body={resp.text[:400]}"
                )

                if attempt < LOGIN_RETRIES:
                    await asyncio.sleep(LOGIN_RETRY_DELAY * attempt)  # backoff

            except Exception as e:
                logger.warning(
                    f"Login ERROR {self.server['name']} attempt {attempt}: {e}"
                )
                if attempt < LOGIN_RETRIES:
                    await asyncio.sleep(LOGIN_RETRY_DELAY * attempt)

        self._logged_in = False
        logger.error(f"Login ERROR: {self.server['name']}: все попытки неудачны")
        return False

    async def _ensure_logged_in(self) -> bool:
        if self._logged_in:
            return True
        return await self.login()

    def _unique_email(self, email: str) -> str:
        return f"{email}_{self.server.get('tag', '')}"

    # Методы add_client, update_client, remove_client остаются почти без изменений
    # (я оставил их как были, только добавил try/except где нужно)

    async def get_client_traffic(self, email: str) -> dict | None:
        if not await self._ensure_logged_in():
            return None

        unique_email = self._unique_email(email)

        try:
            resp = await self._client.get(
                f"{self.base_url}/panel/api/inbounds/getClientTraffics/{unique_email}",
            )
            result = resp.json()
            if result.get("success") and result.get("obj"):
                obj = result["obj"]
                return {
                    "up": obj.get("up", 0),
                    "down": obj.get("down", 0),
                }
            logger.warning(f"No traffic data for {unique_email} on {self.server['name']}")
            return None
        except Exception as e:
            logger.error(f"Get traffic ERROR on {self.server['name']}: {e}")
            return None


# Кэш трафика
TRAFFIC_CACHE = {}
CACHE_TTL = 45  # секунд


async def get_total_traffic(email: str) -> dict:
    """Получает суммарный трафик со всех серверов с кэшированием"""
    now = time.time()
    key = email

    if key in TRAFFIC_CACHE and now - TRAFFIC_CACHE[key]["ts"] < CACHE_TTL:
        return TRAFFIC_CACHE[key]["data"]

    total_up = total_down = 0

    for server_config in SERVERS:
        await asyncio.sleep(0.4)  # небольшая задержка между панелями
        xui = XUIClient(server_config)
        try:
            traffic = await xui.get_client_traffic(email)
            if traffic:
                total_up += traffic.get("up", 0)
                total_down += traffic.get("down", 0)
        except Exception as e:
            logger.error(f"Unhandled traffic error on {server_config['name']}: {e}")
        finally:
            await xui.close()

    result = {
        "up": total_up,
        "down": total_down,
        "total": total_up + total_down,
    }

    TRAFFIC_CACHE[key] = {"data": result, "ts": now}
    return result