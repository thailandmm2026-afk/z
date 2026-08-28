import cloudscraper
import json
import os
import re
import time
import shutil
import sys
import asyncio
import html
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from bs4 import BeautifulSoup
from flask import Flask
from threading import Thread

ADMIN_ID = 7308292609
BOT_TOKEN = "8692690656:AAHrirr1guyIcmOmosT3-wJLa_7qAmPsgfM"
DEVELOPER_CONTACT = "@kiki20251"

# Colors
G = '\033[38;5;46m'
R = '\033[38;5;196m'
Y = '\033[38;5;226m'
C = '\033[38;5;51m'
V = '\033[38;5;93m'
W = '\033[38;5;255m'
B = '\033[1m'
D = '\033[38;5;242m'
N = '\033[0m'

COOKIE_FILE = 'cookies.json'
CONFIG_FILE = 'config.json'
USERS_FILE = 'users.json'
PRICES_FILE = 'prices.json'

DEFAULT_CONFIG = {
    "mmk_exchange_rate": 85,
    "admin_id": ADMIN_ID,
    "developer_contact": DEVELOPER_CONTACT,
    "bot_name": "SmileOne Topup Bot",
    "max_quantity": 50,
    "min_quantity": 1,
    "default_markup": 1.15
}

# Conversation states
WAITING_UID_ZID, WAITING_QTY = range(2)

EMOJI_IDS = {
    "check": "5206607081334906820", "cross": "5210952531676504517",
    "warning": "5447644880824181073", "info": "5323442290708985472",
    "play": "5348125953090403204", "refresh": "5375338737028841420",
    "search": "5300885126765355672", "copy": "5323334860692015303",
    "chat": "5443038326535759644", "mail": "5253742260054409879",
    "call": "5307746710682869587", "chatgpt": "5287684458881756303",
    "dollar": "5409048419211682843", "chart": "5451882707875276247",
    "stats": "5231200819986047254", "calendar": "5413879192267805083",
    "hourglass": "6113761177056057411", "lock": "5296369303661067030",
    "user": "5890864241388293875", "users": "5942877472163892475",
    "star": "5438496463044752972", "trophy": "5415655814079723871",
    "tag": "5985433648810171091", "ban": "5260293700088511294",
    "database": "5877485980901971030", "wifi": "5447410659077661506",
    "gift": "5449800250032143374", "market": "5440841102871517055",
    "light": "5269282027256950225",
}

NORMAL_TO_PREMIUM = {
    "💡": "light", "🛒": "market", "🎁": "gift", "✅": "check", "❌": "cross",
    "⚠️": "warning", "ℹ️": "info", "▶️": "play", "🔄": "refresh", "🔍": "search",
    "📋": "copy", "💬": "chat", "📧": "mail", "📞": "call", "🤖": "chatgpt",
    "💵": "dollar", "💰": "dollar", "📈": "chart", "📊": "stats", "📅": "calendar",
    "⏳": "hourglass", "🔐": "lock", "👤": "user", "👥": "users", "⭐": "star",
    "💎": "star", "🏆": "trophy", "🎯": "trophy", "🏷️": "tag", "🆔": "tag",
    "🚫": "ban", "⛔": "ban", "🗄️": "database", "📦": "database", "📶": "wifi",
    "🌐": "wifi", "🚀": "play", "🔢": "stats", "📭": "mail", "👋": "user",
}

def emoji_tag(emoji_id, fallback=""):
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>' if emoji_id else fallback

def get_premium_emoji(name, fallback=""):
    emoji_id = EMOJI_IDS.get(name)
    return emoji_tag(emoji_id, fallback) if emoji_id else fallback

