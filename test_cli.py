import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from chorekit.cli import main
from tests.test_rates import GOOD, fake_response


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)
        (self.folder / "a.pdf").write_text("x")

    def tearDown(self):
        self._tmp.cleanup()

    def test_sort_then_undo(self):
        code, out, _ = run("sort", str(self.folder))
        self.assertEqual(code, 0)
        self.assertIn("Documents: 1 file(s)", out)
        self.assertTrue((self.folder / "Documents" / "a.pdf").exists())

        code, out, _ = run("undo", str(self.folder))
        self.assertEqual(code, 0)
        self.assertTrue((self.folder / "a.pdf").exists())

    def test_sort_missing_folder(self):
        code, _, err = run("sort", str(self.folder / "nope"))
        self.assertEqual(code, 1)
        self.assertIn("Folder not found", err)

    def test_undo_without_log(self):
        code, _, err = run("undo", str(self.folder))
        self.assertEqual(code, 1)
        self.assertIn("No undo log", err)

    def test_report_to_file(self):
        target = self.folder / "report.md"
        code, out, _ = run("report", str(self.folder), "--output", str(target))
        self.assertEqual(code, 0)
        self.assertIn("| Documents | 1 |", target.read_text(encoding="utf-8"))

    @mock.patch("chorekit.rates.requests.get")
    def test_rates_with_symbols_and_convert(self, get):
        get.return_value = fake_response()
        target = self.folder / "r.json"
        code, out, _ = run("rates", "--symbols", "EUR", "--convert", "100", "--to", "EUR", "--output", str(target))
        self.assertEqual(code, 0)
        self.assertIn("Got 1 exchange rates", out)
        self.assertIn("100 USD = 90.00 EUR", out)
        self.assertTrue(target.exists())

    def test_rates_convert_needs_target(self):
        code, _, err = run("rates", "--convert", "100")
        self.assertEqual(code, 1)
        self.assertIn("--convert needs --to", err)


if __name__ == "__main__":
    unittest.main()
