from os import getenv

from disnake import ForumChannel
from dotenv import load_dotenv

from src.bot import Krabbe

load_dotenv()

bot = Krabbe()


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    guild_settings = bot.database.get_collection("guild_settings").find({})

    async for guild_setting in guild_settings:
        print(guild_setting)

        if guild_setting.get("settings_event_logging_thread_id") and guild_setting.get("voice_event_logging_thread_id"):
            continue

        event_logging_channel: ForumChannel = bot.get_channel(guild_setting["event_logging_channel_id"])

        if not event_logging_channel:
            await bot.database.get_collection("guild_settings").delete_one({"_id": guild_setting["_id"]})
            continue

        settings_event_logging_thread, _ = await event_logging_channel.create_thread(
            name="設定事件記錄",
            content="這裡是設定事件記錄討論串，用於紀錄成員對於頻道設定的更新"
        )
        voice_event_logging_thread, _ = await event_logging_channel.create_thread(
            name="語音事件記錄",
            content="這裡是語音事件記錄頻道，用於紀錄語音頻道的動態，如成員加入、離開等"
        )

        await bot.database.get_collection("guild_settings").update_one(
            {"_id": guild_setting["_id"]},
            {
                "$set": {
                    "settings_event_logging_thread_id": settings_event_logging_thread.id,
                    "voice_event_logging_thread_id": voice_event_logging_thread.id
                }
            }
        )

    print("Migration Done")


if __name__ == "__main__":
    bot.run(getenv("BOT_TOKEN"))
