
import re
from typing import List, Optional

class ValidationHelper:
    """Input validation utilities for the pinkslip system."""
    
    @staticmethod
    def validate_year(year_str: str) -> bool:
        """Validate manufacturing year."""
        if not year_str.isdigit():
            return False
        year = int(year_str)
        return 1990 <= year <= 2024
    
    @staticmethod
    def validate_steam_id(steam_id: str) -> bool:
        """Validate Steam ID format (17 digits)."""
        return steam_id.isdigit() and len(steam_id) == 17
    
    @staticmethod
    def validate_make_model(make_model: str) -> bool:
        """Validate vehicle make and model."""
        clean_text = make_model.strip()
        return len(clean_text) >= 3 and not clean_text.isdigit()
    
    @staticmethod
    def validate_engine_spec(engine_spec: str) -> bool:
        """Validate engine specifications."""
        clean_text = engine_spec.strip()
        return len(clean_text) >= 5
    
    @staticmethod
    def validate_transmission(transmission: str) -> bool:
        """Validate transmission information."""
        clean_text = transmission.strip()
        return len(clean_text) >= 3
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = 500) -> str:
        """Sanitize and clean text input."""
        # Remove excessive whitespace and limit length
        cleaned = ' '.join(text.split())
        return cleaned[:max_length] if len(cleaned) > max_length else cleaned
    
    @staticmethod
    def validate_slip_id_format(slip_id: str) -> bool:
        """Validate slip ID format."""
        return slip_id.isdigit() and len(slip_id) >= 8
    
    @staticmethod
    def extract_user_id_from_mention(mention: str) -> Optional[str]:
        """Extract user ID from Discord mention."""
        pattern = r'<@!?(\d+)>'
        match = re.search(pattern, mention)
        return match.group(1) if match else None
    
    @staticmethod
    def validate_vehicle_data(vehicle_data: dict) -> List[str]:
        """Comprehensive vehicle data validation."""
        errors = []
        
        # Validate each field
        if not ValidationHelper.validate_make_model(vehicle_data.get('make_model', '')):
            errors.append("❌ Vehicle make and model must be at least 3 characters")
        
        if not ValidationHelper.validate_year(vehicle_data.get('year', '')):
            errors.append("❌ Year must be between 1990 and 2024")
        
        if not ValidationHelper.validate_engine_spec(vehicle_data.get('engine_spec', '')):
            errors.append("❌ Engine specifications must be more detailed (minimum 5 characters)")
        
        if not ValidationHelper.validate_transmission(vehicle_data.get('transmission', '')):
            errors.append("❌ Transmission information must be at least 3 characters")
        
        if not ValidationHelper.validate_steam_id(vehicle_data.get('steam_id', '')):
            errors.append("❌ Steam ID must be exactly 17 digits")
        
        return errors

class SecurityHelper:
    """Security and permissions validation."""
    
    @staticmethod
    def check_channel_permissions(channel, bot_member) -> List[str]:
        """Check if bot has required permissions in channel."""
        required_perms = ['send_messages', 'embed_links', 'read_messages']
        missing_perms = []
        
        permissions = channel.permissions_for(bot_member)
        
        for perm in required_perms:
            if not getattr(permissions, perm, False):
                missing_perms.append(perm.replace('_', ' ').title())
        
        return missing_perms
    
    @staticmethod
    def is_admin_or_moderator(member) -> bool:
        """Check if member has admin or moderator permissions."""
        return (member.guild_permissions.administrator or 
                member.guild_permissions.manage_guild or
                member.guild_permissions.manage_messages)
    
    @staticmethod
    def validate_guild_setup(guild_settings) -> bool:
        """Validate guild has proper setup."""
        return guild_settings is not None and len(guild_settings) >= 2

class DataFormatter:
    """Data formatting utilities."""
    
    @staticmethod
    def format_vehicle_name(make_model: str, year: str) -> str:
        """Format vehicle name consistently."""
        return f"{make_model.strip()} ({year.strip()})"
    
    @staticmethod
    def format_stats_display(wins: int, losses: int) -> str:
        """Format win/loss statistics for display."""
        total = wins + losses
        if total == 0:
            return "No races completed"
        
        win_rate = (wins / total) * 100
        return f"{wins}W-{losses}L ({win_rate:.1f}%)"
    
    @staticmethod
    def format_slip_id(slip_id: str) -> str:
        """Format slip ID for consistent display."""
        return f"#{slip_id}"
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 100) -> str:
        """Truncate text with ellipsis if too long."""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    @staticmethod
    def format_timestamp(timestamp) -> str:
        """Format timestamp for Discord display."""
        if isinstance(timestamp, str):
            # Assume ISO format from database
            return f"<t:{int(timestamp)}:R>"
        return f"<t:{int(timestamp.timestamp())}:R>"
