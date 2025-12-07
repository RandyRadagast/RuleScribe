#Created by Zachary T Meert
import asyncio
import os
import random
import subprocess
import sys
import textwrap
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
from rapidfuzz import fuzz
from version import BOT_VERSION


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
             188167154661588992, #oddish
             }
availClasses = ['cleric', 'wizard', 'bard', 'fighter', 'sorcerer', 'ranger', 'paladin', 'barbarian', 'warlock', 'artificer', 'rogue', 'druid']

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

    # Join everything into one message string
    return "\n".join(lines)

def rangeProps(properties):
    #find range properties, embedded in 'properties' under 'ammunition'
    logging.info('Evaluating Range Properties')

    if not properties:
        logging.info('No Properties found')
        return None
    pattern = re.compile(r"range\s*(\d+)\s*/\s*(\d+)", re.IGNORECASE)
    for prop in properties:
        if not isinstance(prop, str):
            continue
        match = pattern.search(prop)
        if match:
            range = int(match.group(1))
            long_range = int(match.group(2))
            logging.info('Returning short and long range.')
            return range, long_range
    logging.info('No Range Properties found')
    return None

def format_weapon(weapon: dict) -> str:
    # stats = results[0]
    logging.info('Beginning Weapon formatting...')
    lines = []
    lines.append(f'{weapon.get('name')}')
    lines.append(f'Damage: {weapon.get('damage_dice')} {weapon.get("damage_type")}')

    # check range
    props = weapon.get("properties") or []
    propsLower = [p.lower() for p in props]

    logging.info('Checking Range Information...')
    rangeInfo = rangeProps(props)
    if rangeInfo:
        range, long_range = rangeInfo

    if rangeInfo:
        if any('thrown' in p for p in propsLower):
            lines.append('Melee 5ft\n'
                         f'Thrown: Short range{range}\n'
                         f'Thrown: Long range{long_range}\n')
        elif any('ammunition' in p for p in propsLower):
            lines.append(f"Range: {range}")
            lines.append(f"Long range: {long_range}")
    elif any('reach' in p for p in propsLower):
        lines.append('10ft Melee Range')
    else:
        lines.append("5ft Melee Range")

    logging.info('Building Properties...')
    propNames = weapon.get('properties')
    lines.append("Properties:")
    lines.append(", ".join(propNames) if propNames else "None")

    logging.info('Weapon formatting complete.')
    return '\n'.join(lines)

#fuzzy search functionality
def getAttributeOrKey(item, key:str):
    if isinstance(item, dict):
        return item.get(key, '')
    return getattr(item, key, '')

def buildFuzzy(query:str, items, *, key:str = 'name', cutoff:int = 55):
    logging.info(f"Building Fuzzy {query}")
    q = (query or '').strip().lower()
    if not q: return [], []
    exactMatches = []
    scored = []
    processedNames = set()
    logging.info(f'Fuzzy "{query}" prepared, starting...')
    for item in items:
        rawValue = getAttributeOrKey(item, key)
        name = str(rawValue.strip().lower())

        #dedupe
        if not name:
            continue
        if name == q:
            exactMatches.append(item)
        elif name in processedNames:
            continue
        processedNames.add(name)

        #fuzzy score
        score = fuzz.partial_ratio(q, name)
        scored.append((score, item))
    logging.info(f'Fuzzy "{query}" done.')

    scored.sort(key=lambda x: x[0], reverse=True)
    rankedCandidates = [item for score, item in scored if score >= cutoff]
    logging.info(f'Returning organized list.{len(exactMatches)} Exact Results, {len(rankedCandidates)} Fuzzy results.')
    return exactMatches, rankedCandidates

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

@bot.command(name = 'info', help = 'Description of bot')
async def info(ctx):
    await ctx.send('RuleScribe is a helper bot for DND 5e using the Open5e API.\n'
                   f'Current Version: {BOT_VERSION}\n')

@bot.command(name = 'addchar', help = 'Add a character to the Player Database')
async def addChar(ctx, name: str, className: str):
    logging.info('Beginning Character Function')
    className = className.lower()
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

#TODO character data update
@bot.command(name = 'updatechar', help = 'Update a character in the Player Database - Currently nonfunctional -')
async def updateChar(ctx):
    logging.info('Beginning Update Character Function')
    conn = get_connection()
    cursor = conn.cursor()




    cursor.execute()

    conn.commit()
    conn.close()

