
import discord
from discord.ui import View, Button, Modal, Select
from typing import List, Optional
import re

class PinkSlipSubmissionView(View):
    def __init__(self, interaction: discord.Interaction, db, embed_builder) -> None:
        super().__init__(timeout=300)
        self.interaction = interaction
        self.db = db
        self.embed_builder = embed_builder

    @discord.ui.button(label='📝 Submit Registration', style=discord.ButtonStyle.primary)
    async def submit(self, interaction: discord.Interaction, button: Button) -> None:
        await interaction.response.send_modal(
            PinkSlipSubmissionModal(self.interaction, self.db, self.embed_builder)
        )

    @discord.ui.button(label='❌ Cancel', style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: Button) -> None:
        embed = self.embed_builder.create_info_embed(
            "Registration Cancelled",
            "Your vehicle registration has been cancelled. Use `/pinkslip submit` when you're ready to resubmit."
        )
        await interaction.response.edit_message(embed=embed, view=None)

class PinkSlipSubmissionModal(Modal, title='🚗 Vehicle Registration Form'):
    def __init__(self, interaction: discord.Interaction, db, embed_builder) -> None:
        super().__init__()
        self.interaction = interaction
        self.db = db
        self.embed_builder = embed_builder

    make_and_model = discord.ui.TextInput(
        label='Make & Model',
        placeholder='e.g., Ford Mustang GT',
        style=discord.TextStyle.short,
        max_length=100
    )
    year = discord.ui.TextInput(
        label='Year',
        placeholder='e.g., 2023',
        style=discord.TextStyle.short,
        max_length=4
    )
    engine_spec = discord.ui.TextInput(
        label='Engine Specifications',
        placeholder='e.g., 1100whp 1300nm',
        style=discord.TextStyle.short,
        max_length=200
    )
    transmission = discord.ui.TextInput(
        label='Transmission',
        placeholder='e.g., 6-Speed Manual',
        style=discord.TextStyle.short,
        max_length=100
    )
    steam_id = discord.ui.TextInput(
        label='Steam ID',
        placeholder='e.g., 76561198125412123',
        style=discord.TextStyle.short,
        max_length=50
    )
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        vehicle_data = {
            'make_model': self.make_and_model.value,
            'year': self.year.value,
            'engine_spec': self.engine_spec.value,
            'transmission': self.transmission.value,
            'steam_id': self.steam_id.value
        }
        
        success, result = await self.db.create_pinkslip(
            interaction.user.id, interaction.guild_id, vehicle_data
        )
        
        if not success:
            if result == "duplicate":
                embed = self.embed_builder.create_error_embed(
                    "Duplicate Registration",
                    f"You already have a registration for **{vehicle_data['make_model']} {vehicle_data['year']}**"
                )
            else:
                embed = self.embed_builder.create_error_embed(
                    "Registration Failed",
                    "An unexpected error occurred. Please try again."
                )
            await interaction.response.edit_message(embed=embed, view=None)
            return

        # Success - notify user and staff
        embed = self.embed_builder.create_success_embed(
            "Registration Submitted Successfully",
            "Your vehicle registration has been submitted for staff review. You'll be notified once it's processed."
        )
        await interaction.response.edit_message(embed=embed, view=None)
        
        # Send to staff channel
        await self._notify_staff(interaction, vehicle_data)

    async def _notify_staff(self, interaction: discord.Interaction, vehicle_data: dict) -> None:
        guild_settings = await self.db.get_guild_settings(interaction.guild_id)
        if not guild_settings:
            return
            
        channel = interaction.guild.get_channel(guild_settings[0])
        if not channel:
            return

        embed = self.embed_builder.create_review_embed(interaction.user, vehicle_data)
        view = PinkSlipReviewView(interaction, self.db, self.embed_builder)
        await channel.send(embed=embed, view=view)