def convert_to_premium(text):
    for normal, premium_name in NORMAL_TO_PREMIUM.items():
        if normal in text:
            text = text.replace(normal, get_premium_emoji(premium_name, normal))
    return text

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def load_prices():
    if os.path.exists(PRICES_FILE):
        try:
            with open(PRICES_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_prices(prices):
    with open(PRICES_FILE, 'w') as f:
        json.dump(prices, f, indent=4)

def escape_html(text):
    if not text:
        return ""
    return html.escape(str(text))

TRANSLATIONS = {
    "Pacote de Valor por Tempo Limitado": "Limited Time Value Pack",
    "Passe Semanal de Diamante": "Weekly Diamond Pass",
    "Passagem do crepúsculo": "Twilight Pass",
    "Diamante": "Diamond",
    "Sucesso": "Success",
    "Pendente": "Pending",
    "Falhou": "Failed",
    "Pacote Semanal Elite": "Elite Weekly Bundle",
    "Pacote Mensal Épico": "Epic Monthly Bundle",
    "Disponível Uma Vez Por Semana": "Available Once Per Week",
    "Disponível Uma Vez Por Mês": "Available Once Per Month",
    "Saldo insuficiente": "Insufficient Balance"
}

class SmileOneTerryV37Bot:
    def __init__(self):
        self.base_url = "https://www.smile.one"
        self.user_agent = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        self.scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'android', 'mobile': True})
        self.headers = {
            "User-Agent": self.user_agent,
            "Referer": f"{self.base_url}/br/customer/order",
            "X-Requested-With": "XMLHttpRequest"
        }
        self.market_data = None
        self.last_market_update = None
        self.config = load_config()
        self.allowed_users = set()
        self.users = load_users()
        self.prices = load_prices()

    def translate(self, text):
        for pt, en in TRANSLATIONS.items():
            if pt in text:
                text = text.replace(pt, en)
        return text

    def save_cookie(self, raw):
        try:
            d = {c.split('=', 1)[0].strip(): c.split('=', 1)[1].strip() for c in raw.split(';') if '=' in c}
            with open(COOKIE_FILE, 'w') as f:
                json.dump({"parsed_dict": d}, f)
            return True, "✅ Cookie saved successfully!"
        except Exception as e:
            return False, f"❌ Error saving cookie: {str(e)}"

    def check_auth(self):
        if not os.path.exists(COOKIE_FILE):
            return False, "NO_SESSION", None
        try:
            with open(COOKIE_FILE, 'r') as f:
                cookies = json.load(f).get("parsed_dict", {})
            res = self.scraper.get(f"{self.base_url}/br/customer/order", cookies=cookies, headers=self.headers)
            soup = BeautifulSoup(res.text, 'html.parser')
            det = soup.find('div', class_='user-details')
            if det:
                name = det.find('div', class_='user-name').get_text().strip()
                bal_elem = soup.find('div', class_='balance-coins')
                if bal_elem:
                    bal_parts = bal_elem.find_all('p')
                    if len(bal_parts) > 1:
                        bal = bal_parts[1].get_text().strip()
                        return True, "AUTH_SUCCESS", {"name": name, "saldo": f"{bal} coin"}
            return False, "DENIED", None
        except Exception as e:
            return False, f"ERROR: {str(e)}", None

    def id_check(self, u_id, z_id):
        if not os.path.exists(COOKIE_FILE):
            return False, "Auth Required"
        with open(COOKIE_FILE, 'r') as f:
            cookies = json.load(f).get("parsed_dict", {})
        try:
            payload = {
                "user_id": u_id, "zone_id": z_id, "pid": "22590",
                "checkrole": "1", "pay_methond": "smilecoin", "channel_method": "smilecoin"
            }
            res = self.scraper.post(f"{self.base_url}/merchant/mobilelegends/checkrole",
                                   data=payload, cookies=cookies, headers=self.headers)
            data = res.json()
            if data.get('code') == 200:
                return True, data.get('username')
            return False, data.get('info', 'Invalid ID')
        except Exception as e:
            return False, f"Connection Error: {str(e)}"

    def get_market(self, force_refresh=False):
        if not force_refresh and self.market_data and self.last_market_update:
            if (datetime.now() - self.last_market_update).seconds < 300:
                return self.market_data
        try:
            if not os.path.exists(COOKIE_FILE):
                return None
            with open(COOKIE_FILE, 'r') as f:
                cookies = json.load(f).get("parsed_dict", {})
            res = self.scraper.get(f"{self.base_url}/br/merchant/mobilelegends",
                                  cookies=cookies, headers=self.headers)
            match = re.search(r"info\s*=\s*JSON\.parse\('(.*?)'\);", res.text, re.DOTALL)
            data = json.loads(match.group(1)) if match else {}
            soup = BeautifulSoup(res.text, 'html.parser')
            pkgs = []
            rate = self.config.get("mmk_exchange_rate", 85)
            markup = self.config.get("default_markup", 1.15)

            for item in soup.find_all('li', class_='fr fs', id=True):
                pid = item.get('id')
                raw_name = item.find('h3').get_text(strip=True) if item.find('h3') else "Unknown Product"
                name = self.translate(raw_name)
                coin_price = 0
                if pid in data and 'smilecoin' in data[pid] and 'total_amount' in data[pid]['smilecoin']:
                    try:
                        coin_price = float(data[pid]['smilecoin']['total_amount'])
                    except:
                        coin_price = 0

                if pid in self.prices:
                    sell_mmk = self.prices[pid]
                else:
                    sell_mmk = coin_price * rate * markup

                mmk_formatted = f"{int(sell_mmk):,} MMK" if sell_mmk.is_integer() else f"{sell_mmk:,.0f} MMK"
                coin_formatted = f"{int(coin_price)} coin" if coin_price.is_integer() else f"{coin_price} coin"

                pkgs.append({
                    "pid": pid,
                    "name": name,
                    "price": coin_formatted,
                    "mmk_price": mmk_formatted,
                    "coin_value": coin_price,
                    "sell_mmk": sell_mmk
                })
            self.market_data = pkgs
            self.last_market_update = datetime.now()
            return pkgs
        except Exception as e:
            print(f"{R}[!] Market Error: {e}{N}")
            return None

    def get_user_balance(self, user_id):
        uid = str(user_id)
        if uid not in self.users:
            self.users[uid] = {"balance": 0, "total_spent": 0, "orders": 0}
            save_users(self.users)
        return self.users[uid]["balance"]

    def add_user_balance(self, user_id, amount):
        uid = str(user_id)
        if uid not in self.users:
            self.users[uid] = {"balance": 0, "total_spent": 0, "orders": 0}
        self.users[uid]["balance"] += amount
        save_users(self.users)
        return self.users[uid]["balance"]

    def deduct_user_balance(self, user_id, amount):
        uid = str(user_id)
        if uid not in self.users:
            return False
        if self.users[uid]["balance"] < amount:
            return False
        self.users[uid]["balance"] -= amount
        self.users[uid]["total_spent"] = self.users[uid].get("total_spent", 0) + amount
        self.users[uid]["orders"] = self.users[uid].get("orders", 0) + 1
        save_users(self.users)
        return True

    def format_logs_for_telegram(self):
        if not os.path.exists(COOKIE_FILE):
            return "❌ No session found."
        try:
            with open(COOKIE_FILE, 'r') as f:
                cookies = json.load(f).get("parsed_dict", {})
            params = {
                "type": "orderlist", "p": "1", "pageSize": "5",
                "startdate": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                "enddate": datetime.now().strftime("%Y-%m-%d")
            }
            res = self.scraper.get(f"{self.base_url}/customer/activationcode/codelist",
                                  params=params, cookies=cookies, headers=self.headers)
            logs = res.json().get('list', [])
            if not logs:
                return "📭 No recent orders found."
            message = "<b>📋 RECENT ORDERS</b>\n\n"
            for item in logs:
                status = self.translate(item.get('order_status', 'N/A'))
                product = escape_html(self.translate(item.get('goods_name', 'Product')))
                timestamp = item.get('updated_at', '---')
                uid = item.get('user_id', '---')
                zone = item.get('server_id', '---')
                amount = item.get('transaction_amount', '0')
                status_emoji = "✅" if "Success" in status else "⏳" if "Pending" in status else "❌"
                message += f"{status_emoji} <b>{product}</b>\n"
                message += f"   👤 UID: <code>{uid}</code> | Zone: <code>{zone}</code>\n"
                message += f"   💰 {amount} coin | 📅 {timestamp}\n"
                message += f"   📊 Status: {status}\n\n"
            return message
        except Exception as e:
            return f"❌ Error: {escape_html(str(e))}"

    async def topup_diamonds(self, telegram_user_id, uid, zone_id, product_index, quantity=1):
        auth, status, profile = self.check_auth()
        if not auth:
            return "❌ Authentication failed. Please check your cookie."

        pkgs = self.get_market()
        if not pkgs:
            return "❌ Cannot fetch market data."

        if product_index < 1 or product_index > len(pkgs):
            return f"❌ Invalid product number."

        min_qty = self.config.get("min_quantity", 1)
        max_qty = self.config.get("max_quantity", 50)
        if quantity < min_qty or quantity > max_qty:
            return f"❌ Quantity must be between {min_qty}-{max_qty}"

        product = pkgs[product_index - 1]
        total_cost_mmk = product['sell_mmk'] * quantity

        user_balance = self.get_user_balance(telegram_user_id)
        if user_balance < total_cost_mmk:
            return (
                f"❌ <b>Coin မလုံလောက်ပါ</b>\n\n"
                f"💰 လိုအပ်သော ပမာဏ: <b>{total_cost_mmk:,.0f} MMK</b>\n"
                f"💵 သင့်လက်ကျန်: <b>{user_balance:,.0f} MMK</b>\n\n"
                f"Admin ကို ဆက်သွယ်ပြီး Coin ဖြည့်ပါ။"
            )

        try:
            with open(COOKIE_FILE, 'r') as f:
                cookies = json.load(f).get("parsed_dict", {})

            res_init = self.scraper.get(f"{self.base_url}/br/merchant/mobilelegends", cookies=cookies)
            soup = BeautifulSoup(res_init.text, 'html.parser')
            csrf_input = soup.find('input', {'name': '_csrf'})
            if not csrf_input:
                return "❌ CSRF token not found."
            csrf_token = csrf_input['value']

            query_payload = {
                "user_id": uid, "zone_id": zone_id, "pid": product['pid'],
                "checkrole": "", "pay_methond": "smilecoin", "channel_method": "smilecoin"
            }
            res_query = self.scraper.post(f"{self.base_url}/merchant/mobilelegends/query",
                                         data=query_payload, cookies=cookies, headers=self.headers)
            query_data = res_query.json()
            if query_data.get('code') != 200:
                return f"❌ User check failed: {query_data.get('info', 'Unknown error')}"

            username = query_data.get('username', 'Unknown')
            flowid = query_data.get('flowid')

            results = []
            success_count = 0
            fail_count = 0

            for i in range(quantity):
                try:
                    pay_payload = {
                        "_csrf": csrf_token,
                        "user_id": uid,
                        "zone_id": zone_id,
                        "pay_methond": "smilecoin",
                        "product_id": product['pid'],
                        "channel_method": "smilecoin",
                        "flowid": flowid,
                        "email": "",
                        "coupon_id": ""
                    }
                    res_pay = self.scraper.post(f"{self.base_url}/merchant/mobilelegends/pay",
                                               data=pay_payload, cookies=cookies, headers=self.headers, allow_redirects=False)
                    redirect_url = res_pay.headers.get('Location') or res_pay.headers.get('x-redirect')
                    if redirect_url:
                        if not redirect_url.startswith('http'):
                            redirect_url = f"{self.base_url}{redirect_url}"
                        res_final = self.scraper.get(redirect_url, cookies=cookies)
                        if "sucesso" in res_final.text.lower():
                            success_count += 1
                            results.append(f"✅ #{i+1} Successful")
                        else:
                            fail_count += 1
                            fail_reason = "Unknown"
                            if "saldo insuficiente" in res_final.text.lower():
                                fail_reason = "Insufficient Balance"
                            results.append(f"❌ #{i+1} Failed ({fail_reason})")
                    else:
                        fail_count += 1
                        results.append(f"❌ #{i+1} No redirect")
                    if i < quantity - 1:
                        await asyncio.sleep(2)
                except Exception as e:
                    fail_count += 1
                    results.append(f"❌ #{i+1} Error")
                    await asyncio.sleep(2)

            if success_count > 0:
                actual_cost = product['sell_mmk'] * success_count
                self.deduct_user_balance(telegram_user_id, actual_cost)

            new_balance = self.get_user_balance(telegram_user_id)

            summary = (
                f"<b>🎯 TOPUP COMPLETE</b>\n\n"
                f"👤 Username: <code>{escape_html(username)}</code>\n"
                f"🆔 UID: <code>{escape_html(uid)}</code> | Zone: <code>{escape_html(zone_id)}</code>\n"
                f"📦 Product: {escape_html(product['name'])}\n"
                f"🔢 Quantity: {quantity}\n"
                f"💰 Cost: <b>{product['sell_mmk'] * quantity:,.0f} MMK</b>\n"
                f"✅ Success: {success_count} | ❌ Failed: {fail_count}\n\n"
                f"💵 သင့်လက်ကျန်: <b>{new_balance:,.0f} MMK</b>"
            )
            return summary
        except Exception as e:
            return f"❌ Topup error: {escape_html(str(e))}"

