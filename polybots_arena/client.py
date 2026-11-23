"""Dial in to the arena and play. Your bot is one function:

    from polybots_arena import client

    def decide(turn):
        return 0            # an index into turn.moves

    client.play(decide, "wss://...", token="...", version="v1")

`decide` gets a `Turn`: your seat's view and legal moves as numpy arrays, with the names to
read them by (`turn.names`). It needs only numpy, websockets and certifi, not the engine.

By default a bot accepts every board size, map type and tribe rule (`protocol.CONDITIONS`);
`sizes`, `maps` and `tribe_rules` narrow that. What a version accepts is fixed once it has
played: accepting other conditions needs a new version label.

Under the `open` tribe rule your bot picks its own tribe for a match, before the first game,
blind to the other's pick, and plays it in both games. `choose` gets a `Pick` (the size, map
type, mode, the tribe ids to pick from, named in `protocol.TRIBES`, and the opponent) and
returns a tribe id; without one, a bot picks at random, as the server would for it:

    def choose(pick):
        return 7 if 7 in pick.tribes else pick.tribes[0]    # imperius

    client.play(decide, "wss://...", token="...", version="v1", choose=choose)
"""

import json
import random
import ssl
import threading

import certifi

from websockets.exceptions import ConnectionClosed, InvalidHandshake, InvalidURI
from websockets.sync.client import connect

from . import protocol

ARRAYS = ("tiles", "scalars", "players", "tech", "moves", "previews", "defence", "max_health")


class Refused(Exception):
    """The server will not serve this bot as it is (an unknown token, a second connection,
    messages it does not take). Dialling in again unchanged would not help."""


class BotError(Exception):
    """`decide` raised, or returned something that is not a move index."""


class Turn:
    """One request. `names` is the server's welcome: `tile_planes`, `scalar_fields`,
    `player_fields`, `move_fields`, `preview_fields`, `kinds`. `size` is the board's side; a
    tile is `y * size + x`; -1 marks what your seat does not know."""

    def __init__(self, message, names):
        self.names, self.game, self.seat, self.size = names, message["game"], message["seat"], message["size"]
        self.time_left, self.income = message["time_left"], message["income"]
        for name in ARRAYS:
            setattr(self, name, protocol.unpack(message[name]))


class Pick:
    """A match's conditions, for picking a tribe: `size`, `map` (a `protocol.MAPS` id), `mode`,
    `tribes` (the ids you may pick), `opponent` (bot name, version), `time` (seconds to answer)."""

    def __init__(self, message):
        self.match, self.size, self.map, self.mode = message["match"], message["size"], message["map"], message["mode"]
        self.tribes, self.opponent, self.time = message["tribes"], tuple(message["opponent"]), message["time"]


def random_tribe(pick):
    """The chooser of a bot that sets none: a tribe at random, as the server draws for a bot that
    does not answer, so a bot without one loses nothing and nobody waits for the clock."""
    return random.choice(pick.tribes)


class Client:
    def __init__(self, decide, url, token, version, games=1, sizes=protocol.SIZES, maps=tuple(protocol.MAPS),
                 tribe_rules=protocol.TRIBE_RULES, choose=random_tribe, retry=5.0, log=print):
        self.decide, self.choose, self.url, self.retry, self.log = decide, choose, url, retry, log
        self.entry = {"type": "hello", "protocol": protocol.VERSION, "token": token, "version": version,
                      "games": games, "sizes": list(sizes), "maps": list(maps), "tribe_rules": list(tribe_rules)}
        self.socket, self.closed = None, threading.Event()

    def run(self):
        """Plays until `close` is called, dialling in again when the connection drops.
        Raises Refused when the server will not serve it, BotError when `decide` fails."""
        while not self.closed.is_set():
            try:
                # certifi's certificates: some Python builds (python.org's for macOS) have none
                secure = {"ssl": ssl.create_default_context(cafile=certifi.where())} if self.url.startswith("wss:") else {}
                with connect(self.url, max_size=2**20, close_timeout=2, **secure) as self.socket:
                    if self.closed.is_set():  # closed while dialling in
                        return
                    self.socket.send(json.dumps(self.entry))
                    names = json.loads(self.socket.recv())
                    if names.get("type") != "welcome" or names.get("protocol") != protocol.VERSION:
                        raise Refused("the server does not speak this protocol")
                    for text in self.socket:
                        message = json.loads(text)
                        if message["type"] == "turn":
                            self.socket.send(self.answer(message, names))
                        elif message["type"] == "pick":
                            self.socket.send(self.pick(message))
                        else:
                            self.log(json.dumps(message))
            except ConnectionClosed as e:
                if e.rcvd is not None and e.rcvd.code == 1008:
                    raise Refused(e.rcvd.reason) from None
            except (OSError, InvalidHandshake, InvalidURI) as e:
                self.log(json.dumps({"event": "connection_error", "error": type(e).__name__}))
            self.closed.wait(self.retry)

    def answer(self, message, names):
        try:
            index = int(self.decide(Turn(message, names)))
        except Exception as e:  # the bot's own error, shown as such and not as a dropped connection
            raise BotError(repr(e)) from e
        return json.dumps({"type": "move", "game": message["game"], "request": message["request"], "index": index})

    def pick(self, message):
        try:
            tribe = int(self.choose(Pick(message)))
        except Exception as e:  # as in `answer`
            raise BotError(repr(e)) from e
        return json.dumps({"type": "tribe", "match": message["match"], "tribe": tribe})

    def drop(self):
        """Closes the connection; `run` dials in again."""
        if self.socket is not None:
            self.socket.close()

    def drain(self):
        """Stops taking new matches: dials in again asking for none, and plays out the match
        in play. Call `close` once its results have come; closing mid-match forfeits."""
        self.entry["games"] = 0
        self.drop()

    def close(self):
        self.closed.set()
        self.drop()


def play(decide, url, token, version, games=1, **options):
    """Plays until the server refuses the bot; `options` takes `sizes`, `maps`, `tribe_rules`
    and `choose`."""
    Client(decide, url, token, version, games, **options).run()
