#Created by Zachary T Meert
import asyncio
import os
import random
import textwrap
from idlelib import query

import discord
from discord.ext import commands
from discord.ext.commands import bot
from dotenv import load_dotenv
import aiohttp
import re
import logging
import sqlite3
from pathlib import Path
import traceback

 #bunches of setup
logging.basicConfig(level=logging.INFO,
    format= '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt="%Y-%m-%d %H:%M:%S",
    filename = "bot.log",
    filemode = "a"
)

#Misc
DEBUG = False
ADMIN_IDS = {188166161756585985,#self
             188167154661588992 #oddish
             }
availClasses = ['cleric', 'ranger', 'paladin', 'barbarian', 'warlock', 'artificer', 'rogue']

#load token
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

#intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


def format_spell(spell: dict) -> str:
    # Basic fields
    name = spell.get("name", "Unknown Spell")
    level = spell.get("level", 0)
    target_type = spell.get("target_type")
    range_text = spell.get("range")
    is_ritual = bool(spell.get("ritual"))
    casttime = spell.get("casting_time") or "Unknown"
    duration = spell.get("duration") or "Unknown"
    is_concentration = bool(spell.get("concentration"))
    targets = spell.get("target_count")
    saving_throw = (spell.get("saving_throw_ability") or "").strip()
    attack_roll = bool(spell.get("attack_roll"))
    damage_roll = (spell.get("damage_roll") or "").strip()
    damage_types = spell.get("damage_types") or []
    shape_type = spell.get("shape_type")
    shape_size = spell.get("shape_size")
    shape_size_unit = spell.get("shape_size_unit") or ""
    description = spell.get("desc") or ""

    # Components: V / S / M → VSM, VM, SM etc.
    components = []
    if spell.get("verbal"):
        components.append("V")
    if spell.get("somatic"):
        components.append("S")
    if spell.get("material"):
        components.append("M")

    components_text = "".join(components) if components else "None"

    #Material details
    material_details = None
    if spell.get("material"):
        parts = []
        mat_spec = (spell.get("material_specified") or "").strip()
        if mat_spec:
            parts.append(mat_spec)

        mat_cost = spell.get("material_cost")
        if mat_cost is not None:
            parts.append(f"Cost: {mat_cost}")

        if spell.get("material_consumed"):
            parts.append("Consumed")

        material_details = "; ".join(parts) if parts else "Requires material components"

    #Saving throw
    if saving_throw:
        saving_throw_display = saving_throw.upper()
    else:
        saving_throw_display = "N/A"

    #Attack roll
    attack_roll_display = "Yes" if attack_roll else "N/A"

    #Damage
    damage_line = None
    if damage_roll:
        if damage_types:
            damage_types_text = ", ".join(damage_types)
            damage_line = f"{damage_roll} ({damage_types_text})"
        else:
            damage_line = damage_roll

    # Spell Shape / Area
    shape_line = None
    if shape_type:
        if shape_size is not None:
            shape_line = f"{shape_type} ({shape_size} {shape_size_unit.strip()})"
        else:
            shape_line = shape_type

    # Target info
    if targets is not None:
        target_line = f"{targets} ({target_type})"
    else:
        target_line = target_type

    #Ritual / Concentration
    ritual_text = "Yes" if is_ritual else "No"
    concentration_text = "Yes" if is_concentration else "No"


    #Build the lines for the Discord message
    lines = [
        f"**{name}**",
        f"Spell Level: {level}",
        f"Target Type: {target_type}",
        f"Target Count: {target_line}",
        f"Range: {range_text}",
        f"Ritual: {ritual_text}",
        f"Casting Time: {casttime}",
        f"Duration: {duration}",
        f"Concentration: {concentration_text}",
        f"Components: {components_text}",
    ]

    if material_details:
        lines.append(f"Material Details: {material_details}")

    lines.append(f"Saving Throw: {saving_throw_display}")
    lines.append(f"Attack Roll: {attack_roll_display}")

    if damage_line:
        lines.append(f"Damage: {damage_line}")

    if shape_line:
        lines.append(f"Shape: {shape_line}")

    if description:
        # Optionally truncate the description to avoid huge walls of text
        desc_short = textwrap.shorten(description, width=900, placeholder=" …")
        lines.append("")
        lines.append(desc_short)

    # Join everything into ONE message string
    return "\n".join(lines)

