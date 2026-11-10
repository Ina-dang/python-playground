"""공통 타이머 테스트. 모든 기록/복제 교재는 임시 폴더에서만 만듭니다."""
import contextlib
from datetime import datetime
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

SOURCE = Path(__file__).parent
CORE = SOURCE / "study_timer.py"


def load_core(path=CORE):
    module = types.ModuleType("fresh_shared_timer")
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


class TimerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "physical-ai-lab"
        self.root.mkdir()
        (self.root / "_shared").mkdir()
        shutil.copyfile(CORE, self.root / "_shared/study_timer.py")
        self.mod = load_core()
        self.lesson = "day22-goal-distance"
        self.date = "2026-11-10"
        self.name = "day22.ipynb"
        self.folder = self.make_lesson(self.lesson, self.name)
        self.timer = self.create()
        self.record = self.folder / ".study_timer" / self.timer.NAME
        self.old_cwd = Path.cwd()

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.assertTrue(self.base.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()))
        self.temp.cleanup()

    def make_lesson(self, lesson, notebook):
        folder = self.root / lesson
        folder.mkdir()
        (folder / notebook).write_text('{"cells": []}', encoding="utf-8")
        return folder

    def create(self, mod=None, **kw):
        return (mod or self.mod).create_timer(
            self.lesson, self.date, self.name,
            notebook_path=kw.pop("notebook_path", self.folder / self.name), **kw)

    def call(self, kind, *args, timer=None, **kw):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            (timer or self.timer).action(kind, *args, **kw)
        return output.getvalue()

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob("*") if p.is_file()}

    def cell(self, kind, cwd=None, answer="", cells=None):
        code = (cells or self.mod.notebook_cells(self.lesson, self.date, self.name))[kind]
        old = Path.cwd()
        try:
            os.chdir(cwd or self.folder)
            with mock.patch("builtins.input", return_value=answer), contextlib.redirect_stdout(io.StringIO()):
                scope = {}
                exec(code, scope)
            return scope
        finally:
            os.chdir(old)

    def test_start_restore_cancel_first_finish_and_idempotence(self):
        self.call("start")
        raw = self.record.read_bytes()
        self.call("start")
        self.assertEqual(raw, self.record.read_bytes())
        fresh = self.create(mod=load_core())
        self.call("start", timer=fresh)
        self.assertEqual(raw, self.record.read_bytes())
        self.call("finish", "", timer=fresh)
        self.assertEqual(raw, self.record.read_bytes())
        self.call("finish", "종료", timer=fresh)
        done = self.record.read_bytes()
        self.assertIsNotNone(json.loads(done)["end"])
        self.call("finish", "종료")
        self.assertEqual(done, self.record.read_bytes())

    def test_finish_without_start_and_cancel_do_not_create_files(self):
        before = self.snapshot()
        self.call("finish", "")
        self.call("finish", "종료")
        self.call("reset", "초기화", enabled=True)
        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.record.parent.exists())

    def test_v1_compatibility_and_fixed_lesson_date(self):
        self.record.parent.mkdir()
        obj = {"version": 1, "lesson": self.lesson, "date": self.date,
               "start": "2026-11-10T23:59:59+09:00", "end": "2026-11-11T00:00:01+09:00"}
        self.record.write_text(json.dumps(obj), encoding="utf-8")
        raw = self.record.read_bytes()
        output = self.call("start")
        self.assertIn("2초", output)
        self.assertIn("KST", output)
        self.assertIn("벽시계", output)
        self.assertEqual(raw, self.record.read_bytes())
        self.assertEqual(self.record.name, self.date + "-" + self.lesson + ".json")

    def test_malformed_records_are_preserved_for_all_actions(self):
        self.call("start")
        good = json.loads(self.record.read_bytes())
        bad = [b"{broken", b"\xff",
               json.dumps({**good, "lesson": "other"}).encode(),
               json.dumps({**good, "date": "2026-11-11"}).encode(),
               json.dumps({**good, "version": True}).encode(),
               json.dumps({**good, "extra": 1}).encode(),
               json.dumps({**good, "start": "2026-11-10T00:00:00"}).encode(),
               json.dumps({**good, "start": "2026-11-10T00:00:00+00:00"}).encode(),
               json.dumps({**good, "start": "2026-11-11T00:00:00+09:00",
                           "end": "2026-11-10T00:00:00+09:00"}).encode(),
               b'{"version":1,"version":1}']
        for raw in bad:
            self.record.write_bytes(raw)
            before = self.snapshot()
            for action, kwargs in [("start", {}), ("finish", {"answer": "종료"}),
                                   ("reset", {"answer": "초기화", "enabled": True})]:
                self.call(action, **kwargs)
                self.assertEqual(raw, self.record.read_bytes())
                self.assertEqual(before, self.snapshot())

    def test_backward_clock_is_rejected(self):
        self.call("start")
        obj = json.loads(self.record.read_bytes())
        obj["start"] = "9999-01-01T00:00:00+09:00"
        self.record.write_text(json.dumps(obj), encoding="utf-8")
        raw = self.record.read_bytes()
        self.assertIn("시계", self.call("finish", "종료"))
        self.assertEqual(raw, self.record.read_bytes())

    def test_reset_requires_enable_and_confirmation_then_verified_backup(self):
        self.call("start")
        raw = self.record.read_bytes()
        for enabled, answer in [(False, "초기화"), (True, ""), (True, "yes")]:
            self.call("reset", answer, enabled=enabled)
            self.assertEqual(raw, self.record.read_bytes())
        self.call("reset", "초기화", enabled=True)
        self.assertFalse(self.record.exists())
        self.assertEqual([raw], [p.read_bytes() for p in self.record.parent.glob("*.backup")])
        self.call("start")
        self.assertTrue(self.record.exists())

    def test_backup_name_collision_never_overwrites(self):
        self.call("start")
        raw = self.record.read_bytes()
        backup = self.record.parent / (self.timer.NAME + ".collision.backup")
        backup.write_bytes(b"existing")
        with mock.patch.object(self.mod.uuid, "uuid4", return_value=types.SimpleNamespace(hex="collision")):
            self.call("reset", "초기화", enabled=True)
        self.assertEqual(raw, self.record.read_bytes())
        self.assertEqual(b"existing", backup.read_bytes())

    def test_write_and_backup_failure_preserve_original(self):
        self.call("start")
        raw = self.record.read_bytes()
        with mock.patch.object(self.mod.os, "replace", side_effect=OSError("simulated")):
            self.call("finish", "종료")
        self.assertEqual(raw, self.record.read_bytes())

    def test_reset_unlink_failure_preserves_record_and_backup(self):
        self.call("start")
        raw = self.record.read_bytes()
        original = Path.unlink
        def fail_record(path, *args, **kwargs):
            if path == self.record:
                raise OSError("simulated record unlink failure")
            return original(path, *args, **kwargs)
        with mock.patch.object(Path, "unlink", fail_record):
            self.call("reset", "초기화", enabled=True)
        self.assertEqual(raw, self.record.read_bytes())
        self.assertIn(raw, [p.read_bytes() for p in self.record.parent.glob("*.backup")])
        self.assertFalse(list(self.record.parent.glob("*.tmp")))
        with mock.patch.object(self.mod.os, "fsync", side_effect=OSError("simulated")):
            self.call("reset", "초기화", enabled=True)
        self.assertEqual(raw, self.record.read_bytes())

    def test_existing_finish_temp_is_not_removed(self):
        self.call("start")
        raw = self.record.read_bytes()
        temp = self.record.parent / (self.timer.NAME + ".collision.tmp")
        temp.write_bytes(b"prior evidence")
        with mock.patch.object(self.mod.uuid, "uuid4", return_value=types.SimpleNamespace(hex="collision")):
            self.call("finish", "종료")
        self.assertEqual(b"prior evidence", temp.read_bytes())
        self.assertEqual(raw, self.record.read_bytes())

    def test_lock_is_shared_by_start_finish_and_reset(self):
        self.record.parent.mkdir()
        lock = self.record.parent / (self.timer.NAME + ".lock")
        lock.write_bytes(b"other owner")
        self.call("start")
        self.assertFalse(self.record.exists())
        lock.unlink()
        self.call("start")
        raw = self.record.read_bytes()
        lock.write_bytes(b"other owner")
        self.call("finish", "종료")
        self.call("reset", "초기화", enabled=True)
        self.assertEqual(raw, self.record.read_bytes())
        self.assertEqual(b"other owner", lock.read_bytes())

    def test_cancel_and_finished_replay_have_no_writes_or_prompt(self):
        self.cell("start")
        before = self.snapshot()
        original_open = Path.open
        def read_only_open(path, mode="r", *a, **kw):
            if any(x in mode for x in "wax+"):
                raise AssertionError("Unexpected write")
            return original_open(path, mode, *a, **kw)
        with mock.patch.object(Path, "open", read_only_open), \
             mock.patch.object(Path, "mkdir", side_effect=AssertionError("mkdir")), \
             mock.patch.object(Path, "unlink", side_effect=AssertionError("unlink")), \
             mock.patch.object(self.mod.os, "replace", side_effect=AssertionError("replace")):
            self.cell("finish", answer="")
        self.assertEqual(before, self.snapshot())
        self.cell("finish", answer="종료")
        before = self.snapshot()
        with mock.patch("builtins.input", side_effect=AssertionError("No prompt")), \
             mock.patch.object(Path, "open", read_only_open), \
             mock.patch.object(Path, "mkdir", side_effect=AssertionError("mkdir")), \
             mock.patch.object(Path, "unlink", side_effect=AssertionError("unlink")), \
             contextlib.redirect_stdout(io.StringIO()):
            exec(self.mod.notebook_cells(self.lesson, self.date, self.name)["finish"], {})
        self.assertEqual(before, self.snapshot())
        self.assertFalse(list(self.root.rglob("__pycache__")))

    def test_old_finish_confirmation_cannot_finish_new_session(self):
        class Clock(datetime):
            ticks = iter(["2026-11-10T10:00:00+09:00", "2026-11-10T10:00:01+09:00"])
            @classmethod
            def now(cls, tz=None):
                return cls.fromisoformat(next(cls.ticks))
        with mock.patch.object(self.mod, "datetime", Clock):
            self.call("start")
            saved = []
            def while_prompting(_):
                self.call("reset", "초기화", enabled=True)
                self.call("start")
                saved.append(self.record.read_bytes())
                return "종료"
            with mock.patch("builtins.input", side_effect=while_prompting), contextlib.redirect_stdout(io.StringIO()):
                self.timer.finish_interactive()
            self.assertEqual(saved[0], self.record.read_bytes())
            self.assertIsNone(json.loads(saved[0])["end"])


    @unittest.skipUnless(os.name == "nt", "Windows read-handle conflict")
    def test_transient_reader_conflict_retries_atomic_finish(self):
        self.call("start")
        reader = self.record.open("rb")
        native_replace = self.mod.os.replace
        attempts = []
        def replace(source, destination):
            attempts.append(True)
            try:
                return native_replace(source, destination)
            except PermissionError:
                # 첫 충돌이 발생한 뒤 경쟁 독자가 읽기를 마친 상황입니다.
                reader.close()
                raise
        try:
            with mock.patch.object(self.mod.os, "replace", side_effect=replace):
                self.call("finish", "종료")
            self.assertGreaterEqual(len(attempts), 2)
            self.assertIsNotNone(json.loads(self.record.read_bytes())["end"])
        finally:
            reader.close()

    @unittest.skipUnless(os.name == "nt", "Windows read-handle conflict")
    def test_persistent_reader_conflict_is_bounded_and_preserves_record(self):
        self.call("start")
        original = self.record.read_bytes()
        error = PermissionError("simulated sharing conflict")
        error.winerror = 5
        with mock.patch.object(self.mod.os, "replace", side_effect=error) as replace, \
             mock.patch.object(self.mod.time, "sleep"):
            self.call("finish", "종료")
        self.assertEqual(6, replace.call_count)
        self.assertEqual(original, self.record.read_bytes())
        self.assertFalse(list(self.record.parent.glob("*.tmp")))

    @unittest.skipUnless(os.name == "nt", "Windows read-handle conflict")
    def test_record_changed_between_publish_retries_is_not_overwritten(self):
        self.call("start")
        changed = []
        def replace(_source, _destination):
            obj = json.loads(self.record.read_bytes())
            obj["start"] = "2026-11-10T01:00:00+09:00"
            self.record.write_text(json.dumps(obj), encoding="utf-8")
            changed.append(self.record.read_bytes())
            error = PermissionError("simulated sharing conflict")
            error.winerror = 5
            raise error
        with mock.patch.object(self.mod.os, "replace", side_effect=replace) as replacement, \
             mock.patch.object(self.mod.time, "sleep"):
            self.call("finish", "종료")
        self.assertEqual(1, replacement.call_count)
        self.assertEqual(changed[0], self.record.read_bytes())
        self.assertIsNone(json.loads(changed[0])["end"])
        self.assertFalse(list(self.record.parent.glob("*.tmp")))

    def test_concurrent_finish_processes_keep_first_end(self):
        self.call("start")
        script = ("from pathlib import Path; import sys; ns={'__name__':'timer_child'};"
                  "exec(compile(Path(sys.argv[1]).read_bytes(),sys.argv[1],'exec'),ns);"
                  "ns['create_timer'](sys.argv[2],sys.argv[3],sys.argv[4],"
                  "notebook_path=sys.argv[5]).action('finish','종료')")
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        workers = [subprocess.Popen(
            [sys.executable, "-B", "-c", script, str(CORE), self.lesson, self.date,
             self.name, str(self.folder / self.name)], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=env) for _ in range(4)]
        for worker in workers:
            _, err = worker.communicate(timeout=20)
            self.assertEqual(0, worker.returncode, err.decode(errors="replace"))
        raw = self.record.read_bytes()
        self.assertIsNotNone(json.loads(raw)["end"])
        self.call("finish", "종료")
        self.assertEqual(raw, self.record.read_bytes())

    def test_root_and_lesson_cwd_discovery(self):
        for cwd in [self.root, self.folder]:
            timer = self.mod.create_timer(self.lesson, self.date, self.name, cwd=cwd)
            self.assertEqual(self.folder, timer.lesson_path)
        with self.assertRaises(self.mod.TimerError):
            self.mod.create_timer(self.lesson, self.date, self.name, cwd=self.base)

    def test_ambiguous_paths_fail_without_writes(self):
        nested = self.folder / self.lesson
        nested.mkdir()
        (nested / self.name).write_text("{}")
        before = self.snapshot()
        with self.assertRaises(self.mod.TimerError):
            self.mod.create_timer(self.lesson, self.date, self.name, cwd=self.folder)
        self.cell("start")
        self.assertEqual(before, self.snapshot())

    def test_invalid_metadata_and_explicit_paths_rejected(self):
        for lesson, date, name in [("../bad", self.date, self.name), (self.lesson, "2026-11-31", self.name),
                                   (self.lesson, self.date, "../outside.ipynb")]:
            with self.assertRaises(self.mod.TimerError):
                self.mod.create_timer(lesson, date, name, notebook_path=self.folder / self.name)
        with self.assertRaises(self.mod.TimerError):
            self.create(notebook_path=self.folder / ".." / self.lesson / self.name)
        with self.assertRaises(self.mod.TimerError):
            self.create(notebook_path=self.folder / "missing.ipynb")
        before = self.snapshot()
        self.call("not-an-action")
        self.assertEqual(before, self.snapshot())

    def test_two_lessons_share_code_without_state_or_records_mixing(self):
        other_id, other_name, other_date = "day23-next-lesson", "day23.ipynb", "2026-11-11"
        other = self.make_lesson(other_id, other_name)
        b = self.mod.create_timer(other_id, other_date, other_name, notebook_path=other / other_name)
        self.call("start")
        a_raw = self.record.read_bytes()
        self.call("start", timer=b)
        b_record = other / ".study_timer" / b.NAME
        b_raw = b_record.read_bytes()
        self.call("finish", "종료", timer=b)
        self.assertEqual(a_raw, self.record.read_bytes())
        self.call("reset", "초기화", enabled=True)
        self.assertTrue(b_record.exists())
        self.assertNotEqual(a_raw, b_raw)
        self.assertFalse((self.root / "_shared/.study_timer").exists())

    def test_all_cells_independent_at_root_or_lesson_and_reset_disabled(self):
        for cwd in [self.root, self.folder]:
            self.cell("start", cwd=cwd)
            before = self.snapshot()
            self.cell("reset", cwd=cwd)
            self.assertEqual(before, self.snapshot())
            self.cell("finish", cwd=cwd, answer="")
            self.assertEqual(before, self.snapshot())
        self.cell("finish", cwd=self.root, answer="종료")
        before = self.snapshot()
        self.cell("finish", cwd=self.folder)
        self.assertEqual(before, self.snapshot())
        reset_code = self.mod.notebook_cells(self.lesson, self.date, self.name)["reset"].replace("enabled = False", "enabled = True")
        self.cell("reset", cwd=self.root, answer="초기화", cells={"reset": reset_code})
        self.assertFalse(self.record.exists())
        self.assertTrue(list(self.record.parent.glob("*.backup")))
        self.assertFalse(list(self.root.rglob("__pycache__")))

    def test_record_reparse_and_timer_folder_reparse_rejected(self):
        self.call("start")
        raw = self.record.read_bytes()
        original = Path.lstat
        for target in [self.record, self.record.parent]:
            def fake(path, *a, **kw):
                result = original(path, *a, **kw)
                if path == target:
                    return types.SimpleNamespace(st_mode=result.st_mode, st_file_attributes=0x400)
                return result
            with mock.patch.object(Path, "lstat", fake):
                self.call("finish", "종료")
                self.call("reset", "초기화", enabled=True)
            self.assertEqual(raw, self.record.read_bytes())

    def test_helper_reparse_rejected_before_read_or_execution(self):
        helper = self.root / "_shared/study_timer.py"
        helper.write_text("raise AssertionError('must not execute')", encoding="utf-8")
        original = Path.lstat
        def fake(path, *a, **kw):
            result = original(path, *a, **kw)
            if path == helper:
                return types.SimpleNamespace(st_mode=result.st_mode, st_file_attributes=0x400)
            return result
        with mock.patch.object(Path, "lstat", fake):
            self.cell("start")
        self.assertFalse(self.record.parent.exists())

    def test_helper_changed_to_reparse_while_reading_is_not_executed(self):
        helper = self.root / "_shared/study_timer.py"
        original_read = Path.read_bytes
        original_stat = Path.lstat
        changed = []
        def read(path):
            if path == helper:
                changed.append(True)
                return b"raise AssertionError('unsafe helper executed')"
            return original_read(path)
        def info(path, *args, **kwargs):
            result = original_stat(path, *args, **kwargs)
            if path == helper and changed:
                return types.SimpleNamespace(st_mode=result.st_mode, st_file_attributes=0x400)
            return result
        with mock.patch.object(Path, "read_bytes", read), mock.patch.object(Path, "lstat", info):
            self.cell("start")
        self.assertFalse(self.record.parent.exists())

    def test_direct_constructor_cannot_bypass_metadata_checks(self):
        with self.assertRaises(self.mod.TimerError):
            self.mod.StudyTimer("../bad", self.date, self.name, self.folder / self.name)

    def test_old_finish_rejects_recreated_session_even_with_same_start_time(self):
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls.fromisoformat("2026-11-10T10:00:00+09:00")
        with mock.patch.object(self.mod, "datetime", Clock):
            self.call("start")
            def recreate(_):
                self.call("reset", "초기화", enabled=True)
                self.call("start")
                return "종료"
            with mock.patch("builtins.input", side_effect=recreate), contextlib.redirect_stdout(io.StringIO()):
                self.timer.finish_interactive()
        self.assertIsNone(json.loads(self.record.read_bytes())["end"])

    def test_helper_directory_and_ancestor_reparse_rejected(self):
        original = Path.lstat
        for target in [self.root / "_shared", self.root, self.folder, self.folder / self.name]:
            def fake(path, *a, **kw):
                result = original(path, *a, **kw)
                if path == target:
                    return types.SimpleNamespace(st_mode=result.st_mode, st_file_attributes=0x400)
                return result
            with mock.patch.object(Path, "lstat", fake):
                self.cell("start")
            self.assertFalse(self.record.parent.exists())

    def test_real_symlinked_timer_folder_rejected(self):
        outside = self.base / "outside"
        outside.mkdir()
        try:
            self.record.parent.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("Windows symlink creation unavailable; reparse simulation is covered")
        self.call("start")
        self.assertEqual([], list(outside.iterdir()))

    @unittest.skipUnless(os.name == "nt", "Windows junction test")
    def test_real_windows_junction_rejected(self):
        outside = self.base / "junction-target"
        outside.mkdir()
        junction = self.record.parent
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode:
            self.skipTest("Windows junction creation unavailable; reparse simulation is covered")
        try:
            self.call("start")
            self.assertEqual([], list(outside.iterdir()))
        finally:
            junction.rmdir()

    def test_replaced_path_is_revalidated_after_binding(self):
        self.call("start")
        raw = self.record.read_bytes()
        original = Path.lstat
        def fake(path, *a, **kw):
            result = original(path, *a, **kw)
            if path == self.folder:
                return types.SimpleNamespace(st_mode=result.st_mode, st_file_attributes=0x400)
            return result
        with mock.patch.object(Path, "lstat", fake):
            self.call("finish", "종료")
        self.assertEqual(raw, self.record.read_bytes())


if __name__ == "__main__":
    unittest.main()

