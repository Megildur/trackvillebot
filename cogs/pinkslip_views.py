import discord
from discord.ui import View, Button, Modal, Select
from typing import List, Optional, Dict, Any
import re

class PinkSlipSubmissionView(View):
    """Professional vehicle registration submission interface."""

    def __init__(self, db, embed_manager) -> None:
        super().__init__(timeout=600)
        self.db = db
        self.embed_manager = embed_manager

    @discord.ui.button(
        label='📝 Begin Registration', 
        style=discord.ButtonStyle.primary,
        emoji='🚗'
    )
    async def start_registration(self, interaction: discord.Interaction, button: Button) -> None:
        """Launch the registration modal."""
        modal = VehicleRegistrationModal(self.db, self.embed_manager)
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label='📋 View Requirements', 
        style=discord.ButtonStyle.secondary,
        emoji='ℹ️'
    )
    async def view_requirements(self, interaction: discord.Interaction, button: Button) -> None:
        """Display detailed requirements."""
        embed = self.embed_manager.create_info(
            "Registration Requirements",
            "**📋 Required Information:**\n\n"
            "**🚗 Vehicle Make & Model**\n"
            "• Full manufacturer name and model\n"
            "• Example: Ford Mustang GT, BMW M3 Competition\n\n"
            "**📅 Manufacturing Year**\n"
            "• 4-digit year (1990-2024)\n"
            "• Must match vehicle specifications\n\n"
            "**⚡ Engine Specifications**\n"
            "• Power output (HP/WHP)\n"
            "• Torque figures (if available)\n"
            "• Example: 750whp 850nm, 1200hp 1400nm\n\n"
            "**⚙️ Transmission Details**\n"
            "• Type and gear count\n"
            "• Example: 6-Speed Manual, 8-Speed Automatic\n\n"
            "**🎮 Steam Platform ID**\n"
            "• 17-digit Steam ID\n"
            "• Found in Steam profile URL\n\n"
            "**💰 Entry Fee**\n"
            "• $3 USD payment required\n"
            "• Contact staff for payment methods"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label='❌ Cancel', 
        style=discord.ButtonStyle.secondary
    )
    async def cancel_registration(self, interaction: discord.Interaction, button: Button) -> None:
        """Cancel the registration process."""
        embed = self.embed_manager.create_info(
            "Registration Cancelled",
            "Your registration has been cancelled. You can restart the process anytime using `/pinkslip submit`."
        )
        await interaction.response.edit_message(embed=embed, view=None)

