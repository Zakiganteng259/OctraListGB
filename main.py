from server import keep_alive
keep_alive()

from aiogram import Bot, Dispatcher, executor, types
import logging
import asyncio
import datetime
import json
import os
import re

from pytz import timezone
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage

API_TOKEN = "7578453657:AAGh3wqrRpF08jSVg-XuresC0wv7PT0wwKI"
GROUP_ID = -1002594759934

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

DATA_FILE = "data.json"
STARTED_FILE = "started.json"
USER_BASE_FILE = "user_base.json"

user_data = {}
user_base = {}
started_users = set()
jakarta = timezone("Asia/Jakarta")

def load_json(file, default):
    if os.path.exists(file):
        try:
            with open(file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.warning(f"File rusak: {file}, me-reset data.")
            return default
    return default

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

def load_user_data():
    global user_data
    user_data.update(load_json(DATA_FILE, {}))

def save_user_data():
    save_json(DATA_FILE, user_data)

def load_user_base():
    global user_base
    user_base.update(load_json(USER_BASE_FILE, {}))

def save_user_base():
    save_json(USER_BASE_FILE, user_base)

def load_started_users():
    global started_users
    started_users.update(load_json(STARTED_FILE, []))

def save_started_users():
    save_json(STARTED_FILE, list(started_users))

load_user_data()
load_user_base()
load_started_users()

def get_main_keyboard():
    now_jakarta = datetime.datetime.now(jakarta)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(f"⚡ Join List GB {now_jakarta:%d-%m-%Y} ⚡", callback_data="join_list")],
        [InlineKeyboardButton("🔥 List Multisend", callback_data="multisend_list"),
         InlineKeyboardButton("❄️ List Private Transfer", callback_data="private_list")],
    ])

def get_back_edit_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✏️ Edit Address", callback_data="edit_address")],
        [InlineKeyboardButton("🗑 Hapus Address", callback_data="delete_address")],
        [InlineKeyboardButton("⬅️ Kembali", callback_data="back_home")],
    ])

def format_multisend():
    if not user_data:
        return "🔥 <b>List Multisend kosong</b>"
    result = []
    for user_id, data in user_data.items():
        if data.get("multisend"):
            result.append(f"@{data['username']} 🔥")
            for addr in data["multisend"]:
                result.append(f"<code>{addr} 1</code>")
    return "\n".join(result)

def format_private():
    if not user_data:
        return "❄️ <b>List Private Transfer kosong</b>"
    result = []
    for user_id, data in user_data.items():
        if data.get("private"):
            result.append(f"@{data['username']} ❄️")
            for addr in data["private"]:
                result.append(f"<code>{addr}</code>")
    return "\n".join(result)

async def auto_reset():
    while True:
        now = datetime.datetime.now(jakarta)
        next_reset = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
        sleep_seconds = (next_reset - now).total_seconds()

        print(f"[AUTO RESET] Menunggu hingga 00:00 WIB ({sleep_seconds:.0f} detik)...")
        await asyncio.sleep(sleep_seconds)

        user_data.clear()
        save_user_data()

        try:
            await bot.send_message(
                GROUP_ID,
                f"♻️ <b>List berhasil direset</b> ({datetime.datetime.now(jakarta):%d-%m-%Y %H:%M})",
                reply_markup=get_main_keyboard()
            )
        except Exception as e:
            logging.error(f"Gagal kirim reset: {e}")

@dp.message_handler(commands=["start", "join"])
async def handle_start_or_join(message: types.Message):
    started_users.add(message.from_user.id)
    save_started_users()

    menu_msg = await message.answer("Jangan lupa GB cuy👇😎", reply_markup=get_main_keyboard())
    await asyncio.sleep(10)
    try: await bot.delete_message(message.chat.id, message.message_id)
    except: pass

@dp.message_handler(commands=['menu'])
async def show_menu(message: types.Message):
    menu_msg = await message.answer("Ini menu kamu", reply_markup=get_main_keyboard())

    async def auto_delete():
        await asyncio.sleep(3590)  # 1 jam = 3600 detik (kamu bisa ubah sesuai kebutuhan)
        try:
            await bot.delete_message(menu_msg.chat.id, menu_msg.message_id)
        except:
            pass

    asyncio.create_task(auto_delete())  # ← ini yang penting agar jalan di background

    asyncio.create_task(auto_delete())  # ← JALAN di background

