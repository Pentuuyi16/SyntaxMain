"""
Админ-панель SyntaxVPN
"""

import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from database import get_db

admin_router = APIRouter()

ADMIN_PASSWORD = "SyntaxVPN2026!"
admin_sessions = {}


def verify_session(token: str) -> bool:
    if not token:
        return False
    return token in admin_sessions and admin_sessions[token] > datetime.utcnow()


def get_admin_stats() -> dict:
    with get_db() as db:
        total_users = db.execute("SELECT COUNT(*) as cnt FROM users").fetchone()["cnt"]
        now = datetime.utcnow().isoformat()

        active_trial = db.execute(
            "SELECT COUNT(*) as cnt FROM subscriptions WHERE is_active = 1 AND expires_at > ? AND plan_id IN ('trial', 'referral')",
            (now,)
        ).fetchone()["cnt"]

        active_paid = db.execute(
            "SELECT COUNT(*) as cnt FROM subscriptions WHERE is_active = 1 AND expires_at > ? AND plan_id NOT IN ('trial', 'referral')",
            (now,)
        ).fetchone()["cnt"]

        total_revenue = db.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM payments WHERE status = 'confirmed'"
        ).fetchone()["total"]

        total_referrals = db.execute("SELECT COUNT(*) as cnt FROM referrals").fetchone()["cnt"]

        users = db.execute("""
            SELECT u.telegram_id, u.username, u.created_at,
                   s.plan_id, s.expires_at, s.is_active
            FROM users u
            LEFT JOIN subscriptions s ON s.user_id = u.id AND s.id = (
                SELECT MAX(s2.id) FROM subscriptions s2 WHERE s2.user_id = u.id
            )
            ORDER BY u.id DESC
            LIMIT 50
        """).fetchall()

        user_list = []
        for u in users:
            expires = u["expires_at"]
            if expires:
                exp_dt = datetime.fromisoformat(expires)
                is_expired = exp_dt < datetime.utcnow()
                status = "expired" if is_expired else ("trial" if u["plan_id"] in ("trial", "referral") else "paid")
            else:
                status = "none"

            user_list.append({
                "telegram_id": u["telegram_id"],
                "username": u["username"] or "—",
                "created_at": u["created_at"][:10] if u["created_at"] else "—",
                "plan": u["plan_id"] or "—",
                "expires": expires[:10] if expires else "—",
                "status": status,
            })

    return {
        "total_users": total_users,
        "active_trial": active_trial,
        "active_paid": active_paid,
        "active_total": active_trial + active_paid,
        "total_revenue": total_revenue,
        "total_referrals": total_referrals,
        "users": user_list,
    }


def render_page(content: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SyntaxVPN — Админ</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Manrope:wght@400;600;800&display=swap');

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    font-family: 'Manrope', sans-serif;
    background: #0a0a0f;
    color: #e0e0e0;
    min-height: 100vh;
}}

