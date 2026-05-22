import discord
import os
from dotenv import load_dotenv

INTENTS = discord.Intents.default()
INTENTS.message_content = True

APPLICATION_ID = 1507187112804483162

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")