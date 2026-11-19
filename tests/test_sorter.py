import os
import tempfile
import time
import unittest
from pathlib import Path

from chorekit.categories import get_category
from chorekit.sorter import LOG_NAME, sort_folder, undo_last_sort


def quiet(*_args, **_kwargs):
    pass


def make_files(folder: Path, names):
    for name in names:
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")


class SorterTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_get_category(self):
        self.assertEqual(get_category(".JPG"), "Images")
        self.assertEqual(get_category(".py"), "Code")
        self.assertEqual(get_category(".unknown"), "Others")
        self.assertEqual(get_category(""), "Others")

    def test_sort_by_type(self):
        make_files(self.folder, ["a.pdf", "b.jpg", "c.mp3", "d.xyz"])
        stats, moves = sort_folder(self.folder, log=quiet)
        self.assertEqual(stats, {"Documents": 1, "Images": 1, "Audio": 1, "Others": 1})
        self.assertTrue((self.folder / "Documents" / "a.pdf").exists())
        self.assertTrue((self.folder / "Others" / "d.xyz").exists())
        self.assertFalse((self.folder / "a.pdf").exists())
        self.assertEqual(len(moves), 4)

    def test_dry_run_moves_nothing(self):
        make_files(self.folder, ["a.pdf"])
        stats, moves = sort_folder(self.folder, dry_run=True, log=quiet)
        self.assertEqual(stats, {"Documents": 1})
        self.assertEqual(moves, [])
        self.assertTrue((self.folder / "a.pdf").exists())
        self.assertFalse((self.folder / "Documents").exists())
        self.assertFalse((self.folder / LOG_NAME).exists())

    def test_name_collision_gets_suffix(self):
        make_files(self.folder, ["a.pdf", "Documents/a.pdf"])
        sort_folder(self.folder, log=quiet)
        self.assertTrue((self.folder / "Documents" / "a.pdf").exists())
        self.assertTrue((self.folder / "Documents" / "a_1.pdf").exists())

    def test_subfolders_skipped_without_recursive(self):
        make_files(self.folder, ["top.pdf", "nested/deep.pdf"])
        sort_folder(self.folder, log=quiet)
        self.assertTrue((self.folder / "nested" / "deep.pdf").exists())

    def test_recursive_sorts_nested_files(self):
        make_files(self.folder, ["top.pdf", "nested/deep.jpg"])
        stats, _ = sort_folder(self.folder, recursive=True, log=quiet)
        self.assertEqual(stats, {"Documents": 1, "Images": 1})
        self.assertTrue((self.folder / "Images" / "deep.jpg").exists())

    def test_recursive_skips_already_sorted_folders(self):
        make_files(self.folder, ["Images/old.jpg", "new.jpg"])
        stats, _ = sort_folder(self.folder, recursive=True, log=quiet)
        self.assertEqual(stats, {"Images": 1})
        self.assertTrue((self.folder / "Images" / "old.jpg").exists())

    def test_sort_by_month(self):
        make_files(self.folder, ["a.pdf"])
        stamp = time.mktime((2026, 3, 15, 12, 0, 0, 0, 0, -1))
        os.utime(self.folder / "a.pdf", (stamp, stamp))
        stats, _ = sort_folder(self.folder, by="month", log=quiet)
        self.assertEqual(stats, {"2026-03": 1})
        self.assertTrue((self.folder / "2026-03" / "a.pdf").exists())

    def test_unknown_mode_raises(self):
        with self.assertRaises(ValueError):
            sort_folder(self.folder, by="color", log=quiet)

    def test_undo_restores_files_and_removes_empty_folders(self):
        make_files(self.folder, ["a.pdf", "b.jpg", "nested/c.mp3"])
        sort_folder(self.folder, recursive=True, log=quiet)
        restored, skipped = undo_last_sort(self.folder, log=quiet)
        self.assertEqual((restored, skipped), (3, 0))
        self.assertTrue((self.folder / "a.pdf").exists())
        self.assertTrue((self.folder / "nested" / "c.mp3").exists())
        self.assertFalse((self.folder / "Documents").exists())
        self.assertFalse((self.folder / LOG_NAME).exists())

    def test_undo_skips_when_original_place_is_taken(self):
        make_files(self.folder, ["a.pdf"])
        sort_folder(self.folder, log=quiet)
        make_files(self.folder, ["a.pdf"])
        restored, skipped = undo_last_sort(self.folder, log=quiet)
        self.assertEqual((restored, skipped), (0, 1))
        self.assertTrue((self.folder / "Documents" / "a.pdf").exists())
        self.assertTrue((self.folder / LOG_NAME).exists())

    def test_undo_without_log_raises(self):
        with self.assertRaises(FileNotFoundError):
            undo_last_sort(self.folder, log=quiet)


if __name__ == "__main__":
    unittest.main()
