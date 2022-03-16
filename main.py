import logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] [%(funcName)s] %(message)s")
discordLog = logging.getLogger('discord')
discordLog.setLevel(logging.INFO)
import os
import typing
import time
import asyncio
import random
import json
import sqlite3 as lite
import asyncio_redis
import discord
from discord.ext import commands, tasks

botToken = os.getenv('WUBBY_BOT_DISCORD_TOKEN')
botPrefix = '!'
botStatus = 'the Twitch channel'
botDb = 'bot.db'
mainDiscordId = 328300333010911242
sixMonthDiscordId = 859888672467320843
sixMonthRoleId = 940902609810767894
logChannelId = 490766846761500683
sixMonthLogChannelId = 859927647236128808
roleToggleEmojiId = 451081265467359253

modRoles = []
modRoles.append(372244721625464845) # main admin
modRoles.append(490792431717974027) # main developer
modRoles.append(336022934621519874) # main mod
modRoles.append(497550793923362827) # main mod-lite
modRoles.append(859888840801255424) # 6 month admin
modRoles.append(886737623413030932) # 6 month admin
modRoles.append(859960846507835393) # 6 month screener

subRoles = {'base': 900883915118624819, 't1': 900883915118624820, 't2': 900883915118624821, 't3': 900883915118624822}
noXpRole = 796182303080316948

rulesChannel = 403353999178465282
rulesDict = {
    'rules/banner.png': 'rules/info.txt',
    'rules/rules.png': 'rules/rules.txt',
    'rules/staff.png': 'rules/staff.txt',
    'rules/links.png': 'rules/links.txt'
}

eventsOauthRedisHost = os.getenv('WUBBY_EVENTS_OAUTH_REDIS_HOST')
eventsOauthRedisPassword = os.getenv('WUBBY_EVENTS_OAUTH_REDIS_PASSWORD')


bot = commands.Bot(command_prefix=botPrefix, max_messages=50000, intents=discord.Intents.all()) # Set command prefix to !
con = lite.connect(botDb)
cur = con.cursor()
sixMonthSubs = {}

# CHECKINS SYSTEM
#checkinsLock = asyncio.Lock()
#with open('ham_checkins.json') as thefile:
#    checkins = json.load(thefile)
#async def save_checkins():
#    async with checkinsLock:
#        jsonText = json.dumps(checkins)
#        async with aiofile.async_open('ham_checkins.json', 'w') as f:
#            await f.write(jsonText)

async def send_log_message(content: str = None, embed: discord.Embed = None):
    logchannel = bot.get_channel(logChannelId)
    try:
        await logchannel.send(content=content, embed=embed)
        return True
    except:
        return False

async def send_six_month_log_message(content: str = None, embed: discord.Embed = None):
    logchannel = bot.get_channel(sixMonthLogChannelId)
    try:
        await logchannel.send(content=content, embed=embed)
        return True
    except:
        return False

def is_in_guild(guild_id): # Command check for server
    async def guildpredicate(ctx):
        return ctx.guild and ctx.guild.id == guild_id
    return commands.check(guildpredicate)

def is_in_channel(channel_id): # Command check for channel
    async def channelpredicate(ctx):
        return ctx.channel and ctx.channel.id == channel_id
    return commands.check(channelpredicate)

def is_in_category(category_id): # Command check for channel
    async def categorypredicate(ctx):
        return ctx.channel.category and ctx.channel.category.id == category_id
    return commands.check(categorypredicate)

def is_a_mod(ctx): # Check if the member is in the staff list
    found = False
    for role in ctx.author.roles:
        if role.id in modRoles:
            found = True
    return found

def is_number(s): # Function to determine if a string is a float
    try:
        float(s)
        return True
    except ValueError:
        pass
    try:
        import unicodedata
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass
    return False

async def sendbanmessage(guild, user, reason, staffmember):
    embed=discord.Embed(title='You have been banned from `{}`'.format(guild.name), description='Reason: `{}`'.format(reason), color=0xff0000)
    embed.set_footer(text='Banned by: {}'.format(staffmember.top_role.name))
    try:
        finalmessage = await user.send(content=None, embed=embed)
        return finalmessage
    except discord.errors.Forbidden:
        await staffmember.send('User `{}` was banned, however the ban message could not be sent.'.format(user))
        return None

