import discord
from discord.ext import commands
import os
import aiosqlite
import logging
import dotenv
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.all()

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

class MyBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self) -> None:
        # Load sync extension from root directory
        await bot.load_extension('sync')
        
        # Load the main pinkslip cog
        await bot.load_extension('cogs.pinkslip')
        
        # Load other cogs (excluding pinkslip components)
        for filename in os.listdir('cogs'):
            if filename.endswith('.py') and filename not in ['pinkslip.py', 'pinkslip_database.py', 'pinkslip_embeds.py', 'pinkslip_views.py', 'pinkslip_models.py', 'pinkslip_utils.py', 'pinkslip_validators.py']:
                cog_name = filename[:-3]
                await bot.load_extension(f'cogs.{cog_name}')    

    async def on_ready(self) -> None:
        print(f'Logged in as {self.user.name} (ID: {self.user.id})')
        await bot.change_presence(activity=discord.Game(name="Assetto Corsa"), status=discord.Status.idle)

bot = MyBot()

TOKEN = str(os.getenv('TOKEN'))

bot.run(TOKEN, log_handler=handler, log_level=logging.ERROR)