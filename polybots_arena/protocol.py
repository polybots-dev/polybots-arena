"""The arena's wire protocol, version 2: JSON text messages between the match server and a bot.

A bot needs only this module's message shapes: `welcome` carries every name it needs to read
a view, so it needs neither the engine nor the game's rule data.
"""

import base64
import json
import re

import numpy as np

VERSION = 2
MAX_BOT_MESSAGE = 4096  # bytes; a bot's messages are a few short fields
# What the game's own screen shows beyond the view; the other seat's view is never among them.
OUTPUTS = ("previews", "defence", "income", "max_health")
TRIBES = range(2, 18)
# What a match may be played on; a bot's hello says which of each it accepts.
SIZES = (11, 14, 16, 18, 20, 30)  # board sides, the game's tiny to massive
MAPS = {1: "dryland", 2: "lakes", 3: "continents", 4: "archipelago", 5: "water-world", 6: "pangea"}
# mirror: both seats play one drawn tribe; random: two different drawn tribes
TRIBE_RULES = ("mirror", "random")
CONDITIONS = {"sizes": SIZES, "maps": tuple(MAPS), "tribe_rules": TRIBE_RULES}


class ProtocolError(ValueError):
    """A message the receiver does not take."""


def pack(array):
    """An integer array as JSON: its shape, type and little-endian bytes in base64."""
    array = np.ascontiguousarray(array)
    data = array.astype(array.dtype.newbyteorder("<"), copy=False).tobytes()
    return {"shape": list(array.shape), "type": array.dtype.name, "data": base64.b64encode(data).decode()}


def unpack(packed):
    dtype = np.dtype(packed["type"]).newbyteorder("<")
    return np.frombuffer(base64.b64decode(packed["data"]), dtype=dtype).reshape(packed["shape"])


def welcome(engine):
    """The names a bot reads a `turn` with, taken from the engine."""
    return {
        "type": "welcome",
        "protocol": VERSION,
        "tile_planes": list(engine.TILE_PLANES),
        "scalar_fields": list(engine.SCALAR_FIELDS),
        "player_fields": list(engine.PLAYER_FIELDS),
        "move_fields": list(engine.MOVE_FIELDS),
        "preview_fields": list(engine.PREVIEW_FIELDS),
        "kinds": dict(engine.KINDS),
        "outputs": list(OUTPUTS),
    }


def _no_duplicates(pairs):
    message = dict(pairs)
    if len(message) != len(pairs):
        raise ProtocolError("a field is given twice")
    return message


def _parse(text, kind, fields):
    """A bot's message of one kind with exactly `fields` (name to type); bool is not an int.
    Any text at all gives a message or a ProtocolError, never another error. A hello of another
    protocol version is refused for that, before its fields are read."""
    if not isinstance(text, str) or len(text) > MAX_BOT_MESSAGE:
        raise ProtocolError("not text, or over the size limit")
    try:
        if len(text.encode()) > MAX_BOT_MESSAGE:
            raise ProtocolError("message over the size limit")
        message = json.loads(text, object_pairs_hook=_no_duplicates)
    except (ValueError, RecursionError) as e:  # bad JSON or encoding, or nesting too deep
        raise e if isinstance(e, ProtocolError) else ProtocolError("not JSON") from None
    if not isinstance(message, dict) or message.get("type") != kind:
        raise ProtocolError(f"expected a {kind} message")
    if kind == "hello" and message.get("protocol") != VERSION:
        raise ProtocolError(f"this server speaks protocol {VERSION}; update the client")
    if set(message) != {"type", *fields}:
        raise ProtocolError(f"a {kind} message has exactly the fields {sorted(fields)}")
    for name, kind_of in fields.items():
        if type(message[name]) is not kind_of:
            raise ProtocolError(f"{name} is not {kind_of.__name__}")
    return message


def parse_hello(text):
    hello = _parse(text, "hello", {"protocol": int, "token": str, "version": str, "games": int,
                                   "sizes": list, "maps": list, "tribe_rules": list})
    if not re.fullmatch(r"[A-Za-z0-9_-]{16,128}", hello["token"]):
        raise ProtocolError("token is 16 to 128 letters, digits, dashes or underscores")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,32}", hello["version"]):  # it is shown on the public table
        raise ProtocolError("version is 1 to 32 letters, digits, dots, dashes or underscores")
    if not 0 <= hello["games"] <= 4:  # 0: finish the match in play and take no new one
        raise ProtocolError("games at once is 0 to 4")
    for name, allowed in CONDITIONS.items():
        chosen = hello[name]
        if not distinct_values(chosen, allowed):
            raise ProtocolError(f"{name} is a non-empty list of distinct values from {list(allowed)}")
    return hello


def distinct_values(chosen, allowed):
    """Whether `chosen` is a non-empty list of distinct values from `allowed`. The type is
    checked first, so a list of lists is refused rather than raising, and by `type`, not ==:
    True would pass for 1 and 1.0 for a size."""
    return (isinstance(chosen, list) and bool(chosen)
            and all(type(c) is type(allowed[0]) and c in allowed for c in chosen) and len(set(chosen)) == len(chosen))


def accepts(hello):
    """A hello's accepted conditions in one canonical form: each set as a sorted list."""
    return {name: sorted(hello[name]) for name in CONDITIONS}


def parse_move(text):
    return _parse(text, "move", {"game": str, "request": int, "index": int})
