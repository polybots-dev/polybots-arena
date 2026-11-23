"""A bot that plays random legal moves, never resigning, and picks its tribe at random (the client's
default). Run it with your token:

    python examples/random_bot.py TOKEN
"""

import random
import sys

from polybots_arena import client

ADDRESS = "wss://polybot-arena.taild6d50c.ts.net/"


def decide(turn):
    kinds = turn.moves[:, 0].tolist()
    end_turn, resign = turn.names["kinds"]["EndTurn"], turn.names["kinds"]["Resign"]
    if end_turn in kinds and random.random() < 0.25:
        return kinds.index(end_turn)
    return random.choice([i for i, kind in enumerate(kinds) if kind != resign])


if __name__ == "__main__":
    client.play(decide, ADDRESS, token=sys.argv[1], version="random-3")
