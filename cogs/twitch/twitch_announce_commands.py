import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
from typing import Optional

twitch_db = "data/twitch_announce.db"

class TwitchConfirmView(discord.ui.View):
    def __init__(self, guild_id: int, username: str, user_info: dict):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.username = username
        self.user_info = user_info

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green, emoji='✅')
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with aiosqlite.connect(twitch_db) as db:
            try:
                await db.execute("""
                    INSERT INTO twitch_streamers (guild_id, twitch_username)
                    VALUES (?, ?)
                """, (self.guild_id, self.username))
                await db.commit()

                embed = discord.Embed(
                    title="✅ Streamer Added Successfully",
                    description=f"Now monitoring **{self.user_info['display_name']}** (@{self.username}) for live streams!",
                    color=discord.Color.green()
                )
                embed.set_thumbnail(url=self.user_info['profile_image_url'])
                embed.set_footer(text="Live announcements will be sent when they go live.")
                
                # Disable all buttons
                for item in self.children:
                    item.disabled = True
                
                await interaction.response.edit_message(embed=embed, view=self)

            except aiosqlite.IntegrityError:
                embed = discord.Embed(
                    title="❌ Already Monitoring",
                    description=f"**{self.username}** is already being monitored in this server.",
                    color=discord.Color.red()
                )
                
                # Disable all buttons
                for item in self.children:
                    item.disabled = True
                
                await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red, emoji='❌')
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="❌ Cancelled",
            description="Streamer was not added to monitoring.",
            color=discord.Color.orange()
        )
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        # Disable all buttons when view times out
        for item in self.children:
            item.disabled = True

