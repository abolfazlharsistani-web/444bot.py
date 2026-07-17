import requests
import time
import json
import os
from datetime import datetime, timedelta
import random
import string
import urllib3
from flask import Flask

# ===== تنظیمات اولیه =====
app = Flask(__name__)

@app.route('/')
def home():
    return "ربات Black Fire روشن است! ✅"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

proxies = None
TOKEN = "584247713:TdGGHKEzzbnXkBjAx4vSmyipjd62CNpJ4Qw"
BASE = f"https://tapi.bale.ai/bot{TOKEN}/"
offset = 0

SENS_PRICE = 5
PANEL_PRICE = 15
ADMINS = ["459299490"]
PHOTO_URL = "https://uploadkon.ir/uploads/d1c209_26file-00000000f014720cbe177bea305c38d3.png"
REQUIRED_CHANNEL = "@freefire_black_fire"

# ===== کلیدهای ویژه =====
SPECIAL_KEYS = ["gift_codes", "pending_likes"]

# ===== اطلاعات کاربران (همون فایل JSON) =====
FILE = "users.json"

def load_users():
    if not os.path.exists(FILE):
        return {}
    with open(FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users):
    try:
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"⚠️ خطا در ذخیره: {e}")
        return False

def get_user(chat_id):
    users = load_users()
    return users.get(chat_id)

def update_user(chat_id, **kwargs):
    users = load_users()
    if chat_id not in users:
        users[chat_id] = {}
    for key, value in kwargs.items():
        users[chat_id][key] = value
    save_users(users)

def get_all_users():
    users = load_users()
    # فقط کاربرانی که دیکشنری هستند رو برمی‌گردونیم
    return {uid: info for uid, info in users.items() if isinstance(info, dict) and uid not in SPECIAL_KEYS}

# ===== توابع =====
def send_message(chat_id, text, keyboard=None):
    data = {"chat_id": chat_id, "text": text}
    if keyboard:
        data["reply_markup"] = {"inline_keyboard": keyboard}
    try:
        resp = requests.post(BASE + "sendMessage", json=data, timeout=10, proxies=proxies)
        if resp.status_code == 200:
            return True
        if resp.status_code in [403, 404]:
            return False
        if resp.status_code == 429:
            retry = resp.json().get("parameters", {}).get("retry_after", 5)
            time.sleep(retry)
            return send_message(chat_id, text, keyboard)
        return False
    except:
        return False

def send_photo(chat_id, photo_url, caption=None, keyboard=None):
    data = {"chat_id": chat_id, "photo": photo_url}
    if caption:
        data["caption"] = caption
    if keyboard:
        data["reply_markup"] = {"inline_keyboard": keyboard}
    try:
        requests.post(BASE + "sendPhoto", json=data, timeout=10, proxies=proxies)
    except:
        pass

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def check_membership(chat_id):
    try:
        params = {"chat_id": REQUIRED_CHANNEL, "user_id": chat_id}
        resp = requests.get(BASE + "getChatMember", params=params, timeout=10, proxies=proxies)
        if resp.status_code == 403:
            return True
        data = resp.json()
        if data.get("ok"):
            return data["result"].get("status") in ["member", "administrator", "creator"]
        return True
    except:
        return True

def is_admin(chat_id):
    return chat_id in ADMINS

def is_vip_active(chat_id):
    user = get_user(chat_id)
    if not user or not isinstance(user, dict):
        return False
    expiry = user.get("vip_expiry")
    if not expiry:
        return False
    try:
        return datetime.now() < datetime.fromisoformat(expiry)
    except:
        return False

def get_time_remaining(last_claim):
    if not last_claim:
        return None, None
    try:
        last_time = datetime.fromisoformat(last_claim)
        next_time = last_time + timedelta(hours=24)
        now = datetime.now()
        if now >= next_time:
            return None, None
        remaining = next_time - now
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60
        seconds = remaining.seconds % 60
        return f"{hours} ساعت {minutes} دقیقه {seconds} ثانیه", hours
    except:
        return None, None

def activate_vip(chat_id, level):
    duration = 7 if level == "silver" else 30 if level == "gold" else 60
    expiry = datetime.now() + timedelta(days=duration)
    update_user(chat_id,
        vip_level=level,
        vip_expiry=expiry.isoformat()
    )

