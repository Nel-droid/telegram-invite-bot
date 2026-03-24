import asyncio
import logging
import sqlite3
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.exceptions import TelegramMigrateToChat, TelegramForbiddenError

# --- CONFIGURATION ---
TOKEN = "8707458665:AAGa47O8CAPBIksqqhVTBZcCceCtFUOCAbE"

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

# --- TRACKING ---
invite_tasks = {} 

@dp.message(F.new_chat_members)
async def new_member_handler(message: types.Message):
    inviter = message.from_user
    if not inviter or inviter.is_bot:
        return

    user_id = inviter.id
    inviter_name = f"@{inviter.username}" if inviter.username else inviter.full_name
    added_count = len(message.new_chat_members)

    # 1. Update Database
    cursor.execute("""
        INSERT INTO invites (user_id, count) 
        VALUES (?, ?) 
        ON CONFLICT(user_id) DO UPDATE SET count = count + ?
    """, (user_id, added_count, added_count))
    conn.commit()

    # 2. Timer Logic (30-second buffer)
    if user_id in invite_tasks:
        return 

    async def send_summary():
        invite_tasks[user_id] = True
        await asyncio.sleep(30)
        
        cursor.execute("SELECT count FROM invites WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        total = row[0] if row else 0
        
        try:
            await message.answer(f"👤 {inviter_name} {total}ta foydalanuvchini qo'shdi 👥")
        except TelegramMigrateToChat as e:
            # If group upgrades to supergroup, the bot sends to the new ID
            logging.warning(f"Group migrated to {e.migrate_to_chat_id}")
            await bot.send_message(e.migrate_to_chat_id, f"👤 {inviter_name} {total}ta foydalanuvchini qo'shdi 👥")
        except Exception as e:
            logging.error(f"Error sending message: {e}")
        finally:
            invite_tasks.pop(user_id, None)

    asyncio.create_task(send_summary())

# --- STARTUP ---
async def main():
    logging.basicConfig(level=logging.INFO)
    print("Bot is starting with new token...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")