@bot.event
async def on_ready(): # Bot logging
    logging.info('Logged in as: {}|{}'.format(bot.user.name, bot.user.id))
    activity = discord.Game(botStatus) # Set the bot's "Playing" status
    await bot.change_presence(status=discord.Status.online, activity=activity)
    six_month_timer.start()
    logging.info('Status set to: `{}`'.format(botStatus))

@bot.event
async def on_message(message):
    # Protect ourselves from ourselves and dms
    if message.author == bot.user or message.author.bot:
        return

    # No XP role
    if message.guild and message.guild.id == mainDiscordId:
        if discord.utils.get(message.author.roles, id=subRoles['base']) != None and discord.utils.get(message.author.roles, id=noXpRole) != None:
            noxp = discord.utils.get(message.author.roles, id=noXpRole)
            await message.author.remove_roles(noxp)
            await send_log_message(content='[NoXP] `No XP` role removed from user `{}`.'.format(message.author))
            logging.info('[NoXP] `No XP` role removed from user `{}`.'.format(message.author))
        elif discord.utils.get(message.author.roles, id=subRoles['base']) == None and discord.utils.get(message.author.roles, id=noXpRole) == None:
            noxp = discord.utils.get(message.guild.roles, id=noXpRole)
            await message.author.add_roles(noxp)
            await send_log_message(content='[NoXP] `No XP` role added to user `{}`.'.format(message.author))
            logging.info('[NoXP] `No XP` role added to user `{}`.'.format(message.author))

    # CHECKINS SYSTEM
    #if message.channel.id == 865729758696439818:
    #    global checkins
    #    checkins[message.id] = {'timestamp': time.time(), 'members': []}
    #    await save_checkins()
    #    await message.add_reaction('👍')
    #    logging.info('New checkin created for channel {} and content: {}'.format(message.channel.name, message.content))

    await bot.process_commands(message) # Move onto processing the commands below

@bot.event
async def on_member_join(member):
    if member.guild.id == sixMonthDiscordId:
        role = member.guild.get_role(sixMonthRoleId)
        if not role:
            logging.error('Failed to fetch 6 month role!')
            return
        logging.info('Member {} joined the 6 month guild. Processing sub status...'.format(member))
        await process_six_month_membership(member, role)

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

    # ROLE TOGGLES
    if payload.emoji.id == roleToggleEmojiId:
        cur.execute("SELECT RoleID FROM RoleToggles WHERE MessageID = ?;", (str(payload.message_id),))
        result = cur.fetchall()
        if result == []:
            return
        else:
            cur.execute("SELECT GuildID FROM RoleToggles WHERE MessageID = ?;", (str(payload.message_id),))
            guildquery = cur.fetchall()
            guild = bot.get_guild(int(guildquery[0][0]))
            role = discord.utils.get(guild.roles, id=int(result[0][0]))
            user = guild.get_member(int(payload.user_id))
            if user == None:
                logging.warning('[on_raw_reaction_add] WARNING: Member {} not found in member cache!'.format(payload.user_id))
                user = await guild.fetch_member(int(payload.user_id))
            if user == None:
                logging.error('[on_raw_reaction_add] ERROR: Member {} not found in member cache or api fetch!'.format(payload.user_id))
                return
            if role not in user.roles:
                await user.add_roles(role)
                logging.info('[RoleToggle] Added role {} to {} ({})'.format(role.name, user, user.id))
                await send_log_message(content='[RoleToggle] Added role {} to {} (`{}`)'.format(role.name, user, user.id))

    # CHECKINS SYSTEM
    #global checkins
    #if payload.message_id in checkins:
    #    if payload.user_id not in checkins[payload.message_id]['members']:
    #        checkins[payload.message_id]['members'].append(payload.user_id)
    #        logging.info('Userid {} added to checkin {}'.format(payload.user_id, payload.message_id))
    #        await save_checkins()

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.user_id == bot.user.id:
        return

    # ROLE TOGGLES
    if payload.emoji.id == roleToggleEmojiId:
        cur.execute("SELECT RoleID FROM RoleToggles WHERE MessageID = ?;", (str(payload.message_id),))
        result = cur.fetchall()
        if result == []:
            return
        else:
            cur.execute("SELECT GuildID FROM RoleToggles WHERE MessageID = ?;", (str(payload.message_id),))
            guildquery = cur.fetchall()
            guild = bot.get_guild(int(guildquery[0][0]))
            role = discord.utils.get(guild.roles, id=int(result[0][0]))
            user = guild.get_member(int(payload.user_id))
            if user == None:
                logging.warning('[on_raw_reaction_remove] WARNING: Member {} not found in member cache!'.format(payload.user_id))
                user = await guild.fetch_member(int(payload.user_id))
            if user == None:
                logging.error('[on_raw_reaction_remove] ERROR: Member {} not found in member cache or api fetch!'.format(payload.user_id))
                return
            if role in user.roles:
                await user.remove_roles(role)
                logging.info('[RoleToggle] Removed role {} from {} ({})'.format(role.name, user, user.id))
                await send_log_message(content='[RoleToggle] Removed role {} from {} (`{}`)'.format(role.name, user, user.id))