def send_daily_reminder():
    today = datetime.now().strftime("%Y-%m-%d")
    users = get_all_users()  # این فقط کاربران دیکشنری رو برمی‌گردونه
    
    for chat_id, user in users.items():
        if not user.get("notifications", True):
            continue
        if user.get("last_reminder_date") == today:
            continue
        last_claim = user.get("daily_claim")
        if last_claim:
            try:
                if datetime.fromisoformat(last_claim).date() == datetime.now().date():
                    continue
            except:
                pass
        send_message(chat_id, "🎁 **یادآوری جایزه روزانه**\n\nجایزه روزانه (۱ جم) امروز منتظر شماست!\nبرای دریافت، از منوی اصلی روی «🎁 جایزه روزانه» کلیک کنید.\n\n⏰ فقط امروز فرصت دارید!")
        update_user(chat_id, last_reminder_date=today)
        time.sleep(0.3)

# ===== منوها =====
def main_menu():
    return [
        [{"text": "🛍 فروشگاه", "callback_data": "shop"}, {"text": "💎 حساب من", "callback_data": "my_score"}],
        [{"text": "👥 دعوت", "callback_data": "invite"}, {"text": "🎁 جایزه روزانه", "callback_data": "daily"}],
        [{"text": "🎫 کد هدیه", "callback_data": "redeem_code"}, {"text": "🏆 لیدربرد", "callback_data": "leaderboard"}],
        [{"text": "👑 VIP", "callback_data": "vip_shop"}, {"text": "📖 راهنما", "callback_data": "help"}],
        [{"text": "📞 پشتیبانی", "callback_data": "support"}]
    ]

def shop_menu():
    return [
        [{"text": "سنس Xiaomi", "callback_data": "get_sens"}],
        [{"text": "سنس Redmi", "callback_data": "get_sens_redmi"}],
        [{"text": "⚡️ پنل سنس", "callback_data": "get_panel"}],
        [{"text": "👍 لایک اکانت", "callback_data": "like_account"}],
        [{"text": "🔙 برگشت", "callback_data": "back_main"}]
    ]

def vip_menu():
    return [
        [{"text": "⚙️ نقره‌ای (هفتگی) ۳۰,۰۰۰", "callback_data": "vip_silver"}],
        [{"text": "👑 طلایی (ماهانه) ۸۰,۰۰۰", "callback_data": "vip_gold"}],
        [{"text": "💎 کریستالی (دو ماهه) ۱۶۰,۰۰۰", "callback_data": "vip_crystal"}],
        [{"text": "🔙 برگشت", "callback_data": "back_main"}]
    ]

def admin_menu():
    return [
        [{"text": "➕ افزودن جم", "callback_data": "admin_add"}, {"text": "➖ کم کردن جم", "callback_data": "admin_remove"}],
        [{"text": "🚫 بن کاربر", "callback_data": "admin_ban"}, {"text": "✅ آنبن کاربر", "callback_data": "admin_unban"}],
        [{"text": "📋 لیست کاربران", "callback_data": "admin_list"}, {"text": "📊 آمار کل", "callback_data": "admin_stats"}],
        [{"text": "📢 پیام همگانی", "callback_data": "admin_broadcast"}, {"text": "🎁 کد هدیه", "callback_data": "admin_giftcode"}],
        [{"text": "👑 مدیریت VIP", "callback_data": "admin_vip_manage"}, {"text": "💸 واریزی", "callback_data": "admin_pending"}],
        [{"text": "📋 مدیریت صف", "callback_data": "admin_queue_manage"}, {"text": "📊 فعالیت کاربران", "callback_data": "admin_activity"}],
        [{"text": "🔙 بستن پنل", "callback_data": "back_main"}]
    ]

def help_menu():
    return [
        [{"text": "💡 دریافت سنس و پنل", "callback_data": "help_sens"}],
        [{"text": "💎 جم‌ها", "callback_data": "help_score"}],
        [{"text": "😰 آیا اکانت بن می‌شود؟", "callback_data": "help_ban"}],
        [{"text": "🔙 بازگشت", "callback_data": "back_main"}]
    ]

