import asyncio
import logging
import os
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ChatType

API_TOKEN = os.getenv("API_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# DATABASE
conn = sqlite3.connect("data.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS invites (
    user_id INTEGER,
    count INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS daily (
    date TEXT,
    joined INTEGER DEFAULT 0,
    left INTEGER DEFAULT 0
)
""")

conn.commit()

# ➕ USER JOIN
@dp.message(lambda message: message.new_chat_members)
async def new_member_handler(message: types.Message):
    inviter = message.from_user

    if inviter:
        user_id = inviter.id

        cursor.execute("SELECT count FROM invites WHERE user_id=?", (user_id,))
        row = cursor.fetchone()

        if row:
            cursor.execute("UPDATE invites SET count=count+1 WHERE user_id=?", (user_id,))
        else:
            cursor.execute("INSERT INTO invites (user_id, count) VALUES (?, 1)", (user_id,))

        # daily join
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT joined FROM daily WHERE date=?", (today,))
        row = cursor.fetchone()

        if row:
            cursor.execute("UPDATE daily SET joined=joined+1 WHERE date=?", (today,))
        else:
            cursor.execute("INSERT INTO daily (date, joined, left) VALUES (?, 1, 0)", (today,))

        conn.commit()

        await message.answer(
            f"👤 {inviter.full_name} jami takliflari: +1 👥"
        )

# ➖ USER LEFT
@dp.message(lambda message: message.left_chat_member)
async def left_handler(message: types.Message):
    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("SELECT left FROM daily WHERE date=?", (today,))
    row = cursor.fetchone()

    if row:
        cursor.execute("UPDATE daily SET left=left+1 WHERE date=?", (today,))
    else:
        cursor.execute("INSERT INTO daily (date, joined, left) VALUES (?, 0, 1)", (today,))

    conn.commit()

# 📊 STATS
@dp.message(lambda message: message.text == "/stats")
async def stats_handler(message: types.Message):
    cursor.execute("SELECT * FROM invites ORDER BY count DESC LIMIT 10")
    rows = cursor.fetchall()

    text = "📊 TOP foydalanuvchilar:\n\n"

    for i, row in enumerate(rows, start=1):
        text += f"{i}. ID:{row[0]} — {row[1]} ta\n"

    await message.answer(text)

# 📊 DAILY REPORT (22:00)
async def daily_report():
    while True:
        now = datetime.now()

        if now.hour == 22 and now.minute == 0:
            today = now.strftime("%Y-%m-%d")

            cursor.execute("SELECT joined, left FROM daily WHERE date=?", (today,))
            row = cursor.fetchone()

            joined = row[0] if row else 0
            left = row[1] if row else 0

            cursor.execute("SELECT * FROM invites ORDER BY count DESC LIMIT 3")
            top = cursor.fetchall()

            text = "📊 Bugungi hisobot:\n\n"
            text += f"➕ +{joined} ta qo‘shildi\n"
            text += f"➖ -{left} ta chiqdi\n\n"
            text += "👑 TOP 3:\n"

            for i, user in enumerate(top, start=1):
                text += f"{i}. ID:{user[0]} — {user[1]} ta\n"

            # SEND TO GROUP
            for chat_id in ACTIVE_CHATS:
                await bot.send_message(chat_id, text)

            await asyncio.sleep(60)

        await asyncio.sleep(30)

# STORE ACTIVE CHATS
ACTIVE_CHATS = set()

@dp.message()
async def save_chat(message: types.Message):
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        ACTIVE_CHATS.add(message.chat.id)

async def main():
    asyncio.create_task(daily_report())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