.header {{
    background: linear-gradient(135deg, #12121a 0%, #1a1a2e 100%);
    border-bottom: 1px solid #2a2a3e;
    padding: 20px 40px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}

.header h1 {{
    font-size: 22px;
    font-weight: 800;
    background: linear-gradient(90deg, #7c6ff7, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}

.header a {{
    color: #666;
    text-decoration: none;
    font-size: 14px;
    transition: color 0.2s;
}}
.header a:hover {{ color: #a78bfa; }}

.container {{ max-width: 1200px; margin: 0 auto; padding: 30px 20px; }}

.stats {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 30px;
}}

.stat-card {{
    background: #12121a;
    border: 1px solid #1e1e30;
    border-radius: 12px;
    padding: 24px;
    transition: border-color 0.3s;
}}
.stat-card:hover {{ border-color: #7c6ff7; }}

.stat-card .label {{
    font-size: 13px;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
}}

.stat-card .value {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 32px;
    font-weight: 700;
    color: #fff;
}}

.stat-card .value.revenue {{ color: #4ade80; }}
.stat-card .value.trial {{ color: #fbbf24; }}
.stat-card .value.paid {{ color: #7c6ff7; }}

.table-wrap {{
    background: #12121a;
    border: 1px solid #1e1e30;
    border-radius: 12px;
    overflow: hidden;
}}

.table-header {{
    padding: 20px 24px;
    border-bottom: 1px solid #1e1e30;
    font-weight: 600;
    font-size: 16px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
}}

th {{
    text-align: left;
    padding: 12px 24px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #555;
    border-bottom: 1px solid #1e1e30;
}}

td {{
    padding: 14px 24px;
    font-size: 14px;
    border-bottom: 1px solid #111118;
}}

tr:hover td {{ background: #15151f; }}

.badge {{
    display: inline-block;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
.badge.paid {{ background: #7c6ff720; color: #a78bfa; }}
.badge.trial {{ background: #fbbf2420; color: #fbbf24; }}
.badge.expired {{ background: #ef444420; color: #ef4444; }}
.badge.none {{ background: #33333340; color: #666; }}

.mono {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
}}

.login-wrap {{
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
}}
.login-box {{
    background: #12121a;
    border: 1px solid #1e1e30;
    border-radius: 16px;
    padding: 40px;
    width: 360px;
}}
.login-box h2 {{
    text-align: center;
    margin-bottom: 24px;
    font-size: 20px;
    color: #a78bfa;
}}
.login-box input {{
    width: 100%;
    padding: 12px 16px;
    background: #0a0a0f;
    border: 1px solid #2a2a3e;
    border-radius: 8px;
    color: #e0e0e0;
    font-size: 14px;
    margin-bottom: 16px;
    outline: none;
    font-family: 'JetBrains Mono', monospace;
}}
.login-box input:focus {{ border-color: #7c6ff7; }}
.login-box button {{
    width: 100%;
    padding: 12px;
    background: linear-gradient(135deg, #7c6ff7, #a78bfa);
    border: none;
    border-radius: 8px;
    color: #fff;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.2s;
}}
.login-box button:hover {{ opacity: 0.9; }}
.error {{ color: #ef4444; text-align: center; margin-bottom: 12px; font-size: 13px; }}
</style>
</head>
<body>
{content}
</body>
</html>"""


@admin_router.get("/admin", response_class=HTMLResponse)
async def admin_page(admin_token: str = Cookie(default=None)):
    if not verify_session(admin_token):
        content = """
<div class="login-wrap">
<div class="login-box">
<h2>🔐 SyntaxVPN Admin</h2>
<form method="post" action="/admin/login">
<input type="password" name="password" placeholder="Пароль" autofocus>
<button type="submit">Войти</button>
</form>
</div>
</div>"""
        return HTMLResponse(render_page(content))

    stats = get_admin_stats()

    user_rows = ""
    for u in stats["users"]:
        badge_class = u["status"]
        badge_text = {"paid": "Платная", "trial": "Пробная", "expired": "Истекла", "none": "Нет"}[u["status"]]
        user_rows += f"""<tr>
<td class="mono">{u['telegram_id']}</td>
<td>@{u['username']}</td>
<td>{u['created_at']}</td>
<td>{u['plan']}</td>
<td>{u['expires']}</td>
<td><span class="badge {badge_class}">{badge_text}</span></td>
</tr>\n"""

    content = f"""
<div class="header">
<h1>⚡ SyntaxVPN Admin</h1>
<a href="/admin/logout">Выйти</a>
</div>
<div class="container">
<div class="stats">
<div class="stat-card">
<div class="label">Всего пользователей</div>
<div class="value">{stats['total_users']}</div>
</div>
<div class="stat-card">
<div class="label">Активных подписок</div>
<div class="value paid">{stats['active_total']}</div>
</div>
<div class="stat-card">
<div class="label">Бесплатных</div>
<div class="value trial">{stats['active_trial']}</div>
</div>
<div class="stat-card">
<div class="label">Платных</div>
<div class="value paid">{stats['active_paid']}</div>
</div>
<div class="stat-card">
<div class="label">Заработано</div>
<div class="value revenue">{int(stats['total_revenue'])}₽</div>
</div>
<div class="stat-card">
<div class="label">Рефералов</div>
<div class="value">{stats['total_referrals']}</div>
</div>
</div>

<div class="table-wrap">
<div class="table-header">Пользователи (последние 50)</div>
<table>
<thead>
<tr>
<th>Telegram ID</th>
<th>Username</th>
<th>Регистрация</th>
<th>Тариф</th>
<th>Истекает</th>
<th>Статус</th>
</tr>
</thead>
<tbody>
{user_rows}
</tbody>
</table>
</div>
</div>"""

    return HTMLResponse(render_page(content))


@admin_router.post("/admin/login")
async def admin_login(password: str = Form(...)):
    if password == ADMIN_PASSWORD:
        token = secrets.token_hex(32)
        admin_sessions[token] = datetime.utcnow() + timedelta(hours=12)
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie("admin_token", token, httponly=True, max_age=43200)
        return response
    else:
        content = """
<div class="login-wrap">
<div class="login-box">
<h2>🔐 SyntaxVPN Admin</h2>
<p class="error">Неверный пароль</p>
<form method="post" action="/admin/login">
<input type="password" name="password" placeholder="Пароль" autofocus>
<button type="submit">Войти</button>
</form>
</div>
</div>"""
        return HTMLResponse(render_page(content))


@admin_router.get("/admin/logout")
async def admin_logout(admin_token: str = Cookie(default=None)):
    if admin_token in admin_sessions:
        del admin_sessions[admin_token]
    response = RedirectResponse(url="/admin", status_code=303)
    response.delete_cookie("admin_token")
    return response