def vip_confirm_menu():
    return [
        [{"text": "⚙️ نقره‌ای (هفتگی)", "callback_data": "vip_admin_silver"}],
        [{"text": "👑 طلایی (ماهانه)", "callback_data": "vip_admin_gold"}],
        [{"text": "💎 کریستالی (دو ماهه)", "callback_data": "vip_admin_crystal"}],
        [{"text": "🗑 حذف اشتراک VIP", "callback_data": "admin_remove_vip"}],
        [{"text": "🔙 برگشت", "callback_data": "back_admin"}]
    ]

def like_amount_menu():
    return [
        [{"text": "💯 100 لایک (۶ جم)", "callback_data": "like_100"}],
        [{"text": "👑 لایک خودکار", "callback_data": "auto_like"}],
        [{"text": "📍 وضعیت نوبت من", "callback_data": "my_queue_status"}],
        [{"text": "📖 راهنما", "callback_data": "like_help"}],
        [{"text": "🔙 برگشت", "callback_data": "back_main"}]
    ]

def my_score_menu():
    return [
        [{"text": "✏️ تغییر نام (۱ جم)", "callback_data": "change_name"}],
        [{"text": "📊 آمار پیشرفت", "callback_data": "my_progress"}],
        [{"text": "🔗 لینک دعوت من", "callback_data": "my_invite_link"}],
        [{"text": "🎯 تنظیم اکانت لایک", "callback_data": "set_like_account"}],
        [{"text": "🔔 تنظیمات اعلان", "callback_data": "notification_settings"}],
        [{"text": "🔙 برگشت", "callback_data": "back_main"}]
    ]

def broadcast_confirm_menu():
    return [
        [{"text": "✅ تأیید", "callback_data": "broadcast_confirm"}],
        [{"text": "❌ خیر", "callback_data": "back_admin"}]
    ]

def get_vip_icon(chat_id):
    user = get_user(chat_id)
    if not user or not is_vip_active(chat_id):
        return ""
    level = user.get("vip_level", "none")
    if level == "silver":
        return "⚙️"
    elif level == "gold":
        return "👑"
    elif level == "crystal":
        return "💎"
    return ""

# ===== پردازش پیام‌ها =====
def handle_message(chat_id, text, update):
    user = get_user(chat_id)
    if not user:
        username = update["message"]["from"].get("username", None)
        users = load_users()
        users[chat_id] = {
            "score": 0,
            "invites": 0,
            "display_name": None,
            "username": username,
            "is_banned": False,
            "notifications": True,
            "vip_level": "none",
            "vip_expiry": None,
            "daily_claim": None,
            "last_reminder_date": None,
            "msg_count": 0
        }
        save_users(users)
        user = get_user(chat_id)

    if not check_membership(chat_id):
        send_message(chat_id, f"🔒 عضو کانال {REQUIRED_CHANNEL} شوید.", [[{"text": "✅ عضو شدم", "callback_data": "check_membership"}]])
        return

    if user.get("display_name") is None:
        send_message(chat_id, "📝 لطفاً نام خود را وارد کنید:")
        return

    if user.get("is_banned", False):
        send_message(chat_id, "🚫 شما توسط ادمین بن شده‌اید!")
        return

    # شمارش پیام‌ها
    update_user(chat_id, msg_count=user.get("msg_count", 0) + 1)

    if text.startswith("/start"):
        send_message(chat_id, "🔥 به ربات Black Fire خوش آمدید!", main_menu())
        return

    if text == "/admin" and is_admin(chat_id):
        send_message(chat_id, "👑 پنل مدیریت:", admin_menu())
        return

