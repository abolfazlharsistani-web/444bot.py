import requests
import time
import json
import os
from datetime import datetime, timedelta
import random
import string
import urllib3

# ===== تنظیمات =====
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
proxies = None
TOKEN = "584247713:bVrTx_v15rKPA6fxw4sd631K_c7x8NjXhA8"
BASE = f"https://tapi.bale.ai/bot{TOKEN}/"
offset = 0
FILE = "users.json"

SENS_PRICE = 5
PANEL_PRICE = 15
ADMINS = ["459299490"]
PHOTO_URL = "https://uploadkon.ir/uploads/d1c209_26file-00000000f014720cbe177bea305c38d3.png"
REQUIRED_CHANNEL = "@freefire_black_fire"

broadcast_data = {}
like_data = {}
admin_state = {}
name_change_state = {}
vip_admin_state = {}
membership_cache = {}
SPECIAL_KEYS = ["gift_codes", "pending_likes", "like_queue"]
DAILY_LIKE_CAPACITY = 300

# ===== توابع =====
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
    now = time.time()
    if chat_id in membership_cache:
        cached_time, status = membership_cache[chat_id]
        if now - cached_time < 300:
            return status

    try:
        params = {"chat_id": REQUIRED_CHANNEL, "user_id": chat_id}
        resp = requests.get(BASE + "getChatMember", params=params, timeout=10, proxies=proxies)
        if resp.status_code == 403:
            membership_cache[chat_id] = (now, True)
            return True
        data = resp.json()
        if data.get("ok"):
            status = data["result"].get("status") in ["member", "administrator", "creator"]
            membership_cache[chat_id] = (now, status)
            return status
        membership_cache[chat_id] = (now, True)
        return True
    except:
        membership_cache[chat_id] = (now, True)
        return True

def is_admin(chat_id):
    return chat_id in ADMINS

def is_vip_active(chat_id):
    user = users.get(chat_id)
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
    users[chat_id]["vip_level"] = level
    users[chat_id]["vip_expiry"] = expiry.isoformat()
    if level in ["silver", "gold", "crystal"]:
        users[chat_id]["auto_like_active"] = False
        users[chat_id]["daily_like_limit"] = 100
        users[chat_id]["daily_like_sent"] = 0
        users[chat_id]["daily_like_date"] = None
    save_users(users)

def add_pending_like(chat_id, uid, amount, source="manual"):
    if "pending_likes" not in users:
        users["pending_likes"] = []
    users["pending_likes"].append({
        "chat_id": chat_id,
        "uid": uid,
        "amount": amount,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": source
    })
    save_users(users)

def remove_pending_like(index):
    if "pending_likes" in users and 0 <= index < len(users["pending_likes"]):
        del users["pending_likes"][index]
        save_users(users)
        return True
    return False

