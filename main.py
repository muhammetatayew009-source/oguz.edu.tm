from fastapi import FastAPI, Request
from pydantic import BaseModel
import requests
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import datetime
import random
import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, balance REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS vpn_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    username TEXT, 
                    plan TEXT, 
                    sub_url TEXT, 
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    try:
        c.execute("ALTER TABLE vpn_keys ADD COLUMN vpn_user TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

init_db()

def add_vpn_key(username, vpn_user, plan, sub_url):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('INSERT INTO vpn_keys (username, vpn_user, plan, sub_url) VALUES (?, ?, ?, ?)', (username, vpn_user, plan, sub_url))
    conn.commit()
    conn.close()

def get_balance(username):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT balance FROM users WHERE username = ?', (username,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0.0

def add_balance(username, amount):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    balance = get_balance(username)
    new_balance = balance + amount
    c.execute('INSERT OR REPLACE INTO users (username, balance) VALUES (?, ?)', (username, new_balance))
    conn.commit()
    conn.close()
    return new_balance
    
def deduct_balance(username, amount):
    balance = get_balance(username)
    if balance >= amount:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('UPDATE users SET balance = ? WHERE username = ?', (balance - amount, username))
        conn.commit()
        conn.close()
        return True
    return False

app = FastAPI()

# Разрешаем запросы с твоего сайта
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- НАСТРОЙКИ (ЗАПОЛНИ СВОИМИ ДАННЫМИ) ---
BOT_TOKEN = "7804733565:AAGzq2gA3cQCKqFDU2bXLvEJ_7kYx1i7Y6M"
ADMIN_CHAT_ID = "8442349046"

MARZBAN_ADDRESS = "https://tkm.susbmarztm.xyz:8000" # Адрес твоей панели (Без /dashboard...)
MARZBAN_USERNAME = "a7vpn"
MARZBAN_PASSWORD = "a7vpn"
# ------------------------------------------

class PaymentRequest(BaseModel):
    plan: str
    method: str

# Функция авторизации в Marzban
def get_marzban_token():
    try:
        url = f"{MARZBAN_ADDRESS}/api/admin/token"
        data = {"username": MARZBAN_USERNAME, "password": MARZBAN_PASSWORD}
        response = requests.post(url, data=data, timeout=5)
        return response.json().get("access_token")
    except Exception as e:
        print(f"Ошибка входа в Marzban: {e}")
        return None

# Функция создания юзера в Marzban
def get_default_inbounds_and_proxies():
    token = get_marzban_token()
    if not token: return {"vless": {}}, {}
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(f"{MARZBAN_ADDRESS}/api/users?limit=20", headers=headers, timeout=5)
        if resp.status_code == 200:
            users = resp.json().get("users", [])
            for u in users:
                inbounds = u.get("inbounds", {})
                if inbounds and any(inbounds.values()):
                    proxies = {}
                    for proto in inbounds.keys():
                        proxies[proto] = {}
                    return proxies, inbounds
    except Exception as e:
        print("Ошибка получения шаблона:", e)
    return {"vless": {}}, {}

def create_vpn_user(username):
    token = get_marzban_token()
    if not token: return None
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    expire_date = int((datetime.datetime.now() + datetime.timedelta(days=30)).timestamp())
    
    proxies, inbounds = get_default_inbounds_and_proxies()
    
    user_data = {
        "username": username,
        "proxies": proxies,
        "expire": expire_date,
        "data_limit": 150 * 1024 * 1024 * 1024, # 50 GB
        "data_limit_reset_strategy": "no_reset",
        "status": "active"
    }
    if inbounds:
        user_data["inbounds"] = inbounds

    
    try:
        url = f"{MARZBAN_ADDRESS}/api/user"
        response = requests.post(url, json=user_data, headers=headers, timeout=5)
        if response.status_code == 200:
            sub_url = response.json().get("subscription_url")
            if sub_url:
                from urllib.parse import urlparse
                parsed = urlparse(sub_url)
                sub_url = MARZBAN_ADDRESS.rstrip("/") + parsed.path
            return sub_url
        else:
            print(f"Marzban API Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Ошибка создания юзера: {e}")
    return None

class OrderRequest(BaseModel):
    plan_name: str
    telegram_username: str

@app.post("/api/order")
async def create_order(data: OrderRequest):
    return {"status": "success"}

@app.get("/api/balance/{username}")
async def fetch_balance(username: str):
    username = username.strip().lstrip('@')
    balance = get_balance(username)
    return {"balance": balance}

class BuyRequest(BaseModel):
    username: str
    plan: str
    price: float

@app.post("/api/buy_with_balance")
async def buy_with_balance(data: BuyRequest):
    username = data.username.strip().lstrip('@')
    if deduct_balance(username, data.price):
        vpn_user = f"{username}_{random.randint(100, 999)}"
        sub_url = create_vpn_user(vpn_user)
        if sub_url:
            add_vpn_key(username, vpn_user, data.plan, sub_url)
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            msg = f"🛒 <b>Täze satuw (Balansdan)</b>\n👤 Ulanyjy: @{username}\n📦 Tarif: {data.plan}\n💵 Baha: {data.price} TMT"
            requests.post(url, json={"chat_id": ADMIN_CHAT_ID, "text": msg, "parse_mode": "HTML"})
            return {"status": "success", "url": sub_url}
        else:
            add_balance(username, data.price)
            return {"status": "error", "message": "Marzban paneli bilen baglanşyk gurup bolmady."}
    else:
        return {"status": "error", "message": "Balansyňyz ýeterlik däl."}

def check_marzban_user_exists(vpn_user):
    token = get_marzban_token()
    if not token: return True
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{MARZBAN_ADDRESS}/api/user/{vpn_user}"
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 404:
            return False
    except:
        pass
    return True

@app.get("/api/my_keys/{username}")
async def get_my_keys(username: str):
    username = username.strip().lstrip('@')
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT id, plan, sub_url, created_at, vpn_user FROM vpn_keys WHERE username = ? ORDER BY created_at DESC', (username,))
    rows = c.fetchall()
    
    valid_keys = []
    for row in rows:
        key_id, plan, sub_url, created_at, vpn_user = row
        if vpn_user and not check_marzban_user_exists(vpn_user):
            c.execute('DELETE FROM vpn_keys WHERE id = ?', (key_id,))
            continue
        valid_keys.append({"plan": plan, "url": sub_url, "date": created_at})
        
    conn.commit()
    conn.close()
    
    return {"status": "success", "keys": valid_keys}


@app.get("/api/admin/add_balance")
async def admin_add_balance(username: str, amount: float):
    # This endpoint allows adding balance locally without Telegram webhooks
    new_bal = add_balance(username.lstrip('@'), amount)
    return {"status": "success", "username": username, "new_balance": new_bal}

@app.get("/api/admin/fix_marzban")
async def fix_marzban():
    token = get_marzban_token()
    if not token: return {"status": "error", "message": "Marzban token alynmady"}
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        resp = requests.get(f"{MARZBAN_ADDRESS}/api/users", headers=headers, timeout=10)
        users = resp.json().get("users", [])
    except Exception as e:
        return {"status": "error", "message": str(e)}
        
    deleted = []
    for u in users:
        links = u.get("links", [])
        inbounds = u.get("inbounds", {})
        # If a user has no links and no inbounds, it's the broken one
        if not links and not inbounds:
            uname = u.get("username")
            del_resp = requests.delete(f"{MARZBAN_ADDRESS}/api/user/{uname}", headers=headers)
            if del_resp.status_code == 200:
                deleted.append(uname)
                
    return {
        "status": "success", 
        "deleted_broken_users": deleted,
        "message": "Panel successfully cleaned! Go refresh your Marzban dashboard."
    }

# Прием уведомления с сайта
@app.post("/api/notify")

async def send_telegram_notification(data: PaymentRequest):
    message_text = (
        "🚨 <b>Täze töleg garaşylýar!</b>\n\n"
        f"📦 <b>Tarif:</b> {data.plan}\n"
        f"💳 <b>Töleg usuly:</b> {data.method}\n\n"
        "Tölegi tassyklap, abuna açaryny döretmek isleýärsiňizmi?"
    )
    
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Tassyklamak (Açar döret)", "callback_data": f"confirm_{data.plan}"},
            {"text": "❌ Bes etmek", "callback_data": "cancel"}
        ]]
    }
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": message_text,
        "parse_mode": "HTML",
        "reply_markup": keyboard
    }
    
    requests.post(url, json=payload)
    return {"status": "success"}

