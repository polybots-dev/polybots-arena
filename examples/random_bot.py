"""A bot that plays random legal moves, never resigning. Run it with your token:

    python examples/random_bot.py TOKEN [TRIBE]
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
    tribe = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    client.play(decide, ADDRESS, token=sys.argv[1], version="random-1", tribe=tribe)
