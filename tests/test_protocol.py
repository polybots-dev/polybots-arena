import json
import unittest

import numpy as np

from polybots_arena import protocol

HELLO = {"type": "hello", "protocol": protocol.VERSION, "token": "a-token_of-16chars", "version": "v1", "games": 1,
         "sizes": [16, 11], "maps": [6], "tribe_rules": ["random", "mirror"]}


class Protocol(unittest.TestCase):
    def test_arrays_survive_the_wire(self):
        for dtype in ("int16", "int32", "int64"):
            a = np.arange(-6, 6, dtype=dtype).reshape(3, 4)
            b = protocol.unpack(json.loads(json.dumps(protocol.pack(a))))
            self.assertEqual((b.dtype.itemsize, b.shape, b.tolist()), (a.dtype.itemsize, a.shape, a.tolist()))

    def test_hello(self):
        hello = protocol.parse_hello(json.dumps(HELLO))
        # the accepted sets come back sorted, so one set is always written one way
        self.assertEqual(protocol.accepts(hello), {"sizes": [11, 16], "maps": [6], "tribe_rules": ["mirror", "random"]})
        for change in (
            {"games": 5}, {"games": -1}, {"version": ""}, {"version": "x" * 33}, {"version": "a\nb"}, {"version": "a b"},
            {"version": "<b>"}, {"token": 5}, {"token": "short"}, {"token": "x" * 129}, {"token": "\ud800" * 16},
            {"token": "sixteen characters"}, {"extra": 1}, {"type": "move"}, {"tribe": 7},
            {"sizes": []}, {"sizes": [12]}, {"sizes": [[11]]}, {"sizes": [{}]}, {"maps": [[1], [1]]}, {"sizes": [11, 11]}, {"sizes": [True]}, {"sizes": 11}, {"sizes": ["11"]},
            {"maps": []}, {"maps": [0]}, {"maps": [7]}, {"maps": [6, 6]}, {"tribe_rules": []},
            {"tribe_rules": ["own"]}, {"tribe_rules": ["mirror", "mirror"]}, {"tribe_rules": "mirror"},
        ):
            with self.assertRaises(protocol.ProtocolError, msg=change):
                protocol.parse_hello(json.dumps(HELLO | change))
        missing = dict(HELLO)
        del missing["token"]
        with self.assertRaises(protocol.ProtocolError):
            protocol.parse_hello(json.dumps(missing))

    def test_an_old_client_is_told_to_update(self):
        first = {"type": "hello", "protocol": 1, "token": "a-token_of-16chars", "version": "v1", "tribe": 7, "games": 1}
        # protocol 2's hello has the same fields as this one's: only its number tells them apart
        for old in (first, HELLO | {"protocol": 2}):
            with self.assertRaisesRegex(protocol.ProtocolError, f"protocol {protocol.VERSION}; update the client"):
                protocol.parse_hello(json.dumps(old))

    def test_move(self):
        move = {"type": "move", "game": "g", "request": 3, "index": 0}
        self.assertEqual(protocol.parse_move(json.dumps(move)), move)
        for text in (
            "", "[]", "nonsense", json.dumps(move | {"index": 1.0}), json.dumps(move | {"index": "0"}),
            json.dumps(move | {"request": None}), json.dumps(move | {"pad": "x" * 5000}),
            "[" * 3000, '"\ud800"', None, b"{}", '{"type":"move","game":"g","request":3,"index":9,"index":0}',
            json.dumps(move | {"game": "é" * 2040}),  # under the limit in characters, over it in bytes
        ):
            with self.assertRaises(protocol.ProtocolError, msg=str(text)[:40]):
                protocol.parse_move(text)

    def test_tribe(self):
        tribe = {"type": "tribe", "match": "m", "tribe": 7}
        move = {"type": "move", "game": "g", "request": 3, "index": 0}
        self.assertEqual(protocol.parse_tribe(json.dumps(tribe)), tribe)
        self.assertEqual([protocol.parse_answer(json.dumps(m)) for m in (tribe, move)], [tribe, move])
        with self.assertRaises(protocol.ProtocolError):
            protocol.parse_tribe(json.dumps(move))
        with self.assertRaises(protocol.ProtocolError):
            protocol.parse_move(json.dumps(tribe))
        # the range is the pick's to judge (a tribe outside it is drawn), the types are refused here
        self.assertEqual(protocol.parse_tribe(json.dumps(tribe | {"tribe": 99}))["tribe"], 99)
        for wrong in ({"tribe": "7"}, {"tribe": True}, {"tribe": 7.0}, {"match": 1}, {"index": 0}, {"type": "hello"},
                      {"type": ["tribe"]}):
            with self.assertRaises(protocol.ProtocolError, msg=wrong):
                protocol.parse_answer(json.dumps(tribe | wrong))
        self.assertEqual(list(protocol.TRIBES), list(range(2, 18)))
        self.assertEqual(protocol.TRIBE_RULES[0], "open")  # the default table's rule comes first


if __name__ == "__main__":
    unittest.main()