# ===== پردازش کالبک‌ها =====
def handle_callback(chat_id, data):
    user = get_user(chat_id)
    if not user:
        users = load_users()
        users[chat_id] = {
            "score": 0,
            "invites": 0,
            "display_name": None,
            "username": None,
            "is_banned": False,
            "notifications": True,
            "vip_level": "none",
            "vip_expiry": None,
            "daily_claim": None,
            "last_reminder_date": None,
            "msg_count": 0
        }
        save_users(users)
        user = get_user(chat_id)

    if not check_membership(chat_id):
        send_message(chat_id, f"🔒 عضو کانال {REQUIRED_CHANNEL} شوید.", [[{"text": "✅ عضو شدم", "callback_data": "check_membership"}]])
        return

    if user.get("is_banned", False):
        send_message(chat_id, "🚫 شما توسط ادمین بن شده‌اید!")
        return

    # ===== منوی اصلی =====
    if data == "shop":
        send_message(chat_id, "🛍 فروشگاه:", shop_menu())
    
    elif data == "my_score":
        score = user.get("score", 0)
        invites = user.get("invites", 0)
        display_name = user.get("display_name", "ناشناس")
        vip_icon = get_vip_icon(chat_id)
        vip_status = "فعال ✅" if is_vip_active(chat_id) else "غیرفعال ❌"
        vip_level = user.get("vip_level", "ندارد")
        vip_level_names = {"silver": "نقره‌ای", "gold": "طلایی", "crystal": "کریستالی", "none": "ندارد"}
        vip_level_name = vip_level_names.get(vip_level, "ندارد")
        text = f"💎 **حساب من**\n\n👤 نام: {display_name} {vip_icon}\n💎 جم: {score}\n👥 دعوت‌ها: {invites}\n🎁 جایزه روزانه = ۱ جم\n👑 VIP: {vip_level_name} ({vip_status})"
        send_message(chat_id, text, my_score_menu())
    
    elif data == "invite":
        invite_link = "https://ble.ir/blackfire_bot?start=" + chat_id
        send_message(chat_id, f"🔗 **لینک دعوت شما**\n\n{invite_link}\n\n🌟 هر دعوت موفق = ۱ جم")
    
    elif data == "daily":
        last_claim = user.get("daily_claim")
        remaining_text, remaining_hours = get_time_remaining(last_claim)
        if remaining_text is None:
            update_user(chat_id, 
                score=user.get("score", 0) + 1,
                daily_claim=datetime.now().isoformat()
            )
            send_message(chat_id, "🎁 جایزه روزانه دریافت شد! +۱ جم")
        else:
            send_message(chat_id, f"⏳ {remaining_text} دیگر صبر کنید.")
    
    elif data == "leaderboard":
        users = get_all_users()
        users_list = []
        for uid, info in users.items():
            if info.get("is_banned", False):
                continue
            if info.get("score", 0) <= 0:
                continue
            users_list.append({
                "id": uid,
                "score": info.get("score", 0),
                "display_name": info.get("display_name"),
                "username": info.get("username")
            })
        users_list.sort(key=lambda x: x["score"], reverse=True)
        top = users_list[:10]
        if not top:
            text = "🏆 لیدربرد: هنوز کاربری وجود ندارد!"
        else:
            text = "🏆 لیدربرد:\n"
            for i, u in enumerate(top, 1):
                name = u.get("display_name") or u.get("username") or "ناشناس"
                text += f"{i}. {name} → {u.get('score', 0)} جم\n"
        send_message(chat_id, text)
    
    elif data == "vip_shop":
        send_message(chat_id, "👑 اشتراک VIP:", vip_menu())
    
    elif data in ["vip_silver", "vip_gold", "vip_crystal"]:
        send_message(chat_id, "📞 برای خرید VIP با پشتیبانی تماس بگیرید: @Abol_Tak66")
    
    elif data == "help":
        send_message(chat_id, "📖 راهنما:", help_menu())
    
    elif data == "support":
        send_message(chat_id, "📞 پیام خود را برای پشتیبانی ارسال کنید.", [[{"text": "🔙 برگشت", "callback_data": "back_main"}]])
    
    elif data == "back_main":
        send_message(chat_id, "🏠 منوی اصلی:", main_menu())

    # ===== فروشگاه =====
    elif data == "get_sens":
        score = user.get("score", 0)
        price = 1 if is_vip_active(chat_id) and user.get("vip_level") == "crystal" else SENS_PRICE
        text = f"🇧🇷 خرید سنس Xiaomi\n💰 قیمت: {price} جم\n💎 جم شما: {score}\nآیا خریداری می‌کنید؟"
        send_message(chat_id, text, [[{"text": "خرید ✅", "callback_data": "confirm_buy_sens"}], [{"text": "🔙 برگشت", "callback_data": "back_main"}]])
    
    elif data == "confirm_buy_sens":
        price = 1 if is_vip_active(chat_id) and user.get("vip_level") == "crystal" else SENS_PRICE
        if user.get("score", 0) >= price:
            update_user(chat_id, score=user.get("score", 0) - price)
            send_photo(chat_id, PHOTO_URL, "✅ سنس Xiaomi خریداری شد!")
        else:
            send_message(chat_id, "❌ جم کافی نیست!")
    
    elif data == "get_sens_redmi":
        score = user.get("score", 0)
        price = 1 if is_vip_active(chat_id) and user.get("vip_level") == "crystal" else SENS_PRICE
        text = f"🇧🇷 خرید سنس Redmi\n💰 قیمت: {price} جم\n💎 جم شما: {score}\nآیا خریداری می‌کنید؟"
        send_message(chat_id, text, [[{"text": "خرید ✅", "callback_data": "confirm_buy_sens_redmi"}], [{"text": "🔙 برگشت", "callback_data": "back_main"}]])
    
    elif data == "confirm_buy_sens_redmi":
        price = 1 if is_vip_active(chat_id) and user.get("vip_level") == "crystal" else SENS_PRICE
        if user.get("score", 0) >= price:
            update_user(chat_id, score=user.get("score", 0) - price)
            send_photo(chat_id, PHOTO_URL, "✅ سنس Redmi خریداری شد!")
        else:
            send_message(chat_id, "❌ جم کافی نیست!")
    
    elif data == "get_panel":
        score = user.get("score", 0)
        price = 1 if is_vip_active(chat_id) and user.get("vip_level") == "crystal" else PANEL_PRICE
        text = f"⚡️ پنل سنس\n💰 قیمت: {price} جم\n💎 جم شما: {score}\nآیا خریداری می‌کنید؟"
        send_message(chat_id, text, [[{"text": "خرید ✅", "callback_data": "confirm_buy_panel"}], [{"text": "🔙 برگشت", "callback_data": "back_main"}]])
    
    elif data == "confirm_buy_panel":
        price = 1 if is_vip_active(chat_id) and user.get("vip_level") == "crystal" else PANEL_PRICE
        if user.get("score", 0) >= price:
            update_user(chat_id, score=user.get("score", 0) - price)
            send_message(chat_id, "✅ پنل خریداری شد!\n📥 لینک: https://apkpure.com/fa/sensi-master/")
        else:
            send_message(chat_id, "❌ جم کافی نیست!")
    
    elif data == "like_account":
        send_message(chat_id, "📊 خرید لایک:", like_amount_menu())
    
    elif data == "like_100":
        price = 6
        if user.get("score", 0) >= price:
            update_user(chat_id, score=user.get("score", 0) - price)
            send_message(chat_id, "📱 لطفاً UID خود را ارسال کنید:")
        else:
            send_message(chat_id, "❌ جم کافی نیست!")
    
    elif data == "auto_like":
        if is_vip_active(chat_id):
            update_user(chat_id, auto_like_active=True)
            send_message(chat_id, "✅ لایک خودکار فعال شد.")
        else:
            send_message(chat_id, "❌ VIP نیستید!")

    # ===== پنل ادمین =====
    elif data.startswith("admin_"):
        if not is_admin(chat_id):
            send_message(chat_id, "❌ شما ادمین نیستید!")
            return
        
        if data == "admin_add":
            send_message(chat_id, "➕ افزودن جم:\n`add USER_ID مقدار`")
        elif data == "admin_remove":
            send_message(chat_id, "➖ کم کردن جم:\n`remove USER_ID مقدار`")
        elif data == "admin_ban":
            send_message(chat_id, "🚫 بن کاربر:\n`ban USER_ID`")
        elif data == "admin_unban":
            send_message(chat_id, "✅ آنبن کاربر:\n`unban USER_ID`")
        elif data == "admin_list":
            users = get_all_users()
            text = "📋 لیست کاربران:\n"
            cnt = 0
            for uid, info in users.items():
                cnt += 1
                if cnt > 20:
                    break
                name = info.get("display_name") or info.get("username") or uid
                status = "🚫" if info.get("is_banned", False) else "✅"
                text += f"{cnt}. {name} → {info.get('score', 0)} جم {status}\n"
            send_message(chat_id, text)
        elif data == "admin_stats":
            users = get_all_users()
            total = len(users)
            total_score = sum(info.get("score", 0) for info in users.values())
            banned = sum(1 for info in users.values() if info.get("is_banned", False))
            text = f"📊 آمار:\n👥 کل کاربران: {total}\n💎 کل جم‌ها: {total_score}\n🚫 بن‌شده: {banned}"
            send_message(chat_id, text)
        elif data == "admin_broadcast":
            send_message(chat_id, "📢 پیام همگانی:\nپیام خود را ارسال کنید.", [[{"text": "❌ لغو", "callback_data": "back_admin"}]])
        elif data == "admin_vip_manage":
            send_message(chat_id, "👑 مدیریت VIP:", vip_confirm_menu())
        elif data in ["vip_admin_silver", "vip_admin_gold", "vip_admin_crystal"]:
            level_map = {"vip_admin_silver": "silver", "vip_admin_gold": "gold", "vip_admin_crystal": "crystal"}
            level = level_map.get(data, "silver")
            send_message(chat_id, f"📋 آیدی کاربر را برای فعال‌سازی {level} ارسال کنید:")
        elif data == "admin_remove_vip":
            send_message(chat_id, "🗑 آیدی کاربر برای حذف VIP را ارسال کنید:")
        elif data == "admin_pending":
            send_message(chat_id, "💸 واریزی: هیچ درخواستی وجود ندارد.", [[{"text": "🔙 برگشت", "callback_data": "back_admin"}]])
        elif data == "admin_queue_manage":
            send_message(chat_id, "📋 مدیریت صف: صف خالی است.", [[{"text": "🔙 برگشت", "callback_data": "back_admin"}]])
        elif data == "admin_activity":
            users = get_all_users()
            activity_list = []
            for uid, info in users.items():
                msg_count = info.get("msg_count", 0)
                if msg_count > 0:
                    name = info.get("display_name") or info.get("username") or uid
                    activity_list.append({"name": name, "count": msg_count})
            activity_list.sort(key=lambda x: x["count"], reverse=True)
            text = "📊 فعالیت کاربران:\n"
            for i, u in enumerate(activity_list[:10], 1):
                text += f"{i}. {u['name']} → {u['count']} پیام\n"
            send_message(chat_id, text)

    elif data == "back_admin":
        if is_admin(chat_id):
            send_message(chat_id, "👑 پنل مدیریت:", admin_menu())

