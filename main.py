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
        await self.load_extension('sync')
        for filename in os.listdir('cogs'):
            if filename.endswith('.py'):
                cog_name = filename[:-3]
                await bot.load_extension(f'cogs.{cog_name}')

    async def on_ready(self) -> None:
        print(f'Logged in as {self.user.name} (ID: {self.user.id})')
        await bot.change_presence(activity=discord.Game(name="Assetto Corsa"), status=discord.Status.idle)

bot = MyBot()

TOKEN = str(os.getenv('TOKEN'))

bot.run(TOKEN, log_handler=handler, log_level=logging.ERROR)