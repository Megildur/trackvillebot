
import aiosqlite
import random
import os
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

class PinkslipDatabase:
    """Centralized database management for the pinkslip system."""
    
    def __init__(self):
        # Ensure data directory exists
        os.makedirs('data', exist_ok=True)
        self.db_path = 'data/pinkslip_system.db'

    async def initialize(self) -> None:
        """Initialize all database tables with proper indexes."""
        async with aiosqlite.connect(self.db_path) as db:
            # Enable foreign keys
            await db.execute('PRAGMA foreign_keys = ON')
            
            # Vehicles table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS vehicles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    make_model TEXT NOT NULL,
                    year TEXT NOT NULL,
                    engine_spec TEXT NOT NULL,
                    transmission TEXT NOT NULL,
                    steam_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    slip_id TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # User statistics table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, guild_id)
                )
            ''')
            
            # Guild settings table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    review_channel_id INTEGER,
                    notification_channel_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Race history table for audit trail
            await db.execute('''
                CREATE TABLE IF NOT EXISTS race_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    winner_id INTEGER NOT NULL,
                    loser_id INTEGER NOT NULL,
                    vehicle_id TEXT,
                    confirmed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            await db.execute('CREATE INDEX IF NOT EXISTS idx_vehicles_user_guild ON vehicles(user_id, guild_id)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_vehicles_slip_id ON vehicles(slip_id)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_user_stats_guild ON user_stats(guild_id)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_race_history_guild ON race_history(guild_id)')
            
            await db.commit()

    async def create_vehicle_registration(self, user_id: int, guild_id: int, vehicle_data: Dict[str, str]) -> Tuple[bool, str]:
        """Create a new vehicle registration with duplicate checking."""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                # Check for duplicates
                async with db.execute('''
                    SELECT COUNT(*) FROM vehicles 
                    WHERE user_id = ? AND guild_id = ? AND make_model = ? AND year = ?
                ''', (user_id, guild_id, vehicle_data['make_model'], vehicle_data['year'])) as cursor:
                    count = (await cursor.fetchone())[0]
                    if count > 0:
                        return False, "duplicate"

                # Generate unique slip ID
                slip_id = await self._generate_unique_slip_id(db, user_id)
                
                await db.execute('''
                    INSERT INTO vehicles 
                    (user_id, guild_id, make_model, year, engine_spec, transmission, steam_id, status, slip_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                ''', (
                    user_id, guild_id, vehicle_data['make_model'], vehicle_data['year'],
                    vehicle_data['engine_spec'], vehicle_data['transmission'],
                    vehicle_data['steam_id'], slip_id
                ))
                
                await db.commit()
                return True, slip_id

            except Exception as e:
                await db.rollback()
                return False, str(e)

    async def get_user_complete_data(self, user_id: int, guild_id: int) -> Dict[str, Any]:
        """Get complete user data including vehicles and statistics."""
        async with aiosqlite.connect(self.db_path) as db:
            # Get vehicles with all necessary fields
            async with db.execute('''
                SELECT user_id, guild_id, make_model, year, engine_spec, transmission, steam_id, status, slip_id, created_at
                FROM vehicles 
                WHERE user_id = ? AND guild_id = ?
                ORDER BY created_at DESC
            ''', (user_id, guild_id)) as cursor:
                vehicles = await cursor.fetchall()

            # Get statistics
            async with db.execute('''
                SELECT wins, losses FROM user_stats 
                WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id)) as cursor:
                stats = await cursor.fetchone()
                wins, losses = stats if stats else (0, 0)

            return {
                'vehicles': vehicles,
                'stats': {'wins': wins, 'losses': losses}
            }

    async def get_vehicle_by_id(self, slip_id: str) -> Optional[Tuple]:
        """Get vehicle details by slip ID."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT user_id, guild_id, make_model, year, engine_spec, transmission, steam_id, status, slip_id, created_at
                FROM vehicles WHERE slip_id = ?
            ''', (slip_id,)) as cursor:
                return await cursor.fetchone()

    async def update_vehicle_status(self, user_id: int, guild_id: int, make_model: str, year: str, status: str) -> bool:
        """Update vehicle approval status."""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute('''
                    UPDATE vehicles 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND guild_id = ? AND make_model = ? AND year = ?
                ''', (status, user_id, guild_id, make_model, year))
                
                await db.commit()
                return True
            except Exception:
                await db.rollback()
                return False

    async def delete_vehicle_by_details(self, user_id: int, guild_id: int, make_model: str, year: str) -> bool:
        """Delete vehicle by user details."""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute('''
                    DELETE FROM vehicles 
                    WHERE user_id = ? AND guild_id = ? AND make_model = ? AND year = ?
                ''', (user_id, guild_id, make_model, year))
                
                await db.commit()
                return True
            except Exception:
                await db.rollback()
                return False

    async def transfer_vehicle_ownership(self, slip_id: str, new_owner_id: int, guild_id: int) -> bool:
        """Transfer vehicle ownership with validation."""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                # Check if vehicle exists and get current owner
                async with db.execute('''
                    SELECT user_id FROM vehicles WHERE slip_id = ? AND guild_id = ? AND status = 'approved'
                ''', (slip_id, guild_id)) as cursor:
                    result = await cursor.fetchone()
                    if not result:
                        return False
                    
                    # Don't transfer if already owned by new_owner_id
                    if result[0] == new_owner_id:
                        return False

                # Update ownership
                result = await db.execute('''
                    UPDATE vehicles 
                    SET user_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE slip_id = ? AND guild_id = ?
                ''', (new_owner_id, slip_id, guild_id))
                
                await db.commit()
                return result.rowcount > 0
            except Exception:
                await db.rollback()
                return False

    async def delete_vehicle(self, slip_id: str, guild_id: int) -> bool:
        """Delete vehicle by slip ID."""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                result = await db.execute('''
                    DELETE FROM vehicles WHERE slip_id = ? AND guild_id = ?
                ''', (slip_id, guild_id))
                
                await db.commit()
                return result.rowcount > 0
            except Exception:
                await db.rollback()
                return False

    async def get_guild_settings(self, guild_id: int) -> Optional[Tuple[int, int]]:
        """Get guild configuration settings."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT review_channel_id, notification_channel_id 
                FROM guild_settings WHERE guild_id = ?
            ''', (guild_id,)) as cursor:
                return await cursor.fetchone()

    async def update_guild_settings(self, guild_id: int, review_channel: int, notification_channel: int) -> None:
        """Update guild settings with upsert logic."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO guild_settings 
                (guild_id, review_channel_id, notification_channel_id, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (guild_id, review_channel, notification_channel))
            await db.commit()

    async def update_user_stats(self, user_id: int, guild_id: int, stat_type: str, increment: int = 1) -> None:
        """Update user statistics with upsert logic."""
        async with aiosqlite.connect(self.db_path) as db:
            if stat_type == "wins":
                await db.execute('''
                    INSERT OR REPLACE INTO user_stats 
                    (user_id, guild_id, wins, losses, updated_at)
                    VALUES (?, ?, 
                        COALESCE((SELECT wins FROM user_stats WHERE user_id = ? AND guild_id = ?), 0) + ?,
                        COALESCE((SELECT losses FROM user_stats WHERE user_id = ? AND guild_id = ?), 0),
                        CURRENT_TIMESTAMP)
                ''', (user_id, guild_id, user_id, guild_id, increment, user_id, guild_id))
            else:
                await db.execute('''
                    INSERT OR REPLACE INTO user_stats 
                    (user_id, guild_id, wins, losses, updated_at)
                    VALUES (?, ?, 
                        COALESCE((SELECT wins FROM user_stats WHERE user_id = ? AND guild_id = ?), 0),
                        COALESCE((SELECT losses FROM user_stats WHERE user_id = ? AND guild_id = ?), 0) + ?,
                        CURRENT_TIMESTAMP)
                ''', (user_id, guild_id, user_id, guild_id, user_id, guild_id, increment))
            
            await db.commit()

    async def modify_user_stats(self, user_id: int, guild_id: int, stat_type: str, action: str, amount: int) -> int:
        """Modify user statistics for administrative purposes."""
        async with aiosqlite.connect(self.db_path) as db:
            # Get current stats
            async with db.execute('''
                SELECT wins, losses FROM user_stats WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id)) as cursor:
                current = await cursor.fetchone()
                wins, losses = current if current else (0, 0)

            # Calculate new value
            if stat_type == "wins":
                new_value = max(0, wins + amount if action == "add" else wins - amount)
                await db.execute('''
                    INSERT OR REPLACE INTO user_stats 
                    (user_id, guild_id, wins, losses, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, guild_id, new_value, losses))
            else:
                new_value = max(0, losses + amount if action == "add" else losses - amount)
                await db.execute('''
                    INSERT OR REPLACE INTO user_stats 
                    (user_id, guild_id, wins, losses, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, guild_id, wins, new_value))

            await db.commit()
            return new_value

    async def record_race_result(self, guild_id: int, winner_id: int, loser_id: int, vehicle_id: str = None) -> None:
        """Record race result for audit purposes."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO race_history (guild_id, winner_id, loser_id, vehicle_id)
                VALUES (?, ?, ?, ?)
            ''', (guild_id, winner_id, loser_id, vehicle_id))
            await db.commit()

    async def _generate_unique_slip_id(self, db: aiosqlite.Connection, user_id: int) -> str:
        """Generate a unique slip ID."""
        while True:
            slip_id = f"{user_id}{random.randint(1000, 9999)}"
            async with db.execute('SELECT COUNT(*) FROM vehicles WHERE slip_id = ?', (slip_id,)) as cursor:
                count = (await cursor.fetchone())[0]
                if count == 0:
                    return slip_id
