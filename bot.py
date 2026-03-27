import logging
import sqlite3
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")  # set this in Railway

# ================= LOGGING =================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ================= DATABASE =================
DB_PATH = os.getenv("DB_PATH", "stats.db")

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS stats (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    count INTEGER
)
""")
conn.commit()

# ================= JOIN HANDLER =================
async def handle_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return

    inviter = update.message.from_user
    new_members = update.message.new_chat_members

    user_id = inviter.id
    name = inviter.full_name
    added_count = len(new_members)

    try:
        cursor.execute("SELECT count FROM stats WHERE user_id=?", (user_id,))
        result = cursor.fetchone()

        if result:
            new_total = result[0] + added_count
            cursor.execute(
                "UPDATE stats SET count=?, name=? WHERE user_id=?",
                (new_total, name, user_id)
            )
        else:
            cursor.execute(
                "INSERT INTO stats (user_id, name, count) VALUES (?, ?, ?)",
                (user_id, name, added_count)
            )

        conn.commit()

    except Exception as e:
        logging.error(f"Error in handle_join: {e}")

# ================= /stats =================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cursor.execute("SELECT name, count FROM stats ORDER BY count DESC")
        rows = cursor.fetchall()

        if not rows:
            await update.message.reply_text("📭 Hali hech kim foydalanuvchi qo‘shmagan.")
            return

        medals = ["🥇", "🥈", "🥉"]

        text = "📊 Statistika:\n\n"

        for i, (name, count) in enumerate(rows):
            medal = medals[i] if i < 3 else "👤"
            text += f"{medal} {name} — {count}ta foydalanuvchini qo'shdi 👥\n"

        await update.message.reply_text(text)

    except Exception as e:
        logging.error(f"Error in stats: {e}")

# ================= /addstats =================
async def addstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Reply qilib yozing:\n/addstats 10")
            return

        user = update.message.reply_to_message.from_user
        amount = int(context.args[0])

        cursor.execute("SELECT count FROM stats WHERE user_id=?", (user.id,))
        result = cursor.fetchone()

        if result:
            new_total = result[0] + amount
            cursor.execute(
                "UPDATE stats SET count=?, name=? WHERE user_id=?",
                (new_total, user.full_name, user.id)
            )
        else:
            cursor.execute(
                "INSERT INTO stats (user_id, name, count) VALUES (?, ?, ?)",
                (user.id, user.full_name, amount)
            )

        conn.commit()

        await update.message.reply_text(
            f"✅ {user.full_name} ga {amount} ta qo‘shildi!"
        )

    except Exception as e:
        logging.error(f"Error in addstats: {e}")
        await update.message.reply_text("❌ Xatolik yuz berdi.")

# ================= MAIN =================
def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN environment variable is not set!")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_join))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("addstats", addstats))

    print("🚀 Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