bot_instance = SmileOneTerryV37Bot()

def is_authorized(user_id):
    return user_id == bot_instance.config.get("admin_id") or user_id in bot_instance.allowed_users

def is_admin(user_id):
    return user_id == bot_instance.config.get("admin_id")

# ==================== KEYBOARDS (Full Width) ====================

def main_menu_keyboard(is_admin_user=False):
    keyboard = [
        [InlineKeyboardButton("🛒 Market", callback_data="menu_market")],
        [InlineKeyboardButton("💵 Balance", callback_data="menu_balance")],
        [InlineKeyboardButton("💎 Topup", callback_data="menu_topup")],
        [InlineKeyboardButton("📋 Logs", callback_data="menu_logs")],
        [InlineKeyboardButton("👤 Status", callback_data="menu_status")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="menu_help")],
    ]
    if is_admin_user:
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="menu_admin")])
    return InlineKeyboardMarkup(keyboard)

def back_to_menu_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]])

def market_keyboard(pkgs, page=0, per_page=8):
    keyboard = []
    start = page * per_page
    end = start + per_page
    page_pkgs = pkgs[start:end]

    for i, p in enumerate(page_pkgs, start=start + 1):
        name = p['name'][:22] + "..." if len(p['name']) > 22 else p['name']
        btn_text = f"{i}. {name} | {p['mmk_price']}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"select_prod_{i}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"market_page_{page-1}"))
    if end < len(pkgs):
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"market_page_{page+1}"))
    if nav:
        keyboard.append(nav)

    keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="menu_market")])
    keyboard.append([InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")])
    return InlineKeyboardMarkup(keyboard)

def qty_keyboard(prod_index):
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data=f"qty_{prod_index}_1"),
            InlineKeyboardButton("2", callback_data=f"qty_{prod_index}_2"),
            InlineKeyboardButton("3", callback_data=f"qty_{prod_index}_3"),
            InlineKeyboardButton("5", callback_data=f"qty_{prod_index}_5"),
        ],
        [
            InlineKeyboardButton("10", callback_data=f"qty_{prod_index}_10"),
            InlineKeyboardButton("20", callback_data=f"qty_{prod_index}_20"),
        ],
        [InlineKeyboardButton("🔙 Back to Market", callback_data="menu_market")]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_keyboard():
    keyboard = [
        [InlineKeyboardButton("🍪 Set Cookie", callback_data="admin_cookie")],
        [InlineKeyboardButton("🔄 Refresh Market", callback_data="admin_refresh")],
        [InlineKeyboardButton("💱 Set Rate", callback_data="admin_setrate")],
        [InlineKeyboardButton("📈 Set Markup", callback_data="admin_setmarkup")],
        [InlineKeyboardButton("💵 Add Coin to User", callback_data="admin_addcoin")],
        [InlineKeyboardButton("👥 Manage Users", callback_data="admin_users")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== COMMANDS & CALLBACKS ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        msg = (
            f"⛔ <b>Access Denied</b>\n\n"
            f"You are not authorized.\n"
            f"Contact: {bot_instance.config.get('developer_contact')}"
        )
        await update.message.reply_text(convert_to_premium(msg), parse_mode=ParseMode.HTML)
        return

    first_name = escape_html(update.effective_user.first_name or "User")
    balance = bot_instance.get_user_balance(user_id)
    rate = bot_instance.config.get("mmk_exchange_rate", 85)

    text = (
        f"🤖 <b>{escape_html(bot_instance.config.get('bot_name'))}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👋 Welcome, <b>{first_name}</b>!\n\n"
        f"💵 Coin လက်ကျန်: <code>{balance:,.0f} MMK</code>\n"
        f"💱 Rate: <code>1 coin = {rate} MMK</code>\n\n"
        f"အောက်က Button တွေကို နှိပ်ပြီး အသုံးပြုပါ။"
    )
    await update.message.reply_text(
        convert_to_premium(text),
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard(is_admin(user_id))
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if not is_authorized(user_id):
        await query.edit_message_text("⛔ Access Denied")
        return

    # ===== MAIN MENU =====
    if data == "menu_main":
        balance = bot_instance.get_user_balance(user_id)
        text = (
            f"🤖 <b>Main Menu</b>\n\n"
            f"💵 Coin လက်ကျန်: <code>{balance:,.0f} MMK</code>\n\n"
            f"Button ကို နှိပ်ပြီး ဆက်လုပ်ပါ။"
        )
        await query.edit_message_text(
            convert_to_premium(text),
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_keyboard(is_admin(user_id))
        )

    elif data == "menu_balance":
        bal = bot_instance.get_user_balance(user_id)
        text = f"<b>💵 သင့် Coin လက်ကျန်</b>\n\n💰 <code>{bal:,.0f} MMK</code>"
        await query.edit_message_text(
            convert_to_premium(text),
            parse_mode=ParseMode.HTML,
            reply_markup=back_to_menu_keyboard()
        )

    elif data == "menu_status":
        auth, status, profile = bot_instance.check_auth()
        if auth:
            text = (
                f"<b>✅ ACCOUNT STATUS</b>\n\n"
                f"👤 Name: {escape_html(profile['name'])}\n"
                f"💰 Balance: {escape_html(profile['saldo'])}"
            )
        else:
            text = f"<b>❌ NOT AUTHENTICATED</b>\n\n{escape_html(status)}"
        await query.edit_message_text(
            convert_to_premium(text),
            parse_mode=ParseMode.HTML,
            reply_markup=back_to_menu_keyboard()
        )

    elif data == "menu_logs":
        await query.edit_message_text(convert_to_premium("⏳ Fetching logs..."), parse_mode=ParseMode.HTML)
        msg = bot_instance.format_logs_for_telegram()
        await query.edit_message_text(
            convert_to_premium(msg),
            parse_mode=ParseMode.HTML,
            reply_markup=back_to_menu_keyboard()
        )

    elif data == "menu_help":
        text = (
            "<b>ℹ️ Help</b>\n\n"
            "🛒 <b>Market</b> - Product များကြည့်ပြီး Topup လုပ်ရန်\n"
            "💵 <b>Balance</b> - သင့် Coin လက်ကျန်\n"
            "💎 <b>Topup</b> - Diamond ဝယ်ရန်\n"
            "📋 <b>Logs</b> - နောက်ဆုံး Order များ\n\n"
            f"📞 Developer: {bot_instance.config.get('developer_contact')}"
        )
        await query.edit_message_text(
            convert_to_premium(text),
            parse_mode=ParseMode.HTML,
            reply_markup=back_to_menu_keyboard()
        )

    elif data == "menu_market" or data.startswith("market_page_"):
        page = 0
        if data.startswith("market_page_"):
            page = int(data.split("_")[-1])

        await query.edit_message_text(convert_to_premium("⏳ Loading market..."), parse_mode=ParseMode.HTML)
        pkgs = bot_instance.get_market()
        if not pkgs:
            await query.edit_message_text(
                convert_to_premium("❌ Market data မရရှိပါ။ Cookie စစ်ပါ။"),
                parse_mode=ParseMode.HTML,
                reply_markup=back_to_menu_keyboard()
            )
            return

        rate = bot_instance.config.get("mmk_exchange_rate", 85)
        text = (
            f"<b>🛒 MARKET PRODUCTS</b>\n"
            f"💱 Rate: 1 coin = {rate} MMK\n\n"
            f"Product ကို နှိပ်ပြီး Topup လုပ်ပါ။"
        )
        await query.edit_message_text(
            convert_to_premium(text),
            parse_mode=ParseMode.HTML,
            reply_markup=market_keyboard(pkgs, page)
        )

    elif data.startswith("select_prod_"):
        prod_index = int(data.split("_")[-1])
        pkgs = bot_instance.get_market()
        if not pkgs or prod_index < 1 or prod_index > len(pkgs):
            await query.edit_message_text("❌ Invalid product", reply_markup=back_to_menu_keyboard())
            return

        product = pkgs[prod_index - 1]
        context.user_data['selected_prod'] = prod_index
        context.user_data['selected_product_name'] = product['name']
        context.user_data['selected_sell_mmk'] = product['sell_mmk']

        text = (
            f"<b>📦 Selected Product</b>\n\n"
            f"Name: <b>{escape_html(product['name'])}</b>\n"
            f"Price: <b>{product['mmk_price']}</b>\n\n"
            f"Quantity ရွေးပါ:"
        )
        await query.edit_message_text(
            convert_to_premium(text),
            parse_mode=ParseMode.HTML,
            reply_markup=qty_keyboard(prod_index)
        )

    elif data.startswith("qty_"):
        parts = data.split("_")
        prod_index = int(parts[1])
        qty = int(parts[2])
        context.user_data['selected_prod'] = prod_index
        context.user_data['selected_qty'] = qty

        product_name = context.user_data.get('selected_product_name', 'Product')
        sell_mmk = context.user_data.get('selected_sell_mmk', 0)
        total = sell_mmk * qty

        text = (
            f"<b>💎 TOPUP CONFIRM</b>\n\n"
            f"📦 Product: <b>{escape_html(product_name)}</b>\n"
            f"🔢 Quantity: <b>{qty}</b>\n"
            f"💰 Total: <b>{total:,.0f} MMK</b>\n\n"
            f"အခု <b>UID နဲ့ Zone ID</b> ကို ဤပုံစံဖြင့် ပို့ပါ:\n\n"
            f"<code>123456789 2001</code>\n\n"
            f"<i>(UID space ZoneID)</i>"
        )
        await query.edit_message_text(
            convert_to_premium(text),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="menu_market")]])
        )
        context.user_data['waiting_for_uid'] = True

    elif data == "menu_topup":
        text = (
            "<b>💎 TOPUP</b>\n\n"
            "Market ကို သွားပြီး Product ရွေးပါ။\n"
            "သို့မဟုတ် /topup command သုံးပါ။"
        )
        await query.edit_message_text(
            convert_to_premium(text),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Go to Market", callback_data="menu_market")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")]
            ])
        )

    elif data == "menu_admin":
        if not is_admin(user_id):
            await query.answer("Admin only!", show_alert=True)
            return
        text = "<b>⚙️ ADMIN PANEL</b>\n\nစီမံခန့်ခွဲရန် Button နှိပ်ပါ။"
        await query.edit_message_text(
            convert_to_premium(text),
            parse_mode=ParseMode.HTML,
            reply_markup=admin_keyboard()
        )

    elif data == "admin_refresh":
        if not is_admin(user_id):
            return
        bot_instance.market_data = None
        bot_instance.last_market_update = None
        await query.edit_message_text(
            convert_to_premium("🔄 Market cache cleared!"),
            parse_mode=ParseMode.HTML,
            reply_markup=admin_keyboard()
        )

    elif data == "admin_cookie":
        if not is_admin(user_id):
            return
        context.user_data['waiting_cookie'] = True
        await query.edit_message_text(
            convert_to_premium("🍪 Cookie ကို ဤ message ကို reply လုပ်ပြီး ပို့ပါ။\n\nCancel လုပ်ရန် /cancel"),
            parse_mode=ParseMode.HTML
        )

    elif data == "admin_setrate":
        if not is_admin(user_id):
            return
        context.user_data['waiting_rate'] = True
        await query.edit_message_text(
            convert_to_premium("💱 Rate အသစ်ကို ပို့ပါ (ဥပမာ: 90)\n\nCancel: /cancel"),
            parse_mode=ParseMode.HTML
        )

    elif data == "admin_setmarkup":
        if not is_admin(user_id):
            return
        context.user_data['waiting_markup'] = True
        await query.edit_message_text(
            convert_to_premium("📈 Markup ပို့ပါ (ဥပမာ: 1.20 = 20% profit)\n\nCancel: /cancel"),
            parse_mode=ParseMode.HTML
        )

    elif data == "admin_addcoin":
        if not is_admin(user_id):
            return
        context.user_data['waiting_addcoin'] = True
        await query.edit_message_text(
            convert_to_premium("💵 Format: <code>USER_ID AMOUNT</code>\nဥပမာ: <code>123456789 50000</code>\n\nCancel: /cancel"),
            parse_mode=ParseMode.HTML
        )

    elif data == "admin_users":
        if not is_admin(user_id):
            return
        users_list = "\n".join([f"• <code>{uid}</code>" for uid in bot_instance.allowed_users]) or "No extra users"
        text = f"<b>👥 Allowed Users</b>\n\n{users_list}\n\n/adduser နဲ့ /removeuser သုံးပါ။"
        await query.edit_message_text(
            convert_to_premium(text),
            parse_mode=ParseMode.HTML,
            reply_markup=admin_keyboard()
        )

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    text = update.message.text.strip()

    # Waiting for UID ZID after selecting product + qty
    if context.user_data.get('waiting_for_uid'):
        context.user_data['waiting_for_uid'] = False
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text(
                convert_to_premium("❌ မှားနေပါတယ်။ ဥပမာ: <code>123456789 2001</code>"),
                parse_mode=ParseMode.HTML,
                reply_markup=back_to_menu_keyboard()
            )
            return

        uid, zid = parts[0], parts[1]
        prod_index = context.user_data.get('selected_prod', 1)
        qty = context.user_data.get('selected_qty', 1)

        status_msg = await update.message.reply_text(
            convert_to_premium("⏳ Topup လုပ်နေပါသည်... ခဏစောင့်ပါ။"),
            parse_mode=ParseMode.HTML
        )
        result = await bot_instance.topup_diamonds(user_id, uid, zid, prod_index, qty)
        await status_msg.edit_text(
            convert_to_premium(result),
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_keyboard(is_admin(user_id))
        )
        return

    # Admin waiting states
    if is_admin(user_id):
        if context.user_data.get('waiting_cookie'):
            context.user_data['waiting_cookie'] = False
            success, result = bot_instance.save_cookie(text)
            await update.message.reply_text(convert_to_premium(result), reply_markup=admin_keyboard())
            return

        if context.user_data.get('waiting_rate'):
            context.user_data['waiting_rate'] = False
            try:
                new_rate = float(text)
                bot_instance.config["mmk_exchange_rate"] = new_rate
                save_config(bot_instance.config)
                bot_instance.market_data = None
                await update.message.reply_text(
                    convert_to_premium(f"✅ Rate updated to {new_rate}"),
                    reply_markup=admin_keyboard()
                )
            except:
                await update.message.reply_text("❌ Invalid number", reply_markup=admin_keyboard())
            return

        if context.user_data.get('waiting_markup'):
            context.user_data['waiting_markup'] = False
            try:
                m = float(text)
                bot_instance.config["default_markup"] = m
                save_config(bot_instance.config)
                bot_instance.market_data = None
                await update.message.reply_text(
                    convert_to_premium(f"✅ Markup set to {m}x"),
                    reply_markup=admin_keyboard()
                )
            except:
                await update.message.reply_text("❌ Invalid", reply_markup=admin_keyboard())
            return

        if context.user_data.get('waiting_addcoin'):
            context.user_data['waiting_addcoin'] = False
            parts = text.split()
            if len(parts) != 2:
                await update.message.reply_text("❌ Format: USER_ID AMOUNT", reply_markup=admin_keyboard())
                return
            try:
                target = int(parts[0])
                amount = float(parts[1])
                new_bal = bot_instance.add_user_balance(target, amount)
                await update.message.reply_text(
                    convert_to_premium(f"✅ User {target} ကို {amount:,.0f} MMK ထည့်ပြီး။\nလက်ကျန်: {new_bal:,.0f}"),
                    parse_mode=ParseMode.HTML,
                    reply_markup=admin_keyboard()
                )
            except:
                await update.message.reply_text("❌ Invalid", reply_markup=admin_keyboard())
            return

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        convert_to_premium("✅ Cancelled."),
        reply_markup=main_menu_keyboard(is_admin(update.effective_user.id))
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    await start_command(update, context)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Error: {context.error}")

app_web = Flask(__name__)

@app_web.route('/')
def index():
    return "Bot is running!"

def run_server():
    port = int(os.environ.get('PORT', 8080))
    app_web.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_server)
    t.start()

def main():
    config = load_config()
    print(f"{V}╔════════════════════════════════════════════╗")
    print(f"{V}║{W}{B}   SMILE.ONE BOT V3.9 - FULL WIDTH BTN  {V}║")
    print(f"{V}╚════════════════════════════════════════════╝{N}")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_error_handler(error_handler)

    print(f"{G}[+] Bot started with Full-Width Buttons + Coin System!{N}")
    keep_alive()
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
