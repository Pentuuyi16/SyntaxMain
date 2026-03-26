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
        # Один постоянный клиент — сессия и куки сохраняются между запросами
        self._client = httpx.AsyncClient(verify=False, timeout=15)
        self._logged_in = False

    async def close(self):
        """Закрыть HTTP-клиент после использования"""
        await self._client.aclose()

    async def login(self) -> bool:
        """Авторизация в панели. Повторно не логинится если уже авторизован."""
        if self._logged_in:
            return True
        try:
            resp = await self._client.post(
                f"{self.base_url}/login",
                data={"username": self.username, "password": self.password},
            )
            if resp.status_code == 200 and resp.json().get("success"):
                self._logged_in = True
                logger.info(f"Login OK: {self.server['name']} (inbound {self.inbound_id})")
                return True
            logger.error(
                f"Login FAILED: {self.server['name']} "
                f"status={resp.status_code} body={resp.text}"
            )
            return False
        except Exception as e:
            logger.error(f"Login ERROR: {self.server['name']}: {e}")
            return False

    async def _ensure_logged_in(self) -> bool:
        """Гарантирует авторизацию перед запросом."""
        if self._logged_in:
            return True
        self._logged_in = False
        return await self.login()

    def _unique_email(self, email: str) -> str:
        return f"{email}_{self.server['tag']}"

    async def update_client(
        self,
        vpn_uuid: str,
        email: str,
        traffic_limit_bytes: int = 0,
        expiry_time: int = 0,
    ) -> bool:
        """Обновляет существующего клиента — находит его UUID в панели и обновляет данные."""
        if not await self._ensure_logged_in():
            return False

        unique_email = self._unique_email(email)

        try:
            # Получаем inbound чтобы найти текущий UUID (password) клиента
            resp = await self._client.get(
                f"{self.base_url}/panel/api/inbounds/get/{self.inbound_id}",
            )
            inbound = resp.json().get("obj", {})
            settings = json.loads(inbound.get("settings", "{}"))
            clients = settings.get("clients", [])

            existing_uuid = None
            for c in clients:
                if c.get("email") == unique_email:
                    existing_uuid = c.get("password")
                    break

            if not existing_uuid:
                logger.error(
                    f"Update: client {unique_email} not found on {self.server['name']}"
                )
                return False

            client_data = {
                "id": self.inbound_id,
                "settings": json.dumps({
                    "clients": [
                        {
                            "password": vpn_uuid,
                            "email": unique_email,
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

            resp = await self._client.post(
                f"{self.base_url}/panel/api/inbounds/updateClient/{existing_uuid}",
                data=client_data,
            )
            logger.info(
                f"<<< updateClient RESPONSE: server={self.server['name']} "
                f"inbound={self.inbound_id} status={resp.status_code} body={resp.text}"
            )
            result = resp.json()
            if result.get("success"):
                logger.info(
                    f"Client {unique_email} updated on {self.server['name']} "
                    f"(inbound {self.inbound_id})"
                )
                return True
            else:
                logger.error(
                    f"Update client FAILED: {self.server['name']} "
                    f"inbound={self.inbound_id} result={result}"
                )
                return False
        except Exception as e:
            logger.error(
                f"Update client ERROR: {self.server['name']} "
                f"inbound={self.inbound_id}: {e}"
            )
            return False

    async def add_client(
        self,
        vpn_uuid: str,
        email: str,
        traffic_limit_bytes: int = 0,
        expiry_time: int = 0,
    ) -> bool:
        if not await self._ensure_logged_in():
            return False

        unique_email = self._unique_email(email)

        client_data = {
            "id": self.inbound_id,
            "settings": json.dumps({
                "clients": [
                    {
                        "password": vpn_uuid,
                        "email": unique_email,
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

        logger.info(
            f">>> addClient REQUEST: server={self.server['name']} "
            f"inbound={self.inbound_id} email={unique_email}"
        )

        try:
            resp = await self._client.post(
                f"{self.base_url}/panel/api/inbounds/addClient",
                data=client_data,
            )
            logger.info(
                f"<<< addClient RESPONSE: server={self.server['name']} "
                f"inbound={self.inbound_id} status={resp.status_code} body={resp.text}"
            )
            result = resp.json()
            if result.get("success"):
                logger.info(
                    f"Client {unique_email} added to {self.server['name']} "
                    f"(inbound {self.inbound_id})"
                )
                return True
            else:
                msg = result.get("msg", "")
                if "Duplicate" in msg:
                    logger.info(
                        f"Client {unique_email} duplicate on {self.server['name']} — updating..."
                    )
                    return await self.update_client(
                        vpn_uuid, email, traffic_limit_bytes, expiry_time
                    )
                logger.error(
                    f"Add client FAILED: {self.server['name']} "
                    f"inbound={self.inbound_id} result={result}"
                )
                return False
        except Exception as e:
            logger.error(
                f"Add client ERROR: {self.server['name']} "
                f"inbound={self.inbound_id}: {e}"
            )
            return False

    async def remove_client(self, email: str) -> bool:
        if not await self._ensure_logged_in():
            return False

        unique_email = self._unique_email(email)

        try:
            resp = await self._client.get(
                f"{self.base_url}/panel/api/inbounds/get/{self.inbound_id}",
            )
            inbound = resp.json().get("obj", {})
            settings = json.loads(inbound.get("settings", "{}"))
            clients = settings.get("clients", [])

            target = None
            for c in clients:
                if c.get("email") == unique_email:
                    target = c
                    break

            if not target:
                logger.warning(
                    f"Client {unique_email} not found on {self.server['name']} — считаем удалённым"
                )
                return True

            resp = await self._client.post(
                f"{self.base_url}/panel/api/inbounds/{self.inbound_id}/delClient/{target['password']}",
            )
            result = resp.json()
            if result.get("success"):
                logger.info(f"Client {unique_email} removed from {self.server['name']}")
                return True
            else:
                logger.error(f"Remove client FAILED on {self.server['name']}: {result}")
                return False
        except Exception as e:
            logger.error(f"Remove client ERROR on {self.server['name']}: {e}")
            return False

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
                    "total": obj.get("up", 0) + obj.get("down", 0),
                }
            return None
        except Exception as e:
            logger.error(f"Get traffic ERROR on {self.server['name']}: {e}")
            return None


async def add_client_to_all_servers(
    vpn_uuid: str,
    email: str,
    traffic_limit_bytes: int = 0,
    expiry_time: int = 0,
) -> bool:
    results = []
    for server_config in SERVERS:
        xui = XUIClient(server_config)
        try:
            ok = await xui.add_client(vpn_uuid, email, traffic_limit_bytes, expiry_time)
        except Exception as e:
            logger.error(f"Unhandled error on {server_config['name']}: {e}")
            ok = False
        finally:
            await xui.close()

        results.append((server_config["name"], ok))
        logger.info(
            f"=== {server_config['name']} inbound={server_config['inbound_id']}: "
            f"{'OK' if ok else 'FAIL'} ==="
        )

    failed = [name for name, ok in results if not ok]
    if failed:
        logger.warning(f"add_client_to_all_servers: FAILED on servers: {failed}")

    any_ok = any(ok for _, ok in results)
    logger.info(f"ALL SERVERS results: {results} | any_ok={any_ok}")
    return any_ok


async def remove_client_from_all_servers(email: str) -> bool:
    results = []
    for server_config in SERVERS:
        xui = XUIClient(server_config)
        try:
            ok = await xui.remove_client(email)
        except Exception as e:
            logger.error(f"Unhandled error on {server_config['name']}: {e}")
            ok = False
        finally:
            await xui.close()
        results.append(ok)
    return any(results)


async def get_total_traffic(email: str) -> dict:
    total_up = 0
    total_down = 0
    for server_config in SERVERS:
        xui = XUIClient(server_config)
        try:
            traffic = await xui.get_client_traffic(email)
            if traffic:
                total_up += traffic["up"]
                total_down += traffic["down"]
        except Exception as e:
            logger.error(f"Unhandled error on {server_config['name']}: {e}")
        finally:
            await xui.close()
    return {
        "up": total_up,
        "down": total_down,
        "total": total_up + total_down,
    }