class PinkSlipReviewView(View):
    def __init__(self, interaction: discord.Interaction, db=None, embed_builder=None) -> None:
        super().__init__(timeout=None)
        self.interaction = interaction
        self.db = db
        self.embed_builder = embed_builder

    @discord.ui.button(label='✅ Approve', style=discord.ButtonStyle.success, custom_id='approve_ps')
    async def approve(self, interaction: discord.Interaction, button: Button) -> None:
        await self._process_review(interaction, "approved", "✅ Registration Approved")

    @discord.ui.button(label='❌ Deny', style=discord.ButtonStyle.danger, custom_id='deny_ps')
    async def deny(self, interaction: discord.Interaction, button: Button) -> None:
        await interaction.response.send_modal(
            PinkSlipDenyModal(interaction, self.db, self.embed_builder)
        )

    async def _process_review(self, interaction: discord.Interaction, status: str, title: str) -> None:
        message = await interaction.original_response()
        embed_data = self._extract_embed_data(message.embeds[0])
        
        await self.db.update_pinkslip_approval(
            embed_data['user_id'], interaction.guild_id,
            embed_data['make_model'], embed_data['year'], status
        )
        
        # Update staff message
        embed = self.embed_builder.create_success_embed(
            title,
            f"<@{embed_data['user_id']}> has been notified of the decision."
        )
        await interaction.response.edit_message(embed=embed, view=None)
        
        # Notify user
        await self._notify_user_approval(interaction, embed_data)

    def _extract_embed_data(self, embed) -> dict:
        description = embed.description
        mention_pattern = r'<@!?(\d+)>'
        match = re.search(mention_pattern, description)
        fields = embed.fields
        
        return {
            'user_id': match.group(1),
            'make_model': fields[0].value,
            'year': fields[1].value
        }

    async def _notify_user_approval(self, interaction: discord.Interaction, embed_data: dict) -> None:
        guild_settings = await self.db.get_guild_settings(interaction.guild_id)
        if not guild_settings:
            return
            
        channel = interaction.guild.get_channel(guild_settings[1])
        if not channel:
            return

        embed = self.embed_builder.create_approval_notification_embed(
            interaction.user, embed_data['make_model'], embed_data['year']
        )
        await channel.send(f"<@{embed_data['user_id']}>", embed=embed)