# Обработка кнопок из Telegram (Webhook)
@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    
    if "message" in data and "text" in data["message"]:
        message = data["message"]
        chat_id = str(message["chat"]["id"])
        text = message["text"]
        
        if chat_id == ADMIN_CHAT_ID and text.startswith("/addbalance "):
            parts = text.split()
            if len(parts) == 3:
                target_user = parts[1].lstrip('@')
                try:
                    amount = float(parts[2])
                    new_bal = add_balance(target_user, amount)
                    reply = f"✅ @{target_user} ulanyjysyna {amount} TMT goşuldy. Täze balans: {new_bal} TMT."
                except ValueError:
                    reply = "❌ Nätakyr mukdar. Görnüşi: /addbalance @username 100"
            else:
                reply = "❌ Ulanyş: /addbalance @username 100"
            
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": reply})

    if "callback_query" in data:
        query = data["callback_query"]
        chat_id = query["message"]["chat"]["id"]
        callback_data = query["data"]
        
        if callback_data.startswith("confirm_"):
            # Создаем реальную подписку в панели
            username = f"User_{random.randint(1000, 9999)}"
            sub_url = create_vpn_user(username)
            
            if sub_url:
                response_text = (
                    f"✅ <b>Töleg tassyklanyldy!</b>\n"
                    f"👤 Ulanyjy: <code>{username}</code>\n\n"
                    f"🔗 <b>Müşderi üçin abuna açary:</b>\n<code>{sub_url}</code>"
                )
            else:
                response_text = "❌ <b>Ýalňyşlyk:</b> Marzban paneli bilen baglanşyk gurup bolmady."
            
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": response_text, "parse_mode": "HTML"})
            
    return {"status": "ok"}

# Serve static files (HTML, CSS, JS) from the current directory
app.mount("/", StaticFiles(directory=".", html=True), name="static")