# ===== اجرای اصلی =====
print("🔥 Black Fire Bot Started 🔥")
print(f"🤖 ربات: @blackfire_bot")
print(f"👑 ادمین‌ها: {ADMINS}")

try:
    old = requests.get(BASE + "getUpdates", proxies=proxies).json()
    if old.get("result"):
        offset = old["result"][-1]["update_id"] + 1
        print(f"✅ آپدیت‌های قدیمی دریافت شد: {offset}")
except Exception as e:
    print(f"⚠️ خطا در دریافت آپدیت‌های قدیمی: {e}")

last_reminder_time = 0

while True:
    try:
        now = time.time()
        if now - last_reminder_time > 300:
            send_daily_reminder()
            last_reminder_time = now

        result = requests.get(
            BASE + "getUpdates",
            params={"offset": offset, "timeout": 30},
            timeout=35,
            proxies=proxies
        ).json()

        for update in result.get("result", []):
            offset = update["update_id"] + 1

            if "message" in update:
                chat_id = str(update["message"]["chat"]["id"])
                text = update["message"].get("text", "")
                handle_message(chat_id, text, update)

            if "callback_query" in update:
                chat_id = str(update["callback_query"]["message"]["chat"]["id"])
                data = update["callback_query"]["data"]
                handle_callback(chat_id, data)

        time.sleep(1)

    except Exception as e:
        print(f"❌ خطای اصلی: {e}")
        time.sleep(5)

# ===== اجرای Flask برای Railway =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)