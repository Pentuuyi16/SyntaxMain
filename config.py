"""
Конфигурация SyntaxVPN
Замени значения на свои перед запуском
"""

# ========================
# Telegram Bot
# ========================
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"  # Получи у @BotFather
ADMIN_TELEGRAM_IDS = [123456789]  # Твой Telegram ID (можно несколько)

# ========================
# ЮKassa
# ========================
YUKASSA_SHOP_ID = "YOUR_SHOP_ID"
YUKASSA_SECRET_KEY = "YOUR_SECRET_KEY"

# ========================
# Тарифы (можно менять)
# ========================
PLANS = {
    "1month": {
        "name": "1 месяц",
        "duration_days": 30,
        "price": 150,  # рублей
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
TRIAL_TRAFFIC_GB = 1  # лимит трафика для триала

# ========================
# Серверы 3X-UI
# ========================
SERVERS = [
    {
        "name": "🇱🇻 Латвия — Основной",
        "tag": "latvia",
        "panel_url": "https://your-latvia-server:2053",  # Адрес панели 3X-UI
        "panel_user": "admin",
        "panel_pass": "admin",
        "inbound_id": 4,  # ID inbound (Trojan_Proxy на порту 8443)
        # Данные для генерации trojan:// ссылки
        "server_ip": "1.2.3.4",  # IP или домен сервера
        "server_port": 8443,
        "protocol": "trojan",
        "network": "tcp",
        "security": "reality",
        "sni": "google.com",  # SNI для Reality
        "fingerprint": "chrome",
        "public_key": "YOUR_REALITY_PUBLIC_KEY",  # Reality public key
        "short_id": "",  # Reality short ID (если есть)
    },
    {
        "name": "🛡 Обход глушилок",
        "tag": "antiblock",
        "panel_url": "https://your-antiblock-server:2053",
        "panel_user": "admin",
        "panel_pass": "admin",
        "inbound_id": 4,
        "server_ip": "5.6.7.8",
        "server_port": 8443,
        "protocol": "trojan",
        "network": "tcp",
        "security": "reality",
        "sni": "google.com",
        "fingerprint": "chrome",
        "public_key": "YOUR_REALITY_PUBLIC_KEY",
        "short_id": "",
    },
]

# ========================
# Subscription Server
# ========================
SUB_HOST = "0.0.0.0"
SUB_PORT = 8080
SUB_PATH = "/sub"  # Ссылка будет: https://syntax-vpn.tech/sub/{uuid}
DOMAIN = "syntax-vpn.tech"

# ========================
# База данных
# ========================
DATABASE_PATH = "data/syntaxvpn.db"
