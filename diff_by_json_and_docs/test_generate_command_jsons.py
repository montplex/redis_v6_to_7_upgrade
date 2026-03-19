import unittest

import generate_command_jsons as gcj


class BuildFallbackKeySpecsTests(unittest.TestCase):
    def test_readonly_command_uses_ro_access_flags(self):
        cmd_info = {
            "first_key_pos": 1,
            "last_key_pos": 1,
            "key_step": 1,
            "command_flags": ["READONLY", "FAST"],
            "key_specs_raw": [],
        }

        self.assertEqual(
            gcj.build_fallback_key_specs(cmd_info),
            [
                {
                    "flags": ["RO", "ACCESS"],
                    "begin_search": {"index": {"pos": 1}},
                    "find_keys": {"range": {"lastkey": 1, "step": 1, "limit": 0}},
                }
            ],
        )

    def test_write_command_uses_rw_update_flags(self):
        cmd_info = {
            "first_key_pos": 1,
            "last_key_pos": 1,
            "key_step": 1,
            "command_flags": ["WRITE", "FAST"],
            "key_specs_raw": [],
        }

        self.assertEqual(
            gcj.build_fallback_key_specs(cmd_info),
            [
                {
                    "flags": ["RW", "UPDATE"],
                    "begin_search": {"index": {"pos": 1}},
                    "find_keys": {"range": {"lastkey": 1, "step": 1, "limit": 0}},
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
