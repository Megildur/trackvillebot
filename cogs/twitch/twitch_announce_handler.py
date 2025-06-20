
import discord
from discord.ext import commands, tasks
import aiosqlite
import aiohttp
import os
from datetime import datetime, timedelta, timezone
import logging

twitch_db = "data/twitch_announce.db"

class TwitchAnnounceHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.twitch_client_id = os.getenv('TWITCH_CLIENT_ID')
        self.twitch_client_secret = os.getenv('TWITCH_CLIENT_SECRET')
        self.twitch_access_token = None
        self.token_expires_at = None
        self.check_live_streams.start()

    def cog_unload(self):
        self.check_live_streams.cancel()

    async def get_twitch_access_token(self):
        if self.twitch_access_token and self.token_expires_at and datetime.now(timezone.utc) < self.token_expires_at:
            return self.twitch_access_token

        if not self.twitch_client_id or not self.twitch_client_secret:
            logging.error("Twitch Client ID or Client Secret not set in environment variables")
            return None

        url = "https://id.twitch.tv/oauth2/token"
        data = {
            'client_id': self.twitch_client_id,
            'client_secret': self.twitch_client_secret,
            'grant_type': 'client_credentials'
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        self.twitch_access_token = token_data['access_token']
                        expires_in = token_data.get('expires_in', 3600)
                        self.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 300)
                        return self.twitch_access_token
                    else:
                        logging.error(f"Failed to get Twitch access token: {response.status}")
                        return None
        except Exception as e:
            logging.error(f"Error getting Twitch access token: {e}")
            return None

    async def get_twitch_user_id(self, username):
        """Get Twitch user ID from username"""
        access_token = await self.get_twitch_access_token()
        if not access_token:
            return None

        url = f"https://api.twitch.tv/helix/users?login={username}"
        headers = {
            'Client-ID': self.twitch_client_id,
            'Authorization': f'Bearer {access_token}'
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data['data']:
                            return data['data'][0]['id']
                    return None
        except Exception as e:
            logging.error(f"Error getting Twitch user ID for {username}: {e}")
            return None

    async def check_stream_status(self, user_id):
        access_token = await self.get_twitch_access_token()
        if not access_token:
            return None

        url = f"https://api.twitch.tv/helix/streams?user_id={user_id}"
        headers = {
            'Client-ID': self.twitch_client_id,
            'Authorization': f'Bearer {access_token}'
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data['data']:
                            stream_data = data['data'][0]
                            return {
                                'is_live': True,
                                'stream_id': stream_data['id'],
                                'title': stream_data['title'],
                                'game_name': stream_data['game_name'],
                                'viewer_count': stream_data['viewer_count'],
                                'started_at': stream_data['started_at'],
                                'thumbnail_url': stream_data['thumbnail_url']
                            }
                        else:
                            return {'is_live': False}
                    return None
        except Exception as e:
            logging.error(f"Error checking stream status for user {user_id}: {e}")
            return None

    async def get_user_info(self, user_id):
        access_token = await self.get_twitch_access_token()
        if not access_token:
            return None

        url = f"https://api.twitch.tv/helix/users?id={user_id}"
        headers = {
            'Client-ID': self.twitch_client_id,
            'Authorization': f'Bearer {access_token}'
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data['data']:
                            user_data = data['data'][0]
                            return {
                                'display_name': user_data['display_name'],
                                'profile_image_url': user_data['profile_image_url'],
                                'login': user_data['login']
                            }
                    return None
        except Exception as e:
            logging.error(f"Error getting user info for {user_id}: {e}")
            return None

    @tasks.loop(minutes=2)
    async def check_live_streams(self):
        try:
            async with aiosqlite.connect(twitch_db) as db:
                cursor = await db.execute("""
                    SELECT s.guild_id, s.twitch_username, s.is_live, s.last_stream_id,
                           st.channel_id, st.role_id
                    FROM twitch_streamers s
                    JOIN twitch_settings st ON s.guild_id = st.guild_id
                """)
                streamers = await cursor.fetchall()

                for guild_id, username, is_currently_live, last_stream_id, channel_id, role_id in streamers:
                    try:
                        user_id = await self.get_twitch_user_id(username)
                        if not user_id:
                            continue
                        stream_status = await self.check_stream_status(user_id)
                        if not stream_status:
                            continue

                        if stream_status['is_live'] and not is_currently_live:
                            stream_id = stream_status['stream_id']
                            
                            if stream_id == last_stream_id:
                                continue

                            user_info = await self.get_user_info(user_id)
                            if not user_info:
                                continue

                            await self.send_live_announcement(
                                guild_id, channel_id, role_id, 
                                username, user_info, stream_status
                            )

                            await db.execute("""
                                UPDATE twitch_streamers 
                                SET is_live = 1, last_stream_id = ?
                                WHERE guild_id = ? AND twitch_username = ?
                            """, (stream_id, guild_id, username))

                        elif not stream_status['is_live'] and is_currently_live:
                            await db.execute("""
                                UPDATE twitch_streamers 
                                SET is_live = 0
                                WHERE guild_id = ? AND twitch_username = ?
                            """, (guild_id, username))

                        await db.commit()

                    except Exception as e:
                        logging.error(f"Error processing streamer {username} in guild {guild_id}: {e}")
                        continue

        except Exception as e:
            logging.error(f"Error in check_live_streams task: {e}")

    async def send_live_announcement(self, guild_id, channel_id, role_id, username, user_info, stream_status):
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return

            channel = guild.get_channel(channel_id)
            if not channel:
                return

            embed = discord.Embed(
                title=f"🔴 {user_info['display_name']} is now live on Twitch!",
                description=stream_status['title'],
                color=0x9146FF,
                url=f"https://twitch.tv/{user_info['login']}"
            )

            if stream_status['game_name']:
                embed.add_field(name="Game", value=stream_status['game_name'], inline=True)
            
            embed.add_field(name="Viewers", value=str(stream_status['viewer_count']), inline=True)
            
            try:
                started_at = datetime.fromisoformat(stream_status['started_at'].replace('Z', '+00:00'))
                embed.add_field(name="Started", value=f"<t:{int(started_at.timestamp())}:R>", inline=True)
            except:
                pass

            if stream_status['thumbnail_url']:
                thumbnail_url = stream_status['thumbnail_url'].format(width=320, height=180)
                embed.set_image(url=thumbnail_url)

            if user_info['profile_image_url']:
                embed.set_author(
                    name=user_info['display_name'],
                    icon_url=user_info['profile_image_url'],
                    url=f"https://twitch.tv/{user_info['login']}"
                )

            embed.set_footer(text="Twitch", icon_url="https://static-cdn.jtvnw.net/jtv_user_pictures/8a6381c7-d0c0-4576-b179-38bd5ce1d6af-profile_image-70x70.png")

            content = ""
            if role_id:
                role = guild.get_role(role_id)
                if role:
                    content = f"{role.mention} "

            content += f"**{user_info['display_name']}** is now live! 🎮"

            await channel.send(content=content, embed=embed)

        except Exception as e:
            logging.error(f"Error sending live announcement for {username}: {e}")

    @check_live_streams.before_loop
    async def before_check_live_streams(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(TwitchAnnounceHandler(bot))