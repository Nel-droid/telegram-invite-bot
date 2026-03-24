invite_buffer = {}
invite_tasks = {}

@dp.message(lambda message: message.new_chat_members)
async def new_member_handler(message: types.Message):
    inviter = message.from_user
    if not inviter:
        return

    user_id = inviter.id
    chat_id = message.chat.id
    inviter_name = "@" + inviter.username if inviter.username else inviter.full_name

    count = len(message.new_chat_members)

    # SAVE TO DATABASE
    cursor.execute("SELECT count FROM invites WHERE user_id=?", (user_id,))
    row = cursor.fetchone()

    if row:
        cursor.execute("UPDATE invites SET count=count+? WHERE user_id=?", (count, user_id))
    else:
        cursor.execute("INSERT INTO invites (user_id, count) VALUES (?, ?)", (user_id, count))

    conn.commit()

    # ADD TO BUFFER
    invite_buffer[user_id] = invite_buffer.get(user_id, 0) + count

    # 🔥 ONLY CREATE ONE TIMER
    if user_id not in invite_tasks:

        async def send_after_delay():
            await asyncio.sleep(180)  # ⏳ 3 minutes

            total = invite_buffer.get(user_id, 0)

            if total > 0:
                await bot.send_message(
                    chat_id,
                    f"👤 {inviter_name} invited {total} users 👥"
                )

            # RESET
            invite_buffer[user_id] = 0
            invite_tasks.pop(user_id, None)

        invite_tasks[user_id] = asyncio.create_task(send_after_delay())