@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
class TwitchAnnounceCommands(commands.GroupCog, group_name="twitch"):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        async with aiosqlite.connect(twitch_db) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS twitch_settings (
                    guild_id INTEGER PRIMARY KEY,
                    channel_id INTEGER NOT NULL,
                    role_id INTEGER
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS twitch_streamers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    twitch_username TEXT NOT NULL,
                    is_live INTEGER DEFAULT 0,
                    last_stream_id TEXT,
                    UNIQUE(guild_id, twitch_username)
                )
            """)
            await db.commit()

    @app_commands.command(name="setup", description="Set up Twitch live announcements for this server")
    @app_commands.describe(
        channel="The channel where Twitch live announcements will be sent",
        role="Optional role to ping when streamers go live"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def setup_twitch(self, interaction: discord.Interaction, channel: discord.TextChannel, role: Optional[discord.Role] = None):
        if not interaction.user.guild_permissions.manage_guild:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need the `Manage Server` permission to set up Twitch announcements.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        bot_permissions = channel.permissions_for(interaction.guild.me)
        if not bot_permissions.send_messages or not bot_permissions.embed_links:
            embed = discord.Embed(
                title="❌ Insufficient Permissions",
                description=f"I need `Send Messages` and `Embed Links` permissions in {channel.mention}.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        async with aiosqlite.connect(twitch_db) as db:
            await db.execute("""
                INSERT OR REPLACE INTO twitch_settings (guild_id, channel_id, role_id)
                VALUES (?, ?, ?)
            """, (interaction.guild_id, channel.id, role.id if role else None))
            await db.commit()

        embed = discord.Embed(
            title="✅ Twitch Announcements Setup Complete",
            description=f"Twitch live announcements will be sent to {channel.mention}",
            color=discord.Color.purple()
        )
        if role:
            embed.add_field(name="Ping Role", value=role.mention, inline=False)
        embed.add_field(
            name="Next Steps",
            value="Use `/twitch add <username>` to add Twitch streamers to monitor.",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="add", description="Add a Twitch streamer to monitor for live announcements")
    @app_commands.describe(username="The Twitch username to monitor (without @)")
    @app_commands.default_permissions(manage_guild=True)
    async def add_streamer(self, interaction: discord.Interaction, username: str):
        if not interaction.user.guild_permissions.manage_guild:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need the `Manage Server` permission to add Twitch streamers.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        async with aiosqlite.connect(twitch_db) as db:
            cursor = await db.execute("SELECT channel_id FROM twitch_settings WHERE guild_id = ?", (interaction.guild_id,))
            settings = await cursor.fetchone()
            if not settings:
                embed = discord.Embed(
                    title="❌ Setup Required",
                    description="Please set up Twitch announcements first using `/twitch setup`.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

        username = username.lower().strip().replace('@', '').replace('twitch.tv/', '')

        # Check if already monitoring
        async with aiosqlite.connect(twitch_db) as db:
            cursor = await db.execute("SELECT 1 FROM twitch_streamers WHERE guild_id = ? AND twitch_username = ?", (interaction.guild_id, username))
            if await cursor.fetchone():
                embed = discord.Embed(
                    title="❌ Already Monitoring",
                    description=f"**{username}** is already being monitored in this server.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

        # Get handler instance to access API methods
        handler = self.bot.get_cog('TwitchAnnounceHandler')
        if not handler:
            embed = discord.Embed(
                title="❌ Service Error",
                description="Twitch service is not available. Please try again later.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check if user exists on Twitch
        user_id = await handler.get_twitch_user_id(username)
        if not user_id:
            embed = discord.Embed(
                title="❌ User Not Found",
                description=f"The Twitch user **{username}** doesn't exist or couldn't be found.\nPlease check the username and try again.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="💡 Tip",
                value="Make sure you're using the exact Twitch username (without @ or twitch.tv/)",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Get user profile information
        user_info = await handler.get_user_info(user_id)
        if not user_info:
            embed = discord.Embed(
                title="❌ Profile Error",
                description="Could not retrieve profile information. Please try again later.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Create confirmation embed with profile info
        confirm_embed = discord.Embed(
            title="📺 Confirm Twitch Streamer",
            description=f"Found Twitch user: **{user_info['display_name']}**",
            color=discord.Color.purple(),
            url=f"https://twitch.tv/{user_info['login']}"
        )
        
        if user_info['profile_image_url']:
            confirm_embed.set_thumbnail(url=user_info['profile_image_url'])
        
        confirm_embed.add_field(
            name="Username",
            value=f"@{user_info['login']}",
            inline=True
        )
        confirm_embed.add_field(
            name="Display Name",
            value=user_info['display_name'],
            inline=True
        )
        confirm_embed.add_field(
            name="Profile Link",
            value=f"[View on Twitch](https://twitch.tv/{user_info['login']})",
            inline=True
        )
        
        confirm_embed.set_footer(text="Click 'Confirm' to add this streamer to monitoring or 'Cancel' to abort.")

        # Create confirmation view
        view = TwitchConfirmView(interaction.guild_id, username, user_info)
        
        await interaction.response.send_message(embed=confirm_embed, view=view, ephemeral=True)

    @app_commands.command(name="remove", description="Remove a Twitch streamer from monitoring")
    @app_commands.describe(username="The Twitch username to stop monitoring")
    @app_commands.default_permissions(manage_guild=True)
    async def remove_streamer(self, interaction: discord.Interaction, username: str):
        if not interaction.user.guild_permissions.manage_guild:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need the `Manage Server` permission to remove Twitch streamers.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        username = username.lower().strip().replace('@', '').replace('twitch.tv/', '')

        async with aiosqlite.connect(twitch_db) as db:
            cursor = await db.execute("""
                DELETE FROM twitch_streamers 
                WHERE guild_id = ? AND twitch_username = ?
            """, (interaction.guild_id, username))
            await db.commit()

            if cursor.rowcount > 0:
                embed = discord.Embed(
                    title="✅ Streamer Removed",
                    description=f"No longer monitoring **{username}** for live streams.",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="❌ Streamer Not Found",
                    description=f"**{username}** is not being monitored in this server.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="list", description="List all monitored Twitch streamers for this server")
    async def list_streamers(self, interaction: discord.Interaction):
        async with aiosqlite.connect(twitch_db) as db:
            cursor = await db.execute("""
                SELECT twitch_username, is_live FROM twitch_streamers 
                WHERE guild_id = ? ORDER BY twitch_username
            """, (interaction.guild_id,))
            streamers = await cursor.fetchall()

            if not streamers:
                embed = discord.Embed(
                    title="📺 No Streamers Monitored",
                    description="No Twitch streamers are currently being monitored in this server.\nUse `/twitch add <username>` to add some!",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            live_streamers = []
            offline_streamers = []

            for username, is_live in streamers:
                if is_live:
                    live_streamers.append(f"🔴 **{username}** (LIVE)")
                else:
                    offline_streamers.append(f"⚫ {username}")

            description = ""
            if live_streamers:
                description += "**Currently Live:**\n" + "\n".join(live_streamers) + "\n\n"
            if offline_streamers:
                description += "**Offline:**\n" + "\n".join(offline_streamers)

            embed = discord.Embed(
                title="📺 Monitored Twitch Streamers",
                description=description,
                color=discord.Color.purple()
            )
            embed.set_footer(text=f"Total: {len(streamers)} streamers")
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="settings", description="View current Twitch announcement settings")
    async def view_settings(self, interaction: discord.Interaction):
        async with aiosqlite.connect(twitch_db) as db:
            cursor = await db.execute("""
                SELECT channel_id, role_id FROM twitch_settings 
                WHERE guild_id = ?
            """, (interaction.guild_id,))
            settings = await cursor.fetchone()

            if not settings:
                embed = discord.Embed(
                    title="❌ Not Set Up",
                    description="Twitch announcements are not set up for this server.\nUse `/twitch setup` to get started!",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            channel_id, role_id = settings
            channel = interaction.guild.get_channel(channel_id)
            role = interaction.guild.get_role(role_id) if role_id else None

            embed = discord.Embed(
                title="📺 Twitch Announcement Settings",
                color=discord.Color.purple()
            )

            if channel:
                embed.add_field(name="Announcement Channel", value=channel.mention, inline=False)
            else:
                embed.add_field(name="Announcement Channel", value="❌ Channel not found", inline=False)

            if role:
                embed.add_field(name="Ping Role", value=role.mention, inline=False)
            else:
                embed.add_field(name="Ping Role", value="None", inline=False)

            cursor = await db.execute("SELECT COUNT(*) FROM twitch_streamers WHERE guild_id = ?", (interaction.guild_id,))
            count = await cursor.fetchone()
            embed.add_field(name="Monitored Streamers", value=str(count[0]), inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="disable", description="Disable Twitch announcements for this server")
    @app_commands.default_permissions(manage_guild=True)
    async def disable_twitch(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need the `Manage Server` permission to disable Twitch announcements.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        async with aiosqlite.connect(twitch_db) as db:
            cursor1 = await db.execute("DELETE FROM twitch_settings WHERE guild_id = ?", (interaction.guild_id,))
            cursor2 = await db.execute("DELETE FROM twitch_streamers WHERE guild_id = ?", (interaction.guild_id,))
            await db.commit()

            if cursor1.rowcount > 0:
                embed = discord.Embed(
                    title="✅ Twitch Announcements Disabled",
                    description="Twitch live announcements have been disabled and all monitored streamers have been removed.",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="❌ Not Set Up",
                    description="Twitch announcements were not enabled in this server.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(TwitchAnnounceCommands(bot))