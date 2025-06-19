import discord
from discord.app_commands.commands import autocomplete
from discord.ext import commands
from discord import app_commands
from discord.app_commands import Choice
import aiosqlite
import sqlite3
from discord.ui import View, Button, Modal, Select
import re
import random
from typing import List, Literal

pinkslipdb = 'data/pinkslip.db'
guild_settings = 'data/guild_settings.db'
wins_loses = 'data/wins_loses.db'

class PinkslipCog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        print(f"PinkslipCog loaded")
      
    async def cog_load(self) -> None:
        async with aiosqlite.connect(pinkslipdb) as db:
            await db.execute(
                '''CREATE TABLE IF NOT EXISTS pinkslip (
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
                )'''
            )
            await db.commit()
        async with aiosqlite.connect(guild_settings) as db:
            await db.execute(
                '''CREATE TABLE IF NOT EXISTS guild_settings (
                   guild_id INTEGER NOT NULL,
                   pinkslip_channel INTEGER,
                   notification_channel INTEGER,
                   PRIMARY KEY (guild_id)
                )'''
            )
            await db.commit()
        async with aiosqlite.connect(wins_loses) as db:
            await db.execute(
                '''CREATE TABLE IF NOT EXISTS wins_loses (
                   user_id INTEGER NOT NULL,
                   guild_id INTEGER NOT NULL,
                   wins INTEGER NOT NULL,
                   loses INTEGER NOT NULL,
                   PRIMARY KEY (user_id, guild_id)
                )'''
            )
            await db.commit()

    pinkslip = app_commands.Group(name='pinkslip', description='Manage your pinkslip')

    win_loss = app_commands.Group(name='win_loss', description='Manage wins/loses', parent=pinkslip)

    view = app_commands.Group(name='view', description='View pinkslip and stats', parent=pinkslip)

    admin = app_commands.Group(name='admin', description='Admin commands', parent=pinkslip)
    
    @pinkslip.command(name='submit', description='Sends a pinkslip for approval')
    async def pinkslip_submit(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(title='Thankyou for submitting your pinkslip request!', description='To complete the process please make sure you have the following information ready and have paid or are ready to pay the 3$ entry fee before pressing the submit below.\n\n**1.** *Make and Model*\n**2.** *Year*\n**3.** *Engine Specs*\n**4.** *Transmission*\n**5.** *Steam ID*\n**6.** *Car File*\n\nIf you have any other questions please contact a staff member.', color=discord.Color.dark_blue())
        embed.set_footer(text='Made by @megildur272')
        embed.set_thumbnail(url=interaction.guild.icon.url)
        view = PinkSlipButton(interaction)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @pinkslip.command(name='settings', description='Sets the channel for pinkslip requests')
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(mod_channel='The channel to send approval/denial requests for pinkslips', notification_channel='The channel to send notifications for approved or denied pinkslips')
    async def pinkslip_settings(self, interaction: discord.Interaction, mod_channel: discord.TextChannel, notification_channel: discord.TextChannel) -> None:
        missing_permissions = []
        if not mod_channel.permissions_for(interaction.guild.me).send_messages:
            missing_permissions.append(mod_channel.mention)
        if not notification_channel.permissions_for(interaction.guild.me).send_messages:
            missing_permissions.append(notification_channel.mention)
        if missing_permissions:
            channels = ', '.join(missing_permissions)
            embed = discord.Embed(title='Error', description=f"I don't have permission to send messages in the following channels: {channels}.", color=discord.Color.red())
            embed.set_footer(text='Please make sure I have permission to send messages in all the channels.')
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        async with aiosqlite.connect(guild_settings) as db:
            async with db.execute('SELECT * FROM guild_settings WHERE guild_id = ?', (interaction.guild_id,)) as cursor:
                result = await cursor.fetchone()
                if result is not None:
                    await db.execute('UPDATE guild_settings SET pinkslip_channel = ?, notification_channel = ? WHERE guild_id = ?', (mod_channel.id, notification_channel.id, interaction.guild_id))
                    await db.commit()
                else:
                    await db.execute('INSERT INTO guild_settings (guild_id, pinkslip_channel, notification_channel) VALUES (?, ?, ?)', (interaction.guild_id, mod_channel.id, notification_channel.id))
                    await db.commit()
        embed = discord.Embed(title='Pinkslip channels set', description=f'{mod_channel.mention} will now be used for moderators to approve pinkslip requests\n\n{notification_channel.mention} will not be used for approved and denied request notifications', color=discord.Color.dark_blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @view.command(name='owner', description="Views a member's pinkslips")
    @app_commands.describe(member='The user to view pinkslips for')
    async def pinkslip_view_owner(self, interaction: discord.Interaction, member: discord.Member = None) -> None:
        if member is None:
            member = interaction.user
        async with aiosqlite.connect(pinkslipdb) as db:
            async with db.execute('SELECT make_model, year, engine_spec, transmission FROM pinkslip WHERE user_id = ? AND guild_id = ?', (member.id, interaction.guild_id)) as cursor:
                pinkslips = await cursor.fetchall()
            if not pinkslips:
                embed = discord.Embed(title='No pinkslips found', description=f'{member.mention} has not submitted any pinkslips yet.', color=discord.Color.dark_blue())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            count = len(pinkslips)
            embed = discord.Embed(title=f'Pinkslips for {member.mention}', description=f'{member.display_name} has {count} pinkslips. Please select from the menu below to view one.', color=discord.Color.dark_blue())
            async with aiosqlite.connect('data/wins_loses.db') as db:
                async with db.execute('SELECT wins, loses FROM wins_loses WHERE user_id = ? AND guild_id = ?', (member.id, interaction.guild_id)) as cursor:
                    win_lose = await cursor.fetchone()
                    if win_lose:
                        wins = win_lose[0]
                        loses = win_lose[1]
                        embed.add_field(name='Wins/Loses', value=f'{wins}/{loses}', inline=False)
                    else:
                        embed.add_field(name='Wins/Loses:', value='0/0', inline=False)
            embed.set_footer(text='Made by @megildur272')
            embed.set_thumbnail(url=member.avatar.url)
            view = PinkSlipInventory(interaction, member)
            await interaction.response.send_message(embed=embed, view=view, delete_after=600)

    @win_loss.command(name='transfer', description='Update wins and loses and tranfer pinkslip ownership')
    @app_commands.describe(member='The user you raced against')
    async def pinkslip_win_loss_transfer(self, interaction: discord.Interaction, member: discord.Member) -> None:
        embed = discord.Embed(title='Race Tracker!', description='Did you win or lose the race? Please select from the buttons below.', color=discord.Color.dark_blue())
        embed.add_field(name='WARNING!', value='*claiming a win fraudulently will result in action and possible punishment from the server*', inline=True)
        embed.set_footer(text='Made by @megildur272')
        embed.set_thumbnail(url=interaction.guild.icon.url)
        view = RaceTrackerP(interaction, member)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def autocomplete_car(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        async with aiosqlite.connect(pinkslipdb) as db:
            async with db.execute('SELECT user_id, make_model, year, slip_id FROM pinkslip WHERE guild_id = ?', (interaction.guild_id,)) as cursor:
                return [app_commands.Choice(name=f'{row[0]} - {row[1]} - {row[2]}', value=row[0]) for row in await cursor.fetchall() if current.lower() in row[1].lower()]
        
    @admin.command(name='transfer', description='Transfer ownership of a pinkslip')
    @app_commands.describe(slip_id='The car to be transfered', member='The user to transfer ownership to')
    @app_commands.default_permissions(manage_guild=True)
    async def pinkslip_admin_transfer(self, interaction: discord.Interaction, slip_id: str, member: discord.Member) -> None:
        async with aiosqlite.connect(pinkslipdb) as db:
            async with db.execute('SELECT * FROM pinkslip WHERE slip_id = ? AND guild_id = ?', (slip_id, interaction.guild_id)) as cursor:
                pinkslip = await cursor.fetchone()
                if pinkslip is None:
                    embed = discord.Embed(title='Pinkslip not found', description=f'No pinkslip with the ID {slip_id} was found in this server.', color=discord.Color.dark_blue())
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                await db.execute('UPDATE pinkslip SET user_id = ? WHERE slip_id = ? AND guild_id = ?', (member.id, slip_id, interaction.guild_id))
                await db.commit()
                embed = discord.Embed(title='Pinkslip transferred', description=f'The pinkslip with ID {slip_id} has been transferred to {member.mention}.', color=discord.Color.dark_blue())
                await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin.command(name='delete', description='Delete a pinkslip')
    @app_commands.describe(slip_id='The car to be deleted')
    @app_commands.default_permissions(manage_guild=True)
    async def pinkslip_admin_delete(self, interaction: discord.Interaction, slip_id: str) -> None:
        async with aiosqlite.connect(pinkslipdb) as db:
            async with db.execute('SELECT * FROM pinkslip WHERE slip_id = ? AND guild_id = ?', (slip_id, interaction.guild_id)) as cursor:
                pinkslip = await cursor.fetchone()
                if pinkslip is None:
                    embed = discord.Embed(title='Pinkslip not found', description=f'No pinkslip with the ID {slip_id} was found in this server.', color=discord.Color.dark_blue())
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                await db.execute('DELETE FROM pinkslip WHERE slip_id = ? AND guild_id = ?', (slip_id, interaction.guild_id))
                await db.commit()
                embed = discord.Embed(title='Pinkslip deleted', description=f'The pinkslip with ID {slip_id} has been deleted.', color=discord.Color.dark_blue())
                await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin.command(name='win_loss_change', description='Change wins and loses')
    @app_commands.describe(member='The user to change wins and loses for', action='The action to perform', stat='The stat to change', amount='The amount to change by')
    @app_commands.default_permissions(manage_guild=True)
    async def pinkslip_admin_win_loss_change(self, interaction: discord.Interaction, member: discord.Member, action: Literal['add', 'remove'], stat: Literal['wins', 'loses'], amount: int) -> None:
        async with aiosqlite.connect(wins_loses) as db:
            async with db.execute('SELECT wins, loses FROM wins_loses WHERE user_id = ? AND guild_id = ?', (member.id, interaction.guild_id)) as cursor:
                win_lose = await cursor.fetchone()
                if win_lose is None:
                    await db.execute('INSERT INTO wins_loses (user_id, guild_id, wins, loses) VALUES (?, ?, ?, ?)', (member.id, interaction.guild_id, 0 , 0))
                    await db.commit()
                    win_lose = (0, 0)
                if action == 'add':
                    if stat == 'wins':
                        await db.execute('UPDATE wins_loses SET wins = wins + ? WHERE user_id = ? AND guild_id = ?', (amount + win_lose[0], member.id, interaction.guild_id))
                        change = amount + win_lose[0]
                    elif stat == 'loses':
                        await db.execute('UPDATE wins_loses SET loses = loses + ? WHERE user_id = ? AND guild_id = ?', (amount + win_lose[1], member.id, interaction.guild_id))
                        change = amount + win_lose[1]
                    await db.commit()
                elif action == 'remove':
                    if stat == 'wins':
                        await db.execute('UPDATE wins_loses SET wins = wins - ? WHERE user_id = ? AND guild_id = ?', (win_lose[0] - amount, member.id, interaction.guild_id))
                        change = win_lose[0] - amount
                    elif stat == 'loses':
                        await db.execute('UPDATE wins_loses SET loses = loses - ? WHERE user_id = ? AND guild_id = ?', (win_lose[1] - amount, member.id, interaction.guild_id))
                        change = win_lose[1] - amount
                    await db.commit()
                embed = discord.Embed(title='Wins/Loses changed', description=f'The {stat} for {member.mention} have been changed to {change}.', color=discord.Color.dark_blue())
                embed.set_footer(text='Made by @megildur272')
                await interaction.response.send_message(embed=embed, ephemeral=True)

class RaceTrackerP(View):
    def __init__(self, interaction: discord.Interaction, member: discord.Member) -> None:
        self.interaction = interaction
        self.member = member
        super().__init__(timeout=None)

    @discord.ui.button(label='Win', style=discord.ButtonStyle.green)
    async def win(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        async with aiosqlite.connect(wins_loses) as db:
            async with db.execute('SELECT wins FROM wins_loses WHERE user_id = ? AND guild_id = ?', (interaction.user.id, self.interaction.guild_id)) as cursor:
                win_lose = await cursor.fetchone()
                if win_lose is not None:
                    wins = win_lose[0]
                    await db.execute('UPDATE wins_loses SET wins = ? WHERE user_id = ? AND guild_id = ?', (wins + 1, interaction.user.id, self.interaction.guild_id))
                    await db.commit()
                else:
                    await db.execute('INSERT INTO wins_loses (user_id, guild_id, wins, loses) VALUES (?, ?, ?, ?)', (interaction.user.id, self.interaction.guild_id, 1, 0))
                    await db.commit()
        embed = discord.Embed(title='Wins updated!', description=f'Please select the car you won(The one you raced against)', color=discord.Color.dark_blue())
        embed.set_footer(text='Made by @megildur272')
        embed.set_thumbnail(url=self.interaction.guild.icon.url)
        outcome = "win"
        view = PinkSlipInventoryW(self.interaction, self.member, outcome)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='Loss', style=discord.ButtonStyle.red)
    async def loss(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        async with aiosqlite.connect(wins_loses) as db:
            async with db.execute('SELECT loses FROM wins_loses WHERE user_id = ? AND guild_id = ?', (interaction.user.id, self.interaction.guild_id)) as cursor:
                win_lose = await cursor.fetchone()
                if win_lose is not None:
                    loses = win_lose[0]
                    await db.execute('UPDATE wins_loses SET loses = ? WHERE user_id = ? AND guild_id = ?', (loses + 1, interaction.user.id, self.interaction.guild_id))
                    await db.commit()
                else:
                    await db.execute('INSERT INTO wins_loses (user_id, guild_id, wins, loses) VALUES (?, ?, ?, ?)', (interaction.user.id, self.interaction.guild_id, 0, 1))
                    await db.commit()
        embed = discord.Embed(title='Loses updated!', description=f'Please select the car you lost(The one you raced with)', color=discord.Color.dark_blue())
        embed.set_footer(text='Made by @megildur272')
        embed.set_thumbnail(url=self.interaction.guild.icon.url)
        outcome = "lose"
        view = PinkSlipInventoryL(self.interaction, self.interaction.user, self.member, outcome)
        await interaction.response.edit_message(embed=embed, view=view)

class RaceTrackerWL(View):
    def __init__(self, interaction: discord.Interaction, member: discord.Member, user, outcome, car) -> None:
        self.interaction = interaction
        self.member = member
        self.user = user
        self.outcome = outcome
        self.car = car
        super().__init__(timeout=None)

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.member.id:
            await interaction.response.send_message('You cannot confirm your this race!', ephemeral=True)
            return
        async with aiosqlite.connect(wins_loses) as db:
            async with db.execute('SELECT wins, loses FROM wins_loses WHERE user_id = ? AND guild_id = ?', (self.member.id, self.interaction.guild_id)) as cursor:
                win_lose = await cursor.fetchone()
                if win_lose is not None:
                    wins = win_lose[0]
                    loses = win_lose[1]
                    if self.outcome == "win":
                        wins += 1
                        loses = loses
                    else:
                        wins = wins
                        loses += 1
                    await db.execute('UPDATE wins_loses SET wins = ?, loses = ? WHERE user_id = ? AND guild_id = ?', (wins, loses, self.member.id, self.interaction.guild_id))
                    await db.commit()
                else:
                    if self.outcome == "win":
                        await db.execute('INSERT INTO wins_loses (user_id, guild_id, wins, loses) VALUES (?, ?, ?, ?)', (self.member.id, self.interaction.guild_id, 0, 1))
                        await db.commit()
                    else:
                        await db.execute('INSERT INTO wins_loses (user_id, guild_id, wins, loses) VALUES (?, ?, ?, ?)', (self.member.id, self.interaction.guild_id, 1, 0))
                        await db.commit()
        embed = discord.Embed(title='Race confirmed!', description=f'wins/Losses have been updated and cars have been tranfered', color=discord.Color.dark_blue())
        embed.set_footer(text='Made by @megildur272')
        embed.set_thumbnail(url=self.interaction.guild.icon.url)
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.member.id:
            await interaction.response.send_message('You cannot cancel your this race!', ephemeral=True)
            return
        async with aiosqlite.connect(wins_loses) as db:
            async with db.execute('SELECT wins, loses FROM wins_loses WHERE user_id = ? AND guild_id = ?', (self.user.id, self.interaction.guild_id)) as cursor:
                win_lose = await cursor.fetchone()
                if win_lose is not None:
                    wins = win_lose[0]
                    loses = win_lose[1]
                    if self.outcome == "win":
                        wins -= wins
                        loses = loses
                    else:
                        wins = wins
                        loses -= loses
                    await db.execute('UPDATE wins_loses SET wins = ?, loses = ? WHERE user_id = ? AND guild_id = ?', (wins, loses, self.user.id, self.interaction.guild_id))
                    await db.commit()
        async with aiosqlite.connect(pinkslipdb) as db:
            if self.outcome == "win":
                await db.execute('UPDATE pinkslip SET user_id = ? WHERE slip_id = ?', (self.member.id, self.car))
                await db.commit()
            else:
                await db.execute('UPDATE pinkslip SET user_id = ? WHERE slip_id = ?', (self.user.id, self.car))
                await db.commit()
        embed = discord.Embed(title='Tranfer cancelled!', description=f'wins/Losses have not been updated and cars have not been tranfered', color=discord.Color.dark_blue())
        embed.set_footer(text='Made by @megildur272')
        embed.set_thumbnail(url=self.interaction.guild.icon.url)
        await interaction.response.edit_message(embed=embed, view=None)
            
class PinkSlipButton(View):
    def __init__(self, interaction: discord.Interaction) -> None:
        super().__init__(timeout=None)
        self.interaction = interaction

    @discord.ui.button(label='Submit', style=discord.ButtonStyle.green)
    async def submit(self, interaction: discord.Interaction, button: Button) -> None:
        await interaction.response.send_modal(PinkSlipModal(self.interaction))

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: Button) -> None:
        embed = discord.Embed(title='Pinkslip request cancelled', description='Your pinkslip request has been cancelled. Use the `/pinkslip sumbit` command to resubmit your pinkslip request when you are ready.', color=discord.Color.dark_red())
        embed.set_footer(text='Made by @megildur272')
        embed.set_thumbnail(url=interaction.guild.icon.url)
        await interaction.response.edit_message(embed=embed, view=None)

class PinkSlipModal(Modal, title='Pinkslip request. Please fill out all fields'):
    def __init__(self, interaction: discord.Interaction) -> None:
        super().__init__()
        self.interaction = interaction

    make_and_model = discord.ui.TextInput(label='Make And Model', placeholder='Example: Ford Mustang', style=discord.TextStyle.short)
    year = discord.ui.TextInput(label='Year', placeholder='Example: 2022', style=discord.TextStyle.short)
    engine_spec = discord.ui.TextInput(label='Engine Specs', placeholder='Example: 1100whp 1300nm', style=discord.TextStyle.short)
    transmission = discord.ui.TextInput(label='Transmission', placeholder='Example: V8 Manual', style=discord.TextStyle.short)
    steam_id = discord.ui.TextInput(label='Steam ID', placeholder='Example: 76561198125412123', style=discord.TextStyle.short)
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        async with aiosqlite.connect(pinkslipdb) as db:
            async with db.execute('SELECT make_model, year FROM pinkslip WHERE user_id = ? AND guild_id = ?', (interaction.user.id, interaction.guild_id)) as cursor:
                pinkslips = await cursor.fetchall()
                id = int(interaction.user.id) + int(len(pinkslips) + 1) + int(random.randint(1, 999))
                if pinkslips:
                    for pinksliprecord in pinkslips:
                        if pinksliprecord[0] == self.make_and_model.value and pinksliprecord[1] == self.year.value:
                            embed = discord.Embed(title='Pinkslip request failed', description='You have already submitted a pinkslip request for this car or already own it.', color=discord.Color.dark_red())
                            embed.set_footer(text='Made by @megildur272')
                            embed.set_thumbnail(url=interaction.guild.icon.url)
                            await interaction.response.send_message(embed=embed, ephemeral=True)
                            return
                        else:
                            await db.execute('INSERT INTO pinkslip (user_id, guild_id, make_model, year, engine_spec, transmission, steam_id, approved, slip_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', (interaction.user.id, interaction.guild_id, self.make_and_model.value, self.year.value, self.engine_spec.value, self.transmission.value, self.steam_id.value, "pending approval", id))
                            await db.commit()
                            embed = discord.Embed(title='Pinkslip request submitted', description='Your pinkslip request has been submitted. Please wait for a staff member to review your request.', color=discord.Color.dark_green())
                            embed.set_footer(text='Made by @megildur272')
                            embed.set_thumbnail(url=interaction.guild.icon.url)
                            await interaction.response.edit_message(embed=embed, view=None)
                else:
                    await db.execute('INSERT INTO pinkslip (user_id, guild_id, make_model, year, engine_spec, transmission, steam_id, approved, slip_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', (interaction.user.id, interaction.guild_id, self.make_and_model.value, self.year.value, self.engine_spec.value, self.transmission.value, self.steam_id.value, "pending approval", id))
                    await db.commit()
                    pembed = discord.Embed(title='Pinkslip request submitted', description='Your pinkslip request has been submitted. Please wait for a staff member to review your request.')
                    pembed.set_footer(text='Made by @megildur272')
                    pembed.set_thumbnail(url=interaction.guild.icon.url)
                    await interaction.response.edit_message(embed=pembed, view=None)
                embed = discord.Embed(title='New Pinkslip request submitted', description='A new pinkslip request has been submitted by **{}**'.format(interaction.user.mention), color=discord.Color.dark_blue())
                embed.add_field(name='Make and Model', value=self.make_and_model.value, inline=False)
                embed.add_field(name='Year', value=self.year.value, inline=False)
                embed.add_field(name='Engine Specs', value=self.engine_spec.value, inline=False)
                embed.add_field(name='Transmission', value=self.transmission.value, inline=False)
                embed.add_field(name='Steam ID', value=self.steam_id.value, inline=False)
                embed.set_footer(text='Made by @megildur272')
                embed.set_thumbnail(url=interaction.user.avatar.url)
                async with aiosqlite.connect(guild_settings) as db:
                    async with db.execute('SELECT pinkslip_channel FROM guild_settings WHERE guild_id = ?', (interaction.guild_id,)) as cursor:
                        mod_channel = await cursor.fetchone()
                            
                channel = interaction.guild.get_channel(mod_channel[0])
                view = PinkSlipReview(interaction)
                await channel.send(embed=embed, view=view)

class PinkSlipReview(View):
    def __init__(self, interaction: discord.Interaction) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label='Approve', style=discord.ButtonStyle.green, custom_id='approveps')
    async def approve(self, interaction: discord.Interaction, button: Button) -> None:
        await interaction.response.defer()
        message = await interaction.original_response()
        pembed = message.embeds[0] 
        description = pembed.description
        mention_pattern = r'<@!?(\d+)>'
        match = re.search(mention_pattern, description)
        fields = pembed.fields
        make_and_model = fields[0].value
        year = fields[1].value
        async with aiosqlite.connect(pinkslipdb) as db:
            await db.execute('UPDATE pinkslip SET approved = ? WHERE user_id = ? AND guild_id = ? AND make_model = ? AND year = ?', ("approved", match.group(1), interaction.guild_id, make_and_model, year))
            await db.commit()
        membed = discord.Embed(title='Pinkslip request approved', description=f'Applicant <@{match.group(1)}> will be notified of their approval.', color=discord.Color.dark_blue())
        membed.set_footer(text='Made by @megildur272')
        membed.set_thumbnail(url=interaction.guild.icon.url)
        await interaction.edit_original_response(embed=membed, view=None)
        embed = discord.Embed(title='Pinkslip request approved!', description=f'Your pinkslip request has been approved by **{interaction.user.mention}**', color=discord.Color.dark_blue())
        embed.add_field(name='Make and Model', value=make_and_model, inline=False)
        embed.add_field(name='Year', value=year, inline=False)
        embed.set_footer(text='Made by @megildur272')
        embed.set_thumbnail(url=interaction.guild.icon.url)
        async with aiosqlite.connect(guild_settings) as db:
            async with db.execute('SELECT notification_channel FROM guild_settings WHERE guild_id = ?', (interaction.guild_id,)) as cursor:
                notification_channel = await cursor.fetchone()
                channel = interaction.guild.get_channel(notification_channel[0])
                await channel.send(f'<@{match.group(1)}>', embed=embed)
        

    @discord.ui.button(label='Deny', style=discord.ButtonStyle.red, custom_id='denyps')
    async def deny(self, interaction: discord.Interaction, button: Button) -> None:
        await interaction.response.send_modal(PinkSlipDenyModal(interaction))

class PinkSlipDenyModal(Modal, title='Pinkslip denial.'):
    def __init__(self, interaction: discord.Interaction) -> None:
        super().__init__()
        self.interaction = interaction

    reason = discord.ui.TextInput(label='Please provide a reason for denial.', placeholder='Example: Steam ID invalid, or did not pay fee', style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        message = await interaction.original_response()
        pembed = message.embeds[0] 
        description = pembed.description
        mention_pattern = r'<@!?(\d+)>'
        match = re.search(mention_pattern, description)
        fields = pembed.fields
        make_and_model = fields[0].value
        year = fields[1].value
        membed = discord.Embed(title='Pinkslip denied', description=f"Applicant <@!{match.group(1)}> will be notified their request has been denied", color=discord.Color.dark_blue())
        membed.add_field(name='Make and Model', value=make_and_model, inline=False)
        membed.add_field(name='Year', value=year, inline=False)
        membed.add_field(name='Reason', value=self.reason.value, inline=False)
        membed.set_footer(text='Made by @megildur272')
        membed.set_thumbnail(url=interaction.guild.icon.url)
        async with aiosqlite.connect(pinkslipdb) as db:
            await db.execute('DELETE FROM pinkslip WHERE user_id = ? AND guild_id = ? AND make_model = ? AND year = ?', (match.group(1), interaction.guild_id, make_and_model, year))
            await db.commit()
        await message.edit(embed=membed, view=None)
        embed = discord.Embed(title='Pinkslip request denied', description='Your pinkslip request has been denied by **{}**'.format(interaction.user.mention), color=discord.Color.dark_red())
        embed.add_field(name='Make and Model', value=make_and_model, inline=False)
        embed.add_field(name='Year', value=year, inline=False)
        embed.add_field(name='Reason', value=self.reason.value, inline=False)
        embed.set_footer(text='Made by @megildur272')
        embed.set_thumbnail(url=interaction.guild.icon.url)
        
        async with aiosqlite.connect(guild_settings) as db:
            async with db.execute('SELECT notification_channel FROM guild_settings WHERE guild_id = ?', (interaction.guild_id,)) as cursor:
                notification_channel = await cursor.fetchone()
                channel = interaction.guild.get_channel(notification_channel[0])
                await channel.send(f'<@{match.group(1)}>', embed=embed)
                
class PinkslipDropdown(Select):
    def __init__(self, interaction: discord.Interaction, member: discord.Member) -> None:
        self.interaction = interaction
        self.member = member
        db = sqlite3.connect(pinkslipdb)
        cursor = db.execute('SELECT make_model, year, slip_id FROM pinkslip WHERE user_id = ? AND guild_id = ?', (self.member.id, self.interaction.guild_id))
        pinkslips = cursor.fetchall()
        options = []
        for pinkslip in pinkslips:
            options.append(discord.SelectOption(label=f'{pinkslip[0]} - {pinkslip[1]}', value=f'{pinkslip[2]}'))
        super().__init__(placeholder='Select a pinkslip to view', options=options, custom_id='pinkslip_dropdown')

    async def callback(self, interaction: discord.Interaction) -> None:
        selected_option = self.values[0]
        async with aiosqlite.connect(pinkslipdb) as db:
            async with db.execute('SELECT user_id, make_model, year, engine_spec, transmission, approved, slip_id FROM pinkslip WHERE slip_id = ?', (selected_option,)) as cursor:
                pinkslip = await cursor.fetchone()
        embed = discord.Embed(title='Pinkslip', description='Here is the requested pinkslip.', color=discord.Color.dark_blue())
        embed.add_field(name='Make and Model', value=pinkslip[1], inline=False)
        embed.add_field(name='Year', value=pinkslip[2], inline=False)
        embed.add_field(name='Engine Specs', value=pinkslip[3], inline=False)
        embed.add_field(name='Transmission', value=pinkslip[4], inline=False)
        embed.add_field(name='Status', value=pinkslip[5], inline=False)
        embed.add_field(name='Slip ID', value=pinkslip[6], inline=False)
        embed.set_footer(text='Made by @megildur272')
        embed.set_thumbnail(url=self.member.avatar.url)
        await interaction.response.edit_message(embed=embed, view=PinkSlipInventory(interaction, self.member), delete_after=600)

class PinkSlipInventory(View):
    def __init__(self, interaction: discord.Interaction, member) -> None:
        super().__init__(timeout=None)
        self.member = member
        self.interaction = interaction
        pinkslips = PinkslipDropdown(interaction, self.member)
        self.add_item(pinkslips)

    @discord.ui.button(label='Back', style=discord.ButtonStyle.grey, custom_id='psi_back', row=1)
    async def back(self, interaction: discord.Interaction, button: Button) -> None:
        async with aiosqlite.connect(pinkslipdb) as db:
            async with db.execute('SELECT make_model, year, engine_spec, transmission FROM pinkslip WHERE user_id = ? AND guild_id = ?', (self.member.id, interaction.guild_id)) as cursor:
                pinkslips = await cursor.fetchall()
            count = len(pinkslips)
            embed = discord.Embed(title=f'Pinkslips for {self.member.mention}', description=f'{self.member.display_name} has {count} pinkslips. Please select from the menu below to view one.', color=discord.Color.dark_blue())
            async with aiosqlite.connect('data/wins_loses.db') as db:
                async with db.execute('SELECT wins, loses FROM wins_loses WHERE user_id = ? AND guild_id = ?', (self.member.id, interaction.guild_id)) as cursor:
                    win_lose = await cursor.fetchone()
                    if win_lose:
                        wins = win_lose[0]
                        loses = win_lose[1]
                        embed.add_field(name='Wins/Loses', value=f'{wins}/{loses}', inline=False)
                    else:
                        embed.add_field(name='Wins/Loses:', value='0/0', inline=False)
            embed.set_footer(text='Made by @megildur272')
            embed.set_thumbnail(url=self.member.avatar.url)
            view = PinkSlipInventory(interaction, self.member)
            await interaction.response.edit_message(embed=embed, view=view, delete_after=600)

class PinkSlipInventoryW(View):
    def __init__(self, interaction: discord.Interaction, member, outcome) -> None:
        super().__init__(timeout=None)
        self.member = member
        self.interaction = interaction
        self.outcome = outcome
        pinkslips = PinkslipDropdownW(interaction, self.member, self.outcome)
        self.add_item(pinkslips)

class PinkslipDropdownW(Select):
    def __init__(self, interaction: discord.Interaction, member: discord.Member, outcome) -> None:
        self.interaction = interaction
        self.member = member
        self.outcome = outcome
        db = sqlite3.connect(pinkslipdb)
        cursor = db.execute('SELECT make_model, year, slip_id FROM pinkslip WHERE user_id = ? AND guild_id = ?', (self.member.id, self.interaction.guild_id))
        pinkslips = cursor.fetchall()
        options = []
        for pinkslip in pinkslips:
            options.append(discord.SelectOption(label=f'{pinkslip[0]} - {pinkslip[1]}', value=f'{pinkslip[2]}'))
        super().__init__(placeholder='Select a pinkslip to view', options=options, custom_id='pinkslip_dropdown')

    async def callback(self, interaction: discord.Interaction) -> None:
        selected_option = self.values[0]
        async with aiosqlite.connect(pinkslipdb) as db:
            async with db.execute('SELECT make_model, year FROM pinkslip WHERE slip_id = ?', (selected_option,)) as cursor:
                pinkslip = await cursor.fetchone()
            await db.execute('UPDATE pinkslip SET user_id = ? WHERE slip_id = ?', (self.interaction.user.id, selected_option))
            await db.commit()
        embed = discord.Embed(title='Pinkslip Transfered', description='Your opponent must confirm your transfer.', color=discord.Color.dark_blue())
        embed.add_field(name='WARNING', value='*SEVERE ACTION WILL BE TAKEN IF THIS WAS DONE FRAUDULENTLY*', inline=False)
        embed.set_footer(text='Made by @megildur272')
        embed.set_thumbnail(url=interaction.guild.icon.url)
        await interaction.response.edit_message(embed=embed, view=None)
        cembed = discord.Embed(title='Please confirm', description=f'{interaction.user.mention} claims a win against you and has tranfered started a transfer for your {pinkslip[0]} - {pinkslip[1]} to them. Is this correct? If not please contact a staff member after canceling.', color=discord.Color.dark_blue())
        cembed.set_footer(text='Made by @megildur272')
        cembed.set_thumbnail(url=interaction.guild.icon.url)
        async with aiosqlite.connect(guild_settings) as db:
            async with db.execute('SELECT notification_channel FROM guild_settings WHERE guild_id = ?', (interaction.guild_id,)) as cursor:
                notification_channel = await cursor.fetchone()
                channel = interaction.guild.get_channel(notification_channel[0])
                view = RaceTrackerWL(interaction, self.member, self.interaction.user, self.outcome, selected_option)
                await channel.send(f'{self.member.mention}', embed=cembed, view=view)

class PinkSlipInventoryL(View):
    def __init__(self, interaction: discord.Interaction, member, user, outcome) -> None:
        super().__init__(timeout=None)
        self.member = member
        self.interaction = interaction
        self.user = user
        self.outcome = outcome
        pinkslips = PinkslipDropdownL(interaction, member, user, outcome)
        self.add_item(pinkslips)

class PinkslipDropdownL(Select):
    def __init__(self, interaction: discord.Interaction, member: discord.Member, user, outcome) -> None:
        self.interaction = interaction
        self.member = member
        self.user = user
        self.outcome = outcome
        db = sqlite3.connect(pinkslipdb)
        cursor = db.execute('SELECT make_model, year, slip_id FROM pinkslip WHERE user_id = ? AND guild_id = ?', (self.member.id, self.interaction.guild_id))
        pinkslips = cursor.fetchall()
        options = []
        for pinkslip in pinkslips:
            options.append(discord.SelectOption(label=f'{pinkslip[0]} - {pinkslip[1]}', value=f'{pinkslip[2]}'))
        super().__init__(placeholder='Select a pinkslip to view', options=options, custom_id='pinkslip_dropdown')

    async def callback(self, interaction: discord.Interaction) -> None:
        selected_option = self.values[0]
        async with aiosqlite.connect(pinkslipdb) as db:
            async with db.execute('SELECT make_model, year FROM pinkslip WHERE slip_id = ?', (selected_option,)) as cursor:
                pinkslip = await cursor.fetchone()
            await db.execute('UPDATE pinkslip SET user_id = ? WHERE slip_id = ?', (self.user.id, selected_option))
            await db.commit()
        embed = discord.Embed(title='Pinkslip Transfered', description='Your opponent must confirm your transfer.', color=discord.Color.dark_blue())
        embed.add_field(name='WARNING', value='*SEVERE ACTION WILL BE TAKEN IF THIS WAS DONE FRAUDULENTLY*', inline=False)
        embed.set_footer(text='Made by @megildur272')
        embed.set_thumbnail(url=interaction.user.avatar.url)
        await interaction.response.edit_message(embed=embed, view=None)
        cembed = discord.Embed(title='Please confirm', description=f'{interaction.user.mention} claims a loss against you and has tranfered their {pinkslip[0]} - {pinkslip[1]} to you. is this correct?', color=discord.Color.dark_blue())
        cembed.set_footer(text='Made by @megildur272')
        cembed.set_thumbnail(url=interaction.guild.icon.url)
        async with aiosqlite.connect(guild_settings) as db:
            async with db.execute('SELECT notification_channel FROM guild_settings WHERE guild_id = ?', (interaction.guild_id,)) as cursor:
                notification_channel = await cursor.fetchone()
                channel = interaction.guild.get_channel(notification_channel[0])
                view = RaceTrackerWL(interaction, self.user, self.member, self.outcome, selected_option)
                await channel.send(f'{self.user.mention}', embed=cembed, view=view)

async def setup(bot) -> None:
    await bot.add_cog(PinkslipCog(bot))
    bot.add_view(PinkSlipReview(bot))