
"""
Pinkslip Racing Management System

A comprehensive Discord bot module for managing vehicle registrations,
race tracking, and statistics in racing communities.
"""

from .pinkslip import PinkslipCog
from .pinkslip_database import PinkslipDatabase
from .pinkslip_embeds import EmbedManager
from .pinkslip_views import (
    PinkSlipSubmissionView,
    PinkSlipReviewView,
    RaceTrackerView,
    PinkSlipInventoryView,
    VehicleRegistrationModal,
    RegistrationDenialModal,
    InfoRequestModal,
    TransferConfirmationView
)
from .pinkslip_validators import ValidationHelper, SecurityHelper, DataFormatter

__version__ = "1.0.0"
__author__ = "Racing Management Team"

# Make the main cog easily accessible
async def setup(bot):
    """Setup function for the pinkslip module."""
    from .pinkslip import setup as pinkslip_setup
    await pinkslip_setup(bot)

__all__ = [
    'PinkslipCog',
    'PinkslipDatabase', 
    'EmbedManager',
    'PinkSlipSubmissionView',
    'PinkSlipReviewView',
    'RaceTrackerView',
    'PinkSlipInventoryView',
    'VehicleRegistrationModal',
    'RegistrationDenialModal',
    'InfoRequestModal',
    'TransferConfirmationView',
    'ValidationHelper',
    'SecurityHelper',
    'DataFormatter',
    'setup'
]
