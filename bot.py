import asyncio
import logging
import sqlite3
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.exceptions import TelegramMigrateToChat

# --- CONFIGURATION ---
TOKEN = "8707458665:AAEFz93g5-Gv5O_Mspqav8UADJklUW62pQk"

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

@dp.message(F.new_chat_members)
async def new_member_handler(message: types.Message):
    inviter = message.from_user
    if not inviter or inviter.is_bot:
        return

    user_id = inviter.id
    inviter_name = f"@{inviter.username}" if inviter.username else inviter.full_name
    added_count = len(message.new_chat_members)

    cursor.execute("""
        INSERT INTO invites (user_id, count) 
        VALUES (?, ?) 
        ON CONFLICT(user_id) DO UPDATE SET count = count + ?
    """, (user_id, added_count, added_count))
    conn.commit()

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
            await bot.send_message(e.migrate_to_chat_id, f"👤 {inviter_name} {total}ta foydalanuvchini qo'shdi 👥")
        except Exception as e:
            logging.error(f"Error: {e}")
        finally:
            invite_tasks.pop(user_id, None)

    asyncio.create_task(send_summary())

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