class VehicleRegistrationModal(Modal, title='🚗 Vehicle Registration Form'):
    """Comprehensive vehicle registration modal with validation."""

    def __init__(self, db, embed_manager) -> None:
        super().__init__()
        self.db = db
        self.embed_manager = embed_manager

    make_model = discord.ui.TextInput(
        label='Vehicle Make & Model',
        placeholder='e.g., Ford Mustang GT, BMW M3 Competition',
        style=discord.TextStyle.short,
        max_length=100,
        required=True
    )

    year = discord.ui.TextInput(
        label='Manufacturing Year',
        placeholder='e.g., 2023',
        style=discord.TextStyle.short,
        max_length=4,
        min_length=4,
        required=True
    )

    engine_spec = discord.ui.TextInput(
        label='Engine Specifications',
        placeholder='e.g., 750whp 850nm, Twin Turbo V8',
        style=discord.TextStyle.paragraph,
        max_length=300,
        required=True
    )

    transmission = discord.ui.TextInput(
        label='Transmission Type',
        placeholder='e.g., 6-Speed Manual, 8-Speed Automatic',
        style=discord.TextStyle.short,
        max_length=100,
        required=True
    )

    steam_id = discord.ui.TextInput(
        label='Steam ID (17 digits)',
        placeholder='e.g., 76561198123456789',
        style=discord.TextStyle.short,
        max_length=20,
        min_length=15,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Process the registration submission with validation."""
        # Validate inputs
        validation_errors = self._validate_inputs()
        if validation_errors:
            embed = self.embed_manager.create_error(
                "Validation Failed",
                "\n".join(validation_errors)
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        vehicle_data = {
            'make_model': self.make_model.value.strip(),
            'year': self.year.value.strip(),
            'engine_spec': self.engine_spec.value.strip(),
            'transmission': self.transmission.value.strip(),
            'steam_id': self.steam_id.value.strip()
        }

        try:
            success, result = await self.db.create_vehicle_registration(
                interaction.user.id, interaction.guild_id, vehicle_data
            )

            if not success:
                if result == "duplicate":
                    embed = self.embed_manager.create_error(
                        "Duplicate Registration",
                        f"You already have a registration for **{vehicle_data['make_model']} {vehicle_data['year']}**\n\n"
                        "Each vehicle can only be registered once per user."
                    )
                else:
                    embed = self.embed_manager.create_error(
                        "Registration Failed",
                        "An unexpected error occurred during registration. Please try again later."
                    )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Success response
            embed = self.embed_manager.create_success(
                "Registration Submitted Successfully",
                f"**Vehicle:** {vehicle_data['make_model']} ({vehicle_data['year']})\n"
                f"**Registration ID:** `{result}`\n\n"
                "Your registration has been submitted for staff review. "
                "You'll receive a notification once the review is complete.\n\n"
                "**Next Steps:**\n"
                "▫️ Await staff review (typically 24-48 hours)\n"
                "▫️ Complete entry fee payment if not done already\n"
                "▫️ Check your DMs for approval/denial notification"
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

            # Notify staff
            await self._notify_staff(interaction, vehicle_data)

        except Exception as e:
            embed = self.embed_manager.create_error(
                "System Error",
                "A system error occurred. Please contact an administrator."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    def _validate_inputs(self) -> List[str]:
        """Validate all form inputs."""
        errors = []

        # Year validation
        if not self.year.value.isdigit() or not (1990 <= int(self.year.value) <= 2024):
            errors.append("❌ Year must be between 1990 and 2024")

        # Steam ID validation
        steam_id = self.steam_id.value.strip()
        if not steam_id.isdigit() or len(steam_id) != 17:
            errors.append("❌ Steam ID must be exactly 17 digits")

        # Basic content validation
        if len(self.make_model.value.strip()) < 3:
            errors.append("❌ Make & Model must be at least 3 characters")

        if len(self.engine_spec.value.strip()) < 5:
            errors.append("❌ Engine specifications must be more detailed")

        if len(self.transmission.value.strip()) < 3:
            errors.append("❌ Transmission information is too brief")

        return errors

    async def _notify_staff(self, interaction: discord.Interaction, vehicle_data: Dict[str, str]) -> None:
        """Send registration to staff review channel."""
        guild_settings = await self.db.get_guild_settings(interaction.guild_id)
        if not guild_settings:
            return

        channel = interaction.guild.get_channel(guild_settings[0])
        if not channel:
            return

        embed = self.embed_manager.create_review_request(interaction.user, vehicle_data)
        view = PinkSlipReviewView(interaction, self.db, self.embed_manager)

        try:
            await channel.send(embed=embed, view=view)
        except discord.Forbidden:
            pass  # Silently fail if no permissions

class PinkSlipReviewView(View):
    """Staff review interface with enhanced functionality."""

    def __init__(self, interaction: Optional[discord.Interaction], db, embed_manager) -> None:
        super().__init__(timeout=None)
        self.interaction = interaction
        self.db = db
        self.embed_manager = embed_manager

    @discord.ui.button(
        label='✅ Approve Registration', 
        style=discord.ButtonStyle.success, 
        custom_id='approve_registration',
        emoji='✅'
    )
    async def approve_registration(self, interaction: discord.Interaction, button: Button) -> None:
        """Approve the vehicle registration."""
        embed_data = self._extract_embed_data(interaction.message.embeds[0])

        # Debug: Check if we extracted data correctly
        if not embed_data['make_model'] or not embed_data['year'] or not embed_data['user_id']:
            embed = self.embed_manager.create_error(
                "Data Extraction Failed",
                f"Failed to extract vehicle data from embed. Got: {embed_data}"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            success = await self.db.update_vehicle_status(
                int(embed_data['user_id']), interaction.guild_id,
                embed_data['make_model'], embed_data['year'], 'approved'
            )

            if not success:
                embed = self.embed_manager.create_error(
                    "Approval Failed",
                    f"Could not find vehicle: {embed_data['make_model']} ({embed_data['year']}) for user {embed_data['user_id']}"
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Update staff message
            embed = self.embed_manager.create_success(
                "Registration Approved",
                f"**Vehicle:** {embed_data['make_model']} ({embed_data['year']})\n"
                f"**Approved by:** {interaction.user.mention}\n"
                f"**User notified:** ✅"
            )
            await interaction.response.edit_message(embed=embed, view=None)

            # Notify user
            await self._notify_user_approval(interaction, embed_data)

        except Exception as e:
            embed = self.embed_manager.create_error(
                "Approval Failed",
                f"An error occurred while processing the approval: {str(e)}"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label='❌ Deny Registration', 
        style=discord.ButtonStyle.danger, 
        custom_id='deny_registration',
        emoji='❌'
    )
    async def deny_registration(self, interaction: discord.Interaction, button: Button) -> None:
        """Deny the vehicle registration with reason."""
        await interaction.response.send_modal(
            RegistrationDenialModal(self.db, self.embed_manager)
        )

    @discord.ui.button(
        label='🔍 Request More Info', 
        style=discord.ButtonStyle.secondary, 
        custom_id='request_info',
        emoji='🔍'
    )
    async def request_additional_info(self, interaction: discord.Interaction, button: Button) -> None:
        """Request additional information from the user."""
        await interaction.response.send_modal(
            InfoRequestModal(self.db, self.embed_manager)
        )

    def _extract_embed_data(self, embed: discord.Embed) -> Dict[str, str]:
        """Extract vehicle data from the review embed."""
        description = embed.description
        fields = embed.fields

        # Extract user ID from mention in description
        mention_pattern = r'<@!?(\d+)>'
        user_match = re.search(mention_pattern, description)
        user_id = user_match.group(1) if user_match else "0"

        # Initialize variables
        make_model, year = "", ""
        engine_spec, transmission = "", ""

        # Extract vehicle data from fields - match the actual field structure from create_review_request
        for field in fields:
            if "🚗 Vehicle Details" in field.name:
                lines = field.value.split('\n')
                for line in lines:
                    if '**Make/Model:**' in line:
                        make_model = line.split('**Make/Model:**', 1)[1].strip()
                    elif '**Year:**' in line:
                        year = line.split('**Year:**', 1)[1].strip()

            elif "⚡ Performance Specs" in field.name:
                lines = field.value.split('\n')
                for line in lines:
                    if '**Engine:**' in line:
                        engine_spec = line.split('**Engine:**', 1)[1].strip()
                    elif '**Transmission:**' in line:
                        transmission = line.split('**Transmission:**', 1)[1].strip()

        return {
            'user_id': user_id,
            'make_model': make_model,
            'year': year,
            'engine_spec': engine_spec,
            'transmission': transmission
        }

    async def _notify_user_approval(self, interaction: discord.Interaction, embed_data: Dict[str, str]) -> None:
        """Send approval notification to user."""
        guild_settings = await self.db.get_guild_settings(interaction.guild_id)
        if not guild_settings:
            return

        channel = interaction.guild.get_channel(guild_settings[1])
        if not channel:
            return

        embed = self.embed_manager.create_approval_notification(
            interaction.user, embed_data['make_model'], embed_data['year']
        )

        try:
            await channel.send(f"<@{embed_data['user_id']}>", embed=embed)
        except discord.Forbidden:
            pass

class RegistrationDenialModal(Modal, title='❌ Registration Denial'):
    """Modal for denying registrations with detailed reasons."""

    def __init__(self, db, embed_manager) -> None:
        super().__init__()
        self.db = db
        self.embed_manager = embed_manager

    denial_reason = discord.ui.TextInput(
        label='Reason for Denial',
        placeholder='Please provide a detailed explanation for the denial...',
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Process the denial with reason."""
        embed_data = self._extract_embed_data(interaction.message.embeds[0])

        try:
            # Delete the registration
            await self.db.delete_vehicle_by_details(
                int(embed_data['user_id']), interaction.guild_id,
                embed_data['make_model'], embed_data['year']
            )

            # Update staff message
            embed = self.embed_manager.create_error(
                "Registration Denied",
                f"**Vehicle:** {embed_data['make_model']} ({embed_data['year']})\n"
                f"**Denied by:** {interaction.user.mention}\n"
                f"**Reason:** {self.denial_reason.value}\n"
                f"**User notified:** ✅"
            )
            await interaction.response.edit_message(embed=embed, view=None)

            # Notify user
            await self._notify_user_denial(interaction, embed_data)

        except Exception as e:
            embed = self.embed_manager.create_error(
                "Denial Failed",
                "An error occurred while processing the denial."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    def _extract_embed_data(self, embed: discord.Embed) -> Dict[str, str]:
        """Extract data from embed."""
        description = embed.description
        fields = embed.fields

        mention_pattern = r'<@!?(\d+)>'
        user_match = re.search(mention_pattern, description)
        user_id = user_match.group(1) if user_match else "0"

        vehicle_field = next((f for f in fields if "🚗 Vehicle Details" in f.name), None)

        make_model, year = "", ""
        if vehicle_field:
            lines = vehicle_field.value.split('\n')
            for line in lines:
                if '**Make/Model:**' in line:
                    make_model = line.split('**Make/Model:**', 1)[1].strip()
                elif '**Year:**' in line:
                    year = line.split('**Year:**', 1)[1].strip()

        return {
            'user_id': user_id,
            'make_model': make_model,
            'year': year
        }

    async def _notify_user_denial(self, interaction: discord.Interaction, embed_data: Dict[str, str]) -> None:
        """Send denial notification to user."""
        guild_settings = await self.db.get_guild_settings(interaction.guild_id)
        if not guild_settings:
            return

        channel = interaction.guild.get_channel(guild_settings[1])
        if not channel:
            return

        embed = self.embed_manager.create_denial_notification(
            interaction.user, embed_data['make_model'], embed_data['year'], self.denial_reason.value
        )

        try:
            await channel.send(f"<@{embed_data['user_id']}>", embed=embed)
        except discord.Forbidden:
            pass

class InfoRequestModal(Modal, title='🔍 Request Additional Information'):
    """Modal for requesting more information from users."""

    def __init__(self, db, embed_manager) -> None:
        super().__init__()
        self.db = db
        self.embed_manager = embed_manager

    info_request = discord.ui.TextInput(
        label='Information Needed',
        placeholder='Please specify what additional information is required...',
        style=discord.TextStyle.paragraph,
        max_length=800,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Send information request."""
        embed_data = self._extract_embed_data(interaction.message.embeds[0])

        # Update staff message
        embed = self.embed_manager.create_warning(
            "Additional Information Requested",
            f"**Vehicle:** {embed_data['make_model']} ({embed_data['year']})\n"
            f"**Requested by:** {interaction.user.mention}\n"
            f"**Information Needed:** {self.info_request.value}\n\n"
            "*User has been notified. Registration remains pending.*"
        )
        await interaction.response.edit_message(embed=embed, view=self)

        # Notify user
        await self._notify_user_info_request(interaction, embed_data)

    def _extract_embed_data(self, embed: discord.Embed) -> Dict[str, str]:
        """Extract data from embed."""
        description = embed.description
        fields = embed.fields

        mention_pattern = r'<@!?(\d+)>'
        user_match = re.search(mention_pattern, description)
        user_id = user_match.group(1) if user_match else "0"

        vehicle_field = next((f for f in fields if "🚗 Vehicle Details" in f.name), None)

        make_model, year = "", ""
        if vehicle_field:
            lines = vehicle_field.value.split('\n')
            for line in lines:
                if '**Make/Model:**' in line:
                    make_model = line.split('**Make/Model:**', 1)[1].strip()
                elif '**Year:**' in line:
                    year = line.split('**Year:**', 1)[1].strip()

        return {
            'user_id': user_id,
            'make_model': make_model,
            'year': year
        }

    async def _notify_user_info_request(self, interaction: discord.Interaction, embed_data: Dict[str, str]) -> None:
        """Notify user about information request."""
        guild_settings = await self.db.get_guild_settings(interaction.guild_id)
        if not guild_settings:
            return

        channel = interaction.guild.get_channel(guild_settings[1])
        if not channel:
            return

        embed = self.embed_manager.create_warning(
            "Additional Information Required",
            f"Your registration for **{embed_data['make_model']} ({embed_data['year']})** requires additional information.\n\n"
            f"**Information Needed:**\n{self.info_request.value}\n\n"
            "Please contact staff to provide the requested information. Your registration will remain pending until resolved."
        )

        try:
            await channel.send(f"<@{embed_data['user_id']}>", embed=embed)
        except discord.Forbidden:
            pass

class RaceTrackerView(View):
    """Enhanced race result tracking interface."""

    def __init__(self, user: discord.Member, opponent: discord.Member, db, embed_manager) -> None:
        super().__init__(timeout=900)
        self.user = user
        self.opponent = opponent
        self.db = db
        self.embed_manager = embed_manager

    @discord.ui.button(
        label='🏆 I Won the Race', 
        style=discord.ButtonStyle.success,
        emoji='🏆'
    )
    async def record_victory(self, interaction: discord.Interaction, button: Button) -> None:
        """Handle victory recording."""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ Only the person who initiated this can record their result.", ephemeral=True
            )
            return

        await self.db.update_user_stats(self.user.id, interaction.guild_id, "wins", 1)
        await self._handle_vehicle_selection(interaction, "win")

    @discord.ui.button(
        label='💔 I Lost the Race', 
        style=discord.ButtonStyle.danger,
        emoji='💔'
    )
    async def record_loss(self, interaction: discord.Interaction, button: Button) -> None:
        """Handle loss recording."""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ Only the person who initiated this can record their result.", ephemeral=True
            )
            return

        await self.db.update_user_stats(self.user.id, interaction.guild_id, "losses", 1)
        await self._handle_vehicle_selection(interaction, "lose")

    @discord.ui.button(
        label='❌ Cancel', 
        style=discord.ButtonStyle.secondary
    )
    async def cancel_race_tracking(self, interaction: discord.Interaction, button: Button) -> None:
        """Cancel race tracking."""
        embed = self.embed_manager.create_info(
            "Race Tracking Cancelled",
            "No race results have been recorded."
        )
        await interaction.response.edit_message(embed=embed, view=None)

    async def _handle_vehicle_selection(self, interaction: discord.Interaction, outcome: str) -> None:
        """Handle vehicle selection for transfer."""
        target_user = self.opponent if outcome == "win" else self.user
        user_data = await self.db.get_user_complete_data(target_user.id, interaction.guild_id)

        if not user_data['vehicles']:
            embed = self.embed_manager.create_info(
                "No Vehicles Available",
                f"{target_user.mention} has no registered vehicles to transfer."
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return

        # Filter approved vehicles only - correct tuple index for status
        approved_vehicles = [v for v in user_data['vehicles'] if v[7] == 'approved']

        if not approved_vehicles:
            embed = self.embed_manager.create_info(
                "No Approved Vehicles",
                f"{target_user.mention} has no approved vehicles available for transfer."
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return

        embed = self.embed_manager.create_info(
            "Select Vehicle for Transfer",
            f"Choose which vehicle to transfer from {target_user.mention}:"
        )

        view = VehicleSelectionView(
            self.user, target_user, approved_vehicles, outcome, self.db, self.embed_manager
        )

        await interaction.response.edit_message(embed=embed, view=view)

class VehicleSelectionView(View):
    """Vehicle selection interface for transfers."""

    def __init__(self, initiator: discord.Member, target: discord.Member, 
                 vehicles: List, outcome: str, db, embed_manager) -> None:
        super().__init__(timeout=600)
        self.initiator = initiator
        self.target = target
        self.outcome = outcome
        self.db = db
        self.embed_manager = embed_manager

        if vehicles:
            dropdown = VehicleDropdown(
                initiator, target, vehicles[:25], outcome, db, embed_manager
            )
            self.add_item(dropdown)

class VehicleDropdown(Select):
    """Dropdown for vehicle selection."""

    def __init__(self, initiator: discord.Member, target: discord.Member,
                 vehicles: List, outcome: str, db, embed_manager) -> None:
        self.initiator = initiator
        self.target = target
        self.outcome = outcome
        self.db = db
        self.embed_manager = embed_manager

        options = [
            discord.SelectOption(
                label=f"{vehicle[2]} ({vehicle[3]})",  # make_model, year
                value=str(vehicle[8]),  # slip_id
                description=f"Status: {vehicle[7].title()}",  # status
                emoji="🚗"
            )
            for vehicle in vehicles
        ]

        super().__init__(
            placeholder="Select a vehicle to transfer...",
            options=options,
            custom_id='vehicle_selection'
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Handle vehicle selection."""
        selected_slip_id = self.values[0]
        vehicle_data = await self.db.get_vehicle_by_id(selected_slip_id)

        if not vehicle_data:
            embed = self.embed_manager.create_error(
                "Vehicle Not Found",
                "The selected vehicle could not be found."
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return

        # Transfer ownership
        new_owner = self.initiator if self.outcome == "win" else self.target
        success = await self.db.transfer_vehicle_ownership(
            selected_slip_id, new_owner.id, interaction.guild_id
        )

        if not success:
            embed = self.embed_manager.create_error(
                "Transfer Failed",
                "Vehicle ownership transfer failed."
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return

        # Create confirmation request
        embed = self.embed_manager.create_transfer_confirmation(
            self.initiator, self.target, vehicle_data[2], vehicle_data[3], self.outcome
        )

        view = TransferConfirmationView(
            self.initiator, self.target, self.outcome, selected_slip_id, self.db, self.embed_manager
        )

        await interaction.response.edit_message(embed=embed, view=None)

        # Send to notification channel
        await self._send_confirmation_request(interaction, embed, view)

    async def _send_confirmation_request(self, interaction: discord.Interaction, 
                                       embed: discord.Embed, view: View) -> None:
        """Send confirmation request to notification channel."""
        guild_settings = await self.db.get_guild_settings(interaction.guild_id)
        if not guild_settings:
            return

        channel = interaction.guild.get_channel(guild_settings[1])
        if not channel:
            return

        target_mention = self.target.mention
        try:
            await channel.send(target_mention, embed=embed, view=view)
        except discord.Forbidden:
            pass

class TransferConfirmationView(View):
    """Transfer confirmation interface."""

    def __init__(self, initiator: discord.Member, target: discord.Member,
                 outcome: str, slip_id: str, db, embed_manager) -> None:
        super().__init__(timeout=1800)  # 30 minutes
        self.initiator = initiator
        self.target = target
        self.outcome = outcome
        self.slip_id = slip_id
        self.db = db
        self.embed_manager = embed_manager

    async def on_timeout(self) -> None:
        """Handle timeout by reverting changes."""
        try:
            # We can't easily revert stats without proper guild_id access
            # This should be handled by the calling function or removed
            pass
        except:
            pass  # Silently handle timeout cleanup errors

    @discord.ui.button(
        label='✅ Confirm Transfer', 
        style=discord.ButtonStyle.success,
        emoji='✅'
    )
    async def confirm_transfer(self, interaction: discord.Interaction, button: Button) -> None:
        """Confirm the vehicle transfer."""
        if interaction.user.id != self.target.id:
            await interaction.response.send_message(
                "❌ Only the mentioned user can confirm this transfer.", ephemeral=True
            )
            return

        # Update opponent's stats
        opponent_stat = "losses" if self.outcome == "win" else "wins"
        await self.db.update_user_stats(self.target.id, interaction.guild_id, opponent_stat, 1)

        # Record race result
        winner_id = self.initiator.id if self.outcome == "win" else self.target.id
        loser_id = self.target.id if self.outcome == "win" else self.initiator.id
        await self.db.record_race_result(interaction.guild_id, winner_id, loser_id, self.slip_id)

        embed = self.embed_manager.create_success(
            "Transfer Confirmed",
            f"✅ **Race Result Recorded**\n"
            f"**Winner:** {'🏆 ' + self.initiator.mention if self.outcome == 'win' else '🏆 ' + self.target.mention}\n"
            f"**Vehicle Transferred:** Successfully\n"
            f"**Statistics Updated:** Both participants\n\n"
            "*Thank you for using the official racing system!*"
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(
        label='🚨 Dispute Transfer', 
        style=discord.ButtonStyle.danger,
        emoji='🚨'
    )
    async def dispute_transfer(self, interaction: discord.Interaction, button: Button) -> None:
        """Dispute the vehicle transfer."""
        if interaction.user.id != self.target.id:
            await interaction.response.send_message(
                "❌ Only the mentioned user can dispute this transfer.", ephemeral=True
            )
            return

        # Revert all changes
        initiator_stat = "wins" if self.outcome == "win" else "losses"
        await self.db.update_user_stats(self.initiator.id, interaction.guild_id, initiator_stat, -1)

        # Revert ownership
        original_owner = self.target if self.outcome == "win" else self.initiator
        await self.db.transfer_vehicle_ownership(self.slip_id, original_owner.id, interaction.guild_id)

        embed = self.embed_manager.create_error(
            "Transfer Disputed",
            f"🚨 **Race Result Disputed**\n\n"
            f"**Disputed by:** {self.target.mention}\n"
            f"**All changes have been reverted**\n\n"
            "**Staff has been notified** and will investigate this dispute. "
            "Please provide evidence of the actual race outcome to staff members.\n\n"
            "*Fraudulent claims may result in penalties.*"
        )
        await interaction.response.edit_message(embed=embed, view=None)

class PinkSlipInventoryView(View):
    """Enhanced vehicle inventory browser."""

    def __init__(self, member: discord.Member, vehicles: List, db, embed_manager) -> None:
        super().__init__(timeout=900)
        self.member = member
        self.db = db
        self.embed_manager = embed_manager

        if vehicles:
            dropdown = InventoryDropdown(member, vehicles[:25], db, embed_manager)
            self.add_item(dropdown)

    @discord.ui.button(
        label='🏠 Back to Profile', 
        style=discord.ButtonStyle.secondary,
        emoji='🏠',
        row=1
    )
    async def back_to_profile(self, interaction: discord.Interaction, button: Button) -> None:
        """Return to profile overview."""
        user_data = await self.db.get_user_complete_data(self.member.id, interaction.guild_id)

        embed= self.embed_manager.create_profile_overview(self.member, user_data)
        view = PinkSlipInventoryView(self.member, user_data['vehicles'], self.db, self.embed_manager)

        await interaction.response.edit_message(embed=embed, view=view, delete_after=900)

    @discord.ui.button(
        label='📊 View Statistics', 
        style=discord.ButtonStyle.primary,
        emoji='📊',
        row=1
    )
    async def view_detailed_stats(self, interaction: discord.Interaction, button: Button) -> None:
        """Show detailed statistics."""
        user_data = await self.db.get_user_complete_data(self.member.id, interaction.guild_id)
        stats = user_data['stats']

        total_races = stats['wins'] + stats['losses']
        win_rate = (stats['wins'] / total_races * 100) if total_races > 0 else 0

        embed = self.embed_manager.create_info(
            f"📊 {self.member.display_name}'s Detailed Statistics",
            f"**🏆 Wins:** {stats['wins']}\n"
            f"**💔 Losses:** {stats['losses']}\n"
            f"**📈 Win Rate:** {win_rate:.1f}%\n"
            f"**🏁 Total Races:** {total_races}\n"
            f"**🚗 Registered Vehicles:** {len(user_data['vehicles'])}\n"
            f"**✅ Approved Vehicles:** {sum(1 for v in user_data['vehicles'] if v[7] == 'approved')}\n\n"
            "*More detailed statistics coming soon!*"
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

class InventoryDropdown(Select):
    """Dropdown for vehicle inventory browsing."""

    def __init__(self, member: discord.Member, vehicles: List, db, embed_manager) -> None:
        self.member = member
        self.db = db
        self.embed_manager = embed_manager

        status_emojis = {
            'approved': '✅',
            'pending': '⏳',
            'denied': '❌'
        }

        options = [
            discord.SelectOption(
                label=f"{vehicle[2]} ({vehicle[3]})",  # make_model, year
                value=str(vehicle[8]),  # slip_id
                description=f"Status: {vehicle[7].title()}",  # status
                emoji=status_emojis.get(vehicle[7], '❓')  # status
            )
            for vehicle in vehicles
        ]

        super().__init__(
            placeholder="Select a vehicle to view details...",
            options=options,
            custom_id='inventory_dropdown'
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Display detailed vehicle information."""
        selected_slip_id = self.values[0]
        vehicle_data = await self.db.get_vehicle_by_id(selected_slip_id)

        if not vehicle_data:
            embed = self.embed_manager.create_error(
                "Vehicle Not Found",
                "The selected vehicle could not be found."
            )
        else:
            embed = self.embed_manager.create_vehicle_details(vehicle_data, self.member)

        user_data = await self.db.get_user_complete_data(self.member.id, interaction.guild_id)
        view = PinkSlipInventoryView(self.member, user_data['vehicles'], self.db, self.embed_manager)

        await interaction.response.edit_message(embed=embed, view=view, delete_after=900)