# Main entry point for the bot.
import discord
from discord.ext import commands
import os
from Ollama_Setup_Manager.ollama_manager import init_async
from bot.bot_config import INTENTS, BOT_TOKEN, APPLICATION_ID
from AI_manager.Client import AI_Client
import atexit
from sesh_database import *
from discord import app_commands

AI_INIT = init_async()

def load_inst() -> str:
    return open("AI_manager/Inst.md", "r", encoding="utf-8").read()

async def send_long_message(channel, text, limit=2000):
    while len(text) > limit:
        chunk = text[:limit]
        text = text[limit:]
        await channel.send(chunk)
    if text:
        await channel.send(text)

class Client(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=INTENTS, application_id=APPLICATION_ID)

    async def setup_hook(self):
        print("[SETUP HOOK] started")

        # await self.load_cogs("Cogs")

        await AI_INIT.initialize()

        await initialize_db()

        await initialize_crypto_db()

        # await self.tree.sync()

        print("[SETUP HOOK] finished")

    '''
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
    '''

    async def on_ready(self):
        print(f"Bot ready: {self.user}")

bot = Client()

# make this contact the AI and make prompts
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # Allow process of prefix commands
    if message.content.startswith("!"):
        await bot.process_commands(message)
        return
    
    # hitting the daily limit
    if not await can_interact(message.author.id):
        await message.channel.send("You hit your daily limit... \n Come back tomorow to chat more!")
        return

    # This is where the AI gets called
    if message.guild is None:
        async with message.channel.typing():
            await update_sql(message.author.id)

            ai = AI_Client()
            memory = await ai.extract_memory(message.content)
            await merge_memory(message.author.id, memory)

            await add_to_history(message.author.id, message.author.name, message.content)

            reply = await ai.request(
                message.author.id,
                message.content,
                instruction=load_inst(),
                stream=True
            )

            await add_to_history(message.author.id, "ai girlfriend", reply)

            if not reply.strip():
                reply = "⚠️ AI returned an empty response."

            await send_long_message(message.channel, reply)

@bot.command()
@commands.is_owner()
async def givePremium(ctx, target: discord.Member | None = None):
    user_id = ctx.author.id if target is None else target.id
    
    await give_premium(user_id)
    
    recipient = ctx.author if target is None else target
    
    await ctx.send(f"Premium given to {recipient.mention}")

@bot.command()
@commands.is_owner()
async def rmPremium(ctx, target: discord.Member | None = None):
    user_id = ctx.author.id if target is None else target.id
    
    await rm_premium(user_id)
    
    recipient = ctx.author if target is None else target
    
    await ctx.send(f"Premium removed from {recipient.mention}")

@bot.command()
@commands.is_owner()
async def wipeAll(ctx, target: str):
    # Accepts: @mention, <@id>, <@!id>, raw ID, username text
    cleaned = target.replace("<@", "").replace("<@!", "").replace(">", "")
    
    try:
        user_id = int(cleaned)
    except ValueError:
        await ctx.send("❌ Invalid user ID or mention.")
        return

    await wipe_all_memory(user_id)
    await ctx.send(f"🧹 All memory wiped for <@{user_id}>.")

@bot.command()
async def wipeMe(ctx):
    await wipe_all_memory(ctx.author.id)
    await ctx.send("🧹 Your memory has been wiped. Fresh start!")

@bot.tree.command(
    name="buy_premium",
    description="Want to chat more with the bot? Create a crypto wallet and buy premium!"
)
async def buy_premium(interaction: discord.Interaction):
   await interaction.response.send_message("Payment has not been setup yet")


# some exit handling
def exit_function():
    AI_INIT.stop_ollama()

atexit.register(exit_function)

bot.run(BOT_TOKEN)