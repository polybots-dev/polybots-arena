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

    client.play(decide, "wss://polybot-arena.taild6d50c.ts.net/", token="...", version="v1")

`examples/random_bot.py` is a complete bot that plays random legal moves:

    python examples/random_bot.py YOUR_TOKEN

## What your bot gets

`decide(turn)` is called each time your bot is to move, and returns the index of one of
`turn.moves`. One call is one move; a turn is many moves, ending with an end-turn move.

| Field | What |
| --- | --- |
| `turn.moves` | the legal moves, one row each; columns named in `turn.names["move_fields"]` (kind, source tile, target tile, option, opponent, price), -1 where one does not apply |
| `turn.size` | the board's side: 11, 14, 16, 18, 20 or 30 |
| `turn.tiles` | the board, one row per plane named in `turn.names["tile_planes"]`; a tile is `y * turn.size + x` |
| `turn.scalars` | `turn.names["scalar_fields"]`: your player id, the turn, your stars |
| `turn.players` | you first, then the players you have met; columns `turn.names["player_fields"]` |
| `turn.tech` | your technologies |
| `turn.previews`, `turn.defence`, `turn.max_health`, `turn.income` | what the game's own screen shows: an attack's forecast per move, defence bonuses and maximum health of units you can see, your income |
| `turn.time_left` | seconds of thinking time you have left in this game |

Before a game starts your bot's log gets a `game` message: its seat, the board size, the map
type, the tribe rule, both seats' tribes and the opponent.

`turn.names["kinds"]` maps each move kind's name to its number, for example
`turn.names["kinds"]["EndTurn"]`. -1 marks what your seat does not know: the server sends only
what your seat can see.

## The rules

- **1v1**, capture-the-capital mode.
- **Boards:** sizes 11, 14, 16, 18, 20 and 30; map types dryland, lakes, continents,
  archipelago, water world and pangea (numbered 1 to 6).
- **Tribes are drawn by the arena**, by one of two rules: `mirror`, both seats one tribe, or
  `random`, two different tribes. Ids: 2 Ai-Mo, 3 Aquarion, 4 Bardur, 5 Elyrion, 6 Hoodrick,
  7 Imperius, 8 Kickoo, 9 Luxidoor, 10 Oumaji, 11 Quetzali, 12 Vengir, 13 Xin-xi, 14 Yadakk,
  15 Zebasi, 16 Polaris, 17 Cymanti.
- **What your bot accepts:** by default every size, map type and tribe rule. Narrow it with
  `client.play(..., sizes=[11, 14], maps=[3, 6], tribe_rules=["random"])`. A match's
  conditions are drawn from what both bots accept. A version of your bot keeps what it has
  played accepting; other conditions need a new version label.
- **A match is two games** on the same conditions and seat tribes, each on its own map, with
  the bots swapping seats: your bot plays each seat and each tribe once.
- **Tables:** per tribe rule, for all games, for each map type and for each size. Your bot is
  listed on a table only if it accepts everything the table covers: a bot that plays only
  11 by 11 is on the 11 by 11 table, not on the one for all sizes. Ratings are per bot and
  version, on the Elo scale; a version appears on a table after 20 of its games. A new
  version starts fresh. In the Discord, `/arena table` shows them.
- **Clock:** 10 minutes of thinking per bot per game, plus 0.5 seconds for each move your bot
  makes (at most 10 more minutes), counted from the server sending a request to it receiving
  your answer, so your network delay counts (the increment covers a usual connection's). A move over 10 seconds is
  a strike; three strikes, or the time running out, lose the game.
- **Draw:** a game that reaches the size's move limit: 3 000 at 11, 4 000 at 14, 5 000 at 16,
  6 000 at 18, 7 000 at 20, 10 000 at 30.
- **Leaving:** a bot gone for more than 60 seconds forfeits its game, and the second game of a
  match is played even if your bot has gone. After `/arena newtoken`, restart your bot with
  the new token within the minute, or it forfeits the match in play. To stop without a forfeit, call
  `Client.drain()`: it plays out the match in play and takes no new one.

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
