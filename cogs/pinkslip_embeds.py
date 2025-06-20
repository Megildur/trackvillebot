
import discord
from typing import Dict, Tuple, Any
from datetime import datetime

class EmbedManager:
    """Professional embed creation with consistent branding and styling."""
    
    def __init__(self):
        # Professional color scheme
        self.colors = {
            'primary': discord.Color.from_rgb(70, 130, 180),      # Steel Blue
            'success': discord.Color.from_rgb(46, 125, 50),       # Green
            'error': discord.Color.from_rgb(211, 47, 47),         # Red
            'warning': discord.Color.from_rgb(255, 152, 0),       # Orange
            'info': discord.Color.from_rgb(66, 165, 245),         # Light Blue
            'neutral': discord.Color.from_rgb(97, 97, 97)         # Gray
        }
        
        self.footer_text = "Professional Racing Management System"
        self.thumbnail_url = "https://cdn.discordapp.com/attachments/your-logo-here.png"  # Replace with actual logo

    def _create_base_embed(self, title: str, description: str, color: discord.Color) -> discord.Embed:
        """Create a professionally styled base embed."""
        embed = discord.Embed(title=title, description=description, color=color)
        embed.set_footer(text=self.footer_text, icon_url=self.thumbnail_url)
        embed.timestamp = datetime.utcnow()
        return embed

    def create_submission_intro(self, guild: discord.Guild) -> discord.Embed:
        """Create an engaging vehicle registration introduction."""
        embed = self._create_base_embed(
            "🏁 Vehicle Registration Portal",
            "**Welcome to the Professional Racing Registry**\n\n"
            "Register your vehicle to participate in official racing events. "
            "All submissions undergo thorough review by our racing officials.\n\n"
            "**📋 Required Information:**\n"
            "▫️ Vehicle Make & Model\n"
            "▫️ Manufacturing Year\n"
            "▫️ Engine Specifications\n"
            "▫️ Transmission Details\n"
            "▫️ Steam Platform ID\n\n"
            "**⚠️ Important Guidelines:**\n"
            "• All information must be accurate and verifiable\n"
            "• Entry fee of **$3 USD** is required\n"
            "• Processing typically takes 24-48 hours\n"
            "• False information will result in immediate denial\n\n"
            "*Ready to register? Click the button below to begin.*",
            self.colors['primary']
        )
        
        if guild and guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.add_field(
            name="💡 Need Help?",
            value="Contact our support team for assistance with your registration.",
            inline=False
        )
        
        return embed

    def create_success(self, title: str, description: str) -> discord.Embed:
        """Create a success notification embed."""
        embed = self._create_base_embed(f"✅ {title}", description, self.colors['success'])
        return embed

    def create_error(self, title: str, description: str) -> discord.Embed:
        """Create an error notification embed."""
        embed = self._create_base_embed(f"❌ {title}", description, self.colors['error'])
        return embed

    def create_info(self, title: str, description: str) -> discord.Embed:
        """Create an informational embed."""
        embed = self._create_base_embed(f"ℹ️ {title}", description, self.colors['info'])
        return embed

    def create_warning(self, title: str, description: str) -> discord.Embed:
        """Create a warning embed."""
        embed = self._create_base_embed(f"⚠️ {title}", description, self.colors['warning'])
        return embed

    def create_review_request(self, user: discord.Member, vehicle_data: Dict[str, str]) -> discord.Embed:
        """Create a professional review request for staff."""
        embed = self._create_base_embed(
            "🔍 Registration Review Required",
            f"**Applicant:** {user.mention} (`{user.id}`)\n"
            f"**Submitted:** <t:{int(datetime.utcnow().timestamp())}:R>\n\n"
            "*Please review the following vehicle registration for approval or denial.*",
            self.colors['warning']
        )
        
        embed.add_field(
            name="🚗 Vehicle Details",
            value=f"**Make/Model:** {vehicle_data['make_model']}\n"
                  f"**Year:** {vehicle_data['year']}",
            inline=True
        )
        
        embed.add_field(
            name="⚡ Performance Specs",
            value=f"**Engine:** {vehicle_data['engine_spec']}\n"
                  f"**Transmission:** {vehicle_data['transmission']}",
            inline=True
        )
        
        embed.add_field(
            name="🎮 Platform Information",
            value=f"**Steam ID:** `{vehicle_data['steam_id']}`",
            inline=False
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        return embed

    def create_approval_notification(self, approver: discord.Member, vehicle: str, year: str) -> discord.Embed:
        """Create an approval notification for users."""
        embed = self._create_base_embed(
            "🎉 Registration Approved!",
            f"Congratulations! Your vehicle registration has been **approved** by our racing officials.\n\n"
            f"**Approved by:** {approver.mention}\n"
            f"**Vehicle:** {vehicle} ({year})\n"
            f"**Approval Date:** <t:{int(datetime.utcnow().timestamp())}:F>\n\n"
            "**Next Steps:**\n"
            "▫️ Your vehicle is now eligible for official races\n"
            "▫️ Use `/pinkslip race result` to record race outcomes\n"
            "▫️ View your profile with `/pinkslip view profile`\n\n"
            "*Welcome to the racing community!* 🏁",
            self.colors['success']
        )
        return embed

    def create_denial_notification(self, staff_member: discord.Member, vehicle: str, year: str, reason: str) -> discord.Embed:
        """Create a denial notification for users."""
        embed = self._create_base_embed(
            "Registration Review Complete",
            f"After careful review, your vehicle registration has been **declined**.\n\n"
            f"**Reviewed by:** {staff_member.mention}\n"
            f"**Vehicle:** {vehicle} ({year})\n"
            f"**Review Date:** <t:{int(datetime.utcnow().timestamp())}:F>",
            self.colors['error']
        )
        
        embed.add_field(
            name="📝 Reason for Denial",
            value=reason,
            inline=False
        )
        
        embed.add_field(
            name="🔄 Resubmission Process",
            value="You may resubmit your registration after addressing the issues mentioned above. "
                  "Please ensure all information is accurate and complete.",
            inline=False
        )
        
        return embed

    def create_profile_overview(self, member: discord.Member, user_data: Dict[str, Any]) -> discord.Embed:
        """Create a comprehensive user profile overview."""
        stats = user_data['stats']
        vehicle_count = len(user_data['vehicles'])
        
        wins, losses = stats['wins'], stats['losses']
        total_races = wins + losses
        win_rate = (wins / total_races * 100) if total_races > 0 else 0
        
        # Determine rank based on performance
        if total_races >= 20 and win_rate >= 80:
            rank = "🏆 Champion"
            rank_color = self.colors['success']
        elif total_races >= 10 and win_rate >= 60:
            rank = "🥇 Expert"
            rank_color = self.colors['primary']
        elif total_races >= 5:
            rank = "🥈 Intermediate"
            rank_color = self.colors['info']
        else:
            rank = "🥉 Novice"
            rank_color = self.colors['neutral']
            
        embed = discord.Embed(
            title=f"🏁 {member.display_name}'s Racing Profile",
            description=f"**Rank:** {rank}\n**Member Since:** <t:{int(member.created_at.timestamp())}:D>",
            color=rank_color
        )
        
        embed.add_field(
            name="🚗 Fleet Overview",
            value=f"**Registered Vehicles:** {vehicle_count}\n"
                  f"**Active Registrations:** {sum(1 for v in user_data['vehicles'] if v[4] == 'approved')}",
            inline=True
        )
        
        embed.add_field(
            name="📊 Race Statistics",
            value=f"**Wins:** {wins} 🏆\n"
                  f"**Losses:** {losses} 💔\n"
                  f"**Win Rate:** {win_rate:.1f}%",
            inline=True
        )
        
        embed.add_field(
            name="📈 Performance",
            value=f"**Total Races:** {total_races}\n"
                  f"**Current Streak:** Computing...\n"
                  f"**Best Season:** Computing...",
            inline=True
        )
        
        if user_data['vehicles']:
            latest_vehicle = user_data['vehicles'][0]
            embed.add_field(
                name="🆕 Latest Registration",
                value=f"**{latest_vehicle[2]}** ({latest_vehicle[3]})\n"
                      f"Status: {latest_vehicle[7].title()}",
                inline=False
            )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(
            name="🔍 Vehicle Details",
            value="*Use the dropdown below to view detailed information about each vehicle.*",
            inline=False
        )
        
        return embed

    def create_vehicle_details(self, vehicle_data: Tuple, member: discord.Member) -> discord.Embed:
        """Create detailed vehicle information display."""
        user_id, guild_id, make_model, year, engine_spec, transmission, steam_id, status, slip_id, created_at = vehicle_data
        
        status_colors = {
            'approved': self.colors['success'],
            'pending': self.colors['warning'],
            'denied': self.colors['error']
        }
        
        status_emojis = {
            'approved': '✅',
            'pending': '⏳',
            'denied': '❌'
        }
        
        embed = discord.Embed(
            title=f"🚗 {make_model} ({year})",
            description=f"**Registration ID:** `{slip_id}`\n"
                       f"**Status:** {status_emojis.get(status, '❓')} {status.title()}\n"
                       f"**Registered:** {created_at}",
            color=status_colors.get(status, self.colors['neutral'])
        )
        
        embed.add_field(
            name="⚡ Performance Specifications",
            value=f"```{engine_spec}```",
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Transmission System",
            value=f"```{transmission}```",
            inline=False
        )
        
        embed.add_field(
            name="👤 Owner Information",
            value=f"**Current Owner:** {member.mention}\n"
                  f"**Owner ID:** `{member.id}`",
            inline=True
        )
        
        if status == 'approved':
            embed.add_field(
                name="🏁 Racing Status",
                value="**Eligible for Official Races**\n"
                      "This vehicle is approved for competitive racing.",
                inline=True
            )
        elif status == 'pending':
            embed.add_field(
                name="⏳ Review Status",
                value="**Under Review**\n"
                      "Awaiting staff approval.",
                inline=True
            )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        return embed

    def create_race_tracker_intro(self, guild: discord.Guild) -> discord.Embed:
        """Create race tracking introduction."""
        embed = self._create_base_embed(
            "🏁 Official Race Results Portal",
            "**Record Your Race Outcome**\n\n"
            "Use this system to officially record race results and handle vehicle transfers. "
            "All results are logged for statistical tracking and leaderboard updates.\n\n"
            "**⚠️ Important Guidelines:**\n"
            "▫️ Only report actual race results\n"
            "▫️ Both parties must confirm transfers\n"
            "▫️ False claims result in penalties\n"
            "▫️ Disputes should be reported to staff\n\n"
            "*Select your race outcome below to proceed.*",
            self.colors['primary']
        )
        
        if guild and guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
            
        return embed

    def create_transfer_confirmation(self, initiator: discord.Member, opponent: discord.Member, 
                                   vehicle: str, year: str, outcome: str) -> discord.Embed:
        """Create transfer confirmation request."""
        if outcome == "win":
            title = "🏆 Victory Claim - Confirmation Required"
            description = (f"**Winner:** {initiator.mention}\n"
                          f"**Opponent:** {opponent.mention}\n\n"
                          f"{initiator.mention} has claimed victory and is requesting transfer of:\n"
                          f"**{vehicle} ({year})**")
            color = self.colors['success']
        else:
            title = "💔 Loss Reported - Confirmation Required" 
            description = (f"**Reporter:** {initiator.mention}\n"
                          f"**Opponent:** {opponent.mention}\n\n"
                          f"{initiator.mention} has reported a loss and is transferring:\n"
                          f"**{vehicle} ({year})**")
            color = self.colors['error']
        
        embed = self._create_base_embed(title, description, color)
        
        embed.add_field(
            name="✅ Confirmation Required",
            value=f"{opponent.mention}, please confirm this race result is accurate.\n"
                  "Click **Confirm** to proceed or **Dispute** if this is incorrect.",
            inline=False
        )
        
        embed.add_field(
            name="🚨 Important Notice",
            value="• Confirming will officially record this race result\n"
                  "• Vehicle ownership will be transferred\n" 
                  "• Statistics will be updated for both parties\n"
                  "• Fraudulent claims will result in penalties",
            inline=False
        )
        
        return embed

    def create_system_status(self, title: str, description: str, status_type: str = "info") -> discord.Embed:
        """Create system status embed."""
        color_map = {
            "success": self.colors['success'],
            "error": self.colors['error'], 
            "warning": self.colors['warning'],
            "info": self.colors['info']
        }
        
        return self._create_base_embed(title, description, color_map.get(status_type, self.colors['info']))
