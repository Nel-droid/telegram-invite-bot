invite_buffer = {}
invite_tasks = {}

@dp.message(lambda message: message.new_chat_members)
async def new_member_handler(message: types.Message):
    inviter = message.from_user
    if not inviter:
        return

    user_id = inviter.id
    chat_id = message.chat.id
    count = len(message.new_chat_members)

    # Save to database (same as before)
    cursor.execute("SELECT count FROM invites WHERE user_id=?", (user_id,))
    row = cursor.fetchone()

    if row:
        cursor.execute("UPDATE invites SET count=count+? WHERE user_id=?", (count, user_id))
    else:
        cursor.execute("INSERT INTO invites (user_id, count) VALUES (?, ?)", (user_id, count))

    conn.commit()

    # BUFFER (collect joins)
    if user_id not in invite_buffer:
        invite_buffer[user_id] = 0

    invite_buffer[user_id] += count

    # If task already running → do nothing
    if user_id in invite_tasks:
        return

    async def send_summary():
        await asyncio.sleep(10)  # ⏳ wait 10 seconds

        total = invite_buffer.get(user_id, 0)

        await bot.send_message(
            chat_id,
            f"👤 {inviter.full_name} invited {total} users 👥"
        )

        # reset
        invite_buffer[user_id] = 0
        invite_tasks.pop(user_id, None)

    invite_tasks[user_id] = asyncio.create_task(send_summary())
