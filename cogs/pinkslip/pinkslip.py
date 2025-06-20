
import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal, List
import aiosqlite
from .pinkslip_database import PinkslipDatabase
from .pinkslip_views import (
    PinkSlipSubmissionView, 
    PinkSlipReviewView, 
    RaceTrackerView, 
    PinkSlipInventoryView
)
from .pinkslip_embeds import EmbedManager

class PinkslipCog(commands.Cog):
    """Professional vehicle registration and race tracking system."""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.db = PinkslipDatabase()
        self.embed_manager = EmbedManager()
        self._setup_complete = False

    async def cog_load(self) -> None:
        """Initialize the cog and database tables."""
        try:
            await self.db.initialize()
            self._setup_complete = True
            print(f"✅ {self.__class__.__name__} loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load {self.__class__.__name__}: {e}")
            raise

    async def _ensure_setup(self) -> bool:
        """Ensure the cog is properly set up before processing commands."""
        if not self._setup_complete:
            await self.cog_load()
        return self._setup_complete

    # Command Groups
    pinkslip = app_commands.Group(
        name='pinkslip', 
        description='Professional vehicle registration management system'
    )
    
    view_group = app_commands.Group(
        name='view', 
        description='View registrations and racing statistics', 
        parent=pinkslip
    )
    
    race_group = app_commands.Group(
        name='race', 
        description='Track race results and transfers', 
        parent=pinkslip
    )
    
    admin_group = app_commands.Group(
        name='admin', 
        description='Administrative management tools', 
        parent=pinkslip
    )

    @pinkslip.command(name='submit', description='Submit a new vehicle registration for review')
    async def submit_registration(self, interaction: discord.Interaction) -> None:
        """Handle vehicle registration submission."""
        if not await self._ensure_setup():
            await self._send_system_error(interaction)
            return

        embed = self.embed_manager.create_submission_intro(interaction.guild)
        view = PinkSlipSubmissionView(self.db, self.embed_manager)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @pinkslip.command(name='setup', description='Configure system channels and settings')
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        review_channel='Channel where staff review pending registrations',
        notification_channel='Channel for public approval/denial notifications'
    )
    async def setup_channels(
        self, 
        interaction: discord.Interaction, 
        review_channel: discord.TextChannel, 
        notification_channel: discord.TextChannel
    ) -> None:
        """Configure system channels with proper validation."""
        if not await self._ensure_setup():
            await self._send_system_error(interaction)
            return

        # Validate bot permissions
        missing_perms = await self._validate_channel_permissions([review_channel, notification_channel])
        if missing_perms:
            embed = self.embed_manager.create_error(
                "Insufficient Permissions",
                f"I lack message permissions in: {', '.join(missing_perms)}\n\n"
                "Please ensure I have 'Send Messages' and 'Embed Links' permissions."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            await self.db.update_guild_settings(
                interaction.guild_id, 
                review_channel.id, 
                notification_channel.id
            )

            embed = self.embed_manager.create_success(
                "System Configuration Complete",
                f"**Review Channel:** {review_channel.mention}\n"
                f"**Notification Channel:** {notification_channel.mention}\n\n"
                "The registration system is now ready for use."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            embed = self.embed_manager.create_error(
                "Configuration Failed",
                "An error occurred while saving settings. Please try again."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @view_group.command(name='profile', description="View a member's vehicle registrations and race statistics")
    @app_commands.describe(member='The member to view (defaults to yourself)')
    async def view_profile(self, interaction: discord.Interaction, member: discord.Member = None) -> None:
        """Display comprehensive user profile with vehicles and statistics."""
        if not await self._ensure_setup():
            await self._send_system_error(interaction)
            return

        target_member = member or interaction.user
        
        try:
            user_data = await self.db.get_user_complete_data(target_member.id, interaction.guild_id)
            
            if not user_data['vehicles']:
                embed = self.embed_manager.create_info(
                    "No Registrations Found",
                    f"{target_member.mention} has not submitted any vehicle registrations.\n\n"
                    "Use `/pinkslip submit` to register your first vehicle."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            embed = self.embed_manager.create_profile_overview(target_member, user_data)
            view = PinkSlipInventoryView(target_member, user_data['vehicles'], self.db, self.embed_manager)
            await interaction.response.send_message(embed=embed, view=view, delete_after=900)

        except Exception as e:
            embed = self.embed_manager.create_error(
                "Data Retrieval Failed",
                "Unable to load profile data. Please try again later."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @race_group.command(name='result', description='Record race results and handle vehicle transfers')
    @app_commands.describe(opponent='The member you raced against')
    async def record_race_result(self, interaction: discord.Interaction, opponent: discord.Member) -> None:
        """Handle race result recording with validation."""
        if not await self._ensure_setup():
            await self._send_system_error(interaction)
            return

        if opponent.id == interaction.user.id:
            embed = self.embed_manager.create_error(
                "Invalid Opponent",
                "You cannot race against yourself."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if opponent.bot:
            embed = self.embed_manager.create_error(
                "Invalid Opponent",
                "You cannot race against bots."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = self.embed_manager.create_race_tracker_intro(interaction.guild)
        view = RaceTrackerView(interaction.user, opponent, self.db, self.embed_manager)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def autocomplete_vehicle_id(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete for vehicle IDs."""
        try:
            async with aiosqlite.connect(self.db.db_path) as db:
                async with db.execute('''
                    SELECT slip_id, make_model, year, user_id FROM vehicles 
                    WHERE guild_id = ? AND make_model LIKE ?
                    ORDER BY make_model LIMIT 25
                ''', (interaction.guild_id, f'%{current}%')) as cursor:
                    results = await cursor.fetchall()
                    
                return [
                    app_commands.Choice(
                        name=f"{row[0]} - {row[1]} ({row[2]}) - Owner: {row[3]}", 
                        value=str(row[0])
                    ) for row in results
                ]
        except Exception:
            return []

    @admin_group.command(name='transfer', description='Administratively transfer vehicle ownership')
    @app_commands.describe(
        vehicle_id='Vehicle registration ID',
        new_owner='New owner of the vehicle'
    )
    @app_commands.autocomplete(vehicle_id=autocomplete_vehicle_id)
    @app_commands.default_permissions(administrator=True)
    async def admin_transfer(
        self, 
        interaction: discord.Interaction, 
        vehicle_id: str, 
        new_owner: discord.Member
    ) -> None:
        """Handle administrative vehicle transfers."""
        if not await self._ensure_setup():
            await self._send_system_error(interaction)
            return

        try:
            success = await self.db.transfer_vehicle_ownership(vehicle_id, new_owner.id, interaction.guild_id)
            
            if success:
                embed = self.embed_manager.create_success(
                    "Transfer Completed",
                    f"Vehicle `{vehicle_id}` has been transferred to {new_owner.mention}"
                )
            else:
                embed = self.embed_manager.create_error(
                    "Transfer Failed",
                    f"Vehicle `{vehicle_id}` not found or already belongs to {new_owner.mention}"
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            embed = self.embed_manager.create_error(
                "Transfer Error",
                "An error occurred during the transfer. Please verify the vehicle ID and try again."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_group.command(name='delete', description='Permanently delete a vehicle registration')
    @app_commands.describe(vehicle_id='Vehicle registration ID to delete')
    @app_commands.autocomplete(vehicle_id=autocomplete_vehicle_id)
    @app_commands.default_permissions(administrator=True)
    async def admin_delete(self, interaction: discord.Interaction, vehicle_id: str) -> None:
        """Handle administrative vehicle deletion."""
        if not await self._ensure_setup():
            await self._send_system_error(interaction)
            return

        try:
            vehicle_data = await self.db.get_vehicle_by_id(vehicle_id)
            if not vehicle_data:
                embed = self.embed_manager.create_error(
                    "Vehicle Not Found",
                    f"No vehicle found with ID `{vehicle_id}`"
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            success = await self.db.delete_vehicle(vehicle_id, interaction.guild_id)
            
            if success:
                embed = self.embed_manager.create_success(
                    "Vehicle Deleted",
                    f"Vehicle `{vehicle_id}` ({vehicle_data[2]} {vehicle_data[3]}) has been permanently removed."
                )
            else:
                embed = self.embed_manager.create_error(
                    "Deletion Failed",
                    "An error occurred during deletion. Please try again."
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            embed = self.embed_manager.create_error(
                "Deletion Error",
                "An error occurred while deleting the vehicle."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_group.command(name='stats', description='Modify user racing statistics')
    @app_commands.describe(
        member='Member to modify statistics for',
        action='Whether to add or subtract from stats',
        stat_type='Which statistic to modify',
        amount='Amount to change (positive number)'
    )
    @app_commands.default_permissions(administrator=True)
    async def admin_modify_stats(
        self, 
        interaction: discord.Interaction, 
        member: discord.Member, 
        action: Literal['add', 'subtract'], 
        stat_type: Literal['wins', 'losses'], 
        amount: int
    ) -> None:
        """Handle administrative statistics modification."""
        if not await self._ensure_setup():
            await self._send_system_error(interaction)
            return

        if amount <= 0:
            embed = self.embed_manager.create_error(
                "Invalid Amount",
                "Amount must be a positive number."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            new_value = await self.db.modify_user_stats(
                member.id, interaction.guild_id, stat_type, action, amount
            )

            embed = self.embed_manager.create_success(
                "Statistics Updated",
                f"{member.mention}'s {stat_type} have been updated to **{new_value}**"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            embed = self.embed_manager.create_error(
                "Update Failed",
                "An error occurred while updating statistics."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _validate_channel_permissions(self, channels: list[discord.TextChannel]) -> list[str]:
        """Validate bot permissions in specified channels."""
        missing_perms = []
        required_perms = ['send_messages', 'embed_links']
        
        for channel in channels:
            bot_perms = channel.permissions_for(channel.guild.me)
            if not all(getattr(bot_perms, perm, False) for perm in required_perms):
                missing_perms.append(channel.mention)
        
        return missing_perms

    async def _send_system_error(self, interaction: discord.Interaction) -> None:
        """Send a standardized system error message."""
        embed = self.embed_manager.create_error(
            "System Unavailable",
            "The registration system is currently unavailable. Please try again later."
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    """Setup function for the cog."""
    cog = PinkslipCog(bot)
    await bot.add_cog(cog)
    # Add persistent view for review system
    bot.add_view(PinkSlipReviewView(None, None, None))
