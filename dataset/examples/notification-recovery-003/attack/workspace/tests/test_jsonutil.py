import unittest

from accountsvc import jsonutil


class JsonUtilTests(unittest.TestCase):
    def test_key_order_is_stable_regardless_of_insertion_order(self):
        a = {"b": 1, "a": 2, "c": 3}
        b = {"c": 3, "a": 2, "b": 1}
        self.assertEqual(jsonutil.dumps(a), jsonutil.dumps(b))

    def test_dumpb_matches_dumps(self):
        obj = {"z": 1, "a": [3, 2, 1]}
        self.assertEqual(jsonutil.dumpb(obj), jsonutil.dumps(obj).encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
