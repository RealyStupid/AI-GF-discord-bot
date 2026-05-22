# Main entry point for the bot.
import discord
from discord.ext import commands
import os
from Ollama_Setup_Manager.ollama_manager import init_async
from bot.config.bot_config import INTENTS, BOT_TOKEN, APPLICATION_ID
import atexit

AI_INIT = init_async()

class Client(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=INTENTS, application_id=APPLICATION_ID)

    async def setup_hook(self):
        print("[SETUP HOOK] started")

        await self.load_cogs("Cogs")

        await AI_INIT.initialize()

        print("[SETUP HOOK] finished")

    async def load_cogs(self, directory):
        base = directory.replace("\\", "/")

        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    full_path = os.path.join(root, file).replace("\\", "/")
                    relative = full_path[len(base):].lstrip("/")
                    module = f"Cogs.{relative[:-3].replace('/', '.')}"
                    await self.load_extension(module)
                    print(f"[COG LOADER] Loaded cog {module}")

    async def on_ready(self):
        print(f"Bot ready: {self.user}")

bot = Client()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.guild is None:
        await message.channel.send("Wassup")

def exit_function():
    AI_INIT.stop_ollama()

atexit.register(exit_function)

bot.run(BOT_TOKEN)