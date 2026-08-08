from pathlib import Path
import sys
import tempfile
import unittest


RELEASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RELEASE / "experiments" / "state_policy"))

from run_fork_case import discover_new_stamp, sha256  # noqa: E402


class RunForkCaseTest(unittest.TestCase):
    def test_sha256(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.bin"
            path.write_bytes(b"abc")
            self.assertEqual(
                sha256(path),
                "BA7816BF8F01CFEA414140DE5DAE2223"
                "B00361A396177A9CB410FF61F20015AD",
            )

    def test_discover_new_stamp(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "old_summary.json").write_text("{}", encoding="utf-8")
            before = {"old_summary.json"}
            (path / "new_stamp_summary.json").write_text("{}", encoding="utf-8")
            self.assertEqual(discover_new_stamp(path, before), "new_stamp")

    def test_discover_requires_exactly_one(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "exactly one"):
                discover_new_stamp(Path(directory), set())


if __name__ == "__main__":
    unittest.main()
