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
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from bs4 import BeautifulSoup
from flask import Flask
from threading import Thread



ADMIN_ID = 7308292609  
BOT_TOKEN = "8707027344:AAFlHX4yY7-6fXXaeimh8DrmxldaJFbfknc"  # 
DEVELOPER_CONTACT = "@kiki20251"  
# Premium Color Palette for Terminal (admin only)
G = '\033[38;5;46m'    # Success Green
R = '\033[38;5;196m'   # Critical Red
Y = '\033[38;5;226m'   # Warning Yellow
C = '\033[38;5;51m'    # Cyber Cyan
V = '\033[38;5;93m'    # Cyber Violet
W = '\033[38;5;255m'   # Bright White
B = '\033[1m'          # Bold
D = '\033[38;5;242m'   # Dimmed Gray
N = '\033[0m'          # Reset

COOKIE_FILE = 'cookies.json'
CONFIG_FILE = 'config.json'

# Default configuration
DEFAULT_CONFIG = {
    "mmk_exchange_rate": 85,
    "admin_id": ADMIN_ID,
    "developer_contact": DEVELOPER_CONTACT,
    "bot_name": "SmileOne Topup Bot",
    "max_quantity": 100,
    "min_quantity": 1
}

# ============================================
# Premium Emoji Dictionary & Helpers
# ============================================
EMOJI_IDS = {
    "check": "5206607081334906820",      
    "cross": "5210952531676504517",      
    "warning": "5447644880824181073",    
    "info": "5323442290708985472",       
    "play": "5348125953090403204",       
    "refresh": "5375338737028841420",    
    "search": "5300885126765355672",     
    "copy": "5323334860692015303",       
    "chat": "5443038326535759644",       
    "mail": "5253742260054409879",       
    "call": "5307746710682869587",       
    "chatgpt": "5287684458881756303",    
    "dollar": "5409048419211682843",     
    "chart": "5451882707875276247",      
    "stats": "5231200819986047254",      
    "calendar": "5413879192267805083",   
    "hourglass": "6113761177056057411",  
    "lock": "5296369303661067030",       
    "user": "5890864241388293875",       
    "users": "5942877472163892475",      
    "star": "5438496463044752972",       
    "trophy": "5415655814079723871",     
    "tag": "5985433648810171091",        
    "ban": "5260293700088511294",        
    "database": "5877485980901971030",   
    "wifi": "5447410659077661506",
    "gift": "5449800250032143374",
    "market": "5440841102871517055",
    "light": "5269282027256950225",
}

NORMAL_TO_PREMIUM = {
    "💡": "light",
    "🛒": "market",
    "🎁": "gift",
    "✅": "check",
    "❌": "cross",
    "⚠️": "warning",
    "ℹ️": "info",
    "▶️": "play",
    "🔄": "refresh",
    "🔍": "search",
    "📋": "copy",
    "💬": "chat",
    "📧": "mail",
    "📞": "call",
    "🤖": "chatgpt",
    "💵": "dollar",
    "💰": "dollar",
    "📈": "chart",
    "📊": "stats",
    "📅": "calendar",
    "⏳": "hourglass",
    "🔐": "lock",
    "👤": "user",
    "👥": "users",
    "⭐": "star",
    "💎": "star",
    "🏆": "trophy",
    "🎯": "trophy",
    "🏷️": "tag",
    "🆔": "tag",
    "🚫": "ban",
    "⛔": "ban",
    "🗄️": "database",
    "📦": "database",
    "📶": "wifi",
    "🌐": "wifi",
    "🚀": "play",
    "🔢": "stats",
    "📭": "mail",
    "👋": "user",
}

def emoji_tag(emoji_id, fallback=""):
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>' if emoji_id else fallback

def get_premium_emoji(name, fallback=""):
    emoji_id = EMOJI_IDS.get(name)
    if emoji_id:
        return emoji_tag(emoji_id, fallback)
    return fallback

