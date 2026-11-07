"""별도 임시 폴더에서만 타이머를 검증합니다: python -m unittest test_timer"""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from unittest import mock

SOURCE = Path(__file__).parent

def load(path):
    spec = importlib.util.spec_from_file_location('fresh_timer', path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

class TimerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'day19-time-distance-graphs'
        self.root.mkdir()
        for name in ['study_timer.py', 'day19.ipynb']:
            shutil.copy2(SOURCE/name, self.root/name)
        self.old = Path.cwd(); os.chdir(self.root)
        self.mod = load(self.root/'study_timer.py')
        self.folder = self.root/'.study_timer'; self.record = self.folder/self.mod.NAME

    def tearDown(self):
        os.chdir(self.old); self.temp.cleanup()

    def call(self, kind, *args, mod=None, **kwargs):
        out=io.StringIO()
        with contextlib.redirect_stdout(out): (mod or self.mod).action(kind, *args, **kwargs)
        return out.getvalue()

    def test_start_resume_cancel_finish_and_restart(self):
        self.call('finish', '')
        self.assertFalse(self.folder.exists())
        self.call('finish', '종료')
        self.assertFalse(self.folder.exists())
        self.call('start'); original=self.record.read_bytes()
        self.call('start'); self.assertEqual(original,self.record.read_bytes())
        fresh=load(self.root/'study_timer.py')
        self.call('start',mod=fresh); self.assertEqual(original,self.record.read_bytes())
        self.call('finish','',mod=fresh); self.assertEqual(original,self.record.read_bytes())
        self.call('finish','종료',mod=fresh); finished=self.record.read_bytes()
        self.assertIsNotNone(json.loads(finished)['end'])
        self.call('finish','종료',mod=load(self.root/'study_timer.py'))
        self.assertEqual(finished,self.record.read_bytes())

    def test_bad_records_preserved(self):
        self.call('start'); initial=json.loads(self.record.read_bytes())
        variants=[b'{broken',b'\xff', json.dumps({**initial,'lesson':'other'}).encode(), json.dumps({**initial,'version':2}).encode(), json.dumps({**initial,'extra':1}).encode(), json.dumps({**initial,'start':'2026-11-07T00:00:00'}).encode(), json.dumps({**initial,'start':'2026-11-08T00:00:00+09:00','end':'2026-11-07T00:00:00+09:00'}).encode()]
        for raw in variants:
            self.record.write_bytes(raw)
            self.call('start'); self.assertEqual(raw,self.record.read_bytes())
            self.call('finish','종료'); self.assertEqual(raw,self.record.read_bytes())
            self.call('reset','초기화',enabled=True); self.assertEqual(raw,self.record.read_bytes())

    def test_negative_now_and_cross_midnight(self):
        self.call('start'); obj=json.loads(self.record.read_bytes())
        obj['start']='9999-01-01T00:00:00+09:00'; self.record.write_text(json.dumps(obj))
        raw=self.record.read_bytes(); output=self.call('finish','종료')
        self.assertIn('시계',output); self.assertEqual(raw,self.record.read_bytes())
        obj['start']='2026-11-06T23:59:59+09:00'; obj['end']='2026-11-07T00:00:01+09:00'
        self.record.write_text(json.dumps(obj)); out=self.call('start',mod=load(self.root/'study_timer.py'))
        self.assertIn('2초',out)

    def test_reset_confirmation_and_collision(self):
        self.call('start'); raw=self.record.read_bytes()
        self.call('reset','초기화',enabled=False); self.call('reset','',enabled=True)
        self.assertEqual(raw,self.record.read_bytes())
        class Fixed: hex='collision'
        backup=self.folder/(self.mod.NAME+'.collision.backup'); backup.write_bytes(b'existing')
        with mock.patch.object(self.mod.uuid,'uuid4',return_value=Fixed()): self.call('reset','초기화',enabled=True)
        self.assertEqual(raw,self.record.read_bytes()); self.assertEqual(b'existing',backup.read_bytes())
        self.call('reset','초기화',enabled=True)
        self.assertFalse(self.record.exists())
        self.assertIn(raw,[p.read_bytes() for p in self.folder.glob('*.backup')])
        self.call('start'); self.assertTrue(self.record.exists())

    def test_write_conflict_and_failure(self):
        self.call('start'); raw=self.record.read_bytes()
        lock=self.folder/(self.mod.NAME+'.lock'); lock.write_bytes(b'other process')
        self.call('finish','종료'); self.assertEqual(raw,self.record.read_bytes()); self.assertEqual(b'other process',lock.read_bytes())
        lock.unlink()
        with mock.patch.object(self.mod.os,'replace',side_effect=OSError('fail')):
            self.call('finish','종료')
        self.assertEqual(raw,self.record.read_bytes())
        with mock.patch.object(self.mod.Path,'unlink',side_effect=OSError('fail')):
            self.call('reset','초기화',enabled=True)
        self.assertEqual(raw,self.record.read_bytes())
        self.assertIn(raw,[p.read_bytes() for p in self.folder.glob('*.backup')])

    def test_existing_finish_temp_is_not_deleted(self):
        self.call('start'); raw=self.record.read_bytes()
        class Fixed: hex='collision'
        temp=self.folder/(self.mod.NAME+'.collision.tmp'); temp.write_bytes(b'prior evidence')
        with mock.patch.object(self.mod.uuid,'uuid4',return_value=Fixed()):
            self.call('finish','종료')
        self.assertEqual(temp.read_bytes(),b'prior evidence')
        self.assertEqual(self.record.read_bytes(),raw)

    def test_helper_symlink_rejected_before_execution(self):
        # Windows may disallow creating links; simulate the link check on the exact helper path.
        helper=self.root/'study_timer.py'; marker=self.root/'should-not-exist'
        helper.write_text("from pathlib import Path\nPath('should-not-exist').write_text('bad')",encoding='utf8')
        nb=json.loads((self.root/'day19.ipynb').read_text(encoding='utf8'))
        bottom=[c for c in nb['cells'] if c['cell_type']=='code'][-1]
        original=Path.is_symlink
        with mock.patch.object(Path,'is_symlink',lambda p: True if p==helper else original(p)), \
             mock.patch('builtins.input',return_value=''), contextlib.redirect_stdout(io.StringIO()):
            exec(''.join(bottom['source']),{})
        self.assertFalse(marker.exists())

    def test_cancel_and_finished_rerun_have_no_cache_or_writes(self):
        self.call('start'); raw=self.record.read_bytes()
        cache=self.root/'__pycache__'
        if cache.exists(): shutil.rmtree(cache)
        nb=json.loads((self.root/'day19.ipynb').read_text(encoding='utf8'))
        bottom=[c for c in nb['cells'] if c['cell_type']=='code'][-1]
        with mock.patch('builtins.input',return_value=''), contextlib.redirect_stdout(io.StringIO()):
            exec(''.join(bottom['source']),{})
        self.assertEqual(raw,self.record.read_bytes()); self.assertFalse(cache.exists())
        self.call('finish','종료'); finished=self.record.read_bytes(); out=io.StringIO()
        before={p.name:p.read_bytes() for p in self.folder.iterdir()}
        with mock.patch('builtins.input',side_effect=AssertionError('must not prompt')), contextlib.redirect_stdout(out):
            exec(''.join(bottom['source']),{})
        self.assertIn('종료 시각',out.getvalue()); self.assertEqual(finished,self.record.read_bytes())
        self.assertIn('경과 시간',out.getvalue())
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.folder.iterdir()})
        self.assertFalse(cache.exists())

    def test_old_finish_confirmation_cannot_end_new_start(self):
        class Clock(datetime):
            ticks=iter(['2026-11-07T10:00:00+09:00','2026-11-07T10:00:01+09:00'])
            @classmethod
            def now(cls, tz=None): return cls.fromisoformat(next(cls.ticks))
        with mock.patch.object(self.mod, 'datetime', Clock):
            self.call('start')
            new_session=[]
            def input_during_new_session(_prompt):
                self.call('reset','초기화',enabled=True)
                self.call('start')
                new_session.append(self.record.read_bytes())
                return '종료'
            out=io.StringIO()
            with mock.patch('builtins.input',side_effect=input_during_new_session), contextlib.redirect_stdout(out):
                self.mod.finish_interactive()
            self.assertEqual(self.record.read_bytes(),new_session[0])
            self.assertIsNone(json.loads(new_session[0])['end'])
            self.assertIn('새 측정',out.getvalue())

    def test_wrong_working_directory(self):
        os.chdir(self.root.parent.parent)
        output=self.call('start'); self.assertIn('폴더',output); self.assertFalse(self.folder.exists())

    def test_ambiguous_directory(self):
        nested=self.root/self.root.name; nested.mkdir()
        for name in ['study_timer.py','day19.ipynb']: shutil.copy2(self.root/name,nested/name)
        output=self.call('start'); self.assertIn('폴더',output); self.assertFalse(self.folder.exists())

    def test_concurrent_finish_processes(self):
        self.call('start')
        script="import study_timer; study_timer.action('finish', '종료')"
        workers=[subprocess.Popen([sys.executable,'-c',script],cwd=self.root,stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(4)]
        for worker in workers:
            _, err=worker.communicate(timeout=20)
            self.assertEqual(worker.returncode,0,err.decode(errors='replace'))
        obj=json.loads(self.record.read_bytes()); self.assertIsNotNone(obj['end'])
        finished=self.record.read_bytes(); self.call('finish','종료'); self.assertEqual(finished,self.record.read_bytes())

    def test_symlinked_timer_folder(self):
        target=self.root.parent/'elsewhere'; target.mkdir()
        try: self.folder.symlink_to(target, target_is_directory=True)
        except OSError: self.skipTest('Windows did not allow symlink creation')
        output=self.call('start'); self.assertIn('바로가기',output); self.assertEqual([],list(target.iterdir()))

    def test_notebook_cells_independent(self):
        nb=json.loads((self.root/'day19.ipynb').read_text(encoding='utf-8'))
        cells=[c for c in nb['cells'] if c['cell_type']=='code']
        self.assertTrue(all(not c['outputs'] and c['execution_count'] is None for c in cells))
        with contextlib.redirect_stdout(io.StringIO()): exec(''.join(cells[0]['source']),{})
        self.assertTrue(self.record.exists())
        with mock.patch('builtins.input',return_value='종료'), contextlib.redirect_stdout(io.StringIO()):
            exec(''.join(cells[-1]['source']),{})
        self.assertIsNotNone(json.loads(self.record.read_bytes())['end'])

if __name__=='__main__': unittest.main()