@bot.command()
@commands.has_permissions(administrator=True)
async def maketoggle(ctx, role: discord.Role, *, description):
    """Command to add a role toggle."""
    emoji = bot.get_emoji(roleToggleEmojiId)
    await ctx.message.delete()
    embed = discord.Embed(title=description, color=0xF89817)
    embed.set_footer(text='Adds role: {}'.format(role.name))
    sentmessage = await ctx.send(content=None, embed=embed)
    cur.execute('INSERT INTO RoleToggles(MessageID, RoleID, GuildID, ChannelID) VALUES (?, ?, ?, ?);', (str(sentmessage.id), str(role.id), str(ctx.guild.id), str(ctx.message.channel.id)))
    con.commit()
    dmembed = discord.Embed(title='Role toggle created: {}'.format(description), description='Attached role: {}'.format(role), color=0xF89817)
    await ctx.author.send(content=None, embed=dmembed)
    await sentmessage.add_reaction(emoji)
@maketoggle.error
async def maketoggle_error(ctx, error): # Command error handling
    if isinstance(error, commands.CheckFailure):
        await ctx.send('You do not have permission to create toggles.')
    if isinstance(error, commands.BadArgument):
        await ctx.send('Command failed - Role not found.')
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('You are missing a required argument.')
    logging.error(error)

@bot.command()
@commands.has_permissions(administrator=True)
async def deletetoggle(ctx, messageid: int):
    """Command to remove a role toggle."""
    cur.execute("SELECT ChannelID FROM RoleToggles WHERE MessageID = ?;", (str(messageid),))
    channelid = cur.fetchall()
    if channelid == []:
        await ctx.send('Role toggle does not exist with that message ID!')
    else:
        msgchannel = bot.get_channel(int(channelid[0][0]))
        try:
            tmsg = await msgchannel.get_message(messageid)
            await tmsg.delete()
        except:
            await ctx.send('Message not deleted. Ignoring...')
        cur.execute('DELETE FROM RoleToggles WHERE MessageID = ?;', (str(messageid),))
        con.commit()
        await ctx.send('Toggle deleted.')
@deletetoggle.error
async def deletetoggle_error(ctx, error): # Command error handling
    if isinstance(error, commands.CheckFailure):
        await ctx.send('You do not have permission to delete toggles.')
    logging.error(error)

@bot.command()
async def wubbybot(ctx):
    """Info about the bot."""
    embed = discord.Embed(title='WubbyBot is created and hosted by tt2468#2468.', description='https://github.com/tt2468/wubby_bot', color=0xF89817)
    await ctx.send(content=None, embed=embed)

@bot.command()
async def tt2468(ctx):
    """Returns the total number of bans in the server."""
    bans = await ctx.guild.bans()
    bancount = len(bans)
    await ctx.send('There are ' + str(bancount) + ' bans in this server.')

