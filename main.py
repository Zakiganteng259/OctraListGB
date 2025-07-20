import json
import os
import asyncio
from datetime import datetime, timedelta
import pytz
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

TOKEN = "7578453657:AAGh3wqrRpF08jSVg-XuresC0wv7PT0wwKI"
GROUP_ID = -4979227512

DATA_FILE = "user_data.json"
STARTED_FILE = "started_users.json"
USER_BASE_FILE = "user_base.json"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Pastikan semua file JSON ada
for file, default in [
    (DATA_FILE, {}),
    (STARTED_FILE, []),
    (USER_BASE_FILE, {}),
]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump(default, f)

def load_json(filename, default):
    if not os.path.exists(filename):
        return default
    with open(filename, "r") as f:
        try:
            return json.load(f)
        except:
            return default

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

user_data = load_json(DATA_FILE, {})
started_users = load_json(STARTED_FILE, [])
user_base = load_json(USER_BASE_FILE, {})

# Tombol utama
def get_main_keyboard():
    return InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("🚀 Join List GB", callback_data="join_list"),
        InlineKeyboardButton("📤 Multisend", callback_data="multisend"),
        InlineKeyboardButton("📥 Private Transfer", callback_data="private_transfer"),
        InlineKeyboardButton("✏️ Edit", callback_data="edit_address"),
        InlineKeyboardButton("🗑️ Delete", callback_data="delete_address"),
    )

# Handler /start
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or "unknown"
    if user_id not in started_users:
        started_users.append(user_id)
        save_json(STARTED_FILE, started_users)
    await message.answer(f"👋 Hi @{username}! Silakan pilih opsi di bawah:", reply_markup=get_main_keyboard())

# Callback: Join List
@dp.callback_query_handler(lambda c: c.data == "join_list")
async def cb_join(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    username = callback.from_user.username or "unknown"

    if user_id not in user_base or not user_base[user_id]:
        await callback.message.edit_text("📥 Kirim address kamu (boleh banyak, pisahkan per baris):")
        user_data[user_id] = {"step": "awaiting_address"}
        save_json(DATA_FILE, user_data)
        return

    if user_id not in user_data:
        user_data[user_id] = {
            "address": user_base[user_id],
            "multisend": [],
            "private": [],
            "joined_today": True
        }
    else:
        user_data[user_id]["address"] = user_base[user_id]
        user_data[user_id]["joined_today"] = True
        user_data[user_id]["multisend"] = []
        user_data[user_id]["private"] = []

    save_json(DATA_FILE, user_data)

    formatted = "\n".join(f"oct... {i+1}" for i in range(len(user_base[user_id])))
    await callback.message.edit_text(f"✅ Joined with address:\n{formatted}", reply_markup=get_main_keyboard())

# Callback: Multisend
@dp.callback_query_handler(lambda c: c.data == "multisend")
async def cb_multisend(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    if user_id in user_data and user_data[user_id].get("address"):
        user_data[user_id]["multisend"] = user_data[user_id]["address"]
        save_json(DATA_FILE, user_data)
        await callback.message.edit_text("📤 Address ditambahkan ke daftar Multisend.", reply_markup=get_main_keyboard())
    else:
        await callback.message.edit_text("❌ Belum ada address yang tersimpan.")

# Callback: Private Transfer
@dp.callback_query_handler(lambda c: c.data == "private_transfer")
async def cb_private(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    if user_id in user_data and user_data[user_id].get("address"):
        user_data[user_id]["private"] = user_data[user_id]["address"]
        save_json(DATA_FILE, user_data)
        await callback.message.edit_text("📥 Address ditambahkan ke daftar Private Transfer.", reply_markup=get_main_keyboard())
    else:
        await callback.message.edit_text("❌ Belum ada address yang tersimpan.")

# Callback: Edit
@dp.callback_query_handler(lambda c: c.data == "edit_address")
async def cb_edit(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    await callback.message.edit_text("✏️ Kirim address baru kamu (boleh banyak, pisahkan per baris):")
    user_data[user_id] = {"step": "awaiting_address"}
    save_json(DATA_FILE, user_data)

# Callback: Delete
@dp.callback_query_handler(lambda c: c.data == "delete_address")
async def cb_delete(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    user_data.pop(user_id, None)
    user_base.pop(user_id, None)
    save_json(DATA_FILE, user_data)
    save_json(USER_BASE_FILE, user_base)
    await callback.message.edit_text("🗑️ Address kamu telah dihapus.", reply_markup=get_main_keyboard())

# Handler address input
@dp.message_handler(lambda msg: str(msg.from_user.id) in user_data and user_data[str(msg.from_user.id)].get("step") == "awaiting_address")
async def receive_address(message: types.Message):
    user_id = str(message.from_user.id)
    address_list = [line.strip() for line in message.text.strip().splitlines() if line.strip()]
    if not address_list:
        await message.reply("❌ Format tidak valid. Kirim lagi address kamu (satu per baris).")
        return

    user_data[user_id] = {
        "address": address_list,
        "multisend": [],
        "private": [],
        "joined_today": True
    }
    user_base[user_id] = address_list

    save_json(DATA_FILE, user_data)
    save_json(USER_BASE_FILE, user_base)

    formatted = "\n".join(f"oct... {i+1}" for i in range(len(address_list)))
    await message.reply(f"✅ Address disimpan:\n{formatted}", reply_markup=get_main_keyboard())

# Auto reset tiap jam 00:00 WIB
async def auto_delete():
    while True:
        now = datetime.now(pytz.timezone("Asia/Jakarta"))
        next_reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        wait_time = (next_reset - now).total_seconds()
        print(f"[AUTO RESET] Menunggu hingga 00:00 WIB...")
        await asyncio.sleep(wait_time)

        for user_id in list(user_data.keys()):
            user_data[user_id]["multisend"] = []
            user_data[user_id]["private"] = []
            user_data[user_id]["joined_today"] = False
        save_json(DATA_FILE, user_data)
        print("[AUTO RESET] Data berhasil direset.")

if __name__ == "__main__":
    asyncio.create_task(auto_delete())
    executor.start_polling(dp, skip_updates=True)
