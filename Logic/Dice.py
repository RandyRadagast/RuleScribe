import re, random
from dataclasses import dataclass


@dataclass(frozen=True)
class Dice:
    number: int
    sides: int
    rolls: list[int]
    total: int

def rollDice(expr: str) -> Dice:
    expr = expr.strip()

    match = re.fullmatch(r'(\d+)[dD](\d+)', expr)
    if not match:
        raise ValueError('Invalid format')

    number = int(match.group(1))
    sides = int(match.group(2))
    rolls = [random.randint(1, sides) for _ in range(number)]

    return Dice(number=number, sides=sides, rolls=rolls, total=sum(rolls))