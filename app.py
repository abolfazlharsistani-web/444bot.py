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

# ===== کلیدهای ویژه (برای جلوگیری از خطا) =====
SPECIAL_KEYS = ["gift_codes", "pending_likes"]

# ===== اطلاعات کاربران =====
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
    users = get_all_users()
    
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

# ===== منوها (مثل قبلی) =====
def main_menu():
    return [
        [{"text": "🛍 فروشگاه 🛒", "callback_data": "shop"}, {"text": "💎 حساب من", "callback_data": "my_score"}],
        [{"text": "👥 دعوت افزایش امتیاز", "callback_data": "invite"}, {"text": "🎁 جوایز روزانه ⏰", "callback_data": "daily"}],
        [{"text": "🎫 کد هدیه", "callback_data": "redeem_code"}, {"text": "🏆 لیدربرد", "callback_data": "leaderboard"}],
        [{"text": "👑 VIP 👑", "callback_data": "vip_shop"}, {"text": "📖 راهنما", "callback_data": "help"}],
        [{"text": "📞 پشتیبانی", "callback_data": "support"}]
    ]

def shop_menu():
    return [
        [{"text": "🇧🇷 سنس برزیلی 🇧🇷", "callback_data": "get_sens"}],
        [{"text": "⚡ پنل سنس ⚡", "callback_data": "get_panel"}],
        [{"text": "👍 لایک اکانت 👍", "callback_data": "like_account"}],
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
        [{"text": "⭐️ امتیازات ⭐️", "callback_data": "help_score"}],
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
        [{"text": "💯 200 لایک (۱۲ جم)", "callback_data": "like_200"}],
        [{"text": "💯 300 لایک (۱۸ جم)", "callback_data": "like_300"}],
        [{"text": "💯 400 لایک (۲۴ جم)", "callback_data": "like_400"}],
        [{"text": "💯 500 لایک (۳۰ جم)", "callback_data": "like_500"}],
        [{"text": "👑 لایک خودکار (👑 VIP 👑)", "callback_data": "auto_like"}],
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
        send_message(chat_id, f"🔒 **عضویت اجباری در کانال**\n\nبرای استفاده از ربات **Black Fire**، ابتدا باید در کانال زیر عضو شوید:\n\n📢 {REQUIRED_CHANNEL}\n\n❗️ پس از عضویت، روی دکمه **«عضو شدم ✅»** کلیک کنید.", [[{"text": "✅ عضو شدم", "callback_data": "check_membership"}]])
        return

    if user.get("display_name") is None:
        admin_state = {}
        admin_state[chat_id] = {"step": "waiting_for_name"}
        send_message(chat_id, "📝 **لطفاً نام خود را وارد کنید :**\n\n📌 **قوانین:**\n• حداقل ۳ حرف\n• حداکثر ۱۵ حرف\n• فقط حروف انگلیسی و اعداد\n• بدون فاصله و علامت\n\n⚠️ بدون ثبت نام نمی‌توانید از ربات استفاده کنید.")
        return

    if user.get("is_banned", False):
        send_message(chat_id, "🚫 **شما توسط ادمین بن شده‌اید!**\n\nبرای رفع بن با پشتیبانی تماس بگیرید.")
        return

    # شمارش پیام‌ها
    update_user(chat_id, msg_count=user.get("msg_count", 0) + 1)

    if text.startswith("/start"):
        send_message(chat_id, "*🔥 به ربات Black Fire خوش آمدید 🔥*\n\nدر این ربات می‌توانید به جدیدترین سنس‌های فری فایر، پنل‌ها، تنظیمات و آموزش‌ها دسترسی داشته باشید.\n\n📢 کانال: @freefire_black_fire\n\nاز منوی زیر بخش موردنظر خود را انتخاب کنید 👇", main_menu())
        return

    if text == "/admin" and is_admin(chat_id):
        send_message(chat_id, "👑 **پنل مدیریت** 👑\n\nیک گزینه را انتخاب کنید:", admin_menu())
        return

    # ===== دریافت نام (تغییر نام) =====
    if chat_id in admin_state and admin_state[chat_id].get("step") == "waiting_for_name":
        name = text.strip()
        if not name:
            send_message(chat_id, "❌ نام نمی‌تواند خالی باشد!\n\nلطفاً نام خود را وارد کنید:")
            return
        if len(name) < 3:
            send_message(chat_id, "❌ نام باید حداقل **۳** حرف داشته باشد!\n\nلطفاً نام خود را وارد کنید:")
            return
        if len(name) > 15:
            send_message(chat_id, "❌ نام نباید بیشتر از **۱۵** حرف باشد!\n\nلطفاً نام خود را وارد کنید:")
            return
        if not name.isalnum():
            send_message(chat_id, "❌ نام فقط می‌تواند شامل **حروف انگلیسی** و **اعداد** باشد!\n(بدون فاصله، بدون فارسی، بدون علامت)\n\nلطفاً نام خود را وارد کنید:")
            return
        if not name[0].isalpha():
            send_message(chat_id, "❌ نام باید با یک **حرف** شروع شود!\n\nلطفاً نام خود را وارد کنید:")
            return
        update_user(chat_id, display_name=name)
        admin_state.pop(chat_id, None)
        send_message(chat_id, f"✅ **ثبت نام شما کامل شد!**\n\n👤 نام شما: {name}\n\n🔥 به ربات Black Fire خوش آمدید!", main_menu())
        return

    # ===== پشتیبانی =====
    if chat_id in admin_state and admin_state[chat_id].get("step") == "waiting_for_support_message":
        if text.strip():
            for admin_id in ADMINS:
                try:
                    send_message(admin_id, f"📩 **پیام جدید از پشتیبانی**\n\n👤 کاربر: {user.get('display_name', 'ناشناس')}\n🆔 آیدی: {chat_id}\n📝 پیام:\n{text}")
                except:
                    pass
            send_message(chat_id, "✅ **پیام شما با موفقیت به پشتیبانی ارسال شد!**\n\n📌 در اسرع وقت پاسخ داده خواهد شد.", [[{"text": "🔙 برگشت به منو", "callback_data": "back_main"}]])
            admin_state.pop(chat_id, None)
        else:
            send_message(chat_id, "❌ پیام نمی‌تواند خالی باشد!\n\nلطفاً متن پیام خود را وارد کنید.")
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
        send_message(chat_id, f"🔒 **عضویت اجباری در کانال**\n\nبرای استفاده از ربات **Black Fire**، ابتدا باید در کانال زیر عضو شوید:\n\n📢 {REQUIRED_CHANNEL}\n\n❗️ پس از عضویت، روی دکمه **«عضو شدم ✅»** کلیک کنید.", [[{"text": "✅ عضو شدم", "callback_data": "check_membership"}]])
        return

    if user.get("is_banned", False):
        send_message(chat_id, "🚫 **شما توسط ادمین بن شده‌اید!**\n\nبرای رفع بن با پشتیبانی تماس بگیرید.")
        return

    # ===== بررسی عضویت =====
    if data == "check_membership":
        if check_membership(chat_id):
            send_message(chat_id, "✅ **عضویت شما تأیید شد!**\n\n🔥 به ربات Black Fire خوش آمدید!", main_menu())
        else:
            send_message(chat_id, f"❌ **شما هنوز عضو کانال نشده‌اید!**\n\nلطفاً ابتدا در کانال {REQUIRED_CHANNEL} عضو شوید، سپس روی دکمه **«عضو شدم ✅»** کلیک کنید.", [[{"text": "✅ عضو شدم", "callback_data": "check_membership"}]])
        return

    # ===== پشتیبانی =====
    if data == "support":
        admin_state[chat_id] = {"step": "waiting_for_support_message"}
        send_message(chat_id, "📞 **ارسال پیام به پشتیبانی**\n\nلطفاً پیام خود را بنویسید:\n(مشکل، پیشنهاد، سوال، یا هر چیزی)\n\n📌 پس از ارسال، پیام شما به ادمین ارسال خواهد شد.", [[{"text": "🔙 برگشت", "callback_data": "back_main"}]])
        return

    # ===== منوی اصلی =====
    if data == "shop":
        send_message(chat_id, "🛍 **فروشگاه** 🛍\n\nیکی از گزینه‌های زیر را انتخاب کنید:", shop_menu())
    
    elif data == "my_score":
        score = user.get("score", 0)
        invites = user.get("invites", 0)
        display_name = user.get("display_name", "ناشناس")
        vip_icon = get_vip_icon(chat_id)
        vip_status = "فعال ✅" if is_vip_active(chat_id) else "غیرفعال ❌"
        vip_level = user.get("vip_level", "ندارد")
        vip_level_names = {"silver": "نقره‌ای", "gold": "طلایی", "crystal": "کریستالی", "none": "ندارد"}
        vip_level_name = vip_level_names.get(vip_level, "ندارد")
        text = f"📊 **حساب من**\n\n"
        text += f"👤 نام: {display_name} {vip_icon}\n"
        text += f"⭐ امتیاز: {score}\n"
        text += f"👥 دعوت‌ها: {invites}\n"
        text += f"🎁 جوایز روزانه = ۱ امتیاز\n"
        text += f"👑 VIP: {vip_level_name} ({vip_status})"
        send_message(chat_id, text, my_score_menu())
    
    elif data == "invite":
        invite_link = "https://ble.ir/blackfire_bot?start=" + chat_id
        send_message(chat_id, "*👥 لینک دعوت شما*\n\n" + invite_link + "\n\n🌟 هر دعوت موفق = ۱ امتیاز")
    
    elif data == "daily":
        last_claim = user.get("daily_claim")
        remaining_text, remaining_hours = get_time_remaining(last_claim)
        if remaining_text is None:
            update_user(chat_id, 
                score=user.get("score", 0) + 1,
                daily_claim=datetime.now().isoformat()
            )
            send_message(chat_id, "🎁 *جوایز روزانه دریافت شد!*\n\n✨ +۱ امتیاز به حساب شما اضافه شد.\n\n⏰ ۲۴ ساعت دیگه دوباره می‌تونی بگیری!")
        else:
            send_message(chat_id, f"⏳ *صبر کن!*\n\nتو امروز جوایز روزانه رو گرفتی!\n\n📅 زمان باقی‌مونده:\n⏰ {remaining_text}\n\n🔄 بعد از {remaining_hours} ساعت دوباره بیا!")
    
    elif data == "leaderboard":
        users = get_all_users()
        users_list = []
        for uid, info in users.items():
            if info.get("is_banned", False):
                continue
            users_list.append({
                "id": uid,
                "score": info.get("score", 0),
                "display_name": info.get("display_name"),
                "username": info.get("username"),
                "vip_level": info.get("vip_level", "none"),
                "vip_expiry": info.get("vip_expiry")
            })
        users_list.sort(key=lambda x: x["score"], reverse=True)
        top_users = users_list[:3]
        if not top_users:
            text = "🏆 **لیدربرد**\n\nهنوز هیچ کاربری وجود ندارد!"
        else:
            text = "🏆 **لیدربرد برترین‌ها:**\n\n"
            for i, user in enumerate(top_users, 1):
                medal = ["🥇", "🥈", "🥉"][i-1]
                name = user.get("display_name") or user.get("username") or user['id']
                vip_icon = ""
                if user.get("vip_level") in ["silver", "gold", "crystal"]:
                    if user.get("vip_expiry"):
                        try:
                            expiry = datetime.fromisoformat(user["vip_expiry"])
                            if datetime.now() < expiry:
                                if user["vip_level"] == "silver":
                                    vip_icon = "⚙️"
                                elif user["vip_level"] == "gold":
                                    vip_icon = "👑"
                                elif user["vip_level"] == "crystal":
                                    vip_icon = "💎"
                        except:
                            pass
                if i == 1:
                    text += f"   👑 رکورددار!\n"
                text += f"{medal} `{name}` {vip_icon} → ⭐{user['score']} امتیاز\n"
        send_message(chat_id, text)
    
    elif data == "vip_shop":
        text = "👑 *اشتراک VIP* 👑\n\nبا خرید اشتراک VIP از مزایای ویژه بهره‌مند شوید:\n\n"
        text += "⚙️ *نقره‌ای* (هفتگی) → ۳۰,۰۰۰ تومان\n"
        text += "  ۱۰۰ لایک روزانه خودکار (۷۰۰)\n\n"
        text += "👑 *طلایی* (ماهانه) → ۸۰,۰۰۰ تومان\n"
        text += "   ۱۰۰ لایک روزانه خودکار (۳k)\n\n"
        text += "💎 *کریستالی* (دو ماهه) → ۱۶۰,۰۰۰ تومان\n"
        text += "+ ۱۰۰ لایک روزانه خودکار (درکل ۶k) رایگان\n"
        text += "+ ۹۹% تخفیف روی همه چیز (بجز لایک)\n\n"
        text += "📞برای خرید به پشتیبانی پیام دهید:\n"
        text += "👤 @Abol_Tak66"
        send_message(chat_id, text, vip_menu())
    
    elif data in ["vip_silver", "vip_gold", "vip_crystal"]:
        send_message(chat_id, "📞 **برای خرید اشتراک VIP به پشتیبانی پیام دهید:**\n👤 @Abol_Tak66")
    
    elif data == "help":
        send_message(chat_id, "*📖 راهنمای 𝗕𝗹𝗮𝗰𝗸 𝗙𝗶𝗿𝗲*\n\nگزینه مورد نظر خود را انتخاب کنید :", help_menu())
    
    elif data == "help_sens":
        send_message(chat_id, "*💡 دریافت سنس و پنل*\n\nبا جمع کردن امتیاز میتوانید سنس، پنل و سایر امکانات بازی را رایگان دریافت کنید.\n\nحتی امکان خرید سنس و پنل‌های پولی نیز وجود دارد.\n\nسنس‌های رایگان بدون امتیاز هم منتشر می‌شوند، اما سنس‌ها و پنل‌های امتیازی ارزش و تأثیر بیشتری داشته و درصد هد بالاتری دارند.\n\n📞 برای خرید نسخه پولی به پشتیبانی پیام دهید.")
    
    elif data == "help_score":
        send_message(chat_id, "*⭐️ امتیازات ⭐️*\n\nبرای گرفتن سنس و پنل می‌توانید امتیاز جمع کنید.\n\nلینک اختصاصی خود را برای دوستانتان ارسال کنید.\n\n🌟 به ازای هر دعوت موفق، ۱ امتیاز دریافت خواهید کرد.\n🎁 هر روز ۱ امتیاز رایگان بگیر!")
    
    elif data == "help_ban":
        send_message(chat_id, "*😰 آیا اکانت بن می‌شود؟*\n\n❌ سنس در بازی تقلب محسوب نمی‌شود و بن یا بلک‌لیست ندارد.\n\n⚠️ اما پنل تقلب محسوب می‌شود و هرچه قوی‌تر باشد، احتمال بن یا بلک‌لیست شدن بیشتر است.\n\n❕ اگر اکانت شما ارزش دارد، بهتر است از پنل استفاده نکنید یا از اکانت فیک استفاده کنید.")
    
    elif data == "back_main":
        send_message(chat_id, "*🏠 منوی اصلی*", main_menu())

    # ===== فروشگاه =====
    elif data == "get_sens":
        score = user.get("score", 0)
        price = 1 if is_vip_active(chat_id) and user.get("vip_level") == "crystal" else SENS_PRICE
        text = f"🇧🇷 **خرید سنس برزیلی** 🇧🇷\nمخصوص : Xiaomi \n\n💰 قیمت: {price} امتیاز\n⭐ امتیاز شما: {score}\n\nآیا می‌خواهید 🇧🇷 سنس برزیلی 🇧🇷 را خریداری کنید؟"
        send_message(chat_id, text, [[{"text": "خرید ✅", "callback_data": "confirm_buy_sens"}], [{"text": "🔙 برگشت", "callback_data": "back_main"}]])
    
    elif data == "confirm_buy_sens":
        price = 1 if is_vip_active(chat_id) and user.get("vip_level") == "crystal" else SENS_PRICE
        if user.get("score", 0) >= price:
            update_user(chat_id, score=user.get("score", 0) - price)
            new_score = user.get("score", 0)
            caption = "*🇧🇷 سنس برزیلی ویژه 🇧🇷*\n\n📱مدل گوشی: Xiaomi \n\n💠 دی پی ای: 487\n\n🎯دکمه تیر: 50\n\n⚠️ هشدار:\nتغییر DPI توصیه نمی‌شود\nزیرا در طولانی مدت ممکن است\nباعث کندی موبایل شما بشود 🛑\n\n⭐ امتیاز فعلی شما: " + str(new_score)
            send_photo(chat_id, PHOTO_URL, caption, [[{"text": "🔙 برگشت به منو", "callback_data": "back_main"}]])
        else:
            send_message(chat_id, f"❌ **امتیاز کافی نیست!**\n\n⭐ امتیاز شما: {score}\n💰 قیمت سنس: {price} امتیاز\n\nبرای خرید سنس به {price - score} امتیاز دیگر نیاز دارید.\n\n👥 دوستان خود را دعوت کنید یا امتیاز روزانه بگیرید!", main_menu())
    
    elif data == "get_panel":
        score = user.get("score", 0)
        price = 1 if is_vip_active(chat_id) and user.get("vip_level") == "crystal" else PANEL_PRICE
        text = f"⚡ **پنل سنس** ⚡\n\n📱 توضیحات: در این برنامه تمام سنس گوشی ها با بالاترین کیفیت هست 📱🔱\n\n💰 قیمت: {price} امتیاز\n⭐ امتیاز شما: {score}\n\nآیا میخواهید ⚡ پنل سنس ⚡ را خریداری کنید؟"
        send_message(chat_id, text, [[{"text": "خرید ✅", "callback_data": "confirm_buy_panel"}], [{"text": "🔙 برگشت", "callback_data": "back_main"}]])
    
    elif data == "confirm_buy_panel":
        price = 1 if is_vip_active(chat_id) and user.get("vip_level") == "crystal" else PANEL_PRICE
        if user.get("score", 0) >= price:
            update_user(chat_id, score=user.get("score", 0) - price)
            new_score = user.get("score", 0)
            text = "✅ **خرید موفق!** 🎉\n\n⚡ **پنل سنس** ⚡\n\n📥 **لینک دانلود:**\n🔗 https://apkpure-com.cdn.ampproject.org/v/s/apkpure.com/fa/sensi-master/com.allakore.sensimasterff/amp?amp_gsa=1&amp_js_v=a9&usqp=mq331AQIUAKwASCAAgM%3D#amp_tf=%D8%A7%D8%B2%20%251%24s&aoh=17836942945219&csi=1&referrer=https%3A%2F%2Fwww.google.com&ampshare=https%3A%2F%2Fapkpure.com%2Ffa%2Fsensi-master%2Fcom.allakore.sensimasterff\n\n⭐ **امتیاز فعلی شما:** " + str(new_score)
            send_message(chat_id, text, [[{"text": "🔙 برگشت به منو", "callback_data": "back_main"}]])
        else:
            send_message(chat_id, f"❌ **امتیاز کافی نیست!**\n\n⭐ امتیاز شما: {score}\n💰 قیمت پنل: {price} امتیاز\n\nبرای خرید پنل به {price - score} امتیاز دیگر نیاز دارید.\n\n👥 دوستان خود را دعوت کنید یا امتیاز روزانه بگیرید!", main_menu())
    
    elif data == "like_account":
        text = "📊 **تعداد لایک مورد نظر را انتخاب کنید:**"
        send_message(chat_id, text, like_amount_menu())
    
    elif data in ["like_100", "like_200", "like_300", "like_400", "like_500"]:
        like_counts = {"like_100": 100, "like_200": 200, "like_300": 300, "like_400": 400, "like_500": 500}
        amount = like_counts[data]
        price = (amount // 100) * 6
        today = datetime.now().strftime("%Y-%m-%d")
        if user.get("last_like_date") == today:
            send_message(chat_id, "⛔ **شما امروز لایک خریدید!**\n\n🔄 فردا دوباره امتحان کن.\n\n📅 هر کاربر روزی ۱ بار می‌تواند لایک بخرد.")
            return
        if user.get("score", 0) >= price:
            update_user(chat_id, score=user.get("score", 0) - price, last_like_date=today)
            send_message(chat_id, "📱 **آیدی اکانت فری فایر خود را ارسال کنید:**\n\nپس از تأیید، لایک‌ها به اکانت شما واریز خواهد شد.\n(فقط اعداد، بدون فاصله و حروف)\n\nمثال: 0946481846")
            admin_state[chat_id] = {"step": "waiting_for_uid", "amount": amount}
        else:
            send_message(chat_id, f"❌ **امتیاز کافی نیست!**\n\n⭐ امتیاز شما: {user.get('score', 0)}\n💰 نیاز: {price} امتیاز\n\nبرای خرید لایک به {price - user.get('score', 0)} امتیاز دیگر نیاز دارید.")
    
    elif data == "auto_like":
        if is_vip_active(chat_id):
            update_user(chat_id, auto_like_active=True)
            send_message(chat_id, "✅ **لایک خودکار (👑 VIP 👑) شما فعال شد!**")
        else:
            send_message(chat_id, "❌ **شما اشتراک VIP ندارید!**\n\nبرای استفاده از لایک خودکار، ابتدا اشتراک VIP تهیه کنید.")

    # ===== پنل ادمین =====
    elif data.startswith("admin_"):
        if not is_admin(chat_id):
            send_message(chat_id, "❌ شما ادمین نیستید!")
            return
        
        if data == "admin_add":
            send_message(chat_id, "➕ **افزودن امتیاز**\n\nبه این شکل پیام بفرست:\n`add USER_ID مقدار`\n\nمثال:\n`add 459299490 10`")
        elif data == "admin_remove":
            send_message(chat_id, "➖ **کم کردن امتیاز**\n\nبه این شکل پیام بفرست:\n`remove USER_ID مقدار`\n\nمثال:\n`remove 459299490 5`")
        elif data == "admin_ban":
            send_message(chat_id, "🚫 **بن کاربر**\n\nبه این شکل پیام بفرست:\n`ban USER_ID`\n\nمثال:\n`ban 459299490`")
        elif data == "admin_unban":
            send_message(chat_id, "✅ **آنبن کاربر**\n\nبه این شکل پیام بفرست:\n`unban USER_ID`\n\nمثال:\n`unban 459299490`")
        elif data == "admin_list":
            users = get_all_users()
            text = "📋 **لیست کاربران:**\n\n"
            cnt = 0
            for uid, info in users.items():
                cnt += 1
                if cnt > 20:
                    break
                name = info.get("display_name") or info.get("username") or uid
                vip_icon = ""
                if info.get("vip_level") in ["silver", "gold", "crystal"]:
                    if info.get("vip_expiry"):
                        try:
                            expiry = datetime.fromisoformat(info["vip_expiry"])
                            if datetime.now() < expiry:
                                if info["vip_level"] == "silver":
                                    vip_icon = "⚙️"
                                elif info["vip_level"] == "gold":
                                    vip_icon = "👑"
                                elif info["vip_level"] == "crystal":
                                    vip_icon = "💎"
                        except:
                            pass
                status = "🚫" if info.get("is_banned", False) else "✅"
                text += f"{cnt}. `{name}` {vip_icon} → ⭐{info.get('score', 0)} {status}\n"
            if len(users) > 20:
                text += f"\n... و {len(users)-20} کاربر دیگر"
            send_message(chat_id, text)
        elif data == "admin_stats":
            users = get_all_users()
            total = len(users)
            total_score = sum(info.get("score", 0) for info in users.values())
            banned = sum(1 for info in users.values() if info.get("is_banned", False))
            text = f"📊 **آمار کل ربات:**\n\n"
            text += f"👥 کل کاربران: {total}\n"
            text += f"⭐ کل امتیازات: {total_score}\n"
            text += f"🚫 کاربران بن شده: {banned}"
            send_message(chat_id, text)
        elif data == "admin_broadcast":
            send_message(chat_id, "📢 **پیام همگانی**\n\nآیا می‌خواهید به تمام کاربران پیام ارسال کنید؟\n\n👥 تعداد کاربران: " + str(len(get_all_users())), broadcast_confirm_menu())
        elif data == "admin_vip_manage":
            send_message(chat_id, "👑 **مدیریت VIP**\n\nنوع اشتراک مورد نظر را انتخاب کنید:", vip_confirm_menu())
        elif data in ["vip_admin_silver", "vip_admin_gold", "vip_admin_crystal"]:
            level_map = {"vip_admin_silver": "silver", "vip_admin_gold": "gold", "vip_admin_crystal": "crystal"}
            level = level_map.get(data, "silver")
            vip_admin_state[chat_id] = {"step": "waiting_for_user_id", "level": level}
            send_message(chat_id, "📋 **جهت گرفتن اشتراک VIP، آیدی یا نام کاربر را ارسال کنید:**\n\n(مثال: 459299490)")
        elif data == "admin_remove_vip":
            admin_state[chat_id] = {"step": "waiting_for_remove_vip"}
            send_message(chat_id, "🗑 **حذف اشتراک VIP**\n\nلطفاً آیدی کاربری که می‌خواهید اشتراک VIP او حذف شود را وارد کنید:\n(مثال: 459299490)", [[{"text": "🔙 برگشت", "callback_data": "back_admin"}]])
        elif data == "admin_pending":
            send_message(chat_id, "💸 **واریزی**\n\n✅ هیچ درخواست تایید نشده‌ای وجود ندارد.", [[{"text": "🔙 برگشت", "callback_data": "back_admin"}]])
        elif data == "admin_queue_manage":
            send_message(chat_id, "📋 **مدیریت صف**\n\n✅ صف خالی است.", [[{"text": "🔙 برگشت", "callback_data": "back_admin"}]])
        elif data == "admin_activity":
            users = get_all_users()
            activity_list = []
            for uid, info in users.items():
                msg_count = info.get("msg_count", 0)
                if msg_count > 0:
                    name = info.get("display_name") or info.get("username") or uid
                    activity_list.append({"name": name, "count": msg_count})
            activity_list.sort(key=lambda x: x["count"], reverse=True)
            text = "📊 **فعالیت کاربران (بیشترین پیام‌ها)**\n\n"
            for i, u in enumerate(activity_list[:10], 1):
                text += f"{i}. `{u['name']}` → {u['count']} پیام\n"
            send_message(chat_id, text)

    elif data == "back_admin":
        if is_admin(chat_id):
            send_message(chat_id, "👑 **پنل مدیریت** 👑\n\nیک گزینه را انتخاب کنید:", admin_menu())

# ===== اجرای اصلی =====
admin_state = {}
vip_admin_state = {}

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