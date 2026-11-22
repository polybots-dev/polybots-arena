# polybots-arena

Dial in to **PolyBot Arena**, a leaderboard for bots of *The Battle of Polytopia*, and play
rated games.

Your bot runs on your own machine. It connects out to the arena's match server, which pairs it
with other bots, runs every game and keeps the table. Nothing to upload, no server to host,
and no game files needed on your side.

## Get a token

In the PolyBots Discord, type `/arena register name: your-bot-name`. The arena's Discord bot
answers you privately with your bot's token and the arena's address. `/arena newtoken`
replaces a lost token, `/arena delete` deletes a bot (its name stays taken and its games stay
on record), `/arena mybots` lists yours, and `/arena table` shows the standings. One member may
have up to three bots; one member's bots never play each other.

## Install

    pip install .

Python 3.11 or later. The only dependencies are numpy, websockets and certifi.

## A first bot

    from polybots_arena import client

    def decide(turn):
        return 0  # an index into turn.moves

    client.play(decide, "wss://polybot-arena.taild6d50c.ts.net/", token="...", version="v1", tribe=7)

`examples/random_bot.py` is a complete bot that plays random legal moves:

    python examples/random_bot.py YOUR_TOKEN 7

## What your bot gets

`decide(turn)` is called each time your bot is to move, and returns the index of one of
`turn.moves`. One call is one move; a turn is many moves, ending with an end-turn move.

| Field | What |
| --- | --- |
| `turn.moves` | the legal moves, one row each; columns named in `turn.names["move_fields"]` (kind, source tile, target tile, option, opponent, price), -1 where one does not apply |
| `turn.tiles` | the board, one row per plane named in `turn.names["tile_planes"]`; a tile is `y * 11 + x` |
| `turn.scalars` | `turn.names["scalar_fields"]`: your player id, the turn, your stars |
| `turn.players` | you first, then the players you have met; columns `turn.names["player_fields"]` |
| `turn.tech` | your technologies |
| `turn.previews`, `turn.defence`, `turn.max_health`, `turn.income` | what the game's own screen shows: an attack's forecast per move, defence bonuses and maximum health of units you can see, your income |
| `turn.time_left` | seconds of thinking time you have left in this game |

`turn.names["kinds"]` maps each move kind's name to its number, for example
`turn.names["kinds"]["EndTurn"]`. -1 marks what your seat does not know: the server sends only
what your seat can see.

## The rules

- **1v1 on an 11 by 11 board**, capture-the-capital mode.
- **A match is two games** with the seats swapped, each on its own map.
- **Tribe:** you pick it when you connect, by id: 2 Ai-Mo, 3 Aquarion, 4 Bardur, 5 Elyrion,
  6 Hoodrick, 7 Imperius, 8 Kickoo, 9 Luxidoor, 10 Oumaji, 11 Quetzali, 12 Vengir, 13 Xin-xi,
  14 Yadakk, 15 Zebasi, 16 Polaris, 17 Cymanti. A version of your bot keeps the tribe it has
  played; a new tribe needs a new version label.
- **Rating:** per bot and version, on the Elo scale. A version appears on the table after 20
  games. A new version starts fresh.
- **Clock:** 10 minutes of thinking per bot per game, counted from the server sending a request
  to it receiving your answer, so your network delay counts. A move over 10 seconds is a
  strike; three strikes, or the time running out, lose the game.
- **Draw:** a game that reaches 3 000 moves.
- **Leaving:** a bot gone for more than 60 seconds forfeits its game. To stop without a
  forfeit, call `Client.drain()`: it plays out the match in play and takes no new one.

## Running more than one game

`client.play(..., games=2)` lets the arena give your bot up to two games at once (four at
most); `decide` is then called for each request in turn, from one thread.

## Tests

    python -m unittest discover tests

## Disclaimer

This is an unofficial community project. It is not affiliated with, endorsed by or
supported by Midjiwan AB. *The Battle of Polytopia* and related names are trademarks of
Midjiwan AB, used here only to describe what the project works with. If Midjiwan asks us to
change, restrict or remove any part of this project, we will do so promptly.

## Licence

Apache-2.0 (`LICENSE`).
