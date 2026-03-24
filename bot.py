import asyncio
import logging
import sqlite3
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import ChatMemberUpdatedFilter

# --- CONFIGURATION ---
TOKEN = os.getenv("BOT_TOKEN")
# If running locally for testing, you can uncomment the line below:
# TOKEN = "YOUR_NEW_TOKEN_HERE"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- DATABASE SETUP ---
conn = sqlite3.connect("invites.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS invites (
        user_id INTEGER PRIMARY KEY,
        count INTEGER DEFAULT 0
    )
""")
conn.commit()

# --- TRACKING DICTIONARIES ---
invite_tasks = {} # Tracks active timers per user

# --- HANDLER ---
@dp.message(F.new_chat_members)
async def new_member_handler(message: types.Message):
    inviter = message.from_user
    if not inviter or inviter.is_bot:
        return

    user_id = inviter.id
    chat_id = message.chat.id
    inviter_name = f"@{inviter.username}" if inviter.username else inviter.full_name
    added_count = len(message.new_chat_members)

    # 1. Update Database immediately
    cursor.execute("""
        INSERT INTO invites (user_id, count) 
        VALUES (?, ?) 
        ON CONFLICT(user_id) DO UPDATE SET count = count + ?
    """, (user_id, added_count, added_count))
    conn.commit()

    # 2. Check if a summary message timer is already running for this user
    if user_id in invite_tasks:
        return # Just update the DB and exit; the existing timer will pick up the new total

    # 3. If no timer exists, start a 30-second wait to collect all "adds"
    async def send_summary():
        invite_tasks[user_id] = True
        await asyncio.sleep(30) # Wait 30 seconds for more people to be added
        
        # Fetch the latest total from DB
        cursor.execute("SELECT count FROM invites WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        total = row[0] if row else 0
        
        await message.answer(f"👤 {inviter_name} {total}ta foydalanuvchini qo'shdi 👥")
        
        # Clean up tracking so a new message can be sent next time they add someone
        invite_tasks.pop(user_id, None)

    asyncio.create_task(send_summary())

# --- BOT STARTUP ---
async def main():
    logging.basicConfig(level=logging.INFO)
    print("Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")
