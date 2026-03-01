# 🚀 SyntaxVPN — Инструкция по установке

## Архитектура

```
Пользователь
    │
    ├──▶ Telegram Бот (покупка/управление)
    │        │
    │        ├──▶ ЮKassa (оплата)
    │        ├──▶ 3X-UI API Сервер 1 (Латвия) — создание клиента
    │        └──▶ 3X-UI API Сервер 2 (Обход) — создание клиента
    │
    └──▶ Subscription URL: https://syntax-vpn.tech/sub/{uuid}
             │
             └──▶ FastAPI сервер → возвращает конфиги обоих серверов
```

## Что где стоит

| Компонент | Сервер |
|-----------|--------|
| Telegram-бот | Отдельный сервер (бот-сервер) |
| Subscription-сервер | Тот же бот-сервер |
| Nginx + SSL | Тот же бот-сервер |
| 3X-UI + Trojan | VPN-сервер 1 (Латвия) |
| 3X-UI + Trojan | VPN-сервер 2 (Обход глушилок) |

---

## Шаг 1: Подготовка бот-сервера

```bash
# Обнови систему
apt update && apt upgrade -y

# Установи зависимости
apt install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx git

# Создай директорию проекта
mkdir -p /opt/syntax-vpn
cd /opt/syntax-vpn
```

## Шаг 2: Загрузи файлы проекта

Скопируй все файлы проекта в `/opt/syntax-vpn/`:
```
/opt/syntax-vpn/
├── config.py
├── database.py
├── xui_api.py
├── sub_server.py
├── payments.py
├── bot.py
└── requirements.txt
```

## Шаг 3: Настрой Python окружение

```bash
cd /opt/syntax-vpn
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Шаг 4: Настрой config.py

Открой `config.py` и заполни:

### 4.1 — Telegram Bot Token
1. Открой @BotFather в Telegram
2. `/newbot` → придумай имя (например, SyntaxVPNBot)
3. Скопируй токен в `TELEGRAM_BOT_TOKEN`
4. Узнай свой Telegram ID через @userinfobot → вставь в `ADMIN_TELEGRAM_IDS`

### 4.2 — ЮKassa
1. Зарегистрируйся на https://yookassa.ru
2. Создай магазин
3. Скопируй `shopId` → `YUKASSA_SHOP_ID`
4. Создай секретный ключ → `YUKASSA_SECRET_KEY`

### 4.3 — Серверы 3X-UI
Для КАЖДОГО сервера укажи:
- `panel_url` — адрес панели (например `https://1.2.3.4:2053`)
- `panel_user` / `panel_pass` — логин/пароль от панели
- `inbound_id` — ID inbound (видно в панели)
- `server_ip` — IP сервера
- `server_port` — порт (8443)
- `public_key` — Reality public key (из настроек inbound)
- `sni` — SNI домен (из настроек inbound)
- `short_id` — short ID (если указан)

**Где взять Reality public key:**
В 3X-UI → открой inbound → настройки → раздел Reality → скопируй Public Key.

## Шаг 5: Настрой домен

### 5.1 — DNS
В панели регистратора домена `syntax-vpn.tech` добавь A-запись:
```
syntax-vpn.tech → IP_бот_сервера
```

### 5.2 — SSL сертификат
```bash
certbot --nginx -d syntax-vpn.tech
```

### 5.3 — Nginx
```bash
cp nginx-syntax-vpn.conf /etc/nginx/sites-available/syntax-vpn.tech
ln -s /etc/nginx/sites-available/syntax-vpn.tech /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

## Шаг 6: Запусти сервисы

```bash
# Скопируй service-файлы
cp syntaxvpn-bot.service /etc/systemd/system/
cp syntaxvpn-sub.service /etc/systemd/system/

# Запусти
systemctl daemon-reload
systemctl enable syntaxvpn-bot syntaxvpn-sub
systemctl start syntaxvpn-bot syntaxvpn-sub

# Проверь статус
systemctl status syntaxvpn-bot
systemctl status syntaxvpn-sub
```

## Шаг 7: Проверь что всё работает

```bash
# Проверь subscription-сервер
curl https://syntax-vpn.tech/health

# Логи бота
journalctl -u syntaxvpn-bot -f

# Логи subscription
journalctl -u syntaxvpn-sub -f
```

---

## Шаг 8: Настройка VPN-серверов (3X-UI)

На КАЖДОМ VPN-сервере убедись:

1. **3X-UI установлен и работает**
2. **Inbound создан** (Trojan + TCP + Reality)
3. **API доступен** — панель должна быть доступна с бот-сервера
4. **Firewall разрешает** подключения с бот-сервера к порту панели

### Если панель на порту 2053:
```bash
# На VPN-сервере
ufw allow from IP_БОТ_СЕРВЕРА to any port 2053
```

---

## Добавление нового сервера

Когда купишь новый сервер:

1. Установи 3X-UI
2. Создай Trojan + Reality inbound
3. Добавь новый сервер в `SERVERS` в `config.py`
4. Перезапусти сервисы:
```bash
systemctl restart syntaxvpn-bot syntaxvpn-sub
```

Готово! Новый сервер появится у всех пользователей автоматически при обновлении подписки.

---

## Полезные команды

```bash
# Перезапуск бота
systemctl restart syntaxvpn-bot

# Перезапуск subscription-сервера
systemctl restart syntaxvpn-sub

# Логи в реальном времени
journalctl -u syntaxvpn-bot -f
journalctl -u syntaxvpn-sub -f

# Бэкап базы данных
cp /opt/syntax-vpn/data/syntaxvpn.db /backup/syntaxvpn-$(date +%Y%m%d).db
```

---

## Как это работает для пользователя

1. Пользователь открывает бота → нажимает «Купить»
2. Выбирает тариф → оплачивает через ЮKassa
3. Бот создаёт клиента на ОБОИХ VPN-серверах (одинаковый UUID)
4. Бот выдаёт ссылку: `https://syntax-vpn.tech/sub/uuid`
5. Пользователь вставляет ссылку в приложение
6. Приложение скачивает конфиги → показывает 2 сервера:
   - 🇱🇻 Латвия — Основной
   - 🛡 Обход глушилок
7. Пользователь выбирает сервер и подключается!
