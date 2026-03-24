"""
Конфигурация SyntaxVPN
"""

# ========================
# Telegram Bot
# ========================
TELEGRAM_BOT_TOKEN = "8599559656:AAGghRx82KG-GiYcXOn7KT1ifXiY8XhzfPw"
ADMIN_TELEGRAM_IDS = [6397535545]

# ========================
# ЮKassa
# ========================
YUKASSA_SHOP_ID = "1240278"
YUKASSA_SECRET_KEY = "live_vd9yzrsOo56Owbu0fEqKYi-NZtfsVBRlFm3tcNha270"

# ========================
# Тарифы (можно менять)
# ========================
PLANS = {
    "test": {
        "name": "1 день (тест)",
        "duration_days": 1,
        "price": 1,
        "traffic_gb": 0,
    },
    "1month": {
        "name": "1 месяц",
        "duration_days": 30,
        "price": 99,
        "traffic_gb": 0,
    },
    "3month": {
        "name": "3 месяца",
        "duration_days": 90,
        "price": 289,
        "traffic_gb": 0,
    },
    "6month": {
        "name": "6 месяцев",
        "duration_days": 180,
        "price": 549,
        "traffic_gb": 0,
    },
    "12month": {
        "name": "12 месяцев",
        "duration_days": 365,
        "price": 999,
        "traffic_gb": 0,
    },
}

# ========================
# Пробный период
# ========================
TRIAL_ENABLED = True
TRIAL_DURATION_DAYS = 3
TRIAL_TRAFFIC_GB = 150

# ========================
# Серверы 3X-UI
# ========================
SERVERS = [

    {
        "name": "🇱🇻 Основной №1| Латвия |",
        "tag": "reserve",
        "panel_url": "https://vpn2.syntax-vpn.tech:7080/CEA23FKEvXftAjZk6E",
        "panel_user": "cxaW4VnoGe",
        "panel_pass": "lPGpavSb3p",
        "inbound_id": 1,
        "server_ip": "vpn2.syntax-vpn.tech",
        "server_port": 4443,
        "protocol": "trojan",
        "network": "tcp",
        "security": "tls",
        "fingerprint": "chrome",
        "alpn": "h2,http/1.1",
    },
    {
        "name": "🇵🇱 Основной №2| Польша |",
        "tag": "poland",
        "panel_url": "https://vpn3.syntax-vpn.tech:35566/5uRCQCgVwLdWptXLtY",
        "panel_user": "oEQzht5VLy",
        "panel_pass": "ls2b7k5qHGLRho7OH9",
        "inbound_id": 1,
        "server_ip": "vpn3.syntax-vpn.tech",
        "server_port": 4443,
        "protocol": "trojan",
        "network": "xhttp",
        "security": "reality",
        "sni": "cdnv-img.perekrestok.ru",
        "fingerprint": "firefox",
        "public_key": "eq77SAufWKaaANuwJ_hsLlhcGoOzvNBo1clMPqyOr1g",
        "short_id": "4cb285fb754cec8f",
        "spx": "/",
        "path": "/check-ping",
        "host": "cdnv-img.perekrestok.ru",
        "mode": "packet-up",
    },
    {
        "name": "🛡 Резерв",
        "tag": "latvia",
        "panel_url": "https://vpn2.syntax-vpn.tech:7080/CEA23FKEvXftAjZk6E",
        "panel_user": "cxaW4VnoGe",
        "panel_pass": "lPGpavSb3p",
        "inbound_id": 2,
        "server_ip": "vpn2.syntax-vpn.tech",
        "server_port": 8443,
        "protocol": "trojan",
        "network": "tcp",
        "security": "reality",
        "sni": "www.cloudflare.com",
        "fingerprint": "chrome",
        "public_key": "7nrIqM62zxshxr0dlvnT7JoUZrPMzWWH0r0Qs0q-PUI",
        "short_id": "3cba52d31b9744c2",
    },
    {
        "name": "🇪🇺 №1| ✈️ Беспилотная опасность |",
        "tag": "antiblock",
        "panel_url": "https://vpn1.syntax-vpn.tech:21541/q8BGciAriapa43kbbB",
        "panel_user": "Vl3T6tg6hm",
        "panel_pass": "RTDaskDU5f",
        "inbound_id": 4,
        "server_ip": "vpn1.syntax-vpn.tech",
        "server_port": 8443,
        "protocol": "trojan",
        "network": "tcp",
        "security": "reality",
        "sni": "www.cdnv-img.perekrestok.ru",
        "fingerprint": "chrome",
        "public_key": "hsEsCyGBf-VlPx59IahEln0DVud1IpgR2-443nWrSAQ",
        "short_id": "c1a80ebffc4f063a",
    },
    {
        "name": "🇪🇺 №2| ✈️ Беспилотная опасность |",
        "tag": "antiblock2",
        "panel_url": "https://vpn1.syntax-vpn.tech:21541/q8BGciAriapa43kbbB",
        "panel_user": "Vl3T6tg6hm",
        "panel_pass": "RTDaskDU5f",
        "inbound_id": 3,
        "server_ip": "vpn1.syntax-vpn.tech",
        "server_port": 4443,
        "protocol": "trojan",
        "network": "xhttp",
        "security": "reality",
        "sni": "www.cdnv-img.perekrestok.ru",
        "fingerprint": "chrome",
        "public_key": "X9pnhNNM0eKQR8ySmFwf-YgyrkDWlEYdp9TzgHB6K0c",
        "short_id": "3d",
        "spx": "/",
    },
    
]

# ========================
# Subscription Server
# ========================
SUB_HOST = "0.0.0.0"
SUB_PORT = 8080
SUB_PATH = "/sub"
DOMAIN = "syntax-vpn.tech"

# ========================
# База данных
# ========================
REFERRAL_BONUS_DAYS = 3
DATABASE_PATH = "data/syntaxvpn.db"