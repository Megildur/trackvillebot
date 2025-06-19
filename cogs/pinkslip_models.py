
import aiosqlite
import random
from typing import List, Dict, Optional, Tuple

class PinkslipDatabase:
    def __init__(self):
        self.pinkslip_db = 'data/pinkslip.db'
        self.guild_settings_db = 'data/guild_settings.db'
        self.wins_loses_db = 'data/wins_loses.db'

    async def initialize_tables(self) -> None:
        """Initialize all database tables"""
        await self._create_pinkslip_table()
        await self._create_guild_settings_table()
        await self._create_wins_loses_table()

    async def _create_pinkslip_table(self) -> None:
        async with aiosqlite.connect(self.pinkslip_db) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS pinkslip (
                    user_id INTEGER, 
                    guild_id INTEGER,
                    make_model TEXT NOT NULL,
                    year TEXT NOT NULL,
                    engine_spec TEXT NOT NULL,
                    transmission TEXT NOT NULL,
                    steam_id TEXT NOT NULL,
                    approved TEXT NOT NULL,
                    slip_id INTEGER NOT NULL,
                    PRIMARY KEY (user_id, guild_id, slip_id)
                )
            ''')
            await db.commit()

    async def _create_guild_settings_table(self) -> None:
        async with aiosqlite.connect(self.guild_settings_db) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER NOT NULL,
                    pinkslip_channel INTEGER,
                    notification_channel INTEGER,
                    PRIMARY KEY (guild_id)
                )
            ''')
            await db.commit()

    async def _create_wins_loses_table(self) -> None:
        async with aiosqlite.connect(self.wins_loses_db) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS wins_loses (
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    wins INTEGER NOT NULL,
                    loses INTEGER NOT NULL,
                    PRIMARY KEY (user_id, guild_id)
                )
            ''')
            await db.commit()

    async def create_pinkslip(self, user_id: int, guild_id: int, vehicle_data: Dict[str, str]) -> Tuple[bool, str]:
        """Create a new pinkslip entry"""
        async with aiosqlite.connect(self.pinkslip_db) as db:
            # Check for duplicates
            async with db.execute(
                'SELECT make_model, year FROM pinkslip WHERE user_id = ? AND guild_id = ?',
                (user_id, guild_id)
            ) as cursor:
                existing_pinkslips = await cursor.fetchall()
                
                for existing in existing_pinkslips:
                    if (existing[0] == vehicle_data['make_model'] and 
                        existing[1] == vehicle_data['year']):
                        return False, "duplicate"

                # Generate unique slip ID
                slip_id = int(user_id) + len(existing_pinkslips) + 1 + random.randint(1, 999)
                
                await db.execute('''
                    INSERT INTO pinkslip 
                    (user_id, guild_id, make_model, year, engine_spec, transmission, steam_id, approved, slip_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, guild_id, vehicle_data['make_model'], vehicle_data['year'],
                    vehicle_data['engine_spec'], vehicle_data['transmission'],
                    vehicle_data['steam_id'], "pending approval", slip_id
                ))
                await db.commit()
                return True, str(slip_id)

    async def get_user_pinkslips(self, user_id: int, guild_id: int) -> List[Tuple]:
        """Get all pinkslips for a user"""
        async with aiosqlite.connect(self.pinkslip_db) as db:
            async with db.execute(
                'SELECT make_model, year, engine_spec, transmission, approved, slip_id FROM pinkslip WHERE user_id = ? AND guild_id = ?',
                (user_id, guild_id)
            ) as cursor:
                return await cursor.fetchall()

    async def get_pinkslip_by_id(self, slip_id: str) -> Optional[Tuple]:
        """Get pinkslip by slip_id"""
        async with aiosqlite.connect(self.pinkslip_db) as db:
            async with db.execute(
                'SELECT user_id, make_model, year, engine_spec, transmission, approved, slip_id FROM pinkslip WHERE slip_id = ?',
                (slip_id,)
            ) as cursor:
                return await cursor.fetchone()

    async def update_pinkslip_approval(self, user_id: str, guild_id: int, make_model: str, year: str, status: str) -> None:
        """Update pinkslip approval status"""
        async with aiosqlite.connect(self.pinkslip_db) as db:
            await db.execute(
                'UPDATE pinkslip SET approved = ? WHERE user_id = ? AND guild_id = ? AND make_model = ? AND year = ?',
                (status, user_id, guild_id, make_model, year)
            )
            await db.commit()

    async def delete_pinkslip_by_details(self, user_id: str, guild_id: int, make_model: str, year: str) -> None:
        """Delete pinkslip by user details"""
        async with aiosqlite.connect(self.pinkslip_db) as db:
            await db.execute(
                'DELETE FROM pinkslip WHERE user_id = ? AND guild_id = ? AND make_model = ? AND year = ?',
                (user_id, guild_id, make_model, year)
            )
            await db.commit()

    async def transfer_pinkslip_ownership(self, slip_id: str, new_owner_id: int, guild_id: int) -> bool:
        """Transfer pinkslip ownership"""
        async with aiosqlite.connect(self.pinkslip_db) as db:
            async with db.execute(
                'SELECT * FROM pinkslip WHERE slip_id = ? AND guild_id = ?',
                (slip_id, guild_id)
            ) as cursor:
                if await cursor.fetchone() is None:
                    return False
                
            await db.execute(
                'UPDATE pinkslip SET user_id = ? WHERE slip_id = ? AND guild_id = ?',
                (new_owner_id, slip_id, guild_id)
            )
            await db.commit()
            return True

    async def delete_pinkslip(self, slip_id: str, guild_id: int) -> bool:
        """Delete pinkslip by slip_id"""
        async with aiosqlite.connect(self.pinkslip_db) as db:
            async with db.execute(
                'SELECT * FROM pinkslip WHERE slip_id = ? AND guild_id = ?',
                (slip_id, guild_id)
            ) as cursor:
                if await cursor.fetchone() is None:
                    return False
                
            await db.execute(
                'DELETE FROM pinkslip WHERE slip_id = ? AND guild_id = ?',
                (slip_id, guild_id)
            )
            await db.commit()
            return True

    async def get_guild_settings(self, guild_id: int) -> Optional[Tuple[int, int]]:
        """Get guild pinkslip settings"""
        async with aiosqlite.connect(self.guild_settings_db) as db:
            async with db.execute(
                'SELECT pinkslip_channel, notification_channel FROM guild_settings WHERE guild_id = ?',
                (guild_id,)
            ) as cursor:
                return await cursor.fetchone()

    async def update_guild_settings(self, guild_id: int, pinkslip_channel: int, notification_channel: int) -> None:
        """Update guild settings"""
        async with aiosqlite.connect(self.guild_settings_db) as db:
            async with db.execute(
                'SELECT * FROM guild_settings WHERE guild_id = ?',
                (guild_id,)
            ) as cursor:
                if await cursor.fetchone() is not None:
                    await db.execute(
                        'UPDATE guild_settings SET pinkslip_channel = ?, notification_channel = ? WHERE guild_id = ?',
                        (pinkslip_channel, notification_channel, guild_id)
                    )
                else:
                    await db.execute(
                        'INSERT INTO guild_settings (guild_id, pinkslip_channel, notification_channel) VALUES (?, ?, ?)',
                        (guild_id, pinkslip_channel, notification_channel)
                    )
                await db.commit()

    async def get_win_loss_stats(self, user_id: int, guild_id: int) -> Tuple[int, int]:
        """Get win/loss statistics for a user"""
        async with aiosqlite.connect(self.wins_loses_db) as db:
            async with db.execute(
                'SELECT wins, loses FROM wins_loses WHERE user_id = ? AND guild_id = ?',
                (user_id, guild_id)
            ) as cursor:
                result = await cursor.fetchone()
                return result if result else (0, 0)

    async def update_win_loss_stats(self, user_id: int, guild_id: int, stat: str, increment: int = 1) -> None:
        """Update win/loss statistics"""
        async with aiosqlite.connect(self.wins_loses_db) as db:
            async with db.execute(
                'SELECT wins, loses FROM wins_loses WHERE user_id = ? AND guild_id = ?',
                (user_id, guild_id)
            ) as cursor:
                current_stats = await cursor.fetchone()
                
                if current_stats:
                    wins, loses = current_stats
                    if stat == "wins":
                        wins += increment
                    else:
                        loses += increment
                    
                    await db.execute(
                        'UPDATE wins_loses SET wins = ?, loses = ? WHERE user_id = ? AND guild_id = ?',
                        (wins, loses, user_id, guild_id)
                    )
                else:
                    wins = increment if stat == "wins" else 0
                    loses = increment if stat == "loses" else 0
                    await db.execute(
                        'INSERT INTO wins_loses (user_id, guild_id, wins, loses) VALUES (?, ?, ?, ?)',
                        (user_id, guild_id, wins, loses)
                    )
                await db.commit()

    async def modify_win_loss_stats(self, user_id: int, guild_id: int, stat: str, action: str, amount: int) -> int:
        """Modify win/loss statistics (admin function)"""
        async with aiosqlite.connect(self.wins_loses_db) as db:
            current_stats = await self.get_win_loss_stats(user_id, guild_id)
            wins, loses = current_stats
            
            if stat == "wins":
                new_value = max(0, wins + amount if action == "add" else wins - amount)
                await db.execute(
                    'UPDATE wins_loses SET wins = ? WHERE user_id = ? AND guild_id = ? OR INSERT INTO wins_loses (user_id, guild_id, wins, loses) VALUES (?, ?, ?, ?)',
                    (new_value, user_id, guild_id, user_id, guild_id, new_value, loses)
                )
            else:
                new_value = max(0, loses + amount if action == "add" else loses - amount)
                await db.execute(
                    'UPDATE wins_loses SET loses = ? WHERE user_id = ? AND guild_id = ? OR INSERT INTO wins_loses (user_id, guild_id, wins, loses) VALUES (?, ?, ?, ?)',
                    (new_value, user_id, guild_id, user_id, guild_id, wins, new_value)
                )
            
            await db.commit()
            return new_value
