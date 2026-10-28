"""Regression coverage for malformed output from external CLI tools."""
import sys
import unittest

from phantom import run_command


class CommandOutputTests(unittest.TestCase):
    def test_non_utf8_output_is_replaced_instead_of_crashing(self):
        # External tools can emit arbitrary bytes even with LC_ALL=C.
        command = [
            sys.executable, "-c",
            "import sys; "
            "sys.stdout.buffer.write(bytes([65, 255, 66])); "
            "sys.stderr.buffer.write(bytes([67, 254, 68]))",
        ]
        code, output = run_command(command, timeout=5)
        self.assertEqual(code, 0)
        self.assertIn("A\ufffdB", output)
        self.assertIn("C\ufffdD", output)

    def test_valid_output_is_unchanged(self):
        code, output = run_command(
            [sys.executable, "-c", "print('command complete')"], timeout=5
        )
        self.assertEqual(code, 0)
        self.assertEqual(output, "command complete\n")


if __name__ == "__main__":
    unittest.main()
