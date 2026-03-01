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
YUKASSA_SHOP_ID = "1240278"          # Заполнишь когда подключишь ЮKassa
YUKASSA_SECRET_KEY = "live_vd9yzrsOo56Owbu0fEqKYi-NZtfsVBRlFm3tcNha270"     # Заполнишь когда подключишь ЮKassa

# ========================
# Тарифы (можно менять)
# ========================
PLANS = {
    "1month": {
        "name": "1 месяц",
        "duration_days": 30,
        "price": 1,
        "traffic_gb": 0,  # 0 = безлимит
    },
    "3month": {
        "name": "3 месяца",
        "duration_days": 90,
        "price": 400,
        "traffic_gb": 0,
    },
    "6month": {
        "name": "6 месяцев",
        "duration_days": 180,
        "price": 700,
        "traffic_gb": 0,
    },
}

# ========================
# Пробный период
# ========================
TRIAL_ENABLED = True
TRIAL_DURATION_DAYS = 1
TRIAL_TRAFFIC_GB = 1

# ========================
# Серверы 3X-UI
# ========================
SERVERS = [
    {
        "name": "🇱🇻 Латвия — Основной",
        "tag": "latvia",
        "panel_url": "https://vpn2.syntax-vpn.tech:7080",
        "panel_user": "cxaW4VnoGe",
        "panel_pass": "lPGpavSb3p",
        "inbound_id": 2,
        "server_ip": "213.21.222.148",
        "server_port": 8443,
        "protocol": "trojan",
        "network": "tcp",
        "security": "reality",
        "sni": "www.cloudflare.com",
        "fingerprint": "chrome",
        "public_key": "7nrIqM62zxshxr0dlvnT7JoUZrPMzWWH0r0Qs0q-PUI",
        "short_id": "",
    },
    {
        "name": "🛡 Обход глушилок",
        "tag": "antiblock",
        "panel_url": "https://vpn1.syntax-vpn.tech:21541",
        "panel_user": "Vl3T6tg6hm",
        "panel_pass": "RTDaskDU5f",
        "inbound_id": 4,
        "server_ip": "212.233.89.94",
        "server_port": 8443,
        "protocol": "trojan",
        "network": "tcp",
        "security": "reality",
        "sni": "www.cdnv-img.perekrestok.ru",
        "fingerprint": "chrome",
        "public_key": "hsEsCyGBf-VlPx59IahEln0DVud1IpgR2-443nWrSAQ",
        "short_id": "",
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
DATABASE_PATH = "data/syntaxvpn.db"