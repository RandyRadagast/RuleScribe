import discord
from discord.ext import commands
from discord import app_commands
import logging

from Logic.Dice import Dice

class RollDice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='roll', description='Roll X dice with Y sides, get result Format: 4D6')
    @app_commands.describe(dice="Dice expression, e.g. 2d6")
    async def roll_dice(self, interaction: discord.Interaction, dice: str):
        try:
            result = Dice(dice)
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return
        except Exception:
            logging.exception('Error in /roll')
            await interaction.response.send_message('Something went wrong. Please verify format (4D6, 2D20)', ephemeral=True)
            return
        logging.info("User %s rolled %sd%s total=%s",interaction.user.id, result.number, result.sides, result.total)
        await interaction.response.send_message(f'You rolled {result.number}d{result.sides}/n'
        f'Results: {result.rolls} = {result.total}')
