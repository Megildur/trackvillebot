import discord
from discord.ext import commands
from discord import app_commands

allowed_guilds = [1293647067998326936]

class SyncCog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        print(f"SyncCog loaded")

    @commands.command(name='sync', description='Syncs the bot', hidden=True)
    @commands.is_owner()
    async def sync(self, ctx) -> None:
        await self.bot.tree.sync(guild=None)
        await ctx.send('Commands synced.')

    @commands.command(name='syncg', description='Syncs the bot', hidden=True)
    @commands.is_owner()
    async def syncg(self, ctx, guild: discord.Guild) -> None:
        await self.bot.tree.sync(guild=guild)
        await ctx.send('Commands synced.')

    @commands.command(name='clear', description='Clears all commands from the tree', hidden=True)
    @commands.is_owner()
    async def clear(self, ctx) -> None:
        ctx.bot.tree.clear_commands(guild=None)
        await ctx.send('Commands cleared.')

    @app_commands.command(name='help', description='Show help for slash commands')
    async def help(self, ctx):
        embed = discord.Embed(title='Help', description='**List of available slash commands:**')
        embed.add_field(name='**General commands:**', value='', inline=False)
        for command in self.bot.tree.walk_commands(type=discord.AppCommandType.chat_input, ):
            if command.root_parent is not None and not isinstance(command, discord.app_commands.Group):
                 embed.add_field(name=f'/{command.qualified_name}', value=command.description, inline=False)
        await ctx.response.send_message(embed=embed)
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if ctx.guild.id not in allowed_guilds and isinstance(error, commands.NotOwner):
            print(f"Error: this user tried to use an owner command in another guild {ctx.author.name} in {ctx.guild.name}:{ctx.guild.id}")
            return
        if ctx.guild.id not in allowed_guilds:
            print(f"Error: this user tried to use a command in another guild {ctx.author.name} in {ctx.guild.name}:{ctx.guild.id}")
            return
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(f"Invalid command. Type `!wchelp` for a list of available commands.")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have the required permissions to use this command.")
        elif isinstance(error, commands.NotOwner):
            print(f"Error: this user tried to use an owner command {ctx.author.name}")
            await ctx.send("You cannot use this command because you are not the owner of this bot.")
        else:
            print(f"Error: {error}")
            await ctx.send(f"An error occurred. {error}")
        
async def setup(bot) -> None:
    await bot.add_cog(SyncCog(bot))