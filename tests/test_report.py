import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from chorekit.report import build_report, human_size, render_csv, render_json, render_markdown


class ReportTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)
        (self.folder / "a.pdf").write_bytes(b"x" * 2048)
        (self.folder / "b.jpg").write_bytes(b"x" * 100)
        (self.folder / "c.jpg").write_bytes(b"x" * 300)
        (self.folder / "sub").mkdir()
        (self.folder / "sub" / "d.mp3").write_bytes(b"x" * 10)

    def tearDown(self):
        self._tmp.cleanup()

    def test_human_size(self):
        self.assertEqual(human_size(0), "0 B")
        self.assertEqual(human_size(512), "512 B")
        self.assertEqual(human_size(1536), "1.5 KB")
        self.assertEqual(human_size(5 * 1024 * 1024), "5.0 MB")

    def test_build_report_counts_and_sizes(self):
        report = build_report(self.folder)
        self.assertEqual(report["total_files"], 3)
        self.assertEqual(report["total_bytes"], 2448)
        names = [c["name"] for c in report["categories"]]
        self.assertEqual(names, ["Documents", "Images"])
        images = report["categories"][1]
        self.assertEqual((images["files"], images["bytes"]), (2, 400))

    def test_recursive_includes_subfolders(self):
        report = build_report(self.folder, recursive=True)
        self.assertEqual(report["total_files"], 4)
        self.assertIn("sub/d.mp3", [f["path"] for f in report["largest"]])

    def test_largest_is_sorted_and_limited(self):
        report = build_report(self.folder, top=2)
        self.assertEqual([f["path"] for f in report["largest"]], ["a.pdf", "c.jpg"])

    def test_markdown_has_table_and_largest(self):
        text = render_markdown(build_report(self.folder))
        self.assertIn("| Documents | 1 | 2.0 KB |", text)
        self.assertIn("1. a.pdf (2.0 KB)", text)

    def test_csv_is_valid(self):
        rows = list(csv.reader(io.StringIO(render_csv(build_report(self.folder)))))
        self.assertEqual(rows[0], ["category", "files", "bytes"])
        self.assertIn(["Images", "2", "400"], rows)

    def test_json_is_valid(self):
        data = json.loads(render_json(build_report(self.folder)))
        self.assertEqual(data["total_files"], 3)


if __name__ == "__main__":
    unittest.main()
