import discord
from discord.ext import commands
from discord import app_commands
from typing import List, Literal
import aiosqlite
from .pinkslip_models import PinkslipDatabase
from .pinkslip_views import (
    PinkSlipSubmissionView, 
    PinkSlipReviewView, 
    RaceTrackerView, 
    PinkSlipInventoryView
)
from .pinkslip_utils import EmbedBuilder, MessageFormatter

class PinkslipCog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.db = PinkslipDatabase()
        self.embed_builder = EmbedBuilder()
        print(f"PinkslipCog loaded")

    async def cog_load(self) -> None:
        await self.db.initialize_tables()

    # Command Groups
    pinkslip = app_commands.Group(name='pinkslip', description='Manage your vehicle registrations')
    win_loss = app_commands.Group(name='win_loss', description='Track race results', parent=pinkslip)
    view = app_commands.Group(name='view', description='View registrations and statistics', parent=pinkslip)
    admin = app_commands.Group(name='admin', description='Administrative commands', parent=pinkslip)

    @pinkslip.command(name='submit', description='Submit a vehicle registration for approval')
    async def pinkslip_submit(self, interaction: discord.Interaction) -> None:
        embed = self.embed_builder.create_submission_intro_embed(interaction.guild)
        view = PinkSlipSubmissionView(interaction, self.db, self.embed_builder)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @pinkslip.command(name='settings', description='Configure pinkslip channels')
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        mod_channel='Channel for approval/denial requests',
        notification_channel='Channel for approval/denial notifications'
    )
    async def pinkslip_settings(
        self, 
        interaction: discord.Interaction, 
        mod_channel: discord.TextChannel, 
        notification_channel: discord.TextChannel
    ) -> None:
        # Validate permissions
        missing_perms = []
        for channel in [mod_channel, notification_channel]:
            if not channel.permissions_for(interaction.guild.me).send_messages:
                missing_perms.append(channel.mention)

        if missing_perms:
            embed = self.embed_builder.create_error_embed(
                "Missing Permissions",
                f"I don't have permission to send messages in: {', '.join(missing_perms)}"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await self.db.update_guild_settings(interaction.guild_id, mod_channel.id, notification_channel.id)

        embed = self.embed_builder.create_success_embed(
            "Channels Configured",
            f"📋 **Approval Channel:** {mod_channel.mention}\n"
            f"📢 **Notification Channel:** {notification_channel.mention}"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @view.command(name='owner', description="View a member's vehicle registrations")
    @app_commands.describe(member='The member to view registrations for')
    async def pinkslip_view_owner(self, interaction: discord.Interaction, member: discord.Member = None) -> None:
        target_member = member or interaction.user

        pinkslips = await self.db.get_user_pinkslips(target_member.id, interaction.guild_id)
        win_loss_stats = await self.db.get_win_loss_stats(target_member.id, interaction.guild_id)

        if not pinkslips:
            embed = self.embed_builder.create_info_embed(
                "No Registrations Found",
                f"{target_member.mention} has not submitted any vehicle registrations yet."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = self.embed_builder.create_inventory_embed(target_member, len(pinkslips), win_loss_stats)
        view = PinkSlipInventoryView(interaction, target_member, pinkslips, self.db, self.embed_builder)
        await interaction.response.send_message(embed=embed, view=view, delete_after=600)

    @win_loss.command(name='transfer', description='Record race results and transfer ownership')
    @app_commands.describe(opponent='The member you raced against')
    async def pinkslip_win_loss_transfer(self, interaction: discord.Interaction, opponent: discord.Member) -> None:
        embed = self.embed_builder.create_race_tracker_embed(interaction.guild)
        view = RaceTrackerView(interaction, opponent, self.db, self.embed_builder)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @admin.command(name='transfer', description='Transfer vehicle ownership (Admin only)')
    @app_commands.describe(slip_id='Vehicle registration ID', member='New owner')
    @app_commands.default_permissions(manage_guild=True)
    async def pinkslip_admin_transfer(self, interaction: discord.Interaction, slip_id: str, member: discord.Member) -> None:
        success = await self.db.transfer_pinkslip_ownership(slip_id, member.id, interaction.guild_id)

        if success:
            embed = self.embed_builder.create_success_embed(
                "Transfer Completed",
                f"Vehicle registration `{slip_id}` has been transferred to {member.mention}"
            )
        else:
            embed = self.embed_builder.create_error_embed(
                "Transfer Failed",
                f"Vehicle registration `{slip_id}` not found in this server"
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin.command(name='delete', description='Delete a vehicle registration (Admin only)')
    @app_commands.describe(slip_id='Vehicle registration ID to delete')
    @app_commands.default_permissions(manage_guild=True)
    async def pinkslip_admin_delete(self, interaction: discord.Interaction, slip_id: str) -> None:
        success = await self.db.delete_pinkslip(slip_id, interaction.guild_id)

        if success:
            embed = self.embed_builder.create_success_embed(
                "Registration Deleted",
                f"Vehicle registration `{slip_id}` has been permanently removed"
            )
        else:
            embed = self.embed_builder.create_error_embed(
                "Deletion Failed",
                f"Vehicle registration `{slip_id}` not found in this server"
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin.command(name='win_loss_change', description='Modify win/loss statistics (Admin only)')
    @app_commands.describe(
        member='Member to modify stats for',
        action='Add or remove from stats',
        stat='Which statistic to modify',
        amount='Amount to change by'
    )
    @app_commands.default_permissions(manage_guild=True)
    async def pinkslip_admin_win_loss_change(
        self, 
        interaction: discord.Interaction, 
        member: discord.Member, 
        action: Literal['add', 'remove'], 
        stat: Literal['wins', 'losses'], 
        amount: int
    ) -> None:
        new_value = await self.db.modify_win_loss_stats(
            member.id, interaction.guild_id, stat, action, amount
        )

        embed = self.embed_builder.create_success_embed(
            "Statistics Updated",
            f"{member.mention}'s {stat} have been updated to **{new_value}**"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot) -> None:
    await bot.add_cog(PinkslipCog(bot))
    bot.add_view(PinkSlipReviewView(bot))