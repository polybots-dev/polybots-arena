import json
import unittest

import numpy as np

from polybots_arena import protocol

HELLO = {"type": "hello", "protocol": 1, "token": "a-token_of-16chars", "version": "v1", "tribe": 7, "games": 1}


class Protocol(unittest.TestCase):
    def test_arrays_survive_the_wire(self):
        for dtype in ("int16", "int32", "int64"):
            a = np.arange(-6, 6, dtype=dtype).reshape(3, 4)
            b = protocol.unpack(json.loads(json.dumps(protocol.pack(a))))
            self.assertEqual((b.dtype.itemsize, b.shape, b.tolist()), (a.dtype.itemsize, a.shape, a.tolist()))

    def test_hello(self):
        self.assertEqual(protocol.parse_hello(json.dumps(HELLO))["tribe"], 7)
        for change in (
            {"tribe": 1}, {"tribe": 18}, {"tribe": True}, {"games": 5}, {"games": -1},
            {"protocol": 2}, {"version": ""}, {"version": "x" * 33}, {"version": "a\nb"}, {"version": "a b"}, {"version": "<b>"},
            {"token": 5}, {"token": "short"}, {"token": "x" * 129}, {"token": "\ud800" * 16}, {"token": "sixteen characters"}, {"extra": 1}, {"type": "move"},
        ):
            with self.assertRaises(protocol.ProtocolError, msg=change):
                protocol.parse_hello(json.dumps(HELLO | change))
        missing = dict(HELLO)
        del missing["token"]
        with self.assertRaises(protocol.ProtocolError):
            protocol.parse_hello(json.dumps(missing))

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


if __name__ == "__main__":
    unittest.main()
