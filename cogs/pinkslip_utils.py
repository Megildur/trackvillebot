import discord
from typing import Dict, Tuple, Optional

class EmbedBuilder:
    """Centralized embed creation for consistent styling"""
    
    def __init__(self):
        self.color_primary = discord.Color.blue()
        self.color_success = discord.Color.green()
        self.color_error = discord.Color.red()
        self.color_warning = discord.Color.orange()
        self.color_info = discord.Color.blurple()
        self.footer_text = "Powered by Racing Management System"

    def _create_base_embed(self, title: str, description: str, color: discord.Color) -> discord.Embed:
        """Create a base embed with consistent styling"""
        embed = discord.Embed(title=title, description=description, color=color)
        embed.set_footer(text=self.footer_text)
        return embed

    def create_submission_intro_embed(self, guild: discord.Guild) -> discord.Embed:
        """Create the initial submission embed"""
        embed = self._create_base_embed(
            "🚗 Vehicle Registration System",
            "Welcome to the vehicle registration system! Please ensure you have all required information ready before submitting.\n\n"
            "**Required Information:**\n"
            "🔹 **Vehicle Make & Model**\n"
            "🔹 **Year of Manufacture**\n"
            "🔹 **Engine Specifications**\n"
            "🔹 **Transmission Type**\n"
            "🔹 **Steam ID**\n"
            "🔹 **Entry Fee Payment ($3)**\n\n"
            "⚠️ **Important:** All information must be accurate. False information will result in denial.\n\n"
            "Need assistance? Contact a staff member.",
            self.color_primary
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        return embed

    def create_success_embed(self, title: str, description: str) -> discord.Embed:
        """Create a success embed"""
        return self._create_base_embed(title, description, self.color_success)

    def create_error_embed(self, title: str, description: str) -> discord.Embed:
        """Create an error embed"""
        return self._create_base_embed(title, description, self.color_error)

    def create_info_embed(self, title: str, description: str) -> discord.Embed:
        """Create an info embed"""
        return self._create_base_embed(title, description, self.color_info)

    def create_warning_embed(self, title: str, description: str) -> discord.Embed:
        """Create a warning embed"""
        return self._create_base_embed(title, description, self.color_warning)

    def create_review_embed(self, user: discord.Member, vehicle_data: Dict[str, str]) -> discord.Embed:
        """Create embed for staff review"""
        embed = self._create_base_embed(
            "🔍 New Registration Pending Review",
            f"**Submitted by:** {user.mention}\n**User ID:** `{user.id}`",
            self.color_warning
        )
        
        embed.add_field(name="🚗 Make & Model", value=f"`{vehicle_data['make_model']}`", inline=True)
        embed.add_field(name="📅 Year", value=f"`{vehicle_data['year']}`", inline=True)
        embed.add_field(name="⚡ Engine Specs", value=f"`{vehicle_data['engine_spec']}`", inline=False)
        embed.add_field(name="⚙️ Transmission", value=f"`{vehicle_data['transmission']}`", inline=True)
        embed.add_field(name="🎮 Steam ID", value=f"`{vehicle_data['steam_id']}`", inline=True)
        
        embed.set_thumbnail(url=user.display_avatar.url)
        return embed

    def create_approval_notification_embed(self, approver: discord.Member, make_model: str, year: str) -> discord.Embed:
        """Create approval notification embed"""
        embed = self._create_base_embed(
            "✅ Registration Approved!",
            f"Your vehicle registration has been **approved** by {approver.mention}",
            self.color_success
        )
        
        embed.add_field(name="🚗 Vehicle", value=f"**{make_model}** ({year})", inline=False)
        embed.add_field(name="📋 Next Steps", value="Your vehicle is now registered and ready for racing!", inline=False)
        
        return embed

    def create_denial_notification_embed(self, denier: discord.Member, make_model: str, year: str, reason: str) -> discord.Embed:
        """Create denial notification embed"""
        embed = self._create_base_embed(
            "❌ Registration Denied",
            f"Your vehicle registration has been **denied** by {denier.mention}",
            self.color_error
        )
        
        embed.add_field(name="🚗 Vehicle", value=f"**{make_model}** ({year})", inline=False)
        embed.add_field(name="📝 Reason", value=reason, inline=False)
        embed.add_field(name="🔄 Resubmission", value="You may resubmit after addressing the issues mentioned above.", inline=False)
        
        return embed

    def create_denial_embed(self, embed_data: Dict, reason: str) -> discord.Embed:
        """Create denial summary for staff"""
        embed = self._create_base_embed(
            "❌ Registration Denied",
            f"<@{embed_data['user_id']}> has been notified of the denial.",
            self.color_error
        )
        
        embed.add_field(name="🚗 Vehicle", value=f"{embed_data['make_model']} - {embed_data['year']}", inline=False)
        embed.add_field(name="📝 Denial Reason", value=reason, inline=False)
        
        return embed

    def create_inventory_embed(self, member: discord.Member, vehicle_count: int, win_loss_stats: Tuple[int, int]) -> discord.Embed:
        """Create inventory overview embed"""
        wins, losses = win_loss_stats
        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        
        embed = self._create_base_embed(
            f"🏁 {member.display_name}'s Racing Profile",
            f"**Registered Vehicles:** {vehicle_count}\n\n"
            f"**Race Statistics:**\n"
            f"🏆 **Wins:** {wins}\n"
            f"💔 **Losses:** {losses}\n"
            f"📊 **Win Rate:** {win_rate:.1f}%\n\n"
            f"Select a vehicle below to view detailed information.",
            self.color_primary
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        return embed

    def create_detailed_pinkslip_embed(self, pinkslip_data: Tuple, member: discord.Member) -> discord.Embed:
        """Create detailed vehicle information embed"""
        user_id, guild_id, make_model, year, engine_spec, transmission, status, slip_id, created_at = pinkslip_data
        
        status_emoji = "✅" if status == "approved" else "⏳" if status == "pending" else "❌"
        status_color = self.color_success if status == "approved" else self.color_warning
        
        embed = discord.Embed(
            title=f"🚗 {make_model} ({year})",
            description=f"**Registration ID:** `{slip_id}`\n**Status:** {status_emoji} {status.title()}",
            color=status_color
        )
        
        embed.add_field(name="⚡ Engine Specifications", value=f"`{engine_spec}`", inline=False)
        embed.add_field(name="⚙️ Transmission", value=f"`{transmission}`", inline=False)
        embed.add_field(name="👤 Owner", value=member.mention, inline=True)
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=self.footer_text)
        return embed

    def create_race_tracker_embed(self, guild: discord.Guild) -> discord.Embed:
        """Create race tracker embed"""
        embed = self._create_base_embed(
            "🏁 Race Results Tracker",
            "Select the outcome of your race below. This will update your statistics and handle vehicle transfers if applicable.\n\n"
            "⚠️ **Warning:** False claims will result in penalties. Only report actual race results.",
            self.color_warning
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        return embed

    def create_transfer_confirmation_embed(self, initiator: discord.Member, target: discord.Member, 
                                         make_model: str, year: str, outcome: str) -> discord.Embed:
        """Create transfer confirmation embed"""
        if outcome == "win":
            title = "🏆 Victory Claim - Confirmation Required"
            description = (f"{initiator.mention} claims victory against {target.mention} and has initiated "
                          f"transfer of **{make_model} ({year})** to their ownership.")
        else:
            title = "💔 Loss Reported - Confirmation Required"
            description = (f"{initiator.mention} reported a loss to {target.mention} and has transferred "
                          f"their **{make_model} ({year})** to {target.mention}.")
        
        embed = self._create_base_embed(title, description, self.color_warning)
        embed.add_field(
            name="⚠️ Confirmation Required",
            value=f"{target.mention}, please confirm if this race result is accurate.",
            inline=False
        )
        embed.add_field(
            name="🚨 Important",
            value="If this claim is fraudulent, please contact staff immediately after denying.",
            inline=False
        )
        
        return embed

class MessageFormatter:
    """Utility class for message formatting"""
    
    @staticmethod
    def format_vehicle_name(make_model: str, year: str) -> str:
        """Format vehicle name consistently"""
        return f"{make_model} ({year})"
    
    @staticmethod
    def format_win_loss_ratio(wins: int, losses: int) -> str:
        """Format win/loss ratio"""
        total = wins + losses
        if total == 0:
            return "No races yet"
        win_rate = (wins / total) * 100
        return f"{wins}W-{losses}L ({win_rate:.1f}%)"
    
    @staticmethod
    def format_slip_id(slip_id: int) -> str:
        """Format slip ID for display"""
        return f"#{slip_id:06d}"