#setting up SQL DB, hopefully this goes to plan...
DB_PATH = Path('PlayerCharacters.db')
conn = sqlite3.connect(DB_PATH)
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create the characters table if it doesn't exist yet
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            character_name TEXT NOT NULL,
            class_name TEXT NOT NULL,
            level INTEGER NOT NULL,
            str_score INTEGER NOT NULL,
            dex_score INTEGER NOT NULL,
            con_score INTEGER NOT NULL,
            int_score INTEGER NOT NULL,
            wis_score INTEGER NOT NULL,
            cha_score INTEGER NOT NULL
        );
    """)
    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_PATH)


#good stuff
@bot.event
async def on_ready():
    logging.info('We have logged in as {0.user}'.format(bot))
    logging.info('Here Be Dragons.')
    print('Here Be Dragons.')

@bot.command(name = 'info')
async def info(ctx):
    await ctx.send('RuleScribe is a helper bot for DND 5e using the Open5e API.\n'
                   'This bot is a work in progress.\n'
                   'Available commands are: \n'
                   '`!help(function)` for in depth assistance with functions\n'
                   '`!addChar (CharName)(Class)`\n'
                   '`!roll (query)`\n'
                   '`!spell (query)`\n'
                   '`!weapon (query)`\n'
                   '`!condition (query)`\n')

@bot.command(name = 'addchar')
async def addChar(ctx, name: str, className: str):
    logging.info('Beginning Character Function')
    if className not in availClasses:
        await ctx.send('Invalid Class Name. Please check spelling')
        logging.info('Class name entry failed.')
        return

    await ctx.send(f'Adding {0} the {1}.\n'
    'Please `reply` with this format\n'
    '`level STR DEX CON INT WIS CHA`\n'
    )

    def check(message: discord.Message):
        return (
                message.author == ctx.author and
                message.channel == ctx.channel)

    #set wait
    try:
        reply: discord.Message = await bot.wait_for('message', check=check, timeout=60)
    except asyncio.TimeoutError:
        await ctx.send('Sorry, you took too long to respond. please run `!addchar` again')
        logging.info('Add Character Timed Out.')
        return

    parts = reply.content.split()

    #check length and verify int
    if len(parts) != 7:
        await ctx.send(f'7 numbers were expected, {len(parts)} were given. Add Character Failed. Please run `!addchar` again')
        logging.info('Add Character Failed.')
        return
    try:
        level, str_score, dex_score, con_score, int_score, wis_score, cha_score = map(int, parts)
    except ValueError:
        await ctx.send(
            "All seven values must be **numbers**.\n"
            "Example: `3 16 14 12 10 13 8`\n"
            "Please run `!addchar` again."
        )
        return

    #save to DB
    userID = str(ctx.author.id)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO characters (
            user_id, character_name, class_name, level,
            str_score, dex_score, con_score,
            int_score, wis_score, cha_score
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        userID, name, className, level,
        str_score, dex_score, con_score,
        int_score, wis_score, cha_score
    ))
    conn.commit()
    conn.close()

    await ctx.send(f'Saved {name} the {className} successfully.')
    logging.info('Saved {name} the {className} for {ctx.author.id} to DB successfully.')

@bot.event
async def on_command_error(ctx, error):
    logging.error(f"Command error in {ctx.command}: {error}")

    await ctx.send("Something went wrong running that command.")

    # Build traceback
    tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    short_tb = tb[-1500:]

    # DM admins
    for admin_id in ADMIN_IDS:
        try:
            admin_user = await bot.fetch_user(admin_id)
            await admin_user.send(
                f"**RuleScribe Error Alert**\n"
                f"Guild: {ctx.guild.name if ctx.guild else 'DM'}\n"
                f"Channel: {ctx.channel}\n"
                f"User: {ctx.author} (ID: {ctx.author.id})\n"
                f"Command: {ctx.command}\n"
                f"Error: `{error}`\n"
                f"Traceback:\n```py\n{short_tb}\n```"
            )
        except Exception as dm_err:
            logging.error(f"Failed to DM admin {admin_id}: {dm_err}")



@bot.command(name='rshelp')
async def rshelp(ctx, topic: str):
    if topic == 'roll':
        await ctx.send("The roll function allows for rolling of dice in the following format: Number of dice + d + Sides on dice. Example follows:")
    elif topic == 'ping':
        await ctx.send("The ping function allows for ping to the bot. it will pong in response.")
    elif topic == 'addchar':
        await ctx.send('addchar function adds a player character to the database. to run use `!addchar (Character Name) (Class)`')
    elif topic == 'condition':
        await ctx.send('Condition function returns a brief description of the condition. To run use: `!condition (condition query)`')
    elif topic == 'spell':
        await ctx.send('Spell function returns most descriptors of a spell. To run use: `!spell (spell query)`')
    elif topic == 'weapon':
        await ctx.send('Weapon function returns weapon damage, ranges, and properties. To run use: `!weapon (Weapon Name)`')
    else:
        await ctx.send('Unknown Topic or nonexistent function.')

#test ping
@bot.command()
async def ping(ctx):
    await ctx.send('pong')
    logging.info('Ping ran successfully')

#dice roller
@bot.command(name='roll')
async def roll(ctx, dice: str = None):
    if dice is None:
        await ctx.send('You must specify a dice roll. Format: !roll NdM ex. `!roll 1d20` or `!roll 4d6`')
        return
    #check for valid formatting and assign groups for later RanNum
    try:
        match = re.fullmatch(r'(\d+)d?(\d+)?', dice)
        if not match:
            raise ValueError('Invalid format')

        number = int(match.group(1))
        sides = int(match.group(2))
        rolls = [random.randint(1, sides) for _ in range(number)]
        total = sum(rolls)
        await ctx.send(f'You rolled {number} D{sides} with total {total}.')
        logging.info(f'Rolled {number} D{sides} with total {total}')
    except Exception as e:
        await ctx.send('Something went wrong. Please verify format. (ex. 4D20, 6D6)')
        logging.exception(e)

#rule Lookup
@bot.command(name='condition')
async def rule(ctx, *, query: str = None):
    if query is None:
        await ctx.send('You must specify a condition. Format: `!condition (Condition Query)` ex. `!condition grapple` or `!condition incapacitated`')
        return
    await ctx.send('Querying condition rules...')

    url = 'https://api.open5e.com/conditions/?search=' + query

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                await ctx.send('Something went wrong. Please try again in a few moments.')
                logging.exception(response)
                return
            logging.info(f'Query {query} succeeded.')
            data = await response.json()
    results = data['results']
    if not results:
        await ctx.send('No results found. Please verify spelling/format and try again.')
        logging.info('No results found.')
        return
    rule = results[0]
    name = rule.get('name')
    description = rule.get('desc')
    await ctx.send(f'rules for {name} are: {description} rule.'.format(name=name, description=description))
    logging.info(f'Called condition {name} successfully.')


#spell lookup, this may get complicated...
@bot.command(name='spell')
async def spell(ctx, *, query: str = None):
    if query is None:
        await ctx.send('You must specify a spell. Format: `!spell (Spell Query)` ex. `!spell Aid` or `!spell Fireball`')
        return
    await ctx.send('Querying spell rules...')
    url = 'https://api.open5e.com/spells/?search=' + query
    logging.info(f'Querying {query} from Open5e API.')

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                await ctx.send('Something went wrong. Please try again in a few moments.')
                logging.exception(response)
                return
            data = await response.json()

    results = data.get('results', [])
    if not results:
        await ctx.send('No results found. Please verify spelling/format and try again.')
        logging.info(f'No results found for: {query}.')
        return
#check for exact spell match
    queryNormalized = query.strip().lower()
    exactMatch = [s for s in results if s.get('name', '').strip().lower() == queryNormalized]

    if exactMatch:
        chosen = exactMatch[0]
        message = format_spell(chosen)
        await ctx.send(message)
        spell_name = chosen.get('name', 'Unknown Spell')
        logging.info(f"Queried {query} successfully as exact match {spell_name}.")
        return

    candidate = results[0]
    candidateName = candidate.get('name', 'Unknown Spell')
    await ctx.send(f'I did not find an exact match for {query}. Closest match is {candidateName}. Reply `yes` to use this spell, or `no` to cancel')

    def check(message:discord.Message):
        return (message.author == ctx.author and message.channel == ctx.channel)

    try:
        reply: discord.Message = await bot.wait_for('message', check=check, timeout=30)
    except asyncio.TimeoutError:
        await ctx.send('times out waiting for confirmation. Please try `!spell (query)` again with a more specific name.')
        logging.info('Timeout waiting for confirmation.')
        return

    content = reply.content.strip().lower()
    print(content)
    if content in ('yes', 'y'):
        message = format_spell(candidate)
        await ctx.send(message)
        logging.info(f'Queried {candidateName} Successfully.')
    else:
        await ctx.send('Acknowledged. Canceling lookup.')
        logging.info(f'User declined lookup for {candidateName}. Canceling lookup.')


#character data save TBA

#Feat Lookup TBA


#weapon stat lookup
@bot.command(name = 'weapon')
async def weapon(ctx, *, query: str = None):
    if query is None:
        await ctx.send('You must specify a weapon. Format: !weapon (weapon). ex. !weapon club or !weapon shortbow')
    await ctx.send(f'Locating {query} stats...')
    url = 'https://api.open5e.com/weapons/?search=' + query
    logging.info(f'Querying {query} from Open5e API.')

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                await ctx.send('Something went wrong. Please try again in a few moments.')
                logging.exception(response)
                return
            data = await response.json()

    results = data.get('results', [])
    if not results:
        await ctx.send('No results found. Please verify spelling/format and try again.')
        logging.info(f'No results found for: {query}.')
        return

    stats = results[0]
    name = stats.get('name')
    dDice = stats.get('damage_dice')
    dType = stats.get('damage_type')
    sRange = stats.get('range')
    lRange = stats.get('long_range')
    #check range
    if sRange != None:
        fRange = (f'range of {sRange} and long range of {lRange}')
    else:
        fRange = (f'Melee Range')
    propNames = stats.get('properties')
    propText = ", ".join(propNames) if propNames else "None"
    await ctx.send(f'The {name} deals {dDice} {dType} damage with a {fRange}. This weapon also holds the following properties: {propText}')
    logging.info(f'Called weapon {name} successfully.')


@commands.is_owner()
@bot.command(name="shutdown")
async def shutdown(ctx):
    await ctx.send("Shutting down the Machine Spirit…")
    logging.info('Shutdown complete.')
    await bot.close()

@bot.command(name='update')
async def update(ctx):
    isAdmin = ctx.author.id in ADMIN_IDS
    isAppOwner = await bot.is_owner(ctx.author)
    isGuildOwner = (ctx.guild is not None and ctx.author.id == ctx.guild.owner_id)

    if not (isAdmin or isAppOwner or isGuildOwner):
        await ctx.send('You are not authorized to do that, Tech Priest.')
        return

    await ctx.send('Convening with the Source...')
    logging.info('Pulling update from Github')

    os.system('git pull')
    await ctx.send('Machine Spirit restarting...')
    logging.info('Restarting RuleScribe')
    os.system('sudo systemctl restart rulescribe')

if __name__ == "__main__":
    init_db()
    bot.run(TOKEN)