import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types

API_TOKEN = os.getenv("API_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

user_invites = {}

@dp.message(lambda message: message.new_chat_members)
async def new_member_handler(message: types.Message):
    inviter = message.from_user
    new_members = message.new_chat_members

    if inviter:
        inviter_id = inviter.id

        if inviter_id not in user_invites:
            user_invites[inviter_id] = 0

        user_invites[inviter_id] += len(new_members)

        await message.answer(
            f"{inviter.full_name} invited {user_invites[inviter_id]} users 👥"
        )

@dp.message(lambda message: message.text == "/stats")
async def stats_handler(message: types.Message):
    text = "📊 Invite stats:\n"

    for user_id, count in user_invites.items():
        text += f"{user_id}: {count}\n"

    await message.answer(text)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