@bot.command()
@is_in_guild(mainDiscordId)
async def syncedsubs(ctx):
    """Returns how many subscribers of each level are in the server."""
    base = discord.utils.get(ctx.guild.roles, id=subRoles['base']).members
    t1 = discord.utils.get(ctx.guild.roles, id=subRoles['t1']).members
    t2 = discord.utils.get(ctx.guild.roles, id=subRoles['t2']).members
    t3 = discord.utils.get(ctx.guild.roles, id=subRoles['t3']).members
    embed = discord.Embed(title='Members in each role:', description='- T3: `{}`\n- T2: `{}`\n- T1: `{}`\n- Total: `{}`'.format(len(t3), len(t2), len(t1), len(base)))
    await ctx.send(content=None, embed=embed)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def randommember(ctx):
    """Returns a randomly selected member from the guild."""
    members = ctx.guild.members
    length = len(members)
    membernumber = random.randrange(0, length - 1)
    member = members[membernumber]
    embed = discord.Embed(title='Member chosen!', description='The chosen member is <@{}>.'.format(member.id))
    await ctx.send(content=None, embed=embed)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def randomrolemember(ctx, role: discord.Role = None):
    """Returns a randomly selected member from a role."""
    if role == None:
        await ctx.send('Unable to determine a role in this guild from the specified input.')
        return
    if role.members == []:
        await ctx.send('Cannot choose a member because there are no members in the specified role.')
        return
    winner = random.choice(role.members)
    entered = len(role.members)
    embed = discord.Embed(title='Member chosen!', description='The chosen member is <@{}>. There were `{}` eligible members in `{}`.'.format(winner.id, entered, role.name))
    await ctx.send(content=None, embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
@is_in_guild(mainDiscordId)
async def purgenonsub(ctx, role: discord.Role):
    """Purge nonsubs from a specified role."""
    count = 0
    for member in tuple(role.members):
        if subRoles['base'] not in member.roles:
            logging.info('Removed member: `{}`'.format(member))
            await member.remove_roles(role)
            count +=1
    logging.info('Finished purge of nonsubs from the role `{}`. `{}` nonsubs were removed.'.format(role.name, count))
    embed = discord.Embed(title='Finished purge of role: `{}`'.format(role.name), description='Removed `{}` nonsubs.'.format(count), color=0xF89817)
    await ctx.send(content=None, embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def purgerole(ctx, role: discord.Role):
    """Purge all members from a role."""
    count = 0
    for member in tuple(role.members):
        logging.info('Removed member: {}'.format(member))
        await member.remove_roles(role)
        count +=1
    logging.info('Finished purge of the role: `{}`. Kicked `{}` members.'.format(role.name, count))
    embed = discord.Embed(title='Finished purge of role: `{}`'.format(role.name), description='Removed `{}` members.'.format(count), color=0xF89817)
    await ctx.send(content=None, embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def kickrole(ctx, role: discord.Role):
    """Kick all members from the guild in a role."""
    count = 0
    for member in role.members:
        logging.info('Snapped user: `{}`'.format(member))
        await ctx.guild.kick(member, reason="Purge of role: {}".format(role.name))
        count += 1
    logging.info('Finished purge of the role: `{}`. Kicked `{}` members.'.format(role.name, count))
    embed = discord.Embed(title='Finished purge of role: `{}`'.format(role.name), description='Kicked `{}` members.'.format(count), color=0xF89817)
    await ctx.send(content=None, embed=embed)

@bot.command()
@commands.check(is_a_mod)
async def execute(ctx, target: discord.Member, delete_days: typing.Optional[int] = 0, *, reason: typing.Optional[str] = None):
    """A better ban command."""
    if delete_days > 7:
        await ctx.send('Messages can only be purged up to 7 days.')
        return
    await ctx.send('<@{}> you have 10 seconds to say last words before you are executed.'.format(target.id))
    await asyncio.sleep(10)
    await ctx.send('10 seconds over. Now executing ' + str(target) + ' for reason: `' + str(reason) + '`...')
    await asyncio.sleep(1)
    await ctx.send('3')
    await asyncio.sleep(1)
    await ctx.send('2')
    await asyncio.sleep(1)
    await ctx.send('1')
    await asyncio.sleep(1)
    try:
        finalmessage = await sendbanmessage(ctx.guild, target, reason, ctx.author)
        await ctx.guild.ban(target, reason='{}: {}'.format(ctx.author, reason), delete_message_days=delete_days)
        await ctx.send('The target, `' + str(target) + '` has been executed and their messages from the past ' + str(delete_days) + ' days of messages have been purged.')
    except discord.errors.Forbidden:
        embed = discord.Embed(title='Unable to ban `{}`.'.format(target), description='The bot is missing permissions.', color=0xF89817)
        if finalmessage:
            await finalmessage.delete()
        await ctx.send(content=None, embed=embed)
@execute.error
async def execute_error(ctx, error): # Command error handling
    if isinstance(error, commands.CheckFailure):
        await ctx.send('You do not have permission to execute.')
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('You must specify a target.')
    print(error)

@bot.command()
@commands.check(is_a_mod)
async def ban(ctx, target: discord.Member, delete_days: typing.Optional[int] = 0, *, reason: typing.Optional[str] = None):
    """Bans a member and sends them a DM with the reason."""
    if delete_days > 7:
        await ctx.send('Messages can only be purged up to 7 days.')
        return
    finalmessage = await sendbanmessage(ctx.guild, target, reason, ctx.author)
    try:
        await ctx.guild.ban(target, reason='{}: {}'.format(ctx.author, reason), delete_message_days=delete_days)
        embed = discord.Embed(title='User `{}` banned.'.format(target), description='Reason: `{}`'.format(reason), color=0xF89817)
    except discord.errors.Forbidden:
        embed = discord.Embed(title='Unable to ban `{}`.'.format(target), description='The bot is missing permissions.', color=0xF89817)
        if finalmessage is not None:
            await finalmessage.delete()
    await ctx.send(content=None, embed=embed)
@ban.error
async def ban_error(ctx, error): # Command error handling
    if isinstance(error, commands.CheckFailure):
        await ctx.send('You do not have permission to access this command.')

@bot.command()
@commands.has_permissions(administrator=True)
@is_in_guild(mainDiscordId) # Require that the command be sent in the main server
async def sendrules(ctx):
    """Command to reload the rules in the rules channel."""
    msgchannel = bot.get_channel(rulesChannel)
    await msgchannel.purge(limit=10)
    for image, txt in rulesDict.items():
        splitindex = image.index('/') + 1
        file = discord.File(image, image[splitindex:])
        await msgchannel.send("", file=file)
        with open(txt, 'r') as info:
            filetext = info.read()
            finalmessage = await msgchannel.send(filetext)
    await ctx.send("<@{}> Updated Rules".format(ctx.author.id))

@bot.command()
@commands.has_permissions(administrator=True)
async def sendchannel(ctx, channelid: int, *, msgtext):
    """Send a message in a specified channel."""
    await ctx.message.delete()
    msgchannel = bot.get_channel(channelid)
    await msgchannel.send(msgtext)
    await ctx.send('Successfully sent message: `{}`'.format(msgtext))

@bot.command()
@commands.has_permissions(manage_roles=True)
async def roles(ctx):
    """Gets the list of all the roles in the server with their IDs."""
    rolelist = "\n".join(["{}".format(a.name) for a in ctx.guild.roles])
    roleidlist = "\n".join(["{}".format(a.id) for a in ctx.guild.roles])
    embed = discord.Embed(title='Roles in this server:')
    embed.add_field(name='Role:', value=rolelist)
    embed.add_field(name='ID:', value=roleidlist)
    await ctx.send(content=None, embed=embed)

@bot.command()
@commands.has_permissions(manage_roles=True)
async def inrole(ctx, role: discord.Role):
    """Dev command. Prints all members in a role to console and returns the number of users in the role."""
    members = []
    for member in role.members:
        members.append(member.name)
    logging.info('Members in role {}:\n{}'.format(role.name, members))
    await ctx.send('The members of role `{}` have been logged to console. There are `{}` members in the role.'.format(role.name, len(role.members)))

@bot.command()
@commands.check(is_a_mod)
async def checkmember6month(ctx, target: discord.Member = None):
    if not target:
        await ctx.send('Unable to determine target member.')
        return
    await read_six_month_subs()
    key = await redis.get('wubby_events_{}'.format(target.id))
    if not key:
        await ctx.send('Member is not a six month sub. Account not linked to https://events.wubby.tv')
        return
    keyData = json.loads(key)
    twitchUsername = keyData.get('twitchUsername')
    if not twitchUsername:
        await ctx.send('Member is not a six month sub. Invalid database format. Relink to https://events.wubby.tv')
        return
    if twitchUsername.lower() not in sixMonthSubs:
        await ctx.send('Member is not a six month sub. Twitch username {} not found in 6 month database.\nTry relinking Twitch to Discord then redoing https://events.wubby.tv'.format(twitchUsername))
        return
    if sixMonthSubs[twitchUsername.lower()] >= 6:
        await ctx.send('Member is a six month sub.')
    else:
        await ctx.send('Member is not a six month sub. Twitch username {} has only been subscribed for {} months according to database.'.format(twitchUsername, sixMonthSubs[twitchUsername.lower()]))

@bot.command()
@is_in_guild(sixMonthDiscordId)
@commands.has_permissions(administrator=True)
async def loopsixmonth(ctx):
    """Manually process the member list of the 6 month guild and add/remove the role accordingly."""
    ret = await process_six_month_members()
    await ctx.send('Finished processing 6+ month members. There are {} 6 monthers in the guild.'.format(ret))

@tasks.loop(hours=6)
async def six_month_timer():
    await process_six_month_members()

# Fetch the object tying twitch usernames to sub lengths
async def read_six_month_subs():
    global sixMonthSubs
    with open('subscriber_data/subscriber_durations.json') as f:
        sixMonthSubs = json.load(f)

# Determine if a member is a 6 month sub
async def member_is_six_month(memberId):
    key = await redis.get('wubby_events_{}'.format(memberId))
    if not key:
        return False
    keyData = json.loads(key)
    twitchUsername = keyData.get('twitchUsername')
    if not twitchUsername:
        return False
    if twitchUsername.lower() not in sixMonthSubs:
        return False
    return sixMonthSubs[twitchUsername.lower()] >= 6

# Add or remove 6 month role as necessary
async def process_six_month_membership(member, role):
    isSixMonth = await member_is_six_month(member.id)
    if isSixMonth:
        if role not in member.roles:
            await member.add_roles(role)
            await send_six_month_log_message('Added 6 month role to <@{}>'.format(member.id))
            logging.info('Added 6 month role to member {}'.format(member))
    else:
        if role in member.roles:
            await member.remove_roles(role)
            await send_six_month_log_message('Removed 6 month role from <@{}>'.format(member.id))
            logging.info('Removed 6 month role from member {}'.format(member))
    return isSixMonth

# Iterate all guild members of the 6 month server
async def process_six_month_members():
    await read_six_month_subs()
    if not sixMonthSubs:
        logging.error('No six month subs, not processing members.')
        return

    guild = bot.get_guild(sixMonthDiscordId)
    if not guild:
        logging.error('Failed to fetch 6 month guild!')
        return
    role = guild.get_role(sixMonthRoleId)
    if not role:
        logging.error('Failed to fetch 6 month role!')
        return

    logging.info('Processing {} members.'.format(len(guild.members)))

    ret = 0
    for member in guild.members:
        if await process_six_month_membership(member, role):
            ret += 1

    logging.info('Finished processing. There are {} 6 month subs.'.format(ret))
    return ret

async def main():
    global redis
    redis = await asyncio_redis.Connection.create(host=eventsOauthRedisHost, port=6379, password=eventsOauthRedisPassword)
    logging.info('Finished loading.')

    await bot.start(botToken)

    if redis:
        redis.close()
    logging.info('Finished unloading.')

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
