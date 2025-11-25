#Created by Zachary T Meert

import os
import random
import textwrap
import discord
from discord.ext import commands
from discord.ext.commands import bot
from dotenv import load_dotenv
import aiohttp
import re
import logging

logging.basicConfig(level=logging.INFO,
    format= '%(asctime)s [%(levelness)s] %(name)s: %(message)s',
    datefmt="%Y-%m-%d %H:%M:%S",
    filename = "bot.log",
    filemode = "a"
)

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


    #Spell level text
    # if level == 0:
    #     spell_level_text = "Cantrip"
    # elif level == 1:
    #     spell_level_text = "1st-level"
    # elif level == 2:
    #     spell_level_text = "2nd-level"
    # elif level == 3:
    #     spell_level_text = "3rd-level"
    # else:
    #     spell_level_text = f"{level}th-level"

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


#good stuff
@bot.event
async def on_ready():
    logging.info('We have logged in as {0.user}'.format(bot))
    logging.info('Here Be Dragons.')


# @bot.command(name='rshelp')
# async def rshelp(ctx, command = str):

#error catch-most failure
@bot.event
async def on_command_error(ctx, error):
    logging.error(f"Command error in {ctx.command}: {error}")
    await ctx.send("Something went wrong running that command.")

#test ping
@bot.command()
async def ping(ctx):
    await ctx.send('pong')
    logging.info('Ping ran successfully')

#dice roller
@bot.command(name='roll')
async def roll(ctx, dice: str):
    #check for valid formatting and assign groups for later RanNum
    try:
        match = re.fullmatch(r'(\d+)d?(\d+)?', dice)
        if not match:
            raise ValueError('Invalid format')

        number = int(match.group(1))
        sides = int(match.group(2))
        rolls = [random.randint(1, sides) for _ in range(number)]
        total = sum(rolls)
        await ctx.send(f'You rolled {number} d{sides} with total {total}.')
        logging.info(f'Rolled {number} d{sides} with total {total}')
    except Exception as e:
        await ctx.send('Something went wrong. Please verify format. (ex. 4D20, 6D6)')
        logging.exception(e)

#rule Lookup
@bot.command(name='condition')
async def rule(ctx, *, query: str):
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
@bot.command(name = 'spell')
async def spell(ctx, *, query: str):
    await ctx.send('Querying spell rules...')
    url = 'https://api.open5e.com/spells/?search=' + query
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                await ctx.send('Something went wrong. Please try again in a few moments.')
                logging.exception(response)
                return
            data = await response.json()
    results = data['results']
    if not results:
        await ctx.send('No results found. Please verify spelling/format and try again.')
        return
    spell = results[0]
    message = format_spell(spell)
    await ctx.send(message)
    logging.info(f'Called spell {spell["name"]} successfully.')


bot.run(TOKEN)