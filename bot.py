import asyncio
import os
import random
import discord
from discord.ext import commands
from discord.ext.commands import bot
from dotenv import load_dotenv
import aiohttp
import re

#load token
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

#intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

#good stuff
@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))
    print('Here Be Dragons.')


@bot.command(name='rshelp')
async def rshelp(ctx, command = str):



#test ping
@bot.command()
async def ping(ctx):
    await ctx.send('pong')

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
    except Exception as e:
        await ctx.send('Something went wrong. Please verify format. (ex. 4D20, 6D6)')

#rule Lookup
@bot.command(name='condition')
async def rule(ctx, *, query: str):
    await ctx.send('Querying condition rules...')

    url = 'https://api.open5e.com/conditions/?search=' + query

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                await ctx.send('Something went wrong. Please try again in a few moments.')
                return
            data = await response.json()
    results = data['results']
    if not results:
        await ctx.send('No results found. Please verify spelling/format and try again.')
        return
    rule = results[0]
    name = rule.get('name')
    description = rule.get('desc')
    await ctx.send(f'rules for {name} are: {description} rule.'.format(name=name, description=description))

#spell lookup, this may get complicated...
@bot.command(name = 'spell')
async def spell(ctx, *, query: str):
    await ctx.send('Querying spell rules...')
    url = 'https://api.open5e.com/spells/?search=' + query
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                await ctx.send('Something went wrong. Please try again in a few moments.')
                return
            data = await response.json()
    results = data['results']
    if not results:
        await ctx.send('No results found. Please verify spelling/format and try again.')
        return
    spell = results[0]
    name = spell.get('name')
    range = spell.get('range_text')
    isRitual = spell.get('ritual')
    casttime = spell.get('casting_time')
    duration = spell.get('duration')
    isConcentration = spell.get('concentration')
    description = spell.get('desc')




    await ctx.send(name = name)
    await ctx.send(casttime = casttime)
    await ctx.send(description = description)
    await ctx.send(range = range)




    await ctx.send(results)


bot.run(TOKEN)