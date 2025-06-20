
"""
Twitch Integration Module

A comprehensive Discord bot module for Twitch live stream announcements
and streamer monitoring functionality.
"""

from .twitch_announce_commands import TwitchAnnounceCommands
from .twitch_announce_handler import TwitchAnnounceHandler

__version__ = "1.0.0"
__author__ = "Twitch Integration Team"

# Make the main cogs easily accessible
async def setup(bot):
    """Setup function for the twitch module."""
    await bot.add_cog(TwitchAnnounceHandler(bot))
    await bot.add_cog(TwitchAnnounceCommands(bot))

__all__ = [
    'TwitchAnnounceCommands',
    'TwitchAnnounceHandler',
    'setup'
]
