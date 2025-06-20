import aiosqlite
import os
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import random

class PinkslipDatabase:
    """Centralized database management for the pinkslip system."""

    def __init__(self):
        self.db_path = "data/pinkslip.db"
        self.guild_settings_path = "data/guild_settings.db"

    async def initialize(self):
        """Initialize all database tables."""
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)

        # Initialize main pinkslip database
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS vehicles (
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    make_model TEXT NOT NULL,
                    year TEXT NOT NULL,
                    engine_spec TEXT NOT NULL,
                    transmission TEXT NOT NULL,
                    steam_id TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    slip_id TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, guild_id, make_model, year)
                )
            ''')

            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, guild_id)
                )
            ''')

            await db.execute('''
                CREATE TABLE IF NOT EXISTS race_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    winner_id INTEGER NOT NULL,
                    loser_id INTEGER NOT NULL,
                    vehicle_slip_id TEXT NOT NULL,
                    race_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            await db.commit()

        # Initialize guild settings database
        async with aiosqlite.connect(self.guild_settings_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    review_channel_id INTEGER,
                    notification_channel_id INTEGER
                )
            ''')
            await db.commit()

    async def create_vehicle_registration(self, user_id: int, guild_id: int, 
                                        vehicle_data: Dict[str, str]) -> Tuple[bool, str]:
        """Create a new vehicle registration."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Check for duplicates
                async with db.execute('''
                    SELECT 1 FROM vehicles 
                    WHERE user_id = ? AND guild_id = ? AND make_model = ? AND year = ?
                ''', (user_id, guild_id, vehicle_data['make_model'], vehicle_data['year'])) as cursor:
                    if await cursor.fetchone():
                        return False, "duplicate"

                # Generate unique slip ID
                slip_id = str(user_id + guild_id + random.randint(1000, 9999))

                # Insert new registration
                await db.execute('''
                    INSERT INTO vehicles 
                    (user_id, guild_id, make_model, year, engine_spec, transmission, steam_id, status, slip_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, guild_id, vehicle_data['make_model'], vehicle_data['year'],
                    vehicle_data['engine_spec'], vehicle_data['transmission'], 
                    vehicle_data['steam_id'], 'pending', slip_id
                ))
                await db.commit()

                return True, slip_id

        except Exception as e:
            return False, str(e)

    async def update_vehicle_status(self, user_id: int, guild_id: int, 
                                  make_model: str, year: str, status: str) -> bool:
        """Update vehicle approval status."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    UPDATE vehicles SET status = ? 
                    WHERE user_id = ? AND guild_id = ? AND make_model = ? AND year = ?
                ''', (status, user_id, guild_id, make_model, year))

                await db.commit()
                return cursor.rowcount > 0

        except Exception:
            return False

    async def get_user_complete_data(self, user_id: int, guild_id: int) -> Dict[str, Any]:
        """Get complete user data including vehicles and stats."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Get vehicles
                async with db.execute('''
                    SELECT * FROM vehicles WHERE user_id = ? AND guild_id = ?
                    ORDER BY created_at DESC
                ''', (user_id, guild_id)) as cursor:
                    vehicles = await cursor.fetchall()

                # Get stats
                async with db.execute('''
                    SELECT wins, losses FROM user_stats 
                    WHERE user_id = ? AND guild_id = ?
                ''', (user_id, guild_id)) as cursor:
                    stats_row = await cursor.fetchone()

                stats = {
                    'wins': stats_row[0] if stats_row else 0,
                    'losses': stats_row[1] if stats_row else 0
                }

                return {
                    'vehicles': vehicles,
                    'stats': stats
                }

        except Exception:
            return {'vehicles': [], 'stats': {'wins': 0, 'losses': 0}}

    async def get_vehicle_by_id(self, slip_id: str) -> Optional[Tuple]:
        """Get vehicle data by slip ID."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('''
                    SELECT * FROM vehicles WHERE slip_id = ?
                ''', (slip_id,)) as cursor:
                    return await cursor.fetchone()
        except Exception:
            return None

    async def transfer_vehicle_ownership(self, slip_id: str, new_owner_id: int, guild_id: int) -> bool:
        """Transfer vehicle ownership."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    UPDATE vehicles SET user_id = ? 
                    WHERE slip_id = ? AND guild_id = ?
                ''', (new_owner_id, slip_id, guild_id))

                await db.commit()
                return cursor.rowcount > 0

        except Exception:
            return False

    async def delete_vehicle(self, slip_id: str, guild_id: int) -> bool:
        """Delete a vehicle registration."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    DELETE FROM vehicles WHERE slip_id = ? AND guild_id = ?
                ''', (slip_id, guild_id))

                await db.commit()
                return cursor.rowcount > 0

        except Exception:
            return False

    async def delete_vehicle_by_details(self, user_id: int, guild_id: int, 
                                      make_model: str, year: str) -> bool:
        """Delete vehicle by user and vehicle details."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    DELETE FROM vehicles 
                    WHERE user_id = ? AND guild_id = ? AND make_model = ? AND year = ?
                ''', (user_id, guild_id, make_model, year))

                await db.commit()
                return cursor.rowcount > 0

        except Exception:
            return False

    async def update_user_stats(self, user_id: int, guild_id: int, stat_type: str, amount: int = 1) -> None:
        """Update user racing statistics."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Ensure user exists in stats table
                await db.execute('''
                    INSERT OR IGNORE INTO user_stats (user_id, guild_id, wins, losses)
                    VALUES (?, ?, 0, 0)
                ''', (user_id, guild_id))

                # Update the specific stat
                if stat_type == "wins":
                    await db.execute('''
                        UPDATE user_stats SET wins = wins + ? 
                        WHERE user_id = ? AND guild_id = ?
                    ''', (amount, user_id, guild_id))
                elif stat_type == "losses":
                    await db.execute('''
                        UPDATE user_stats SET losses = losses + ? 
                        WHERE user_id = ? AND guild_id = ?
                    ''', (amount, user_id, guild_id))

                await db.commit()

        except Exception:
            pass

    async def modify_user_stats(self, user_id: int, guild_id: int, stat_type: str, 
                              action: str, amount: int) -> int:
        """Modify user statistics for admin commands."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Ensure user exists
                await db.execute('''
                    INSERT OR IGNORE INTO user_stats (user_id, guild_id, wins, losses)
                    VALUES (?, ?, 0, 0)
                ''', (user_id, guild_id))

                # Calculate change
                change = amount if action == "add" else -amount

                if stat_type == "wins":
                    await db.execute('''
                        UPDATE user_stats SET wins = MAX(0, wins + ?) 
                        WHERE user_id = ? AND guild_id = ?
                    ''', (change, user_id, guild_id))
                elif stat_type == "losses":
                    await db.execute('''
                        UPDATE user_stats SET losses = MAX(0, losses + ?) 
                        WHERE user_id = ? AND guild_id = ?
                    ''', (change, user_id, guild_id))

                await db.commit()

                # Return new value
                async with db.execute(f'''
                    SELECT {stat_type} FROM user_stats 
                    WHERE user_id = ? AND guild_id = ?
                ''', (user_id, guild_id)) as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else 0

        except Exception:
            return 0

    async def record_race_result(self, guild_id: int, winner_id: int, 
                               loser_id: int, vehicle_slip_id: str) -> bool:
        """Record a race result."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO race_results (guild_id, winner_id, loser_id, vehicle_slip_id)
                    VALUES (?, ?, ?, ?)
                ''', (guild_id, winner_id, loser_id, vehicle_slip_id))

                await db.commit()
                return True

        except Exception:
            return False

    async def get_guild_settings(self, guild_id: int) -> Optional[Tuple[int, int]]:
        """Get guild channel settings."""
        try:
            async with aiosqlite.connect(self.guild_settings_path) as db:
                async with db.execute('''
                    SELECT review_channel_id, notification_channel_id 
                    FROM guild_settings WHERE guild_id = ?
                ''', (guild_id,)) as cursor:
                    return await cursor.fetchone()
        except Exception:
            return None

    async def update_guild_settings(self, guild_id: int, review_channel_id: int, 
                                  notification_channel_id: int) -> bool:
        """Update guild channel settings."""
        try:
            async with aiosqlite.connect(self.guild_settings_path) as db:
                await db.execute('''
                    INSERT OR REPLACE INTO guild_settings 
                    (guild_id, review_channel_id, notification_channel_id)
                    VALUES (?, ?, ?)
                ''', (guild_id, review_channel_id, notification_channel_id))

                await db.commit()
                return True

        except Exception:
            return False