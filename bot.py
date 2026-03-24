import asyncio

# Dictionary to track if a timer is already running for a user
invite_tasks = {}

@dp.message(lambda message: message.new_chat_members)
async def new_member_handler(message: types.Message):
    inviter = message.from_user
    if not inviter or inviter.is_bot:
        return
        
    user_id = inviter.id
    chat_id = message.chat.id
    inviter_name = f"@{inviter.username}" if inviter.username else inviter.full_name
    added_count = len(message.new_chat_members)

    # 1. Update Database Immediately
    cursor.execute("INSERT INTO invites (user_id, count) VALUES (?, ?) "
                   "ON CONFLICT(user_id) DO UPDATE SET count = count + ?", 
                   (user_id, added_count, added_count))
    conn.commit()

    # 2. Check if we are already waiting to send a message for this user
    if user_id in invite_tasks:
        return # A timer is already running, it will pick up the new DB total later

    # 3. If no timer exists, start one
    async def send_summary():
        invite_tasks[user_id] = True
        await asyncio.sleep(30) # Reduced to 30s for better user experience
        
        # Get the final total from DB after the wait
        cursor.execute("SELECT count FROM invites WHERE user_id=?", (user_id,))
        final_total = cursor.fetchone()[0]
        
        await message.answer(f"👤 {inviter_name} {final_total}ta foydalanuvchini qo'shdi 👥")
        
        # Remove from tracking so they can trigger a new message later
        invite_tasks.pop(user_id, None)

    asyncio.create_task(send_summary())