#Character Delete
@bot.command(name = 'deletechar', help = 'Delete your character from the Player Database')
async def deleteChar(ctx, *, characterName: str):
    logging.info(f'Beginning Delete Character Function for {characterName}')
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""DELETE FROM characters WHERE user_id = ? AND character_name = ?""", (ctx.author.id, characterName))
    changes = cursor.rowcount

    if changes > 0:
        await ctx.send(f'Character {characterName} has been deleted.')
    else:
        await ctx.send(f'Character {characterName} does not exist.')
    conn.commit()
    conn.close()

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


#test ping
@bot.command()
async def ping(ctx):
    await ctx.send('pong')
    logging.info('Ping ran successfully')

#dice roller
@bot.command(name='roll', aliases=['r'], help = 'Roll X dice with Y sides, get result')
async def roll(ctx, dice: str = None):
    """Roll X dice with Y sides, get result
    Format:XDY (ex. 4D20, 6d6, 9D30)"""
    if dice is None:
        await ctx.send('You must specify a dice roll. Format: !roll NdM ex. `!roll 1d20` or `!roll 4d6`')
        return
    #check for valid formatting and assign groups for later RanNum
    dice = dice.lower()
    try:
        match = re.fullmatch(r'(\d+)[dD](\d+)?', dice)
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
@bot.command(name='condition', help = 'This function returns a brief description of the condition.')
async def rule(ctx, *, query: str = None):
    """Lookup a condition and get a brief description, truncated if too long.
    Format: !condition (condition query)"""
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
@bot.command(name='spell', aliases=['s'], help = 'This function returns a rundown of the queried spell.')
async def spell(ctx, *, query: str = None):
    """Lookup a spell and get a rundown of the queried spell
    Format: !spell (spell query) or !s (spell query) are accepted"""

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

    logging.info(f'Query {query} succeeded. Moving on...')
    results = data.get('results', [])
    if not results:
        await ctx.send('No results found. Please verify spelling/format and try again.')
        logging.info(f'No results found for: {query}. Stopping !spell query.')
        return

#fuzzy wuzzy
    logging.info('Loading Fuzzy Filter...')
    exactMatch, candidates = buildFuzzy(query, results, key = 'name', cutoff=55)
    if exactMatch:
        chosen = exactMatch[0]
        message = format_spell(chosen)
        await ctx.send(message)
        spell_name = chosen.get('name', 'Unknown Spell')
        logging.info(f"Queried {query} successfully as exact match {spell_name}.")
        return
    def check(message:discord.Message):
        return (message.author == ctx.author and message.channel == ctx.channel and message.content.lower() in ('y', 'yes', 'n', 'no', 'stop', 's', 'cancel'))
    total = len(candidates)

    logging.info("Wrote raw API response to raw_spell.json")

    for idx, candidate in enumerate(candidates, start=1):
        candidateName = candidate.get('name', 'Unknown Spell')

        await ctx.send(f'I did not find an exact match for {query}. Closest match is {candidateName}. Reply `yes` to use this spell, `no` to move to the next result, or `stop` to cancel lookup')
        logging.info(f'No exact match found for {query}. Waiting 30s for user input...')
        try:
            reply: discord.Message = await bot.wait_for('message', check=check, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send('Timed out waiting for confirmation. Please try `!spell (query)` again with a more specific name.')
            logging.info('Timeout waiting for confirmation.')
            return
        content = reply.content.strip().lower()

        if content in ('yes', 'y'):
            message = format_spell(candidate)
            await ctx.send(message)
            logging.info(f'Queried {candidateName} Successfully.')
            return
        elif content in ('stop', 'cancel', 's'):
            await ctx.send(f'Canceling Search for {query}.')
            logging.info('User stopped search.')
            return
        else:
            if idx < total:
                await ctx.send('Okay, Checking the next result.')
            else:
                await ctx.send('No more results. Please try `!spell (query)` again with a more specific name.')
                logging.info(f'User declined all available results from {query}')
                return

#TODO Feat Lookup



#weapon stat lookup
@bot.command(name = 'weapon', aliases=['wep, w'], help = 'This function returns a rundown of the queried weapon.')
async def weapon(ctx, *, query: str = None):
    """Lookup a weapon and get stats returned back.
    Format: !weapon (weapon query) or !w (weapon query) are accepted"""
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

    import json
    with open("raw_spell.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    logging.info("Wrote raw API response to raw_spell.json")


    logging.info('Loading Fuzzy Filter...')
    exactMatch, candidates = buildFuzzy(query, results, key='name', cutoff=55)

    if exactMatch:
        chosen = exactMatch[0]
        message = format_weapon(chosen)
        await ctx.send(message)
        weapon_name = chosen.get('name', 'Unknown Weapon')
        logging.info(f"Queried {query} successfully as exact match {weapon_name}.")
        return
    def check(message:discord.Message):
        return (message.author == ctx.author and message.channel == ctx.channel and message.content.lower() in ('y', 'yes', 'n', 'no', 'stop', 's', 'cancel'))
    total = len(candidates)


    for idx, candidate in enumerate(candidates, start=1):
        candidateName = candidate.get('name', 'Unknown weapon')

        await ctx.send(f'I did not find an exact match for `{query}`. Closest match is {candidateName}. Reply `yes` to query this weapon, `no` to move to the next result, or `stop` to cancel lookup')
        logging.info(f'No exact match found for {query}. Waiting 30s for user input...')
        try:
            reply: discord.Message = await bot.wait_for('message', check=check, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send('Timed out waiting for confirmation. Please try `!weapon (query)` again with a more specific name.')
            logging.info('Timeout waiting for user confirmation.')
            return
        content = reply.content.strip().lower()

        if content in ('yes', 'y'):
            message = format_weapon(candidate)
            await ctx.send(message)
            logging.info(f'Queried {candidateName} Successfully.')
            return
        elif content in ('stop', 'cancel', 's'):
            await ctx.send(f'Canceling Search for {query}.')
            logging.info('User stopped search.')
            return
        else:
            if idx < total:
                await ctx.send('Okay, Checking the next result.')
            else:
                await ctx.send('No more results. Please try `!weapon (query)` again with a more specific name.')
                logging.info(f'User declined all available results from {query}')
                return
    logging.info(f'Queried weapon {query} successfully.')


@commands.is_owner()
@bot.command(name="shutdown", help = "Shuts down the bot. -Requires permissions")
async def shutdown(ctx):
    """Shuts down the bot.
    Channel Owner permissions are required."""
    await ctx.send("Shutting down the Machine Spirit…")
    logging.info('Shutdown complete.')
    await bot.close()

@bot.command(name="whoami", help = "Shows you the current user's name and permissions.")
#for debugging purposes
async def whoami(ctx):
    """Shows you the current user's name and permissions.
    For Debug purposes"""
    isAdmin      = ctx.author.id in ADMIN_IDS
    isAppOwner   = await bot.is_owner(ctx.author)
    isGuildOwner = (ctx.guild is not None and ctx.author.id == ctx.guild.owner_id)

    await ctx.send(
        "Debug info:\n"
        f"Your ID: `{ctx.author.id}`\n"
        f"isAdmin: `{isAdmin}`\n"
        f"isAppOwner: `{isAppOwner}`\n"
        f"isGuildOwner: `{isGuildOwner}`\n"
    )

#more durable update command
scribeTower = Path(__file__).resolve().parent
@bot.command(name='update', help = 'Updates the bot. -Requires permissions')
async def update(ctx):
    """Updates the bot from Repo and reboots.
    Channel Owner or App Owner permissions are required."""
    isAdmin = ctx.author.id in ADMIN_IDS
    isAppOwner = await bot.is_owner(ctx.author)
    isGuildOwner = (ctx.guild is not None and ctx.author.id == ctx.guild.owner_id)

    if not (isAdmin or isAppOwner or isGuildOwner):
        await ctx.send('You are not authorized to do that.')
        return

    await ctx.send('Convening with the Source...')
    logging.info('Pulling update from Github - master branch')

    try:
        result = subprocess.run(['git', 'checkout', 'master'], cwd=str(scribeTower), capture_output=True, text=True, check=True)
        logging.info(result.stdout)
        logging.info(result.stderr)
    except subprocess.CalledProcessError as e:
        await ctx.send('Could not pull update from Github. See Logs.')
        logging.error(e.stderr)
        return
    try:
        result = subprocess.run(['git', 'pull'], cwd=str(scribeTower), capture_output=True, text=True, check=True)
        logging.info(result.stdout)
        logging.info(result.stderr)
    except subprocess.CalledProcessError as e:
        await ctx.send('Could not pull update from Github. See Logs.')
        logging.error(e.stderr)
        return

    logging.info('Successfully pulled update from Github Repository - master branch.')
    await ctx.send('Installing Dependencies...')
    logging.info('Installing Dependencies...')
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', 'requirements.txt'], cwd=str(scribeTower), capture_output=True, text=True, check=True)
        logging.info(result.stdout)
        logging.info(result.stderr)
    except subprocess.CalledProcessError as e:
        await ctx.send('Could not install dependencies. See Logs.')
        logging.error(e.stderr)
        return
    logging.info('Successfully installed dependencies.')
    await ctx.send('Restarting RuleScribe...')
    logging.info('Restarting RuleScribe...')
    os._exit(0)


@bot.command(name='version', aliases=['versions', 'v'], help = 'Shows the current version of the bot.')
async def version(ctx):
    await ctx.send(f'Rulescribe Version {BOT_VERSION}')

if __name__ == "__main__":
    init_db()
    bot.run(TOKEN)