def convert_to_premium(text):
    for normal, premium_name in NORMAL_TO_PREMIUM.items():
        if normal in text:
            premium = get_premium_emoji(premium_name, normal)
            text = text.replace(normal, premium)
    return text

# ============================================

# Load/Save configuration
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return DEFAULT_CONFIG.copy()
    else:
        return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def escape_markdown(text):
    if not text:
        return ""
    text = str(text)
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def escape_html(text):
    if not text:
        return ""
    return html.escape(str(text))

# --- Advanced Translation Engine ---
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

    def get_width(self):
        try:
            w = shutil.get_terminal_size().columns
            return w if w > 80 else 80
        except:
            return 80

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
                "user_id": u_id, 
                "zone_id": z_id, 
                "pid": "22590", 
                "checkrole": "1",
                "pay_methond": "smilecoin", 
                "channel_method": "smilecoin"
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
                
                mmk_price = coin_price * self.config.get("mmk_exchange_rate", 75)
                mmk_formatted = f"{int(mmk_price):,} MMK" if mmk_price.is_integer() else f"{mmk_price:,.0f} MMK"
                coin_formatted = f"{int(coin_price)} coin" if coin_price.is_integer() else f"{coin_price} coin"
                
                pkgs.append({
                    "pid": pid, 
                    "name": name, 
                    "price": coin_formatted,
                    "mmk_price": mmk_formatted,
                    "coin_value": coin_price
                })
            
            self.market_data = pkgs
            self.last_market_update = datetime.now()
            return pkgs
            
        except Exception as e:
            print(f"{R}[!] Market Error: {e}{N}")
            return None

    def format_market_for_telegram(self, pkgs):
        if not pkgs:
            return "❌ No market data available. Please check your cookie."
        
        rate = self.config.get("mmk_exchange_rate", 75)
        message = f"<b>📊 SMILE.ONE MARKET PRODUCTS</b>\n"
        message += f"<b>💰 Exchange Rate: 1 coin = {rate} MMK</b>\n\n"
        
        for i, p in enumerate(pkgs[:20], 1):
            name = escape_html(p['name'])
            if len(name) > 30:
                name = name[:27] + "..."
            
            message += f"<b>{i:02d}.</b> <code>{name}</code>\n"
            message += f"     💎 {p['price']} | 💵 {p['mmk_price']}\n"
            message += f"     ID: <code>{p['pid']}</code>\n\n"
        
        message += "\n<i>Use /topup [UID] [ZID] [NO] [QTY] to purchase</i>"
        return message

    def format_logs_for_telegram(self):
        if not os.path.exists(COOKIE_FILE):
            return "❌ No session found. Please set cookie first."
        
        try:
            with open(COOKIE_FILE, 'r') as f: 
                cookies = json.load(f).get("parsed_dict", {})
            
            params = {
                "type": "orderlist", 
                "p": "1", 
                "pageSize": "5",
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
            return f"❌ Error fetching logs: {escape_html(str(e))}"

    async def redeem_code(self, code):
        if not os.path.exists(COOKIE_FILE):
            return "❌ No session found. Please set cookie first."
        
        try:
            with open(COOKIE_FILE, 'r') as f: 
                cookies = json.load(f).get("parsed_dict", {})
            
            ref_url = f"{self.base_url}/customer/activationcode"
            res_page = self.scraper.get(ref_url, cookies=cookies)
            soup = BeautifulSoup(res_page.text, 'html.parser')
            csrf_input = soup.find('input', {'name': '_csrf'})
            
            if not csrf_input:
                return "❌ Cannot get CSRF token. Cookie might be expired."
            
            csrf_token = csrf_input['value']
            
            headers = {
                "accept": "application/json, text/javascript, */*; q=0.01",
                "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                "x-requested-with": "XMLHttpRequest",
                "origin": self.base_url,
                "referer": ref_url
            }
            
            check_url = f"{self.base_url}/smilecard/pay/checkcard"
            payload_check = {"sec": code}
            
            res1 = self.scraper.post(check_url, data=payload_check, cookies=cookies, headers=headers)
            data1 = res1.json()
            
            if data1.get('code') != 200:
                return f"❌ Step 1 Failed: {data1.get('info', 'Unknown error')}"
            
            await asyncio.sleep(1.2)
            
            pay_url = f"{self.base_url}/smilecard/pay/payajax"
            payload_pay = {"sec": code}
            
            res2 = self.scraper.post(pay_url, data=payload_pay, cookies=cookies, headers=headers)
            data2 = res2.json()
            
            if data2.get('code') == 200:
                return f"✅ Success! {data2.get('info', 'Balance added')}"
            else:
                return f"❌ Step 2 Failed (Code {data2.get('code')}): {data2.get('info', 'Unknown error')}"
                
        except Exception as e:
            return f"❌ Error: {escape_html(str(e))}"

    async def topup_diamonds(self, uid, zone_id, product_index, quantity=1):
        auth, status, profile = self.check_auth()
        if not auth:
            return "❌ Authentication failed. Please check your cookie."
        
        pkgs = self.get_market()
        if not pkgs:
            return "❌ Cannot fetch market data. Please try again later."
        
        if product_index < 1 or product_index > len(pkgs):
            return f"❌ Invalid product number. Please choose 1-{len(pkgs)}"
        
        min_qty = self.config.get("min_quantity", 1)
        max_qty = self.config.get("max_quantity", 100)
        
        if quantity < min_qty or quantity > max_qty:
            return f"❌ Quantity must be between {min_qty}-{max_qty}"
        
        product = pkgs[product_index - 1]
        total_cost = product['coin_value'] * quantity
        total_mmk = total_cost * self.config.get("mmk_exchange_rate", 75)
        
        try:
            with open(COOKIE_FILE, 'r') as f: 
                cookies = json.load(f).get("parsed_dict", {})
            
            res_init = self.scraper.get(f"{self.base_url}/br/merchant/mobilelegends", cookies=cookies)
            soup = BeautifulSoup(res_init.text, 'html.parser')
            csrf_input = soup.find('input', {'name': '_csrf'})
            
            if not csrf_input:
                return "❌ CSRF token not found. Cookie might be expired."
            
            csrf_token = csrf_input['value']
            
            query_payload = {
                "user_id": uid,
                "zone_id": zone_id,
                "pid": product['pid'],
                "checkrole": "", 
                "pay_methond": "smilecoin", 
                "channel_method": "smilecoin"
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
                            elif "csrf" in res_final.text.lower():
                                fail_reason = "CSRF Error"
                            results.append(f"❌ #{i+1} Failed ({fail_reason})")
                    else:
                        fail_count += 1
                        results.append(f"❌ #{i+1} No redirect")
                    
                    if i < quantity - 1:
                        await asyncio.sleep(2)
                        
                except Exception as e:
                    fail_count += 1
                    results.append(f"❌ #{i+1} Error: {str(e)[:50]}")
                    await asyncio.sleep(2)
            
            summary = (
                f"<b>🎯 BULK TOPUP COMPLETE</b>\n\n"
                f"👤 Username: <code>{escape_html(username)}</code>\n"
                f"🆔 UID: <code>{escape_html(uid)}</code> | Zone: <code>{escape_html(zone_id)}</code>\n"
                f"📦 Product: {escape_html(product['name'])}\n"
                f"🔢 Quantity: {quantity}\n"
                f"💰 Total Cost: {total_cost} coin ({total_mmk:,.0f} MMK)\n\n"
                f"<b>📊 RESULTS</b>\n"
                f"✅ Successful: {success_count}\n"
                f"❌ Failed: {fail_count}\n"
                f"📈 Success Rate: {(success_count/quantity)*100:.1f}%\n\n"
            )
            
            if fail_count > 0:
                summary += f"<b>⚠️ Failed Items:</b>\n"
                for result in results:
                    if "❌" in result:
                        summary += f"{escape_html(result)}\n"
            
            return summary
            
        except Exception as e:
            return f"❌ Topup error: {escape_html(str(e))}"

bot_instance = SmileOneTerryV37Bot()

def is_authorized(user_id):
    return user_id == bot_instance.config.get("admin_id") or user_id in bot_instance.allowed_users

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = escape_html(update.effective_user.username or "Unknown")
    first_name = escape_html(update.effective_user.first_name or "")
    last_name = escape_html(update.effective_user.last_name or "")
    
    full_name = f"{first_name} {last_name}".strip()
    if not full_name:
        full_name = username
    
    if not is_authorized(user_id):
        msg = (
            f"⛔ <b>Access Denied</b>\n\n"
            f"You are not authorized to use this bot.\n"
            f"Contact developer: {bot_instance.config.get('developer_contact', '@Terry85855')}"
        )
        await update.message.reply_text(convert_to_premium(msg), parse_mode=ParseMode.HTML)
        return
    
    rate = bot_instance.config.get("mmk_exchange_rate", 75)
    
    
    welcome_text = (
        f"🤖 <b>{escape_html(bot_instance.config.get('bot_name', 'SMILE.ONE BOT'))}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👋 Welcome, <b>{escape_html(full_name)}</b>!\n"
        f"💰 Current Rate: <code>1 coin = {rate} MMK</code>\n\n"
        f"👤 /status - Check account status\n"
        f"🛒 /market - View products & prices\n"
        f"📋 /logs - View recent orders\n"
        f"🔍 /check [UID] [ZID] - Check user\n"
        f"🎁 /redeem [CODE] - Redeem code\n"
        f"💎 /topup [UID] [ZID] [NO] [QTY] - Bulk purchase\n"
        f"📊 /rate - Check exchange rate\n\n"
        f"💡 <b>Example:</b>\n"
        f"<code>/topup 58515640 2099 30 3</code>\n"
        f"<i>(UID=58515640, ZID=2099, Product#30, Qty=3)</i>\n\n"
        f"📞 <b>Developer:</b> {bot_instance.config.get('developer_contact', '@Terry85855')}"
    )
    
    await update.message.reply_text(convert_to_premium(welcome_text), parse_mode=ParseMode.HTML)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    
    auth, status, profile = bot_instance.check_auth()
    
    if auth:
        message = (
            f"<b>✅ ACCOUNT STATUS</b>\n\n"
            f"👤 Name: {escape_html(profile['name'])}\n"
            f"💰 Balance: {escape_html(profile['saldo'])}\n"
            f"📅 Last Check: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    else:
        message = f"<b>❌ NOT AUTHENTICATED</b>\n\nStatus: {escape_html(status)}\n\nAdmin needs to set cookie."
    
    await update.message.reply_text(convert_to_premium(message), parse_mode=ParseMode.HTML)

async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    
    await update.message.reply_text(convert_to_premium("⏳ Fetching market data..."),parse_mode=ParseMode.HTML)
    
    pkgs = bot_instance.get_market()
    message = bot_instance.format_market_for_telegram(pkgs)
    
    if len(message) > 4000:
        parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
        for part in parts:
            await update.message.reply_text(convert_to_premium(part), parse_mode=ParseMode.HTML)
            await asyncio.sleep(0.5)
    else:
        await update.message.reply_text(convert_to_premium(message), parse_mode=ParseMode.HTML)

async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    
    await update.message.reply_text(convert_to_premium("⏳ Fetching recent orders..."),parse_mode=ParseMode.HTML)
    message = bot_instance.format_logs_for_telegram()
    await update.message.reply_text(convert_to_premium(message), parse_mode=ParseMode.HTML)

async def cookie_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != bot_instance.config.get("admin_id"):
        await update.message.reply_text(convert_to_premium("⛔ This command is for admin only."),parse_mode=ParseMode.HTML)
        return
    
    if context.args:
        cookie_text = ' '.join(context.args)
        success, result = bot_instance.save_cookie(cookie_text)
        await update.message.reply_text(convert_to_premium(result))
        
        if success:
            bot_instance.market_data = None
            await update.message.reply_text(convert_to_premium("🔄 Market cache cleared. Use /market to refresh."))
    else:
        msg = (
            "🔐 <b>SET COOKIE</b>\n\n"
            "Send: /cookie [cookie_text]\n\n"
            "To get cookie:\n"
            "1. Login to smile.one\n"
            "2. Press F12 → Application tab\n"
            "3. Copy cookie from Storage → Cookies\n"
            "4. Paste after /cookie command"
        )
        await update.message.reply_text(convert_to_premium(msg), parse_mode=ParseMode.HTML)

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    
    if len(context.args) != 2:
        await update.message.reply_text(convert_to_premium("❌ Usage: /check [UID] [ZID]"),parse_mode=ParseMode.HTML)
        return
    
    uid, zid = context.args[0], context.args[1]
    msg = f"⏳ Checking UID <code>{escape_html(uid)}</code> Zone <code>{escape_html(zid)}</code>..."
    await update.message.reply_text(convert_to_premium(msg), parse_mode=ParseMode.HTML)
    
    success, result = bot_instance.id_check(uid, zid)
    
    if success:
        res_msg = f"✅ Username found: <code>{escape_html(result)}</code>"
    else:
        res_msg = f"❌ {escape_html(result)}"
        
    await update.message.reply_text(convert_to_premium(res_msg), parse_mode=ParseMode.HTML)

async def redeem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    
    if not context.args:
        
        error_msg = "❌ <b>Usage:</b> <code>/redeem [activation_code]</code>"
        await update.message.reply_text(convert_to_premium(error_msg), parse_mode=ParseMode.HTML)
        return
    
    code = context.args[0]
    
    
    msg = f"⏳ <b>Redeeming code:</b> <code>{escape_html(code)}</code>\n\n<i>Please wait...</i>"
    await update.message.reply_text(convert_to_premium(msg), parse_mode=ParseMode.HTML)
    
    result = await bot_instance.redeem_code(code)
    
    await update.message.reply_text(convert_to_premium(result), parse_mode=ParseMode.HTML)


async def topup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    
    if len(context.args) < 3:
        msg = (
            "❌ <b>Usage:</b> /topup [UID] [ZID] [PRODUCT_NO] [QUANTITY]\n\n"
            "<b>Example:</b>\n"
            "<code>/topup 58515640 2099 30 3</code>\n"
            "<code>/topup 12345678 8888 5 10</code>\n\n"
            "<i>Note: Quantity is optional, default is 1</i>"
        )
        await update.message.reply_text(convert_to_premium(msg), parse_mode=ParseMode.HTML)
        return
    
    uid = context.args[0]
    zid = context.args[1]
    
    try:
        product_no = int(context.args[2])
    except ValueError:
        await update.message.reply_text(convert_to_premium("❌ Product number must be a valid integer"),parse_mode=ParseMode.HTML)
        return
    
    if len(context.args) >= 4:
        try:
            quantity = int(context.args[3])
            min_qty = bot_instance.config.get("min_quantity", 1)
            max_qty = bot_instance.config.get("max_quantity", 100)
            if quantity < min_qty or quantity > max_qty:
                await update.message.reply_text(convert_to_premium(f"❌ Quantity must be between {min_qty}-{max_qty}"),parse_mode=ParseMode.HTML)
                return
        except ValueError:
            await update.message.reply_text(convert_to_premium("❌ Quantity must be a valid integer"),parse_mode=ParseMode.HTML)
            return
    else:
        quantity = 1
    
    init_msg = (
        f"<b>🚀 STARTING TOPUP</b>\n\n"
        f"🆔 UID: <code>{escape_html(uid)}</code>\n"
        f"🌐 Zone: <code>{escape_html(zid)}</code>\n"
        f"📦 Product: #{product_no}\n"
        f"🔢 Quantity: {quantity}\n\n"
        f"⏳ Please wait..."
    )
    
    status_msg = await update.message.reply_text(convert_to_premium(init_msg), parse_mode=ParseMode.HTML)
    
    result = await bot_instance.topup_diamonds(uid, zid, product_no, quantity)
    
    await status_msg.edit_text(convert_to_premium(result), parse_mode=ParseMode.HTML)

async def refresh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != bot_instance.config.get("admin_id"):
        await update.message.reply_text(convert_to_premium("⛔ This command is for admin only."),parse_mode=ParseMode.HTML)
        return
    
    bot_instance.market_data = None
    bot_instance.last_market_update = None
    await update.message.reply_text(convert_to_premium("🔄 Market cache cleared. Use /market to fetch fresh data."),parse_mode=ParseMode.HTML)

async def rate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    
    rate = bot_instance.config.get("mmk_exchange_rate", 75)
    await update.message.reply_text(convert_to_premium(f"<b>💰 Current Exchange Rate</b>\n\n1 coin = {rate} MMK"), parse_mode=ParseMode.HTML)

async def setrate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != bot_instance.config.get("admin_id"):
        await update.message.reply_text(convert_to_premium("⛔ This command is for admin only."),parse_mode=ParseMode.HTML)
        return
    
    if not context.args:
        await update.message.reply_text(convert_to_premium("❌ Usage: /setrate [new_rate]\nExample: /setrate 80"),parse_mode=ParseMode.HTML)
        return
    
    try:
        new_rate = float(context.args[0])
        if new_rate <= 0:
            await update.message.reply_text(convert_to_premium("❌ Rate must be positive"),parse_mode=ParseMode.HTML)
            return
        
        bot_instance.config["mmk_exchange_rate"] = new_rate
        save_config(bot_instance.config)
        bot_instance.market_data = None
        await update.message.reply_text(convert_to_premium(f"✅ Exchange rate updated to {new_rate} MMK per coin"),parse_mode=ParseMode.HTML)
    except ValueError:
        await update.message.reply_text(convert_to_premium("❌ Invalid rate value"))

async def adduser_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != bot_instance.config.get("admin_id"):
        await update.message.reply_text(convert_to_premium("⛔ This command is for admin only."),parse_mode=ParseMode.HTML)
        return
    
    if not context.args:
        await update.message.reply_text(convert_to_premium("❌ Usage: /adduser [user_id]"),parse_mode=ParseMode.HTML)
        return
    
    try:
        user_id = int(context.args[0])
        bot_instance.allowed_users.add(user_id)
        await update.message.reply_text(convert_to_premium(f"✅ User {user_id} added to allowed list"),parse_mode=ParseMode.HTML)
    except ValueError:
        await update.message.reply_text(convert_to_premium("❌ Invalid user ID"),parse_mode=ParseMode.HTML)

async def removeuser_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != bot_instance.config.get("admin_id"):
        await update.message.reply_text(convert_to_premium("⛔ This command is for admin only."),parse_mode=ParseMode.HTML)
        return
    
    if not context.args:
        await update.message.reply_text(convert_to_premium("❌ Usage: /removeuser [user_id]"),parse_mode=ParseMode.HTML)
        return
    
    try:
        user_id = int(context.args[0])
        if user_id in bot_instance.allowed_users:
            bot_instance.allowed_users.remove(user_id)
            await update.message.reply_text(convert_to_premium(f"✅ User {user_id} removed from allowed list"),parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(convert_to_premium(f"❌ User {user_id} not in allowed list"),parse_mode=ParseMode.HTML)
    except ValueError:
        await update.message.reply_text(convert_to_premium("❌ Invalid user ID"),parse_mode=ParseMode.HTML)

async def listusers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != bot_instance.config.get("admin_id"):
        await update.message.reply_text(convert_to_premium("⛔ This command is for admin only."),parse_mode=ParseMode.HTML)
        return
    
    if not bot_instance.allowed_users:
        await update.message.reply_text(convert_to_premium("📋 No additional users allowed"),parse_mode=ParseMode.HTML)
    else:
        users_list = "\n".join([f"• <code>{uid}</code>" for uid in bot_instance.allowed_users])
        await update.message.reply_text(convert_to_premium(f"<b>📋 Allowed Users</b>\n\n{users_list}"), parse_mode=ParseMode.HTML)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    
    help_text = (
        "<b>🤖 BOT COMMANDS</b>\n\n"
        "<b>User Commands:</b>\n"
        "/start - Start the bot\n"
        "/status - Check account status\n"
        "/market - View products & prices\n"
        "/logs - View recent orders\n"
        "/check [UID] [ZID] - Check user\n"
        "/redeem [CODE] - Redeem code\n"
        "/topup [UID] [ZID] [NO] [QTY] - Topup diamonds\n"
        "/rate - Check exchange rate\n"
        "/help - Show this help\n\n"
        "<b>Admin Commands:</b>\n"
        "/cookie [COOKIE] - Set cookie\n"
        "/refresh - Refresh market data\n"
        "/setrate [RATE] - Change exchange rate\n"
        "/adduser [ID] - Add user\n"
        "/removeuser [ID] - Remove user\n"
        "/listusers - List allowed users\n\n"
        f"📞 <b>Developer:</b> {bot_instance.config.get('developer_contact', '@Terry85855')}"
    )
    
    await update.message.reply_text(convert_to_premium(help_text), parse_mode=ParseMode.HTML)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update {update} caused error {context.error}")
    
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update {update} caused error {context.error}")
    
    if update and update.effective_user:
        if is_authorized(update.effective_user.id):
            error_msg = escape_html(str(context.error))
            await update.message.reply_text(convert_to_premium(f"❌ Error occurred: {error_msg}"),parse_mode=ParseMode.HTML)


app_web = Flask(__name__)

@app_web.route('/')
def index():
    return "Nora says Bot is running beautifully!"

def run_server():
    port = int(os.environ.get('PORT', 8080))
    app_web.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_server)
    t.start()
# -----------------------------------------------

def main():
    config = load_config()

    
    print(f"{V}╔════════════════════════════════════════════╗")
    print(f"{V}║{W}{B}   SMILE.ONE TELEGRAM BOT V3.7          {V}║")
    print(f"{V}║{Y}{B}          MULTI-USER TOPUP SYSTEM         {V}║")
    print(f"{V}╚════════════════════════════════════════════╝{N}")
    print(f"{C}[i] Exchange Rate: {config.get('mmk_exchange_rate', 75)} MMK/coin{N}")
    print(f"{C}[i] Developer: {config.get('developer_contact', '@Terry85855')}{N}")
    
    if not os.path.exists(COOKIE_FILE):
        print(f"{Y}[!] No cookie file found. Admin needs to set cookie.{N}")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("market", market_command))
    app.add_handler(CommandHandler("logs", logs_command))
    app.add_handler(CommandHandler("cookie", cookie_command))
    app.add_handler(CommandHandler("check", check_command))
    app.add_handler(CommandHandler("redeem", redeem_command))
    app.add_handler(CommandHandler("topup", topup_command))
    app.add_handler(CommandHandler("refresh", refresh_command))
    app.add_handler(CommandHandler("rate", rate_command))
    app.add_handler(CommandHandler("setrate", setrate_command))
    app.add_handler(CommandHandler("adduser", adduser_command))
    app.add_handler(CommandHandler("removeuser", removeuser_command))
    app.add_handler(CommandHandler("listusers", listusers_command))
    app.add_handler(CommandHandler("help", help_command))
    
    app.add_error_handler(error_handler)
    
    print(f"{G}[+] Bot started successfully!{N}")
    print(f"{C}[i] Admin ID: {config.get('admin_id')}{N}")
        
    
    print(f"{C}[i] Listening for commands...{N}") #[span_4](start_span)[span_4](end_span)
    print(f"{C}[i] Multi-user mode enabled{N}") #[span_5](start_span)[span_5](end_span)
    

    keep_alive() 
    
    app.run_polling(allowed_updates=Update.ALL_TYPES) #[span_6](start_span)[span_6](end_span)

if __name__ == "__main__": #[span_7](start_span)[span_7](end_span)
    main() #[span_8](start_span)[span_8](end_span)
