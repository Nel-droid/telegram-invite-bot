import asyncio
import logging
import sqlite3
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.exceptions import TelegramMigrateToChat

# --- CONFIGURATION ---
TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN_HERE")  # ✅ use env var, not hardcoded
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- DATABASE SETUP ---
db_path = "/tmp/invites.db"
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS invites (
        user_id INTEGER PRIMARY KEY,
        count INTEGER DEFAULT 0
    )
""")
conn.commit()

invite_tasks = {}
invite_buffer = {}  # ✅ tracks count for THIS session only

@dp.message(F.new_chat_members)
async def new_member_handler(message: types.Message):
    inviter = message.from_user
    if not inviter or inviter.is_bot:
        return

    user_id = inviter.id
    chat_id = message.chat.id
    inviter_name = f"@{inviter.username}" if inviter.username else inviter.full_name
    added_count = len(message.new_chat_members)

    # Save to DB (all-time total)
    cursor.execute("""
        INSERT INTO invites (user_id, count)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET count = count + ?
    """, (user_id, added_count, added_count))
    conn.commit()

    # ✅ Add to session buffer
    invite_buffer[user_id] = invite_buffer.get(user_id, 0) + added_count

    # ✅ Guard is set BEFORE creating the task
    if user_id in invite_tasks:
        return  # timer already running, buffer already updated above — nothing else to do

    async def send_summary(uid=user_id, cid=chat_id, name=inviter_name):
        await asyncio.sleep(30)
        total = invite_buffer.get(uid, 0)
        try:
            if total > 0:
                await bot.send_message(cid, f"👤 {name} {total}ta foydalanuvchini qo'shdi 👥")
        except TelegramMigrateToChat as e:
            await bot.send_message(e.migrate_to_chat_id, f"👤 {name} {total}ta foydalanuvchini qo'shdi 👥")
        except Exception as e:
            logging.error(f"Error sending summary: {e}")
        finally:
            invite_buffer.pop(uid, None)   # ✅ reset session buffer
            invite_tasks.pop(uid, None)    # ✅ clear the task guard

    invite_tasks[user_id] = asyncio.create_task(send_summary())  # ✅ guard set before task runs

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