def add_to_queue(chat_id, uid, amount):
    if "like_queue" not in users:
        users["like_queue"] = []
    for item in users["like_queue"]:
        if item["chat_id"] == chat_id:
            return False, "شما قبلاً در صف هستید"
    users["like_queue"].append({
        "chat_id": chat_id,
        "uid": uid,
        "amount": amount,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_users(users)
    return True, len(users["like_queue"])

def process_queue():
    queue = users.get("like_queue", [])
    if not queue:
        return
    today = datetime.now().strftime("%Y-%m-%d")
    vip_count = 0
    for chat_id, user in list(users.items()):
        if chat_id in SPECIAL_KEYS or not isinstance(user, dict):
            continue
        if is_vip_active(chat_id) and user.get("auto_like_active", False) and user.get("daily_like_date") != today:
            vip_count += 1
            uid = user.get("vip_uid")
            if uid:
                add_pending_like(chat_id, uid, 100, "auto")
                users[chat_id]["daily_like_date"] = today
                save_users(users)
    remaining = DAILY_LIKE_CAPACITY - (vip_count * 100)
    if remaining <= 0:
        return
    processed = 0
    for item in queue[:]:
        if processed >= remaining:
            break
        add_pending_like(item["chat_id"], item["uid"], 100, "queue")
        queue.remove(item)
        processed += 1
    users["like_queue"] = queue
    save_users(users)

def send_daily_reminder():
    today = datetime.now().strftime("%Y-%m-%d")
    for chat_id, user in list(users.items()):
        if chat_id in SPECIAL_KEYS or not isinstance(user, dict):
            continue
        if not user.get("notifications", True):
            continue
        last_claim = user.get("daily_claim")
        if last_claim:
            try:
                if datetime.fromisoformat(last_claim).date() == datetime.now().date():
                    continue
            except:
                pass
        send_message(chat_id, "🎁 **یادآوری جایزه روزانه**\n\nجایزه روزانه (۱ جم) امروز منتظر شماست!\nبرای دریافت، از منوی اصلی روی «🎁 جایزه روزانه» کلیک کنید.\n\n⏰ فقط امروز فرصت دارید!")
        time.sleep(0.3)

# ===== منوها =====
def main_menu():
    return [
        [{"text": "🛍 فروشگاه 🛒", "callback_data": "shop"}, {"text": "💎 حساب من", "callback_data": "my_score"}],
        [{"text": "👥 دعوت", "callback_data": "invite"}, {"text": "🎁 جایزه روزانه", "callback_data": "daily"}],
        [{"text": "🎫 کد هدیه", "callback_data": "redeem_code"}, {"text": "🏆 لیدربرد", "callback_data": "leaderboard"}],
        [{"text": "👑 VIP 👑", "callback_data": "vip_shop"}, {"text": "📖 راهنما", "callback_data": "help"}],
        [{"text": "📞 پشتیبانی", "callback_data": "support"}]
    ]

def shop_menu():
    return [
        [{"text": "سنس Xiaomi 🇧🇷", "callback_data": "get_sens"}],
        [{"text": "سنس Redmi not 12 🇧🇷", "callback_data": "get_sens_redmi"}],
        [{"text": "⚡️ پنل سنس ⚡️", "callback_data": "get_panel"}],
        [{"text": "لایک اکانت 👍", "callback_data": "like_account"}],
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
    user = users.get(chat_id, {})
    if not is_vip_active(chat_id):
        return ""
    level = user.get("vip_level", "none")
    if level == "silver":
        return "⚙️"
    elif level == "gold":
        return "👑"
    elif level == "crystal":
        return "💎"
    return ""

users = load_users()

print("🔥 Black Fire Bot Started 🔥")
print(f"🤖 ربات: @blackfire_bot")
print(f"👥 تعداد کاربران: {len([k for k in users.keys() if k not in SPECIAL_KEYS])}")
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
        process_queue()

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

                if chat_id in SPECIAL_KEYS:
                    continue

                if not check_membership(chat_id):
                    send_message(
                        chat_id,
                        f"🔒 **عضویت اجباری در کانال**\n\n"
                        f"برای استفاده از ربات **Black Fire**، ابتدا باید در کانال زیر عضو شوید:\n\n"
                        f"📢 {REQUIRED_CHANNEL}\n\n"
                        f"❗️ پس از عضویت، روی دکمه **«عضو شدم ✅»** کلیک کنید.",
                        [[{"text": "✅ عضو شدم", "callback_data": "check_membership"}]]
                    )
                    continue

                if chat_id not in users:
                    users[chat_id] = {}
                if "msg_count" not in users[chat_id]:
                    users[chat_id]["msg_count"] = 0
                users[chat_id]["msg_count"] += 1
                save_users(users)

                user = users.get(chat_id, {})

                if user.get("display_name") is None:
                    admin_state[chat_id] = {"step": "waiting_for_name"}
                    send_message(chat_id, "📝 **لطفاً نام خود را وارد کنید :**\n\n📌 **قوانین:**\n• حداقل ۳ حرف\n• حداکثر ۱۵ حرف\n• فقط حروف انگلیسی و اعداد\n• بدون فاصله و علامت\n\n⚠️ بدون ثبت نام نمی‌توانید از ربات استفاده کنید.")
                    continue

                if chat_id in admin_state and admin_state[chat_id].get("step") == "waiting_for_support_message":
                    if text.strip():
                        user_name = user.get("display_name", "ناشناس")
                        user_id = chat_id
                        for admin_id in ADMINS:
                            try:
                                send_message(admin_id, f"📩 **پیام جدید از پشتیبانی**\n\n👤 کاربر: {user_name}\n🆔 آیدی: {user_id}\n📝 پیام:\n{text}")
                            except:
                                pass
                        send_message(chat_id, "✅ **پیام شما با موفقیت به پشتیبانی ارسال شد!**\n\n📌 در اسرع وقت پاسخ داده خواهد شد.", [[{"text": "🔙 برگشت به منو", "callback_data": "back_main"}]])
                        admin_state.pop(chat_id, None)
                    else:
                        send_message(chat_id, "❌ پیام نمی‌تواند خالی باشد!\n\nلطفاً متن پیام خود را وارد کنید.")
                    continue

                if chat_id in admin_state and admin_state[chat_id].get("step") == "waiting_for_remove_vip":
                    target_id = text.strip()
                    if target_id not in users or target_id in SPECIAL_KEYS:
                        send_message(chat_id, "❌ **کاربر یافت نشد!**\n\nلطفاً آیدی معتبری وارد کنید.")
                        continue
                    user_target = users[target_id]
                    if user_target.get("vip_level") == "none" or not user_target.get("vip_expiry"):
                        send_message(chat_id, f"❌ کاربر `{target_id}` اشتراک VIP فعالی ندارد!")
                        admin_state.pop(chat_id, None)
                        send_message(chat_id, "👑 **مدیریت VIP**", vip_confirm_menu())
                        continue
                    old_level = user_target.get("vip_level", "none")
                    level_names = {"silver": "⚙️ نقره‌ای", "gold": "👑 طلایی", "crystal": "💎 کریستالی"}
                    old_level_name = level_names.get(old_level, old_level)
                    users[target_id]["vip_level"] = "none"
                    users[target_id]["vip_expiry"] = None
                    users[target_id]["auto_like_active"] = False
                    users[target_id]["daily_like_limit"] = 0
                    users[target_id]["daily_like_sent"] = 0
                    users[target_id]["daily_like_date"] = None
                    save_users(users)
                    send_message(chat_id, f"✅ **اشتراک VIP کاربر `{target_id}` حذف شد!**\n\n🔹 سطح قبلی: {old_level_name}")
                    try:
                        send_message(target_id, f"🗑 **اشتراک VIP شما توسط ادمین حذف شد!**\n\n🔹 سطح قبلی: {old_level_name}\n📌 لایک خودکار غیرفعال شد.\n🔹 برای دریافت مجدد VIP با پشتیبانی تماس بگیرید.")
                    except:
                        pass
                    admin_state.pop(chat_id, None)
                    send_message(chat_id, "👑 **مدیریت VIP**", vip_confirm_menu())
                    continue

                if chat_id in name_change_state and name_change_state[chat_id] == "waiting_for_name":
                    name = text.strip()
                    if not name:
                        send_message(chat_id, "❌ نام نمی‌تواند خالی باشد!\n\nلطفاً نام جدید خود را وارد کنید:")
                        continue
                    if len(name) < 3:
                        send_message(chat_id, "❌ نام باید حداقل **۳** حرف داشته باشد!\n\nلطفاً نام جدید خود را وارد کنید:")
                        continue
                    if len(name) > 15:
                        send_message(chat_id, "❌ نام نباید بیشتر از **۱۵** حرف باشد!\n\nلطفاً نام جدید خود را وارد کنید:")
                        continue
                    if not name.isalnum():
                        send_message(chat_id, "❌ نام فقط می‌تواند شامل **حروف انگلیسی** و **اعداد** باشد!\n(بدون فاصله، بدون فارسی، بدون علامت)\n\nلطفاً نام جدید خود را وارد کنید:")
                        continue
                    if not name[0].isalpha():
                        send_message(chat_id, "❌ نام باید با یک **حرف** شروع شود!\n\nلطفاً نام جدید خود را وارد کنید:")
                        continue
                    if user.get("score", 0) < 1:
                        send_message(chat_id, "❌ **جم کافی نیست!**\n\nبرای تغییر نام به ۱ جم نیاز دارید.\n💎 جم شما: " + str(user.get("score", 0)))
                        name_change_state.pop(chat_id, None)
                        send_message(chat_id, "💎 **حساب من**", my_score_menu())
                        continue
                    users[chat_id]["score"] -= 1
                    users[chat_id]["display_name"] = name
                    save_users(users)
                    name_change_state.pop(chat_id, None)
                    send_message(chat_id, f"✅ **نام شما با موفقیت تغییر کرد!**\n\n👤 نام جدید: {name}\n💎 جم شما: {users[chat_id]['score']}")
                    send_message(chat_id, "💎 **حساب من**", my_score_menu())
                    continue

                if chat_id in admin_state and admin_state[chat_id].get("step") == "waiting_for_name":
                    name = text.strip()
                    if not name:
                        send_message(chat_id, "❌ نام نمی‌تواند خالی باشد!\n\nلطفاً نام خود را وارد کنید:")
                        continue
                    if len(name) < 3:
                        send_message(chat_id, "❌ نام باید حداقل **۳** حرف داشته باشد!\n\nلطفاً نام خود را وارد کنید:")
                        continue
                    if len(name) > 15:
                        send_message(chat_id, "❌ نام نباید بیشتر از **۱۵** حرف باشد!\n\nلطفاً نام خود را وارد کنید:")
                        continue
                    if not name.isalnum():
                        send_message(chat_id, "❌ نام فقط می‌تواند شامل **حروف انگلیسی** و **اعداد** باشد!\n(بدون فاصله، بدون فارسی، بدون علامت)\n\nلطفاً نام خود را وارد کنید:")
                        continue
                    if not name[0].isalpha():
                        send_message(chat_id, "❌ نام باید با یک **حرف** شروع شود!\n\nلطفاً نام خود را وارد کنید:")
                        continue
                    users[chat_id]["display_name"] = name
                    save_users(users)
                    admin_state.pop(chat_id, None)
                    send_message(chat_id, f"✅ **ثبت نام شما کامل شد!**\n\n👤 نام شما: {name}\n\n🔥 به ربات Black Fire خوش آمدید!", main_menu())
                    continue

                if chat_id in vip_admin_state:
                    step = vip_admin_state[chat_id].get("step")
                    if step == "waiting_for_user_id":
                        target_id = text.strip()
                        if target_id not in users or target_id in SPECIAL_KEYS:
                            send_message(chat_id, "❌ **آیدی نادرست است!**\n\nکاربر مورد نظر یافت نشد.\nلطفاً دوباره تلاش کنید.")
                            continue
                        level = vip_admin_state[chat_id].get("level")
                        activate_vip(target_id, level)
                        level_names = {"silver": "⚙️ نقره‌ای", "gold": "👑 طلایی", "crystal": "💎 کریستالی"}
                        level_name = level_names.get(level, level)
                        send_message(chat_id, f"✅ **اشتراک {level_name} VIP برای کاربر `{target_id}` فعال شد!** ✅")
                        send_message(target_id, f"✅ **اشتراک {level_name} VIP برای شما فعال شد!**\n\n🎉 از مزایای VIP استفاده کنید.")
                        vip_admin_state.pop(chat_id, None)
                        send_message(chat_id, "👑 **مدیریت VIP**", vip_confirm_menu())
                        continue

                if chat_id in admin_state and admin_state[chat_id].get("step") == "waiting_for_like_uid":
                    uid = text.strip()
                    if not uid.isdigit():
                        send_message(chat_id, "❌ **UID نامعتبر!**\n\nلطفاً یک UID معتبر وارد کنید.\n(فقط اعداد، بدون فاصله و حروف)\n\nمثال: 0946481846")
                        continue
                    users[chat_id]["vip_uid"] = uid
                    save_users(users)
                    admin_state.pop(chat_id, None)
                    send_message(chat_id, f"✅ **اکانت لایک خودکار شما ثبت شد!**\n\n📱 UID: {uid}\n\nهر روز لایک‌های شما به این اکانت واریز خواهد شد.")
                    send_message(chat_id, "💎 **حساب من**", my_score_menu())
                    continue

                if chat_id in admin_state and admin_state[chat_id].get("step") == "waiting_for_auto_like_uid":
                    uid = text.strip()
                    if not uid.isdigit():
                        send_message(chat_id, "❌ **UID نامعتبر!**\n\nلطفاً یک UID معتبر وارد کنید.\n(فقط اعداد، بدون فاصله و حروف)\n\nمثال: 0946481846")
                        continue
                    users[chat_id]["vip_uid"] = uid
                    users[chat_id]["auto_like_active"] = True
                    save_users(users)
                    admin_state.pop(chat_id, None)
                    send_message(chat_id, f"✅ **لایک خودکار (👑 VIP 👑) شما فعال شد!**\n\n📱 UID: {uid}\n📊 تعداد روزانه: ۱۰۰ لایک\n\nهر روز ۱۰۰ لایک برای شما واریز میشود.\nغیرفعال شدن در صورتی است که تاریخ اشتراک شما تمام شود.")
                    continue

                invite_code = None
                if text.startswith("/start "):
                    invite_code = text.split(" ")[1]

                if chat_id not in users:
                    username = update["message"]["from"].get("username", None)
                    users[chat_id] = {
                        "score": 0,
                        "invites": 0,
                        "invited_by": None,
                        "daily_claim": None,
                        "is_banned": False,
                        "gift_codes": [],
                        "display_name": None,
                        "username": username,
                        "last_like_date": None,
                        "notifications": True,
                        "vip_level": "none",
                        "vip_expiry": None,
                        "vip_uid": None,
                        "auto_like_active": False,
                        "daily_like_limit": 0,
                        "daily_like_sent": 0,
                        "daily_like_date": None,
                        "msg_count": 0
                    }
                    if invite_code and invite_code != chat_id and invite_code in users and invite_code not in SPECIAL_KEYS:
                        users[invite_code]["score"] += 1
                        users[invite_code]["invites"] += 1
                        users[chat_id]["invited_by"] = invite_code
                        send_message(invite_code, "*🎉 دعوت موفق!*\n\n💎 ۱ جم به شما اضافه شد.")
                    save_users(users)

                if text.startswith("/start"):
                    send_message(chat_id, "*🔥 به ربات Black Fire خوش آمدید 🔥*\n\nدر این ربات می‌توانید به جدیدترین سنس‌های فری فایر، پنل‌ها، تنظیمات و آموزش‌ها دسترسی داشته باشید.\n\n📢 کانال: @freefire_black_fire\n\nاز منوی زیر بخش موردنظر خود را انتخاب کنید 👇", main_menu())

                if text == "/admin" and is_admin(chat_id):
                    send_message(chat_id, "👑 **پنل مدیریت** 👑\n\nیک گزینه را انتخاب کنید:", admin_menu())

                if chat_id in admin_state and admin_state[chat_id].get("step") == "waiting_for_code_uses":
                    if text.isdigit():
                        uses = int(text)
                        admin_state[chat_id]["uses"] = uses
                        admin_state[chat_id]["step"] = "waiting_for_code_points"
                        send_message(chat_id, "💎 **کد چند جم باشد؟**\n\nلطفاً عدد جم را وارد کنید:")
                    else:
                        send_message(chat_id, "❌ **لطفاً یک عدد معتبر وارد کنید!**\n\nتعداد مصرف کد را به عدد بفرستید:")
                    continue

                if chat_id in admin_state and admin_state[chat_id].get("step") == "waiting_for_code_points":
                    if text.isdigit():
                        points = int(text)
                        uses = admin_state[chat_id]["uses"]
                        code = generate_code()
                        if "gift_codes" not in users:
                            users["gift_codes"] = {}
                        users["gift_codes"][code] = {
                            "uses": uses,
                            "used": 0,
                            "points": points,
                            "users": []
                        }
                        save_users(users)
                        admin_state.pop(chat_id, None)
                        send_message(chat_id, f"✅ **کد هدیه ساخته شد!** 🎉\n\n🔑 کد: `{code}`\n👥 تعداد مصرف: {uses} نفر\n💎 جم: {points} جم\n\n📋 این کد را به کاربران خود بدهید.")
                        send_message(chat_id, "👑 **پنل مدیریت** 👑\n\nیک گزینه را انتخاب کنید:", admin_menu())
                    else:
                        send_message(chat_id, "❌ **لطفاً یک عدد معتبر وارد کنید!**\n\nجم کد را به عدد بفرستید:")
                    continue

                if text.startswith("/redeem"):
                    parts = text.split(" ", 1)
                    if len(parts) == 2:
                        code = parts[1].strip().upper()
                        if "gift_codes" in users and code in users["gift_codes"]:
                            gift_data = users["gift_codes"][code]
                            if gift_data["used"] >= gift_data["uses"]:
                                send_message(chat_id, "❌ **این کد دیگر نامعتبر است!**\n\nتعداد مصرف این کد به پایان رسیده است.")
                            elif chat_id in gift_data["users"]:
                                send_message(chat_id, "❌ **شما قبلاً از این کد استفاده کرده‌اید!**\n\nهر کاربر فقط یک بار می‌تواند از هر کد استفاده کند.")
                            else:
                                users[chat_id]["score"] += gift_data["points"]
                                gift_data["used"] += 1
                                gift_data["users"].append(chat_id)
                                users["gift_codes"][code] = gift_data
                                save_users(users)
                                send_message(chat_id, f"✅ **تبریک!** 🎉\n\nشما با موفقیت کد `{code}` را استفاده کردید.\n💎 {gift_data['points']} جم به حساب شما اضافه شد.\n\n💎 جم فعلی شما: {users[chat_id]['score']}")
                        else:
                            send_message(chat_id, "❌ **کد نامعتبر!**\n\nکد وارد شده صحیح نمی‌باشد.")
                    else:
                        send_message(chat_id, "❌ **لطفاً کد را به این شکل وارد کنید:**\n\n`/redeem کد`\n\nمثال: `/redeem ABC12345`")
                    continue

                if is_admin(chat_id) and chat_id in broadcast_data and broadcast_data[chat_id] == "waiting_for_message":
                    msg_text = text
                    total_users = len([k for k in users.keys() if k not in SPECIAL_KEYS])
                    sent = 0
                    failed = 0
                    send_message(chat_id, f"📢 **در حال ارسال پیام به {total_users} کاربر...**\n\n⏳ لطفاً صبر کنید...")
                    for uid in users.keys():
                        if uid not in SPECIAL_KEYS:
                            try:
                                if send_message(uid, f"📢 **پیام همگانی:**\n\n{msg_text}"):
                                    sent += 1
                                else:
                                    failed += 1
                                time.sleep(0.1)
                            except:
                                failed += 1
                    broadcast_data.pop(chat_id, None)
                    send_message(chat_id, f"✅ **پیام همگانی ارسال شد!**\n\n📨 ارسال موفق: {sent}\n❌ ارسال ناموفق: {failed}\n👥 کل کاربران: {total_users}")
                    send_message(chat_id, "👑 **پنل مدیریت** 👑\n\nیک گزینه را انتخاب کنید:", admin_menu())
                    continue

                if chat_id in like_data and like_data[chat_id].get("waiting_for_uid", False):
                    uid = text.strip()
                    if uid.isdigit():
                        amount = like_data[chat_id]["amount"]
                        if is_vip_active(chat_id):
                            add_pending_like(chat_id, uid, amount, "manual")
                            send_message(chat_id, "✅ **شما VIP هستید!**\n\n👍 لایک‌های شما مستقیماً واریز می‌شوند.")
                        else:
                            success, result = add_to_queue(chat_id, uid, amount)
                            if success:
                                send_message(chat_id, f"✅ **درخواست شما ثبت شد!**\n\n📍 شماره نوبت شما: {result}\n⏳ به ترتیب نوبت لایک‌ها واریز می‌شود.\n\n🔹 برای مشاهده وضعیت نوبت، از دکمه «📍 وضعیت نوبت من» استفاده کنید.")
                            else:
                                send_message(chat_id, f"❌ {result}")
                        admin_text = f"👍 **درخواست لایک جدید**\n\n👤 کاربر: {chat_id}\n📱 UID: {uid}\n📊 تعداد لایک: {amount}\n💰 هزینه: {amount // 100 * 6} جم\n🔹 منبع: {'VIP' if is_vip_active(chat_id) else 'صف'}"
                        for admin_id in ADMINS:
                            try:
                                send_message(admin_id, admin_text)
                            except:
                                pass
                        like_data.pop(chat_id, None)
                    else:
                        send_message(chat_id, "❌ **UID نامعتبر!**\n\nلطفاً یک UID معتبر وارد کنید.\n(فقط اعداد، بدون فاصله و حروف)\n\nمثال: 0946481846")
                    continue

                if is_admin(chat_id):
                    parts = text.split()
                    if len(parts) >= 3 and parts[0] == "add":
                        target_id = parts[1]
                        try:
                            amount = int(parts[2])
                            if target_id in users and target_id not in SPECIAL_KEYS:
                                users[target_id]["score"] += amount
                                save_users(users)
                                send_message(chat_id, f"✅ {amount} جم به کاربر `{target_id}` اضافه شد.\n💎 جم جدید: {users[target_id]['score']}")
                            else:
                                send_message(chat_id, f"❌ کاربر `{target_id}` یافت نشد!")
                        except:
                            send_message(chat_id, "❌ مقدار نامعتبر!")
                    elif len(parts) >= 3 and parts[0] == "remove":
                        target_id = parts[1]
                        try:
                            amount = int(parts[2])
                            if target_id in users and target_id not in SPECIAL_KEYS:
                                users[target_id]["score"] = max(0, users[target_id]["score"] - amount)
                                save_users(users)
                                send_message(chat_id, f"➖ {amount} جم از کاربر `{target_id}` کم شد.\n💎 جم جدید: {users[target_id]['score']}")
                            else:
                                send_message(chat_id, f"❌ کاربر `{target_id}` یافت نشد!")
                        except:
                            send_message(chat_id, "❌ مقدار نامعتبر!")
                    elif len(parts) >= 2 and parts[0] == "ban":
                        target_id = parts[1]
                        if target_id in users and target_id not in SPECIAL_KEYS:
                            users[target_id]["is_banned"] = True
                            save_users(users)
                            send_message(chat_id, f"🚫 کاربر `{target_id}` بن شد!")
                            try:
                                send_message(target_id, "🚫 شما توسط ادمین بن شدید!")
                            except:
                                pass
                        else:
                            send_message(chat_id, f"❌ کاربر `{target_id}` یافت نشد!")
                    elif len(parts) >= 2 and parts[0] == "unban":
                        target_id = parts[1]
                        if target_id in users and target_id not in SPECIAL_KEYS:
                            users[target_id]["is_banned"] = False
                            save_users(users)
                            send_message(chat_id, f"✅ کاربر `{target_id}` آنبن شد!")
                            try:
                                send_message(target_id, "✅ بن شما توسط ادمین رفع شد!")
                            except:
                                pass
                        else:
                            send_message(chat_id, f"❌ کاربر `{target_id}` یافت نشد!")

            if "callback_query" in update:
                chat_id = str(update["callback_query"]["message"]["chat"]["id"])
                if chat_id in SPECIAL_KEYS:
                    continue

                if not check_membership(chat_id):
                    send_message(
                        chat_id,
                        f"🔒 **عضویت اجباری در کانال**\n\n"
                        f"برای استفاده از ربات **Black Fire**، ابتدا باید در کانال زیر عضو شوید:\n\n"
                        f"📢 {REQUIRED_CHANNEL}\n\n"
                        f"❗️ پس از عضویت، روی دکمه **«عضو شدم ✅»** کلیک کنید.",
                        [[{"text": "✅ عضو شدم", "callback_data": "check_membership"}]]
                    )
                    continue

                user = users.get(chat_id, {})
                if user.get("display_name") is None:
                    admin_state[chat_id] = {"step": "waiting_for_name"}
                    send_message(chat_id, "📝 **لطفاً نام خود را وارد کنید :**\n\n📌 **قوانین:**\n• حداقل ۳ حرف\n• حداکثر ۱۵ حرف\n• فقط حروف انگلیسی و اعداد\n• بدون فاصله و علامت\n\n⚠️ بدون ثبت نام نمی‌توانید از ربات استفاده کنید.")
                    continue

                data = update["callback_query"]["data"]

                if user.get("is_banned", False):
                    send_message(chat_id, "🚫 **شما توسط ادمین بن شده‌اید!**\n\nبرای رفع بن با پشتیبانی تماس بگیرید.")
                    continue

                if data == "check_membership":
                    if check_membership(chat_id):
                        send_message(chat_id, "✅ **عضویت شما تأیید شد!**\n\n🔥 به ربات Black Fire خوش آمدید!", main_menu())
                    else:
                        send_message(chat_id, f"❌ **شما هنوز عضو کانال نشده‌اید!**\n\nلطفاً ابتدا در کانال {REQUIRED_CHANNEL} عضو شوید، سپس روی دکمه **«عضو شدم ✅»** کلیک کنید.", [[{"text": "✅ عضو شدم", "callback_data": "check_membership"}]])
                    continue

                if data == "support":
                    admin_state[chat_id] = {"step": "waiting_for_support_message"}
                    send_message(chat_id, "📞 **ارسال پیام به پشتیبانی**\n\nلطفاً پیام خود را بنویسید:\n(مشکل، پیشنهاد، سوال، یا هر چیزی)\n\n📌 پس از ارسال، پیام شما به ادمین ارسال خواهد شد.", [[{"text": "🔙 برگشت", "callback_data": "back_main"}]])
                    continue

                if data == "shop":
                    send_message(chat_id, "🛍 **فروشگاه** 🛍\n\nیکی از گزینه‌های زیر را انتخاب کنید:", shop_menu())

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

                elif data == "admin_vip_manage":
                    if not is_admin(chat_id):
                        send_message(chat_id, "❌ شما ادمین نیستید!")
                        continue
                    send_message(chat_id, "👑 **مدیریت VIP**\n\nنوع اشتراک مورد نظر را انتخاب کنید:", vip_confirm_menu())

                elif data in ["vip_admin_silver", "vip_admin_gold", "vip_admin_crystal"]:
                    if not is_admin(chat_id):
                        send_message(chat_id, "❌ شما ادمین نیستید!")
                        continue
                    level_map = {"vip_admin_silver": "silver", "vip_admin_gold": "gold", "vip_admin_crystal": "crystal"}
                    level = level_map.get(data, "silver")
                    vip_admin_state[chat_id] = {"step": "waiting_for_user_id", "level": level}
                    send_message(chat_id, "📋 **جهت گرفتن اشتراک VIP، آیدی یا نام کاربر را ارسال کنید:**\n\n(مثال: 459299490)")

                elif data == "admin_remove_vip":
                    if not is_admin(chat_id):
                        send_message(chat_id, "❌ شما ادمین نیستید!")
                        continue
                    admin_state[chat_id] = {"step": "waiting_for_remove_vip"}
                    send_message(chat_id, "🗑 **حذف اشتراک VIP**\n\nلطفاً آیدی کاربری که می‌خواهید اشتراک VIP او حذف شود را وارد کنید:\n(مثال: 459299490)", [[{"text": "🔙 برگشت", "callback_data": "back_admin"}]])
                    continue

                elif data == "auto_like":
                    if not is_vip_active(chat_id):
                        send_message(chat_id, "❌ **شما اشتراک VIP ندارید!**\n\nبرای استفاده از لایک خودکار، ابتدا اشتراک VIP تهیه کنید.")
                        continue
                    level = user.get("vip_level", "none")
                    if level not in ["silver", "gold", "crystal"]:
                        send_message(chat_id, "❌ **لایک خودکار فقط برای VIPهای نقره‌ای، طلایی و کریستالی فعال است!**")
                        continue
                    if user.get("auto_like_active", False):
                        send_message(chat_id, f"✅ **لایک خودکار شما در حال حاضر فعال است!**\n\n👑 {level} VIP\n📊 تعداد روزانه: ۱۰۰ لایک\n📱 UID: {user.get('vip_uid', 'تنظیم نشده')}\n\n⏳ تا پایان اشتراک VIP فعال خواهد ماند.")
                        continue
                    admin_state[chat_id] = {"step": "waiting_for_auto_like_uid"}
                    send_message(chat_id, "📱 **آیدی اکانت فری فایر خود را ارسال کنید:**\n\nپس از تأیید، هر روز لایک‌ها به این اکانت واریز خواهد شد.\n(فقط اعداد، بدون فاصله و حروف)\n\nمثال: 0946481846")

                elif data == "set_like_account":
                    if not is_vip_active(chat_id):
                        send_message(chat_id, "❌ **شما اشتراک VIP ندارید!**\n\nابتدا اشتراک VIP تهیه کنید.")
                        continue
                    level = user.get("vip_level", "none")
                    if level not in ["silver", "gold", "crystal"]:
                        send_message(chat_id, "❌ این بخش فقط برای VIPهای نقره‌ای، طلایی و کریستالی فعال است!")
                        continue
                    admin_state[chat_id] = {"step": "waiting_for_like_uid"}
                    send_message(chat_id, "📱 **آیدی اکانت فری فایر خود را ارسال کنید:**\n\n(فقط اعداد، بدون فاصله و حروف)\n\nمثال: 0946481846")

                elif data == "like_account":
                    text = "📊 **خرید لایک**\n\n"
                    text += "📌 هر کاربر در روز فقط **یک بار** می‌تواند **۱۰۰ لایک** سفارش دهد.\n"
                    text += "💰 هزینه: ۶ جم\n"
                    text += "⏳ بعد از خرید، تا فردا نمی‌توانید دوباره خرید کنید.\n\n"
                    text += "🔹 اگر صف پر باشد، درخواست شما به صف اضافه می‌شود.\n"
                    text += "🔹 برای مشاهده نوبت خود، از دکمه «📍 وضعیت نوبت من» استفاده کنید."
                    send_message(chat_id, text, like_amount_menu())

                elif data == "like_help":
                    text = "📖 **راهنمای خرید لایک**\n\n"
                    text += "📌 هر کاربر در روز فقط **یک بار** می‌تواند **۱۰۰ لایک** سفارش دهد.\n"
                    text += "💰 هزینه: ۶ جم\n"
                    text += "⏳ بعد از خرید، تا فردا نمی‌توانید دوباره خرید کنید.\n\n"
                    text += "🔹 اگر VIP باشید، لایک‌ها بلافاصله واریز می‌شوند.\n"
                    text += "🔹 اگر عادی باشید، به صف اضافه می‌شوید و به ترتیب نوبت لایک دریافت می‌کنید.\n"
                    text += "🔹 برای مشاهده وضعیت نوبت، از دکمه «📍 وضعیت نوبت من» استفاده کنید.\n\n"
                    text += "🔹 اگر جم کافی ندارید، دوستان خود را دعوت کنید یا جوایز روزانه بگیرید."
                    send_message(chat_id, text, like_amount_menu())

                elif data == "like_100":
                    amount = 100
                    price = 6
                    if not user:
                        send_message(chat_id, "❌ لطفا /start رو بزن")
                        continue
                    today = datetime.now().strftime("%Y-%m-%d")
                    if user.get("last_like_date") == today:
                        send_message(chat_id, "⛔ **شما امروز ۱۰۰ لایک خود را خریداری کرده‌اید!**\n\n📊 ظرفیت: ۱۰۰/۱۰۰ پر شده است.\n🔄 فردا دوباره امتحان کنید.")
                        continue
                    score = user.get("score", 0)
                    if score >= price:
                        users[chat_id]["score"] -= price
                        users[chat_id]["last_like_date"] = today
                        save_users(users)
                        like_data[chat_id] = {"waiting_for_uid": True, "amount": amount}
                        send_message(chat_id, "📱 **آیدی اکانت فری فایر خود را ارسال کنید:**\n\nپس از تأیید، ۱۰۰ لایک به اکانت شما واریز خواهد شد.\n(فقط اعداد، بدون فاصله و حروف)\n\nمثال: 0946481846")
                    else:
                        send_message(chat_id, f"❌ **جم کافی نیست!**\n\n💎 جم شما: {score}\n💰 نیاز: {price} جم\n\nبرای خرید لایک به {price - score} جم دیگر نیاز دارید.\n\n👥 دوستان خود را دعوت کنید یا جوایز روزانه بگیرید!")

                elif data == "my_queue_status":
                    queue = users.get("like_queue", [])
                    position = None
                    for i, item in enumerate(queue, 1):
                        if item["chat_id"] == chat_id:
                            position = i
                            break
                    if position is None:
                        send_message(chat_id, "📍 **وضعیت نوبت شما**\n\nشما در صف نیستید.\nبرای قرار گرفتن در صف، از بخش فروشگاه لایک خریداری کنید.", like_amount_menu())
                    else:
                        send_message(chat_id, f"📍 **وضعیت نوبت شما**\n\nشماره نوبت شما: {position}\nتعداد افراد قبل از شما: {position - 1}\n\n⏳ لطفاً صبور باشید، به ترتیب نوبت لایک‌ها واریز می‌شود.", like_amount_menu())

                elif data == "admin_pending":
                    if not is_admin(chat_id):
                        send_message(chat_id, "❌ شما ادمین نیستید!")
                        continue
                    pending_list = users.get("pending_likes", [])
                    pending_count = len(pending_list)
                    if pending_count == 0:
                        send_message(chat_id, "💸 **واریزی**\n\n✅ هیچ درخواست تایید نشده‌ای وجود ندارد.\n📋 همه واریزی‌ها انجام شده‌اند.", [[{"text": "🔙 برگشت", "callback_data": "back_admin"}]])
                        continue
                    text = f"💸 **واریزی**\n\n📊 تعداد درخواست‌های تایید نشده: {pending_count}\n\n📋 لیست درخواست‌ها:\n\n"
                    for i, req in enumerate(pending_list, 1):
                        source_icon = "🤖" if req.get("source") == "auto" else "👤"
                        source_icon = "⏳" if req.get("source") == "queue" else source_icon
                        text += f"{i}. {source_icon} کاربر: `{req['chat_id']}` → {req['amount']} لایک\n"
                    text += "\n🔹 برای مشاهده و تایید، روی دکمه سفارش مورد نظر کلیک کنید:"
                    buttons = []
                    for i in range(1, pending_count + 1):
                        buttons.append([{"text": f"📋 سفارش {i}", "callback_data": f"admin_view_order_{i}"}])
                    buttons.append([{"text": "🔙 برگشت", "callback_data": "back_admin"}])
                    send_message(chat_id, text, buttons)

                elif data.startswith("admin_view_order_"):
                    if not is_admin(chat_id):
                        send_message(chat_id, "❌ شما ادمین نیستید!")
                        continue
                    index = int(data.split("_")[-1]) - 1
                    pending_list = users.get("pending_likes", [])
                    if index < 0 or index >= len(pending_list):
                        send_message(chat_id, "❌ سفارش یافت نشد!")
                        continue
                    req = pending_list[index]
                    admin_state[chat_id] = {"step": "admin_pending_confirm", "index": index}
                    source_text = "خودکار (VIP)" if req.get("source") == "auto" else "دستی"
                    source_text = "صف" if req.get("source") == "queue" else source_text
                    text = f"📋 **جزئیات سفارش {index + 1}:**\n\n"
                    text += f"👤 کاربر: `{req['chat_id']}`\n"
                    text += f"📱 UID: `{req['uid']}`\n"
                    text += f"📊 تعداد لایک: {req['amount']}\n"
                    text += f"💰 هزینه: {(req['amount'] // 100) * 6} جم\n"
                    text += f"📅 زمان: {req['time']}\n"
                    text += f"🔹 منبع: {source_text}\n"
                    keyboard = [[{"text": "✅ تایید واریز", "callback_data": "admin_confirm_like"}], [{"text": "🔙 برگشت به لیست", "callback_data": "admin_pending"}]]
                    send_message(chat_id, text, keyboard)

                elif data == "admin_confirm_like":
                    if not is_admin(chat_id):
                        send_message(chat_id, "❌ شما ادمین نیستید!")
                        continue
                    if chat_id not in admin_state or admin_state[chat_id].get("step") != "admin_pending_confirm":
                        send_message(chat_id, "❌ خطا! لطفاً دوباره از لیست واریزی انتخاب کنید.")
                        continue
                    index = admin_state[chat_id].get("index")
                    pending_list = users.get("pending_likes", [])
                    if index is None or index < 0 or index >= len(pending_list):
                        send_message(chat_id, "❌ درخواست یافت نشد!")
                        admin_state.pop(chat_id, None)
                        continue
                    req = pending_list[index]
                    chat_id_user = req['chat_id']
                    send_message(chat_id_user, f"✅ **لایک شما برای اکانتتون واریز شد!**\n\n📱 UID: {req['uid']}\n📊 تعداد لایک: {req['amount']}\n📅 زمان تایید: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n👍 لایک‌های شما با موفقیت واریز شد.")
                    remove_pending_like(index)
                    admin_state.pop(chat_id, None)
                    send_message(chat_id, "✅ **واریز تایید شد!**\n\nپیام به کاربر ارسال شد و درخواست از لیست حذف گردید.")
                    send_message(chat_id, "💸 **واریزی**\n\n📊 هیچ درخواست تایید نشده‌ای وجود ندارد.", [[{"text": "🔙 برگشت", "callback_data": "back_admin"}]])
                elif data == "admin_queue_manage":
                    if not is_admin(chat_id):
                        send_message(chat_id, "❌ شما ادمین نیستید!")
                        continue
                    queue = users.get("like_queue", [])
                    if not queue:
                        send_message(chat_id, "📋 **مدیریت صف**\n\n✅ صف خالی است.", [[{"text": "🔙 برگشت", "callback_data": "back_admin"}]])
                        continue
                    text = f"📋 **مدیریت صف**\n\n👥 تعداد افراد در صف: {len(queue)}\n\n📋 لیست افراد در صف:\n\n"
                    for i, item in enumerate(queue, 1):
                        text += f"{i}. کاربر: `{item['chat_id']}` | UID: {item['uid']} | زمان: {item['time']}\n"
                    text += "\n🔹 برای مشاهده و حذف یک فرد از صف، روی دکمه مربوطه کلیک کنید:"
                    buttons = []
                    max_display = min(len(queue), 3)
                    for i in range(1, max_display + 1):
                        buttons.append([{"text": f"👤 کاربر {i}", "callback_data": f"admin_queue_view_{i}"}])
                    buttons.append([{"text": "🗑 حذف همه", "callback_data": "admin_queue_clear"}])
                    buttons.append([{"text": "🔙 برگشت", "callback_data": "back_admin"}])
                    send_message(chat_id, text, buttons)

                elif data.startswith("admin_queue_view_"):
                    if not is_admin(chat_id):
                        send_message(chat_id, "❌ شما ادمین نیستید!")
                        continue
                    index = int(data.split("_")[-1]) - 1
                    queue = users.get("like_queue", [])
                    if index < 0 or index >= len(queue):
                        send_message(chat_id, "❌ کاربر در صف یافت نشد!")
                        continue
                    item = queue[index]
                    text = f"📋 **جزئیات فرد {index + 1} در صف:**\n\n"
                    text += f"👤 کاربر: `{item['chat_id']}`\n"
                    text += f"📱 UID: {item['uid']}\n"
                    text += f"📊 تعداد لایک: {item['amount']}\n"
                    text += f"📅 زمان ثبت: {item['time']}\n"
                    keyboard = [[{"text": "🗑 حذف از صف", "callback_data": f"admin_queue_remove_{index}"}], [{"text": "🔙 برگشت به لیست", "callback_data": "admin_queue_manage"}]]
                    send_message(chat_id, text, keyboard)

                elif data.startswith("admin_queue_remove_"):
                    if not is_admin(chat_id):
                        send_message(chat_id, "❌ شما ادمین نیستید!")
                        continue
                    index = int(data.split("_")[-1])
                    queue = users.get("like_queue", [])
                    if index < 0 or index >= len(queue):
                        send_message(chat_id, "❌ کاربر در صف یافت نشد!")
                        continue
                    removed = queue.pop(index)
                    users["like_queue"] = queue
                    save_users(users)
                    send_message(chat_id, f"✅ کاربر `{removed['chat_id']}` از صف حذف شد.")
                    send_message(chat_id, "📋 **مدیریت صف**", admin_menu())

                elif data == "admin_queue_clear":
                    if not is_admin(chat_id):
                        send_message(chat_id, "❌ شما ادمین نیستید!")
                        continue
                    users["like_queue"] = []
                    save_users(users)
                    send_message(chat_id, "✅ کل صف پاک شد.")
                    send_message(chat_id, "📋 **مدیریت صف**", admin_menu())

                elif data == "admin_activity":
                    if not is_admin(chat_id):
                        send_message(chat_id, "❌ شما ادمین نیستید!")
                        continue
                    activity_list = []
                    for uid, info in users.items():
                        if uid in SPECIAL_KEYS or not isinstance(info, dict):
                            continue
                        msg_count = info.get("msg_count", 0)
                        if msg_count > 0:
                            name = info.get("display_name") or info.get("username") or uid
                            activity_list.append({"id": uid, "name": name, "count": msg_count})
                    if not activity_list:
                        send_message(chat_id, "📊 **فعالیت کاربران**\n\nهیچ فعالیتی ثبت نشده است.")
                        continue
                    activity_list.sort(key=lambda x: x["count"], reverse=True)
                    top_activity = activity_list[:10]
                    text = "📊 **فعالیت کاربران (بیشترین پیام‌ها)**\n\n"
                    medals = ["🥇", "🥈", "🥉"]
                    for i, user in enumerate(top_activity, 1):
                        medal = medals[i-1] if i <= 3 else f"{i}."
                        text += f"{medal} `{user['name']}` → {user['count']} پیام\n"
                    send_message(chat_id, text, [[{"text": "🔙 برگشت", "callback_data": "back_admin"}]])

                elif data == "my_score":
                    score = user.get("score", 0)
                    invites = user.get("invites", 0)
                    display_name = user.get("display_name", "ناشناس")
                    vip_icon = get_vip_icon(chat_id)
                    vip_status = "فعال ✅" if is_vip_active(chat_id) else "غیرفعال ❌"
                    vip_level = user.get("vip_level", "ندارد")
                    vip_level_names = {"silver": "نقره‌ای", "gold": "طلایی", "crystal": "کریستالی", "none": "ندارد"}
                    vip_level_name = vip_level_names.get(vip_level, "ندارد")
                    text = f"💎 **حساب من**\n\n"
                    text += f"👤 نام: {display_name} {vip_icon}\n"
                    text += f"💎 جم: {score}\n"
                    text += f"👥 دعوت‌ها: {invites}\n"
                    text += f"🎁 جایزه روزانه = ۱ جم\n"
                    text += f"👑 VIP: {vip_level_name} ({vip_status})"
                    send_message(chat_id, text, my_score_menu())

                elif data == "change_name":
                    score = user.get("score", 0)
                    if score < 1:
                        send_message(chat_id, "❌ **جم کافی نیست!**\n\nبرای تغییر نام به ۱ جم نیاز دارید.\n💎 جم شما: " + str(score))
                        send_message(chat_id, "💎 **حساب من**", my_score_menu())
                        continue
                    name_change_state[chat_id] = "waiting_for_name"
                    send_message(chat_id, "✏️ **تغییر نام**\n\nلطفاً نام جدید خود را وارد کنید:\n\n(هزینه: ۱ جم)\n\n📌 **قوانین:**\n• حداقل ۳ حرف\n• حداکثر ۱۵ حرف\n• فقط حروف انگلیسی و اعداد\n• بدون فاصله و علامت")
                    continue

                elif data == "my_progress":
                    score = user.get("score", 0)
                    invites = user.get("invites", 0)
                    daily_claim = user.get("daily_claim")
                    streak = 0
                    if daily_claim:
                        try:
                            if datetime.fromisoformat(daily_claim).date() == datetime.now().date():
                                streak = 1
                        except:
                            pass
                    level = "💎 الماس" if score >= 300 else "🥇 طلایی" if score >= 150 else "🥈 نقره‌ای" if score >= 50 else "🥉 برنزی"
                    text = f"📊 **آمار پیشرفت شما**\n\n"
                    text += f"💎 جم کل: {score}\n"
                    text += f"👥 دعوت‌ها: {invites}\n"
                    text += f"📅 روزهای متوالی: {streak} روز\n"
                    text += f"🏅 سطح شما: {level}\n"
                    send_message(chat_id, text)

                elif data == "my_invite_link":
                    invite_link = "https://ble.ir/blackfire_bot?start=" + chat_id
                    send_message(chat_id, f"🔗 **لینک دعوت شما**\n\n{invite_link}\n\n🌟 هر دعوت موفق = ۱ جم\n👥 تعداد دعوت‌ها: {user.get('invites', 0)}")

                elif data == "notification_settings":
                    status = "فعال" if user.get("notifications", True) else "غیرفعال"
                    keyboard = [[{"text": "✅ فعال کردن اعلان", "callback_data": "notif_on"}], [{"text": "❌ غیرفعال کردن اعلان", "callback_data": "notif_off"}], [{"text": "🔙 برگشت", "callback_data": "my_score"}]]
                    send_message(chat_id, f"🔔 **تنظیمات اعلان**\n\nوضعیت فعلی: {status}\n\nشما می‌توانید اعلان‌های ربات را فعال یا غیرفعال کنید.", keyboard)

                elif data == "notif_on":
                    users[chat_id]["notifications"] = True
                    save_users(users)
                    send_message(chat_id, "✅ **اعلان‌ها فعال شدند!**")
                    send_message(chat_id, "💎 **حساب من**", my_score_menu())

                elif data == "notif_off":
                    users[chat_id]["notifications"] = False
                    save_users(users)
                    send_message(chat_id, "❌ **اعلان‌ها غیرفعال شدند!**")
                    send_message(chat_id, "💎 **حساب من**", my_score_menu())

                elif data == "get_sens":
                    score = user.get("score", 0)
                    price = SENS_PRICE
                    if is_vip_active(chat_id) and user.get("vip_level") == "crystal":
                        price = 1
                    text = f"🇧🇷 **خرید سنس Xiaomi** 🇧🇷\nمخصوص : Xiaomi \n\n💰 قیمت: {price} جم\n💎 جم شما: {score}\n\nآیا می‌خواهید سنس Xiaomi 🇧🇷 را خریداری کنید؟"
                    send_message(chat_id, text, [[{"text": "خرید ✅", "callback_data": "confirm_buy_sens"}], [{"text": "🔙 برگشت", "callback_data": "back_main"}]])

                elif data == "confirm_buy_sens":
                    if not user:
                        send_message(chat_id, "❌ لطفا /start رو بزن")
                        continue
                    price = SENS_PRICE
                    if is_vip_active(chat_id) and user.get("vip_level") == "crystal":
                        price = 1
                    score = user.get("score", 0)
                    if score >= price:
                        users[chat_id]["score"] -= price
                        save_users(users)
                        new_score = users[chat_id]["score"]
                        caption = "*🇧🇷 سنس Xiaomi ویژه 🇧🇷*\n\n📱مدل گوشی: Xiaomi \n\n💠 دی پی ای: 487\n\n🎯دکمه تیر: 50\n\n⚠️ هشدار:\nتغییر DPI توصیه نمی‌شود\nزیرا در طولانی مدت ممکن است\nباعث کندی موبایل شما بشود 🛑\n\n💎 جم فعلی شما: " + str(new_score)
                        send_photo(chat_id, PHOTO_URL, caption, [[{"text": "🔙 برگشت به منو", "callback_data": "back_main"}]])
                    else:
                        send_message(chat_id, f"❌ **جم کافی نیست!**\n\n💎 جم شما: {score}\n💰 قیمت: {price} جم\n\nبرای خرید سنس به {price - score} جم دیگر نیاز دارید.", main_menu())

                elif data == "get_sens_redmi":
                    score = user.get("score", 0)
                    price = SENS_PRICE
                    if is_vip_active(chat_id) and user.get("vip_level") == "crystal":
                        price = 1
                    text = f"🇧🇷 **خرید سنس Redmi not 12** 🇧🇷\nمخصوص : Redmi not 12 \n\n💰 قیمت: {price} جم\n💎 جم شما: {score}\n\nآیا می‌خواهید سنس Redmi not 12 🇧🇷 را خریداری کنید؟"
                    send_message(chat_id, text, [[{"text": "خرید ✅", "callback_data": "confirm_buy_sens_redmi"}], [{"text": "🔙 برگشت", "callback_data": "back_main"}]])

                elif data == "confirm_buy_sens_redmi":
                    if not user:
                        send_message(chat_id, "❌ لطفا /start رو بزن")
                        continue
                    price = SENS_PRICE
                    if is_vip_active(chat_id) and user.get("vip_level") == "crystal":
                        price = 1
                    score = user.get("score", 0)
                    if score >= price:
                        users[chat_id]["score"] -= price
                        save_users(users)
                        new_score = users[chat_id]["score"]
                        caption = "*🇧🇷 سنس redmi not 12 ویژه 🇧🇷*\n\n📱مدل گوشی: redmi not 12 \n\n💠دی پی ای: 411\n\n🎯دکمه تیر: 50\n\n⚠️ هشدار:\nتغییر DPI توصیه نمی‌شود\nزیرا در طولانی مدت ممکن است\nباعث کندی موبایل شما بشود 🛑\n\n💎 جم فعلی شما: " + str(new_score)
                        send_photo(chat_id, PHOTO_URL, caption, [[{"text": "🔙 برگشت به منو", "callback_data": "back_main"}]])
                    else:
                        send_message(chat_id, f"❌ **جم کافی نیست!**\n\n💎 جم شما: {score}\n💰 قیمت: {price} جم\n\nبرای خرید سنس به {price - score} جم دیگر نیاز دارید.", main_menu())

                elif data == "get_panel":
                    score = user.get("score", 0)
                    price = PANEL_PRICE
                    if is_vip_active(chat_id) and user.get("vip_level") == "crystal":
                        price = 1
                    text = f"⚡️ **پنل سنس** ⚡️\n\n📱 توضیحات: در این برنامه تمام سنس گوشی ها با بالاترین کیفیت هست 📱🔱\n\n💰 قیمت: {price} جم\n💎 جم شما: {score}\n\nآیا میخواهید ⚡️ پنل سنس ⚡️ را خریداری کنید؟"
                    send_message(chat_id, text, [[{"text": "خرید ✅", "callback_data": "confirm_buy_panel"}], [{"text": "🔙 برگشت", "callback_data": "back_main"}]])

                elif data == "confirm_buy_panel":
                    if not user:
                        send_message(chat_id, "❌ لطفا /start رو بزن")
                        continue
                    price = PANEL_PRICE
                    if is_vip_active(chat_id) and user.get("vip_level") == "crystal":
                        price = 1
                    score = user.get("score", 0)
                    if score >= price:
                        users[chat_id]["score"] -= price
                        save_users(users)
                        new_score = users[chat_id]["score"]
                        text = "✅ **خرید موفق!** 🎉\n\n⚡️ **پنل سنس** ⚡️\n\n📥 **لینک دانلود:**\n🔗 https://apkpure-com.cdn.ampproject.org/v/s/apkpure.com/fa/sensi-master/com.allakore.sensimasterff/amp?amp_gsa=1&amp_js_v=a9&usqp=mq331AQIUAKwASCAAgM%3D#amp_tf=%D8%A7%D8%B2%20%251%24s&aoh=17836942945219&csi=1&referrer=https%3A%2F%2Fwww.google.com&ampshare=https%3A%2F%2Fapkpure.com%2Ffa%2Fsensi-master%2Fcom.allakore.sensimasterff\n\n💎 **جم فعلی شما:** " + str(new_score)
                        send_message(chat_id, text, [[{"text": "🔙 برگشت به منو", "callback_data": "back_main"}]])
                    else:
                        send_message(chat_id, f"❌ **جم کافی نیست!**\n\n💎 جم شما: {score}\n💰 قیمت: {price} جم\n\nبرای خرید پنل به {price - score} جم دیگر نیاز دارید.", main_menu())

                elif data == "invite":
                    invite_link = "https://ble.ir/blackfire_bot?start=" + chat_id
                    send_message(chat_id, "*👥 لینک دعوت شما*\n\n" + invite_link + "\n\n🌟 هر دعوت موفق = ۱ جم")

                elif data == "daily":
                    if not user:
                        send_message(chat_id, "❌ لطفا /start رو بزن")
                        continue
                    last_claim = user.get("daily_claim")
                    remaining_text, remaining_hours = get_time_remaining(last_claim)
                    if remaining_text is None:
                        users[chat_id]["score"] += 1
                        users[chat_id]["daily_claim"] = datetime.now().isoformat()
                        save_users(users)
                        send_message(chat_id, "🎁 *جایزه روزانه دریافت شد!*\n\n✨ +۱ جم به حساب شما اضافه شد.\n\n⏰ ۲۴ ساعت دیگه دوباره می‌تونی بگیری!")
                    else:
                        send_message(chat_id, f"⏳ *صبر کن!*\n\nتو امروز جایزه روزانه رو گرفتی!\n\n📅 زمان باقی‌مونده:\n⏰ {remaining_text}\n\n🔄 بعد از {remaining_hours} ساعت دوباره بیا!")

                elif data == "leaderboard":
                    users_list = []
                    for uid, info in users.items():
                        if uid in SPECIAL_KEYS or info.get("is_banned", False) or info.get("score", 0) <= 0:
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
                    top_users = users_list[:10]
                    if not top_users:
                        text = "🏆 لیـدربـرد بــرتــریـن‌ها 🎖\n\nهیچ کاربری وجود ندارد!"
                    else:
                        text = "🏆 لیـدربـرد بــرتــریـن‌ها 🎖\n\n"
                        circle_numbers = ["④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"]
                        for i, user in enumerate(top_users, 1):
                            if i == 1:
                                medal = "🥇"
                            elif i == 2:
                                medal = "🥈"
                            elif i == 3:
                                medal = "🥉"
                            else:
                                medal = circle_numbers[i-4] if i-4 < len(circle_numbers) else f"{i}."
                            name = user.get("display_name")
                            if not name:
                                name = user.get("username")
                            if not name or name == "/start":
                                name = "ناشناس"
                            vip_icon = ""
                            vip_label = ""
                            if user.get("vip_level") in ["silver", "gold", "crystal"] and user.get("vip_expiry"):
                                try:
                                    if datetime.now() < datetime.fromisoformat(user["vip_expiry"]):
                                        if user["vip_level"] == "silver":
                                            vip_icon = "⚙️"
                                            vip_label = "VIP⚙️"
                                        elif user["vip_level"] == "gold":
                                            vip_icon = "👑"
                                            vip_label = "VIP👑"
                                        elif user["vip_level"] == "crystal":
                                            vip_icon = "💎"
                                            vip_label = "VIP💎"
                                except:
                                    pass
                            if i <= 3:
                                if vip_label:
                                    line = f"{medal} {vip_label} {name} {vip_icon} ⇐ جم💎 {user['score']}"
                                else:
                                    line = f"{medal} {name} ⇐ جم💎 {user['score']}"
                            else:
                                if vip_label:
                                    line = f"{medal} {vip_label} {name} {vip_icon} ⇐ جم💎 {user['score']}"
                                else:
                                    line = f"{medal} {name} ⇐ جم💎 {user['score']}"
                            text += line + "\n"
                            if i == 3:
                                text += "____________________________________\n"
                    send_message(chat_id, text)

                elif data == "admin_giftcode":
                    if not is_admin(chat_id):
                        send_message(chat_id, "❌ شما ادمین نیستید!")
                        continue
                    admin_state[chat_id] = {"step": "waiting_for_code_uses"}
                    send_message(chat_id, "🎁 **ساخت کد هدیه**\n\nلطفاً تعداد دفعاتی که این کد قابل استفاده است را وارد کنید:\n(مثلاً ۱۰ یا ۵۰)")

                if data.startswith("admin_"):
                    if not is_admin(chat_id):
                        send_message(chat_id, "❌ شما ادمین نیستید!")
                        continue
                    if data == "admin_add":
                        send_message(chat_id, "➕ **افزودن جم**\n\nبه این شکل پیام بفرست:\n`add USER_ID مقدار`\n\nمثال:\n`add 459299490 10`")
                    elif data == "admin_remove":
                        send_message(chat_id, "➖ **کم کردن جم**\n\nبه این شکل پیام بفرست:\n`remove USER_ID مقدار`\n\nمثال:\n`remove 459299490 5`")
                    elif data == "admin_ban":
                        send_message(chat_id, "🚫 **بن کاربر**\n\nبه این شکل پیام بفرست:\n`ban USER_ID`\n\nمثال:\n`ban 459299490`")
                    elif data == "admin_unban":
                        send_message(chat_id, "✅ **آنبن کاربر**\n\nبه این شکل پیام بفرست:\n`unban USER_ID`\n\nمثال:\n`unban 459299490`")
                    elif data == "admin_list":
                        if not users:
                            send_message(chat_id, "📋 هیچ کاربری ثبت نشده!")
                        else:
                            text = "📋 **لیست کاربران:**\n\n"
                            cnt = 0
                            for uid, info in users.items():
                                if uid in SPECIAL_KEYS:
                                    continue
                                cnt += 1
                                if cnt > 20:
                                    break
                                name = info.get("display_name") or info.get("username") or uid
                                vip_icon = ""
                                if info.get("vip_level") in ["silver", "gold", "crystal"] and info.get("vip_expiry"):
                                    try:
                                        if datetime.now() < datetime.fromisoformat(info["vip_expiry"]):
                                            vip_icon = "⚙️" if info["vip_level"] == "silver" else "👑" if info["vip_level"] == "gold" else "💎"
                                    except:
                                        pass
                                status = "🚫" if info.get("is_banned", False) else "✅"
                                text += f"{cnt}. `{name}` {vip_icon} → 💎{info.get('score',0)} {status}\n"
                            if len(users) > 20:
                                text += f"\n... و {len(users)-20} کاربر دیگر"
                            send_message(chat_id, text)
                    elif data == "admin_stats":
                        total = 0
                        total_score = 0
                        banned = 0
                        total_invites = 0
                        vip_count = {"silver": 0, "gold": 0, "crystal": 0}
                        for uid, info in users.items():
                            if uid in SPECIAL_KEYS:
                                continue
                            total += 1
                            total_score += info.get("score", 0)
                            if info.get("is_banned", False):
                                banned += 1
                            total_invites += info.get("invites", 0)
                            level = info.get("vip_level", "none")
                            if level in vip_count and info.get("vip_expiry"):
                                try:
                                    if datetime.now() < datetime.fromisoformat(info["vip_expiry"]):
                                        vip_count[level] += 1
                                except:
                                    pass
                        text = f"📊 **آمار کل ربات:**\n\n"
                        text += f"👥 کل کاربران: {total}\n"
                        text += f"💎 کل جم‌ها: {total_score}\n"
                        text += f"👥 کل دعوت‌ها: {total_invites}\n"
                        text += f"🚫 کاربران بن شده: {banned}\n"
                        text += f"\n👑 **VIP:**\n"
                        text += f"⚙️ نقره‌ای: {vip_count['silver']}\n"
                        text += f"👑 طلایی: {vip_count['gold']}\n"
                        text += f"💎 کریستالی: {vip_count['crystal']}"
                        send_message(chat_id, text)
                    elif data == "admin_broadcast":
                        send_message(chat_id, "📢 **پیام همگانی**\n\nآیا می‌خواهید به تمام کاربران پیام ارسال کنید؟\n\n👥 تعداد کاربران: " + str(len([k for k in users.keys() if k not in SPECIAL_KEYS])), broadcast_confirm_menu())

                elif data == "broadcast_confirm":
                    if not is_admin(chat_id):
                        send_message(chat_id, "❌ شما ادمین نیستید!")
                        continue
                    broadcast_data[chat_id] = "waiting_for_message"
                    send_message(chat_id, "📝 **پیام خود را ارسال کنید:**\n\nهر متنی که بفرستید، به تمام کاربران ارسال خواهد شد.\n\n🔹 می‌توانید متن، لینک یا هر چیزی بفرستید.\n🔹 برای لغو، دکمه زیر را بزنید.", [[{"text": "❌ لغو", "callback_data": "cancel_broadcast"}]])
                elif data == "cancel_broadcast":
                    if not is_admin(chat_id):
                        continue
                    broadcast_data.pop(chat_id, None)
                    send_message(chat_id, "❌ **پیام همگانی لغو شد!**")
                    send_message(chat_id, "👑 **پنل مدیریت** 👑\n\nیک گزینه را انتخاب کنید:", admin_menu())
                elif data == "back_admin":
                    if not is_admin(chat_id):
                        send_message(chat_id, "❌ شما ادمین نیستید!")
                        continue
                    admin_state.pop(chat_id, None)
                    send_message(chat_id, "👑 **پنل مدیریت** 👑\n\nیک گزینه را انتخاب کنید:", admin_menu())
                elif data == "redeem_code":
                    send_message(chat_id, "🎫 **وارد کردن کد هدیه**\n\nلطفاً کد خود را به این شکل وارد کنید:\n\n`/redeem کد`\n\nمثال: `/redeem ABC12345`")
                elif data == "help":
                    send_message(chat_id, "*📖 راهنمای 𝗕𝗹𝗮𝗰𝗸 𝗙𝗶𝗿𝗲*\n\nگزینه مورد نظر خود را انتخاب کنید :", help_menu())
                elif data == "help_sens":
                    send_message(chat_id, "*💡 دریافت سنس و پنل*\n\nبا جمع کردن جم میتوانید سنس، پنل و سایر امکانات بازی را رایگان دریافت کنید.\n\nحتی امکان خرید سنس و پنل‌های پولی نیز وجود دارد.\n\nسنس‌های رایگان بدون جم هم منتشر می‌شوند، اما سنس‌ها و پنل‌های جمی ارزش و تأثیر بیشتری داشته و درصد هد بالاتری دارند.\n\n📞 برای خرید نسخه پولی به پشتیبانی پیام دهید.")
                elif data == "help_score":
                    send_message(chat_id, "*💎 جم‌ها 💎*\n\nبرای گرفتن سنس و پنل می‌توانید جم جمع کنید.\n\nلینک اختصاصی خود را برای دوستانتان ارسال کنید.\n\n🌟 به ازای هر دعوت موفق، ۱ جم دریافت خواهید کرد.\n🎁 هر روز ۱ جم رایگان بگیر!")
                elif data == "help_ban":
                    send_message(chat_id, "*😰 آیا اکانت بن می‌شود؟*\n\n❌ سنس در بازی تقلب محسوب نمی‌شود و بن یا بلک‌لیست ندارد.\n\n⚠️ اما پنل تقلب محسوب می‌شود و هرچه قوی‌تر باشد، احتمال بن یا بلک‌لیست شدن بیشتر است.\n\n❕ اگر اکانت شما ارزش دارد، بهتر است از پنل استفاده نکنید یا از اکانت فیک استفاده کنید.")
                elif data == "back_main":
                    admin_state.pop(chat_id, None)
                    send_message(chat_id, "*🏠 منوی اصلی*", main_menu())

        time.sleep(1)

    except Exception as e:
        print(f"❌ خطای اصلی: {e}")
        time.sleep(5)