@dp.callback_query_handler(lambda c: c.data == "join_list")
async def join_list(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    username = callback.from_user.username or "unknown"

    if callback.from_user.id not in started_users:
        await callback.answer("🚫 Ketik /start dulu ya cuy lalu klik tombolnya lagi 😎👍", show_alert=True)
        return

    if user_id in user_data:
        await bot.send_message(
            chat_id=callback.from_user.id,
            text="✅ Kamu sudah bergabung hari ini!🫡\n\nSilahkan cek fitur multisend dan private transfer untuk melihat daftar address.\n\nGunakan tombol edit address jika ingin mengubah.",
            reply_markup=get_back_edit_keyboard()
        )
    elif user_id in user_base:
        user_data[user_id] = user_base[user_id]
        save_user_data()
        await bot.send_message(
            chat_id=callback.from_user.id,
            text="🎉 Address kamu otomatis dimasukkan dari data kemarin!\n\nCek menu untuk melihat status kamu sekarang.",
            reply_markup=get_back_edit_keyboard()
        )
    else:
        await bot.send_message(
            chat_id=callback.from_user.id,
            text="📩 Hai! Kamu belum mengisi address.\n\nSilakan kirim address kamu untuk join list GB👇"
        )
    await callback.answer()

@dp.message_handler(lambda m: m.text and any(line.startswith("oct") for line in m.text.splitlines()))
async def receive_address(message: types.Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or "unknown"

    addresses = [line.strip() for line in message.text.strip().splitlines() if line.startswith("oct")]
    if not addresses:
        return

    if user_id not in user_data:
        user_data[user_id] = {
            "username": username,
            "address": [],
            "multisend": [],
            "private": [],
            "joined_today": False
        }

    existing = set(user_data[user_id]["address"])
    new_addresses = [addr for addr in addresses if addr not in existing]

    user_data[user_id]["address"].extend(new_addresses)
    user_data[user_id]["address"] = list(set(user_data[user_id]["address"]))

    # Tambahkan ke multisend dan private
    user_data[user_id]["multisend"] = user_data[user_id]["address"]
    user_data[user_id]["private"] = user_data[user_id]["address"]

    user_base[user_id] = user_data[user_id]
    started_users.add(message.from_user.id)

    save_user_base()
    save_user_data()
    save_started_users()

    if message.chat.type in ["group", "supergroup"]:
        try:
            await bot.send_message(
                message.from_user.id,
                "✅ Address kamu sudah disimpan!\n\nHoree...🥳 kamu sudah terdaftar di list GB octra\n\nBesok cukup klik tombol di grup, tanpa isi address lagi."
            )
        except:
            pass
        return

    await message.reply("✅ Address kamu sudah disimpan!\n\nHoree...🥳 kamu sudah terdaftar di list GB octra\n\nBesok cukup klik tombol di grup, tanpa isi address lagi.")

@dp.callback_query_handler(lambda c: c.data == "multisend_list")
async def show_multisend(callback: types.CallbackQuery):
    msg = await callback.message.answer(format_multisend(), reply_markup=get_back_edit_keyboard())
    await callback.answer()
    await asyncio.sleep(20)
    try: await msg.delete()
    except: pass

@dp.callback_query_handler(lambda c: c.data == "private_list")
async def show_private(callback: types.CallbackQuery):
    msg = await callback.message.answer(format_private(), reply_markup=get_back_edit_keyboard())
    await callback.answer()
    await asyncio.sleep(20)
    try: await msg.delete()
    except: pass

@dp.callback_query_handler(lambda c: c.data == "back_home")
async def back_home(callback: types.CallbackQuery):
    try: await callback.message.delete()
    except: pass
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "edit_address")
async def edit_address(callback: types.CallbackQuery):
    await bot.send_message(callback.from_user.id, "✏️ Masukkan address baru:")
    await callback.answer("Silakan kirim address baru lewat DM.")

@dp.callback_query_handler(lambda c: c.data == "delete_address")
async def delete_address(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    user_data.pop(user_id, None)
    user_base.pop(user_id, None)
    save_user_data()
    save_user_base()
    await bot.send_message(callback.from_user.id, "❌ Address kamu telah dihapus dari list.")
    await callback.answer("Address dihapus.")

@dp.message_handler(lambda m: m.chat.id == GROUP_ID and re.search(r"oct[a-zA-Z0-9]{5,}", m.text, re.IGNORECASE))
async def handle_address_from_group(message: types.Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or "unknown"

    matches = re.findall(r"(oct[a-zA-Z0-9]{5,})", message.text, re.IGNORECASE)
    if not matches:
        return

    address = matches[0]
    user_data[user_id] = {"username": username, "address": address}
    user_base[user_id] = {"username": username, "address": address}
    save_user_data()
    save_user_base()

    try:
        reply_msg = await message.reply("✅ Address kamu disimpan, ketik /start agar bisa buka menu multisend & private transfer 🥳")
        await asyncio.sleep(15)
        await reply_msg.delete()
    except Exception as e:
        logging.warning(f"Gagal balas di grup: {e}")

    if message.from_user.id in started_users:
        try:
            await bot.send_message(
                chat_id=message.from_user.id,
                text="✅ Address kamu berhasil disimpan otomatis!\nKamu sudah masuk list GB hari ini 🎉\n\nGunakan menu untuk cek multisend & private transfer."
            )
        except Exception as e:
            logging.warning(f"Gagal kirim DM: {e}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(auto_reset())
    executor.start_polling(dp, skip_updates=True)
