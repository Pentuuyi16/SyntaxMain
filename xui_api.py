"""
Клиент для API 3X-UI
Создаёт/удаляет клиентов на всех серверах
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
import httpx
from config import SERVERS

logger = logging.getLogger(__name__)

LOGIN_RETRIES = 2
LOGIN_RETRY_DELAY = 1

_http_clients: dict[str, httpx.AsyncClient] = {}
_xui_clients: dict[str, "XUIClient"] = {}
_login_locks: dict[str, asyncio.Lock] = {}


def get_http_client(panel_url: str) -> httpx.AsyncClient:
    if panel_url not in _http_clients:
        _http_clients[panel_url] = httpx.AsyncClient(
            verify=False,
            timeout=12,
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
                keepalive_expiry=30,
            )
        )
    return _http_clients[panel_url]

def get_login_lock(panel_url: str) -> asyncio.Lock:
    if panel_url not in _login_locks:
        _login_locks[panel_url] = asyncio.Lock()
    return _login_locks[panel_url]


def get_xui_client(server: dict) -> "XUIClient":
    key = f"{server['panel_url']}_{server['inbound_id']}"
    if key not in _xui_clients:
        _xui_clients[key] = XUIClient(server)
    return _xui_clients[key]


def get_server_groups() -> dict[str, list]:
    groups = defaultdict(list)
    for s in SERVERS:
        groups[s["panel_url"]].append(s)
    return groups


class XUIClient:
    SESSION_TTL = 300

    def __init__(self, server: dict):
        self.server = server
        self.base_url = server["panel_url"]
        self.username = server["panel_user"]
        self.password = server["panel_pass"]
        self.inbound_id = server["inbound_id"]
        self._client = get_http_client(server["panel_url"])
        self._logged_in = False
        self._login_time = 0

    async def login(self) -> bool:
        lock = get_login_lock(self.base_url)
        async with lock:
            # Если пока ждали лок другой поток уже залогинился — не логинимся повторно
            age = time.time() - self._login_time
            if self._logged_in and age <= self.SESSION_TTL:
                return True

            self._logged_in = False

            for attempt in range(1, LOGIN_RETRIES + 1):
                try:
                    resp = await self._client.post(
                        f"{self.base_url}/login",
                        data={"username": self.username, "password": self.password},
                    )
                    if resp.status_code == 200 and resp.json().get("success"):
                        self._logged_in = True
                        self._login_time = time.time()
                        logger.info(
                            f"Login OK: {self.server['name']} (inbound {self.inbound_id})"
                            + (f" [attempt {attempt}]" if attempt > 1 else "")
                        )
                        return True

                    logger.error(
                        f"Login FAILED: {self.server['name']} "
                        f"status={resp.status_code} body={resp.text} — не повторяем"
                    )
                    return False

                except Exception as e:
                    logger.warning(
                        f"Login ERROR: {self.server['name']} attempt {attempt}/{LOGIN_RETRIES}: {e}"
                    )
                    if attempt < LOGIN_RETRIES:
                        await asyncio.sleep(LOGIN_RETRY_DELAY)

            logger.error(
                f"Login ERROR: {self.server['name']}: все {LOGIN_RETRIES} попытки неудачны"
            )
            return False

    async def _ensure_logged_in(self) -> bool:
        age = time.time() - self._login_time
        if not self._logged_in or age > self.SESSION_TTL:
            return await self.login()
        return True

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        resp = await self._client.request(method, url, **kwargs)
        if resp.status_code in (401, 403):
            logger.warning(
                f"Session expired on {self.server['name']} "
                f"(HTTP {resp.status_code}), re-logging in..."
            )
            self._logged_in = False
            self._login_time = 0
            if await self.login():
                resp = await self._client.request(method, url, **kwargs)
        return resp

    def _unique_email(self, email: str) -> str:
        return f"{email}_{self.server['tag']}"

    async def update_client(
        self,
        vpn_uuid: str,
        email: str,
        traffic_limit_bytes: int = 0,
        expiry_time: int = 0,
    ) -> bool:
        if not await self._ensure_logged_in():
            return False

        unique_email = self._unique_email(email)

        try:
            resp = await self._request(
                "GET",
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

            resp = await self._request(
                "POST",
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
            resp = await self._request(
                "POST",
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
            resp = await self._request(
                "GET",
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

            resp = await self._request(
                "POST",
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
            resp = await self._request(
                "GET",
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
            logger.error(
                f"Get traffic error on {self.server['name']}: {result}"
            )
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
    async def add_group(servers):
        results = []
        for server_config in servers:
            xui = get_xui_client(server_config)
            try:
                ok = await xui.add_client(vpn_uuid, email, traffic_limit_bytes, expiry_time)
            except Exception as e:
                logger.error(f"Unhandled error on {server_config['name']}: {e}")
                ok = False
            logger.info(
                f"=== {server_config['name']} inbound={server_config['inbound_id']}: "
                f"{'OK' if ok else 'FAIL'} ==="
            )
            results.append((server_config["name"], ok))
        return results

    all_results = []
    for group_result in await asyncio.gather(*[add_group(s) for s in get_server_groups().values()]):
        all_results.extend(group_result)

    failed = [name for name, ok in all_results if not ok]
    if failed:
        logger.warning(f"add_client_to_all_servers: FAILED on servers: {failed}")

    any_ok = any(ok for _, ok in all_results)
    logger.info(f"ALL SERVERS results: {all_results} | any_ok={any_ok}")
    return any_ok


async def remove_client_from_all_servers(email: str) -> bool:
    async def remove_group(servers):
        results = []
        for server_config in servers:
            xui = get_xui_client(server_config)
            try:
                ok = await xui.remove_client(email)
            except Exception as e:
                logger.error(f"Unhandled error on {server_config['name']}: {e}")
                ok = False
            results.append(ok)
        return results

    all_results = []
    for group_result in await asyncio.gather(*[remove_group(s) for s in get_server_groups().values()]):
        all_results.extend(group_result)
    return any(all_results)


async def get_total_traffic(email: str) -> dict:
    async def fetch_group(servers):
        results = []
        for server_config in servers:
            xui = get_xui_client(server_config)
            try:
                traffic = await xui.get_client_traffic(email)
                results.append(traffic)
            except Exception as e:
                logger.error(f"Unhandled error on {server_config['name']}: {e}")
                results.append(None)
        return results

    total_up = 0
    total_down = 0
    for group_result in await asyncio.gather(*[fetch_group(s) for s in get_server_groups().values()]):
        for traffic in group_result:
            if traffic:
                total_up += traffic["up"]
                total_down += traffic["down"]

    return {"up": total_up, "down": total_down, "total": total_up + total_down}