import discord
from discord.ext import commands
from discord import app_commands

allowed_guilds = [1270284390919835770]

class SyncCog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        print(f"SyncCog loaded")

    @commands.command(name='sync', description='Syncs the bot', hidden=True)
    @commands.is_owner()
    async def sync(self, ctx) -> None:
        try:
            await ctx.send('🔄 Starting global sync...')
            synced = await self.bot.tree.sync(guild=None)
            await ctx.send(f'✅ Successfully synced {len(synced)} commands globally.')
            print(f"Synced {len(synced)} commands globally")
            for command in synced:
                print(f"  - {command.name}")
        except discord.HTTPException as e:
            await ctx.send(f'❌ HTTP Error during sync: {e}')
            print(f"HTTP Error during sync: {e}")
        except discord.Forbidden as e:
            await ctx.send(f'❌ Forbidden error during sync: {e}')
            print(f"Forbidden error during sync: {e}")
        except Exception as e:
            await ctx.send(f'❌ Unexpected error during sync: {e}')
            print(f"Unexpected error during sync: {e}")

    @commands.command(name='syncg', description='Syncs the bot', hidden=True)
    @commands.is_owner()
    async def syncg(self, ctx, guild: discord.Guild) -> None:
        try:
            await ctx.send(f'🔄 Starting sync for guild: {guild.name}...')
            synced = await self.bot.tree.sync(guild=guild)
            await ctx.send(f'✅ Successfully synced {len(synced)} commands for {guild.name}.')
            print(f"Synced {len(synced)} commands for guild {guild.name}")
            for command in synced:
                print(f"  - {command.name}")
        except discord.HTTPException as e:
            await ctx.send(f'❌ HTTP Error during guild sync: {e}')
            print(f"HTTP Error during guild sync: {e}")
        except discord.Forbidden as e:
            await ctx.send(f'❌ Forbidden error during guild sync: {e}')
            print(f"Forbidden error during guild sync: {e}")
        except Exception as e:
            await ctx.send(f'❌ Unexpected error during guild sync: {e}')
            print(f"Unexpected error during guild sync: {e}")

    @commands.command(name='clear', description='Clears all commands from the tree', hidden=True)
    @commands.is_owner()
    async def clear(self, ctx) -> None:
        try:
            await ctx.send('🔄 Clearing command tree...')
            before_count = len(ctx.bot.tree.get_commands())
            ctx.bot.tree.clear_commands(guild=None)
            await ctx.send(f'✅ Cleared {before_count} commands from the tree.')
            print(f"Cleared {before_count} commands from tree")
        except Exception as e:
            await ctx.send(f'❌ Error clearing commands: {e}')
            print(f"Error clearing commands: {e}")

    @commands.command(name='list_commands', description='List all loaded commands', hidden=True)
    @commands.is_owner()
    async def list_commands(self, ctx) -> None:
        """List all commands currently in the tree for debugging."""
        try:
            commands = list(self.bot.tree.get_commands())
            if not commands:
                await ctx.send('❌ No commands found in the tree.')
                return
            
            await ctx.send(f'📋 Found {len(commands)} commands in tree:')
            for i, command in enumerate(commands, 1):
                if isinstance(command, app_commands.Group):
                    subcommands = list(command.walk_commands())
                    await ctx.send(f'{i}. **{command.name}** (Group) - {len(subcommands)} subcommands')
                    for j, subcmd in enumerate(subcommands, 1):
                        await ctx.send(f'   {j}. {subcmd.qualified_name}')
                else:
                    await ctx.send(f'{i}. **{command.name}** - {command.description}')
        except Exception as e:
            await ctx.send(f'❌ Error listing commands: {e}')
            print(f"Error listing commands: {e}")

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