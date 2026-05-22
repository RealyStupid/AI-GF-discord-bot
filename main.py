# Main entry point for the bot.
import discord
from discord.ext import commands
import os
from Ollama_Setup_Manager.ollama_manager import init_async
from bot.config.bot_config import INTENTS, BOT_TOKEN, APPLICATION_ID

class Client(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=INTENTS, application_id=APPLICATION_ID)

    async def setup_hook(self):
        print("[SETUP HOOK] started")

        await self.load_cogs("Cogs")

        intent = init_async()
        await intent.initialize()

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

bot.run(BOT_TOKEN)