class PinkSlipDenyModal(Modal, title='❌ Registration Denial'):
    def __init__(self, interaction: discord.Interaction, db, embed_builder) -> None:
        super().__init__()
        self.interaction = interaction
        self.db = db
        self.embed_builder = embed_builder

    reason = discord.ui.TextInput(
        label='Reason for Denial',
        placeholder='e.g., Invalid Steam ID, missing payment confirmation',
        style=discord.TextStyle.paragraph,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        message = await interaction.original_response()
        embed_data = self._extract_embed_data(message.embeds[0])
        
        # Delete from database
        await self.db.delete_pinkslip_by_details(
            embed_data['user_id'], interaction.guild_id,
            embed_data['make_model'], embed_data['year']
        )
        
        # Update staff message
        embed = self.embed_builder.create_denial_embed(
            embed_data, self.reason.value
        )
        await interaction.response.edit_message(embed=embed, view=None)
        
        # Notify user
        await self._notify_user_denial(interaction, embed_data)

    def _extract_embed_data(self, embed) -> dict:
        description = embed.description
        mention_pattern = r'<@!?(\d+)>'
        match = re.search(mention_pattern, description)
        fields = embed.fields
        
        return {
            'user_id': match.group(1),
            'make_model': fields[0].value,
            'year': fields[1].value
        }

    async def _notify_user_denial(self, interaction: discord.Interaction, embed_data: dict) -> None:
        guild_settings = await self.db.get_guild_settings(interaction.guild_id)
        if not guild_settings:
            return
            
        channel = interaction.guild.get_channel(guild_settings[1])
        if not channel:
            return

        embed = self.embed_builder.create_denial_notification_embed(
            interaction.user, embed_data['make_model'], embed_data['year'], self.reason.value
        )
        await channel.send(f"<@{embed_data['user_id']}>", embed=embed)

class RaceTrackerView(View):
    def __init__(self, interaction: discord.Interaction, opponent: discord.Member, db, embed_builder) -> None:
        super().__init__(timeout=300)
        self.interaction = interaction
        self.opponent = opponent
        self.db = db
        self.embed_builder = embed_builder

    @discord.ui.button(label='🏆 I Won', style=discord.ButtonStyle.success)
    async def win(self, interaction: discord.Interaction, button: Button) -> None:
        await self.db.update_win_loss_stats(interaction.user.id, interaction.guild_id, "wins")
        await self._handle_outcome(interaction, "win", "Select the vehicle you won:")

    @discord.ui.button(label='💔 I Lost', style=discord.ButtonStyle.danger)
    async def loss(self, interaction: discord.Interaction, button: Button) -> None:
        await self.db.update_win_loss_stats(interaction.user.id, interaction.guild_id, "loses")
        await self._handle_outcome(interaction, "lose", "Select the vehicle you lost:")

    async def _handle_outcome(self, interaction: discord.Interaction, outcome: str, description: str) -> None:
        embed = self.embed_builder.create_info_embed("Race Results Updated", description)
        
        if outcome == "win":
            opponent_pinkslips = await self.db.get_user_pinkslips(self.opponent.id, interaction.guild_id)
            view = VehicleSelectionView(
                interaction, self.opponent, opponent_pinkslips, outcome, self.db, self.embed_builder
            )
        else:
            user_pinkslips = await self.db.get_user_pinkslips(interaction.user.id, interaction.guild_id)
            view = VehicleSelectionView(
                interaction, interaction.user, user_pinkslips, outcome, self.db, self.embed_builder
            )
        
        await interaction.response.edit_message(embed=embed, view=view)

class VehicleSelectionView(View):
    def __init__(self, interaction: discord.Interaction, target_user: discord.Member, 
                 pinkslips: List, outcome: str, db, embed_builder) -> None:
        super().__init__(timeout=300)
        self.interaction = interaction
        self.target_user = target_user
        self.outcome = outcome
        self.db = db
        self.embed_builder = embed_builder
        
        if pinkslips:
            dropdown = VehicleDropdown(interaction, target_user, pinkslips, outcome, db, embed_builder)
            self.add_item(dropdown)

class VehicleDropdown(Select):
    def __init__(self, interaction: discord.Interaction, target_user: discord.Member,
                 pinkslips: List, outcome: str, db, embed_builder) -> None:
        self.interaction = interaction
        self.target_user = target_user
        self.outcome = outcome
        self.db = db
        self.embed_builder = embed_builder
        
        options = [
            discord.SelectOption(
                label=f"{pinkslip[0]} - {pinkslip[1]}",
                value=str(pinkslip[5]),  # slip_id
                description=f"ID: {pinkslip[5]}"
            )
            for pinkslip in pinkslips[:25]  # Discord limit
        ]
        
        super().__init__(
            placeholder="Select a vehicle...",
            options=options,
            custom_id='vehicle_dropdown'
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        selected_slip_id = self.values[0]
        pinkslip_data = await self.db.get_pinkslip_by_id(selected_slip_id)
        
        if not pinkslip_data:
            embed = self.embed_builder.create_error_embed(
                "Error", "Vehicle registration not found."
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return

        # Transfer ownership
        new_owner = interaction.user if self.outcome == "win" else self.target_user
        await self.db.transfer_pinkslip_ownership(selected_slip_id, new_owner.id, interaction.guild_id)

        # Create confirmation view
        embed = self.embed_builder.create_transfer_confirmation_embed(
            interaction.user, self.target_user, pinkslip_data[1], pinkslip_data[2], self.outcome
        )
        
        view = TransferConfirmationView(
            interaction, self.target_user, interaction.user, self.outcome,
            selected_slip_id, self.db, self.embed_builder
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
        
        # Send to notification channel
        await self._send_confirmation_request(interaction, embed, view)

    async def _send_confirmation_request(self, interaction: discord.Interaction, embed: discord.Embed, view: View) -> None:
        guild_settings = await self.db.get_guild_settings(interaction.guild_id)
        if not guild_settings:
            return
            
        channel = interaction.guild.get_channel(guild_settings[1])
        if channel:
            target_mention = self.target_user.mention if self.outcome == "win" else interaction.user.mention
            await channel.send(target_mention, embed=embed, view=view)

class TransferConfirmationView(View):
    def __init__(self, interaction: discord.Interaction, target_user: discord.Member,
                 initiator: discord.Member, outcome: str, slip_id: str, db, embed_builder) -> None:
        super().__init__(timeout=600)
        self.interaction = interaction
        self.target_user = target_user
        self.initiator = initiator
        self.outcome = outcome
        self.slip_id = slip_id
        self.db = db
        self.embed_builder = embed_builder

    @discord.ui.button(label='✅ Confirm', style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: Button) -> None:
        if interaction.user.id != self.target_user.id:
            await interaction.response.send_message(
                "❌ Only the mentioned user can confirm this transfer.", ephemeral=True
            )
            return

        # Update opponent's stats
        opponent_stat = "loses" if self.outcome == "win" else "wins"
        await self.db.update_win_loss_stats(self.target_user.id, interaction.guild_id, opponent_stat)

        embed = self.embed_builder.create_success_embed(
            "Transfer Confirmed",
            "✅ Race results have been recorded and vehicle ownership has been transferred."
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label='❌ Cancel', style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: Button) -> None:
        if interaction.user.id != self.target_user.id:
            await interaction.response.send_message(
                "❌ Only the mentioned user can cancel this transfer.", ephemeral=True
            )
            return

        # Revert changes
        initiator_stat = "wins" if self.outcome == "win" else "loses"
        await self.db.update_win_loss_stats(self.initiator.id, interaction.guild_id, initiator_stat, -1)
        
        # Revert ownership
        original_owner = self.target_user if self.outcome == "win" else self.initiator
        await self.db.transfer_pinkslip_ownership(self.slip_id, original_owner.id, interaction.guild_id)

        embed = self.embed_builder.create_error_embed(
            "Transfer Cancelled",
            "❌ The transfer has been cancelled and changes have been reverted."
        )
        await interaction.response.edit_message(embed=embed, view=None)

class PinkSlipInventoryView(View):
    def __init__(self, interaction: discord.Interaction, member: discord.Member,
                 pinkslips: List, db, embed_builder) -> None:
        super().__init__(timeout=600)
        self.interaction = interaction
        self.member = member
        self.db = db
        self.embed_builder = embed_builder
        
        if pinkslips:
            dropdown = PinkSlipInventoryDropdown(interaction, member, pinkslips, db, embed_builder)
            self.add_item(dropdown)

    @discord.ui.button(label='🔙 Back to Overview', style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: Button) -> None:
        pinkslips = await self.db.get_user_pinkslips(self.member.id, interaction.guild_id)
        win_loss_stats = await self.db.get_win_loss_stats(self.member.id, interaction.guild_id)
        
        embed = self.embed_builder.create_inventory_embed(self.member, len(pinkslips), win_loss_stats)
        view = PinkSlipInventoryView(interaction, self.member, pinkslips, self.db, self.embed_builder)
        
        await interaction.response.edit_message(embed=embed, view=view, delete_after=600)

class PinkSlipInventoryDropdown(Select):
    def __init__(self, interaction: discord.Interaction, member: discord.Member,
                 pinkslips: List, db, embed_builder) -> None:
        self.interaction = interaction
        self.member = member
        self.db = db
        self.embed_builder = embed_builder
        
        options = [
            discord.SelectOption(
                label=f"{pinkslip[0]} - {pinkslip[1]}",
                value=str(pinkslip[5]),  # slip_id
                description=f"Status: {pinkslip[4]}"
            )
            for pinkslip in pinkslips[:25]  # Discord limit
        ]
        
        super().__init__(
            placeholder="Select a vehicle to view details...",
            options=options,
            custom_id='inventory_dropdown'
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        selected_slip_id = self.values[0]
        pinkslip_data = await self.db.get_pinkslip_by_id(selected_slip_id)
        
        if not pinkslip_data:
            embed = self.embed_builder.create_error_embed(
                "Error", "Vehicle registration not found."
            )
        else:
            embed = self.embed_builder.create_detailed_pinkslip_embed(pinkslip_data, self.member)
        
        pinkslips = await self.db.get_user_pinkslips(self.member.id, interaction.guild_id)
        view = PinkSlipInventoryView(interaction, self.member, pinkslips, self.db, self.embed_builder)
        
        await interaction.response.edit_message(embed=embed, view=view, delete_after=600)
